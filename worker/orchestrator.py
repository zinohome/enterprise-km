"""
任务编排器 — 核心链路自动化
文件上传 → 解析 → 识别 → 提取 → 向量化 → 分类 → 图谱 → 审核队列

注意：所有 enqueue 操作创建新的 Queue 实例（安全用于 fork 后的子进程）。
"""
import traceback
from redis import Redis
from rq import Queue, Retry
from loguru import logger

from worker.core.config import REDIS_URL, MAX_RETRIES


def _enqueue(func_path: str, *args, **kwargs):
    """Enqueue a task with a fresh Redis connection (safe in forked processes)."""
    try:
        redis_conn = Redis(host="localhost", port=6379, db=0, decode_responses=True)
        q = Queue("default", connection=redis_conn)
        job_timeout = kwargs.pop("job_timeout", 300)
        job = q.enqueue(func_path, *args, **kwargs, job_timeout=job_timeout, retry=Retry(max=MAX_RETRIES))
        logger.info(f"Enqueued {func_path} -> {job.id}")
        return job.id
    except Exception as e:
        logger.error(f"Failed to enqueue {func_path}: {e}\n{traceback.format_exc()}")
        return None


def start_pipeline(object_key: str, user_id: str):
    """启动核心处理链路。第一步：解析文档。"""
    logger.info(f"Starting pipeline for {object_key} (user: {user_id})")
    job_id = _enqueue("worker.tasks.pipeline.process_document", object_key, user_id, job_timeout=600)
    return {"job_id": job_id, "object_key": object_key}


def on_parse_complete(result: dict):
    """解析完成后，启动识别。"""
    source_id = result.get("source_id")
    object_key = result.get("object_key")
    if not source_id:
        logger.error(f"Parse failed for {object_key}")
        return

    logger.info(f"Parse complete: {source_id}, starting identify")
    job_id = _enqueue("worker.tasks.identify.identify_document_type", source_id, "", job_timeout=120)
    return {"source_id": source_id, "identify_job": job_id}


def on_identify_complete(result: dict):
    """识别完成后，启动字段提取。"""
    source_id = result.get("source_id")
    doc_type = result.get("doc_type", "general")
    logger.info(f"Identify complete: {source_id} -> {doc_type}")

    job_id = _enqueue("worker.tasks.extract.extract_fields", source_id, "", doc_type, job_timeout=180)
    return {"source_id": source_id, "doc_type": doc_type, "extract_job": job_id}


def on_extract_complete(result: dict):
    """提取完成后，启动向量化 + 分类（并行）。"""
    source_id = result.get("source_id")
    doc_type = result.get("doc_type", "general")
    fields = result.get("fields", {})
    logger.info(f"Extract complete: {source_id}, fields: {list(fields.keys())}")

    vec_job = _enqueue("worker.tasks.vectorize.vectorize_document", source_id, "", doc_type, fields, job_timeout=120)
    cls_job = _enqueue("worker.tasks.classify.classify_document", source_id, "", doc_type, job_timeout=120)
    return {"source_id": source_id, "vectorize_job": vec_job, "classify_job": cls_job}


def on_vectorize_classify_complete(vec_result: dict, cls_result: dict):
    """向量化 + 分类完成后，启动图谱关联。"""
    source_id = vec_result.get("source_id")
    doc_type = cls_result.get("doc_type", "general")
    fields = cls_result.get("fields", {})
    logger.info(f"Vectorize + Classify complete: {source_id}")

    job_id = _enqueue("worker.tasks.graph.build_graph_relations", source_id, doc_type, fields, job_timeout=120)
    return {"source_id": source_id, "graph_job": job_id}


def on_graph_complete(result: dict):
    """图谱完成后，文档进入审核队列。"""
    source_id = result.get("source_id")
    logger.info(f"Graph complete: {source_id}, entering review queue")

    from surrealdb import Surreal
    from worker.core.config import (
        SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    )

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)
    db.query(f"UPDATE {source_id} SET status = 'pending_review', updated_at = time::now();")
    db.close()

    return {"source_id": source_id, "status": "pending_review"}
