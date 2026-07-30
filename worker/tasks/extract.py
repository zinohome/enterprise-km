"""
结构化字段提取 — AI 根据文档类型提取制造业结构化字段
"""
import json
import re
import httpx
from loguru import logger
from rq import get_current_job

from worker.core.config import OLLAMA_URL, OLLAMA_MODEL

EXTRACT_PROMPTS = {
    "fa_report": """从以下故障分析报告中提取结构化信息，返回 JSON：
{
  "phenomenon": "故障现象描述",
  "root_cause": "根本原因",
  "solution": "解决措施",
  "part_number": "零件号（如有）",
  "production_line": "产线（如有）",
  "equipment": "设备（如有）",
  "severity": "严重程度: critical/major/minor"
}
只返回 JSON，不要其他内容。""",

    "ecn": """从以下工程变更通知中提取结构化信息，返回 JSON：
{
  "change_reason": "变更原因",
  "impact_scope": "影响范围",
  "change_type": "变更类型: design/process/material/supplier",
  "related_parts": ["零件号列表"],
  "before_state": "变更前状态",
  "after_state": "变更后状态"
}
只返回 JSON，不要其他内容。""",

    "process_spec": """从以下工艺规范中提取结构化信息，返回 JSON：
{
  "process_type": "工艺类型: injection/stamping/welding/assembly",
  "parameters": {"参数名": "参数值"},
  "applicable_products": ["适用产品列表"]
}
只返回 JSON，不要其他内容。""",

    "quality_standard": """从以下质检标准中提取结构化信息，返回 JSON：
{
  "test_method": "检测方法",
  "acceptance_criteria": "合格标准",
  "sampling_plan": "抽样方案",
  "test_type": "检测类型: visual/dimensional/functional/material",
  "applicable_products": ["适用产品列表"]
}
只返回 JSON，不要其他内容。""",

    "sop": """从以下标准操作流程中提取结构化信息，返回 JSON：
{
  "steps": [{"order": 1, "description": "步骤描述", "note": "备注"}],
  "precautions": ["注意事项"],
  "required_tools": ["所需工具"],
  "position": "适用岗位",
  "equipment": "适用设备"
}
只返回 JSON，不要其他内容。""",
}


def extract_fields(source_id: str, content: str, doc_type: str):
    """
    AI 根据文档类型提取结构化字段。
    返回提取的字段 dict，并触发下一步。
    """
    job = get_current_job()
    logger.info(f"Extracting fields for {source_id} (type: {doc_type})")

    prompt = EXTRACT_PROMPTS.get(doc_type, EXTRACT_PROMPTS["fa_report"])
    truncated = content[:4000] if len(content) > 4000 else content

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{prompt}\n\n文档内容：\n{truncated}",
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        result_text = resp.json()["response"].strip()

        try:
            fields = json.loads(result_text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                fields = json.loads(match.group())
            else:
                fields = {}

        logger.info(f"Extracted fields for {source_id}: {list(fields.keys())}")

        result = {"source_id": source_id, "doc_type": doc_type, "fields": fields}

        # Trigger next step
        try:
            from worker.orchestrator import on_extract_complete
            on_extract_complete(result)
        except Exception as e:
            logger.error(f"Failed to trigger next step: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to extract fields for {source_id}: {e}")
        return {"source_id": source_id, "doc_type": doc_type, "fields": {}}
