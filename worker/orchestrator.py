"""
任务编排器 — 核心链路自动化
文件上传 → 解析 → 识别 → 提取 → 向量化 → 分类 → 图谱 → 审核队列
"""
from redis import Redis
from rq import Queue, Retry
from loguru import logger

from worker.core.config import REDIS_URL, MAX_RETRIES

redis_conn = Redis.from_url(REDIS_URL)
high_queue = Queue("high", connection=redis_conn)
default_queue = Queue("default", connection=redis_conn)
low_queue = Queue("low", connection=redis_conn)
retry_policy = Retry(max=MAX_RETRIES)


def start_pipeline(object_key: str, user_id: str):
    """
    启动核心处理链路。
    第一步：解析文档。
    """
    logger.info(f"Starting pipeline for {object_key} (user: {user_id})")
    job = default_queue.enqueue(
        "worker.tasks.parse.parse_document",
        object_key,
        user_id,
        job_timeout=300,
        retry=retry_policy,
    )
    return {"job_id": job.id, "object_key": object_key}


def on_parse_complete(result: dict):
    """
    解析完成后，启动识别 + 提取。
    """
    source_id = result.get("source_id")
    object_key = result.get("object_key")
    if not source_id:
        logger.error(f"Parse failed for {object_key}")
        return

    logger.info(f"Parse complete: {source_id}, starting identify + extract")

    # Read content from SurrealDB
    from surrealdb import Surreal
    from worker.core.config import (
        SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    )

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)

    # Get source content
    result = db.query(f"SELECT * FROM {source_id};")
    content = ""
    for r in result:
        if isinstance(r, dict):
            content = r.get("title", "") + " " + r.get("file_path", "")
            break
    db.close()

    # Enqueue identify
    identify_job = default_queue.enqueue(
        "worker.tasks.identify.identify_document_type",
        source_id,
        content,
        job_timeout=120,
        retry=retry_policy,
    )

    return {"source_id": source_id, "identify_job": identify_job.id}


def on_identify_complete(result: dict):
    """
    识别完成后，启动字段提取。
    """
    source_id = result.get("source_id")
    doc_type = result.get("doc_type", "general")
    logger.info(f"Identify complete: {source_id} -> {doc_type}")

    # Get content again
    from surrealdb import Surreal
    from worker.core.config import (
        SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    )

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)
    result = db.query(f"SELECT * FROM {source_id};")
    content = ""
    for r in result:
        if isinstance(r, dict):
            content = r.get("title", "") + " " + r.get("file_path", "")
            break
    db.close()

    # Enqueue extract
    extract_job = default_queue.enqueue(
        "worker.tasks.extract.extract_fields",
        source_id,
        content,
        doc_type,
        job_timeout=180,
        retry=retry_policy,
    )

    return {"source_id": source_id, "doc_type": doc_type, "extract_job": extract_job.id}


def on_extract_complete(result: dict):
    """
    提取完成后，启动向量化 + 分类（并行）。
    """
    source_id = result.get("source_id")
    doc_type = result.get("doc_type", "general")
    fields = result.get("fields", {})
    logger.info(f"Extract complete: {source_id}, fields: {list(fields.keys())}")

    # Get content
    from surrealdb import Surreal
    from worker.core.config import (
        SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    )

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)
    result = db.query(f"SELECT * FROM {source_id};")
    content = ""
    for r in result:
        if isinstance(r, dict):
            content = r.get("title", "") + " " + r.get("file_path", "")
            break
    db.close()

    # Enqueue vectorize + classify in parallel
    vec_job = default_queue.enqueue(
        "worker.tasks.vectorize.vectorize_document",
        source_id,
        content,
        doc_type,
        fields,
        job_timeout=120,
        retry=retry_policy,
    )

    cls_job = default_queue.enqueue(
        "worker.tasks.classify.classify_document",
        source_id,
        content,
        doc_type,
        job_timeout=120,
        retry=retry_policy,
    )

    return {
        "source_id": source_id,
        "doc_type": doc_type,
        "fields": fields,
        "vectorize_job": vec_job.id,
        "classify_job": cls_job.id,
    }


def on_vectorize_classify_complete(vec_result: dict, cls_result: dict):
    """
    向量化 + 分类完成后，启动图谱关联。
    """
    source_id = vec_result.get("source_id")
    doc_type = cls_result.get("doc_type", "general")
    fields = cls_result.get("fields", {})
    logger.info(f"Vectorize + Classify complete: {source_id}")

    # Enqueue graph
    graph_job = default_queue.enqueue(
        "worker.tasks.graph.build_graph_relations",
        source_id,
        doc_type,
        fields,
        job_timeout=120,
        retry=retry_policy,
    )

    return {
        "source_id": source_id,
        "doc_type": doc_type,
        "fields": fields,
        "classification": cls_result.get("classification", {}),
        "graph_job": graph_job.id,
    }


def on_graph_complete(result: dict):
    """
    图谱完成后，文档进入审核队列。
    """
    source_id = result.get("source_id")
    logger.info(f"Graph complete: {source_id}, entering review queue")

    # Update status to pending_review
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
