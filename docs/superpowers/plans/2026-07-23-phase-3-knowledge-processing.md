# Phase 3: 知识处理增强

**Feature Name:** 企业级知识管理平台 — 知识处理增强
**Goal:** 文件监控自动触发处理、LLM 自动分类、知识分类管理、审批工作流
**Architecture:** enterprise-km-classifier (FastAPI, 端口5057) + enterprise-km-server 扩展
**Tech Stack:** FastAPI, httpx (调用 Open Notebook API), Ollama (LLM 分类)
**Global Constraints:** 不改 Open Notebook 核心代码；通过 API 调用；Ollama 在 192.168.66.163:11434

---

## File Structure

```
enterprise-km/
├── classifier/
│   ├── main.py                    # FastAPI 入口 (已有)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # OLLAMA_URL, OPEN_NOTEBOOK_URL
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classifier.py          # LLM 分类引擎
│   │   └── file_watcher.py        # MinIO 事件监听
│   └── api/
│       ├── __init__.py
│       ├── classify.py            # POST /classify, /batch-classify
│       └── categories.py          # 知识分类树 CRUD
├── server/
│   ├── api/
│   │   ├── categories.py          # 知识分类管理 API
│   │   └── approvals.py           # 审批工作流 API
│   └── domain/
│       ├── category.py            # KnowledgeCategory 模型
│       └── approval.py            # Approval 模型
```

---

## T3.1: 文件监控服务

### Task 3.1.1: 创建 classifier 配置和文件监控

**Files:** `classifier/core/config.py`, `classifier/services/file_watcher.py`, `classifier/api/__init__.py`

```python
# classifier/core/config.py
import os
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.66.163:11434")
OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_URL", "http://192.168.66.40:5055")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://192.168.66.40:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "enterprise-km")
```

```python
# classifier/services/file_watcher.py
import httpx
from loguru import logger
from classifier.core.config import OPEN_NOTEBOOK_URL, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET

async def process_new_file(file_key: str, user_id: str = None):
    """当 MinIO 有新文件时，触发 Open Notebook 处理"""
    # 1. 生成 MinIO 预签名 URL
    file_url = f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{file_key}"
    
    # 2. 调用 Open Notebook API 添加 source
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OPEN_NOTEBOOK_URL}/api/sources",
            json={
                "url": file_url,
                "title": file_key.split("/")[-1],
                "type": "file",
                "metadata": {"user_id": user_id, "source": "minio_sync"}
            },
            timeout=60
        )
        if resp.status_code == 200:
            source = resp.json()
            logger.info(f"Source created: {source.get('id')} for {file_key}")
            
            # 3. 触发处理
            process_resp = await client.post(
                f"{OPEN_NOTEBOOK_URL}/api/sources/{source['id']}/process",
                timeout=300
            )
            logger.info(f"Process result: {process_resp.status_code}")
            return source
        else:
            logger.error(f"Failed to create source: {resp.text}")
            return None

async def scan_minio_bucket():
    """扫描 MinIO bucket 中未处理的文件"""
    # 使用 MinIO events 或定期扫描
    pass
```

## T3.2: 自动分类引擎

### Task 3.2.1: LLM 分类服务

**Files:** `classifier/services/classifier.py`

```python
import httpx
import json
from loguru import logger
from classifier.core.config import OLLAMA_URL

CLASSIFICATION_PROMPT = """你是一个企业知识分类专家。请分析以下文档内容，将其归类到最合适的知识类别中。

可选类别：
- 技术研发 (算法、架构、代码、技术方案)
- 质量管理 (故障分析、8D报告、FMEA、质量控制)
- 生产工艺 (工艺流程、SOP、设备维护)
- 项目管理 (项目计划、进度报告、风险管理)
- 产品设计 (需求文档、设计规范、图纸)
- 市场销售 (市场分析、客户需求、竞品分析)
- 人力资源 (培训材料、制度规范、考核)
- 财务管理 (预算、成本分析、报表)
- 供应链 (采购、物流、库存)
- 其他

文档内容：
{content}

请返回 JSON 格式：
{{"category": "类别名", "confidence": 0.0-1.0, "keywords": ["关键词1", "关键词2"], "summary": "一句话摘要"}}
"""

async def classify_document(content: str, model: str = "qwen2.5:7b") -> dict:
    """使用 LLM 对文档内容进行分类"""
    prompt = CLASSIFICATION_PROMPT.format(content=content[:3000])
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=60
        )
        if resp.status_code == 200:
            result = resp.json()
            try:
                return json.loads(result.get("response", "{}"))
            except json.JSONDecodeError:
                return {"category": "其他", "confidence": 0.0, "keywords": [], "summary": ""}
        return {"category": "其他", "confidence": 0.0, "keywords": [], "summary": ""}

async def extract_keywords(content: str, model: str = "qwen2.5:7b") -> list:
    """提取文档关键词"""
    prompt = f"从以下文档中提取5-10个关键技术关键词，只返回 JSON 数组：\n\n{content[:2000]}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=30
        )
        if resp.status_code == 200:
            try:
                return json.loads(resp.json().get("response", "[]"))
            except:
                return []
        return []

async def suggest_knowledge_tree(documents: list[dict]) -> dict:
    """根据文档集合建议知识树结构"""
    titles = [d.get("title", "") for d in documents[:20]]
    prompt = f"""根据以下文档标题，建议一个企业知识分类树结构（最多3层）。
返回 JSON：{{"tree": [{{"name": "一级分类", "children": [{{"name": "二级分类"}}]}}]}}

文档标题：
{chr(10).join(titles)}"""
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "format": "json"},
            timeout=60
        )
        if resp.status_code == 200:
            try:
                return json.loads(resp.json().get("response", "{}"))
            except:
                return {"tree": []}
        return {"tree": []}
```

