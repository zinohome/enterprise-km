"""
文档类型识别 — AI 识别制造业文档类型
"""
import httpx
from loguru import logger
from rq import get_current_job

from worker.core.config import OLLAMA_URL, OLLAMA_MODEL

IDENTIFY_PROMPT = """你是一个制造业文档分类专家。请分析以下文档内容，判断它属于哪种类型。

类型选项：
- fa_report: 故障分析报告（包含故障现象、根因分析、解决措施）
- ecn: 工程变更通知（包含变更原因、影响范围、审批记录）
- process_spec: 工艺规范（包含工艺参数、适用产品、版本信息）
- quality_standard: 质检标准（包含检测方法、合格标准、抽样方案）
- sop: 标准操作流程（包含操作步骤、注意事项、所需工具）
- general: 通用文档（不属于以上任何类型）

请只返回类型代码，不要返回其他内容。例如：fa_report"""


def identify_document_type(source_id: str, content: str):
    """
    AI 识别文档类型。
    返回文档类型代码，并触发下一步。
    """
    job = get_current_job()
    logger.info(f"Identifying document type for source {source_id}")

    truncated = content[:3000] if len(content) > 3000 else content

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{IDENTIFY_PROMPT}\n\n文档内容：\n{truncated}",
                "stream": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
        doc_type = resp.json()["response"].strip().lower()

        valid_types = ["fa_report", "ecn", "process_spec", "quality_standard", "sop", "general"]
        if doc_type not in valid_types:
            for vt in valid_types:
                if vt in doc_type:
                    doc_type = vt
                    break
            else:
                doc_type = "general"

        logger.info(f"Identified {source_id} as {doc_type}")

        result = {"source_id": source_id, "doc_type": doc_type}

        # Trigger next step
        try:
            from worker.orchestrator import on_identify_complete
            on_identify_complete(result)
        except Exception as e:
            logger.error(f"Failed to trigger next step: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to identify {source_id}: {e}")
        return {"source_id": source_id, "doc_type": "general"}
