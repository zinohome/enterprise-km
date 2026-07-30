"""
自动分类任务 — AI 建议知识树位置
"""
import json
import re
import httpx
from loguru import logger
from rq import get_current_job

from worker.core.config import OLLAMA_URL, OLLAMA_MODEL

CLASSIFY_PROMPT = """你是一个制造业知识管理专家。请根据文档内容，建议它在企业知识树中的分类位置。

知识树结构（制造业）：
- 故障分析报告
  - 注塑工艺
  - 冲压工艺
  - 焊接工艺
  - 装配工艺
  - 其他工艺
- 工程变更
  - 设计变更
  - 工艺变更
  - 材料变更
  - 供应商变更
- 工艺规范
  - 注塑规范
  - 冲压规范
  - 焊接规范
  - 装配规范
- 质检标准
  - 来料检验
  - 过程检验
  - 成品检验
  - 出货检验
- 标准操作流程
  - 设备操作
  - 检验操作
  - 维护操作
  - 安全操作

请返回 JSON：
{
  "category": "一级分类",
  "subcategory": "二级分类",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "confidence": 0.85
}
只返回 JSON，不要其他内容。"""


def classify_document(source_id: str, content: str, doc_type: str):
    """
    AI 建议文档分类位置和关键词。
    完成后触发图谱关联。
    """
    job = get_current_job()
    logger.info(f"Classifying document {source_id}")

    truncated = content[:3000] if len(content) > 3000 else content

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{CLASSIFY_PROMPT}\n\n文档类型：{doc_type}\n文档内容：\n{truncated}",
                "stream": False,
                "format": "json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        result_text = resp.json()["response"].strip()

        try:
            classification = json.loads(result_text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            classification = json.loads(match.group()) if match else {}

        logger.info(f"Classified {source_id}: {classification.get('category', 'unknown')}")

        result = {"source_id": source_id, "classification": classification}

        # Trigger graph step
        try:
            from worker.orchestrator import on_vectorize_classify_complete
            on_vectorize_classify_complete(
                {"source_id": source_id},
                {"source_id": source_id, "doc_type": doc_type, "fields": {}, "classification": classification},
            )
        except Exception as e:
            logger.error(f"Failed to trigger graph step: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to classify {source_id}: {e}")
        return {"source_id": source_id, "classification": {}}