### Task 3.2.2: 分类 API 路由

**Files:** `classifier/api/classify.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from classifier.services.classifier import classify_document, extract_keywords, suggest_knowledge_tree

router = APIRouter(prefix="/classify", tags=["classify"])

class ClassifyRequest(BaseModel):
    content: str
    model: str = "qwen2.5:7b"

class BatchClassifyRequest(BaseModel):
    documents: list[dict]  # [{"id": "...", "content": "..."}]
    model: str = "qwen2.5:7b"

@router.post("")
async def classify(req: ClassifyRequest):
    result = await classify_document(req.content, req.model)
    return result

@router.post("/batch")
async def batch_classify(req: BatchClassifyRequest):
    results = []
    for doc in req.documents:
        r = await classify_document(doc.get("content", ""), req.model)
        r["doc_id"] = doc.get("id")
        results.append(r)
    return {"results": results}

@router.post("/keywords")
async def keywords(req: ClassifyRequest):
    result = await extract_keywords(req.content, req.model)
    return {"keywords": result}

@router.post("/suggest-tree")
async def suggest_tree(documents: list[dict]):
    result = await suggest_knowledge_tree(documents)
    return result
```

## T3.3: 知识分类管理

### Task 3.3.1: Category 模型和 API

**Files:** `server/domain/category.py`, `server/api/categories.py`

```python
# server/domain/category.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from server.core.database import db_query

class KnowledgeCategory(BaseModel):
    id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    created_at: Optional[datetime] = None

    @classmethod
    async def create(cls, name: str, parent_id: str = None, description: str = None) -> "KnowledgeCategory":
        result = await db_query(
            "CREATE knowledge_category CONTENT { name: $name, parent_id: $parent_id, description: $description } RETURN AFTER;",
            {"name": name, "parent_id": parent_id, "description": description}
        )
        return cls(**result[0])

    @classmethod
    async def get_all(cls) -> list["KnowledgeCategory"]:
        result = await db_query("SELECT * FROM knowledge_category ORDER BY sort_order ASC;")
        return [cls(**r) for r in result]

    @classmethod
    async def get_tree(cls) -> list[dict]:
        """返回树形结构"""
        all_cats = await cls.get_all()
        cat_map = {c.id: {**c.model_dump(), "children": []} for c in all_cats}
        roots = []
        for c in all_cats:
            if c.parent_id and c.parent_id in cat_map:
                cat_map[c.parent_id]["children"].append(cat_map[c.id])
            else:
                roots.append(cat_map[c.id])
        return roots

    async def update(self, **kwargs):
        result = await db_query("UPDATE $id MERGE $data RETURN AFTER;", {"id": self.id, "data": kwargs})
        for k, v in result[0].items():
            setattr(self, k, v)
        return self

    async def delete(self):
        await db_query("DELETE $id;", {"id": self.id})
```

## T3.4: 审批工作流

### Task 3.4.1: Approval 模型和 API

**Files:** `server/domain/approval.py`, `server/api/approvals.py`

```python
# server/domain/approval.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from server.core.database import db_query

class Approval(BaseModel):
    id: Optional[str] = None
    source_id: str
    submitter_id: str
    reviewer_id: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def create(cls, source_id: str, submitter_id: str) -> "Approval":
        result = await db_query(
            "CREATE approval CONTENT { source_id: $source_id, submitter_id: $submitter_id, status: 'pending' } RETURN AFTER;",
            {"source_id": source_id, "submitter_id": submitter_id}
        )
        return cls(**result[0])

    @classmethod
    async def get_pending(cls) -> list["Approval"]:
        result = await db_query("SELECT * FROM approval WHERE status = 'pending' ORDER BY created_at DESC;")
        return [cls(**r) for r in result]

    async def approve(self, reviewer_id: str, comment: str = None):
        result = await db_query(
            "UPDATE $id MERGE { status: 'approved', reviewer_id: $reviewer_id, comment: $comment, updated_at: time::now() } RETURN AFTER;",
            {"id": self.id, "reviewer_id": reviewer_id, "comment": comment}
        )
        for k, v in result[0].items():
            setattr(self, k, v)
        return self

    async def reject(self, reviewer_id: str, comment: str):
        result = await db_query(
            "UPDATE $id MERGE { status: 'rejected', reviewer_id: $reviewer_id, comment: $comment, updated_at: time::now() } RETURN AFTER;",
            {"id": self.id, "reviewer_id": reviewer_id, "comment": comment}
        )
        for k, v in result[0].items():
            setattr(self, k, v)
        return self
```

## Phase 3 验证

```bash
# 1. 分类测试
curl -X POST http://192.168.66.40:5057/classify \
  -H "Content-Type: application/json" \
  -d '{"content": "密封圈在高温工况下出现老化裂纹，建议更换为氟橡胶材质，耐温可达250°C"}'

# 2. 知识分类树
curl http://192.168.66.40:5056/categories/tree

# 3. 审批流程
curl -X POST http://192.168.66.40:5056/approvals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "source:xxx", "submitter_id": "user:xxx"}'
```
