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
    prompt = CLASSIFICATION_PROMPT.format(content=content[:3000])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=60,
        )
        if resp.status_code == 200:
            result = resp.json()
            try:
                return json.loads(result.get("response", "{}"))
            except json.JSONDecodeError:
                return {"category": "其他", "confidence": 0.0, "keywords": [], "summary": ""}
        return {"category": "其他", "confidence": 0.0, "keywords": [], "summary": ""}


async def extract_keywords(content: str, model: str = "qwen2.5:7b") -> list:
    prompt = f"从以下文档中提取5-10个关键技术关键词，只返回 JSON 数组：\n\n{content[:2000]}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=30,
        )
        if resp.status_code == 200:
            try:
                return json.loads(resp.json().get("response", "[]"))
            except (json.JSONDecodeError, KeyError):
                return []
        return []


async def suggest_knowledge_tree(documents: list[dict]) -> dict:
    titles = [d.get("title", "") for d in documents[:20]]
    prompt = f"""根据以下文档标题，建议一个企业知识分类树结构（最多3层）。
返回 JSON：{{"tree": [{{"name": "一级分类", "children": [{{"name": "二级分类"}}]}}]}}

文档标题：
{chr(10).join(titles)}"""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False, "format": "json"},
            timeout=60,
        )
        if resp.status_code == 200:
            try:
                return json.loads(resp.json().get("response", "{}"))
            except (json.JSONDecodeError, KeyError):
                return {"tree": []}
        return {"tree": []}
