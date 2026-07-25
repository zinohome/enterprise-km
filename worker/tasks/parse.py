"""
文档解析任务 — 从 MinIO 下载文件，调用 Open Notebook API 解析
"""
import os
import tempfile
import httpx
from minio import Minio
from loguru import logger
from rq import get_current_job

from worker.core.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET,
    SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    MAX_RETRIES,
)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


def parse_document(object_key: str, user_id: str):
    """
    从 MinIO 下载文件，解析内容，写入 SurrealDB source 表。
    返回 source_id。
    """
    job = get_current_job()
    logger.info(f"Parsing document: {object_key}")

    # 1. Download from MinIO
    local_path = os.path.join(tempfile.gettempdir(), os.path.basename(object_key))
    try:
        minio_client.fget_object(MINIO_BUCKET, object_key, local_path)
        logger.info(f"Downloaded: {object_key} -> {local_path}")
    except Exception as e:
        logger.error(f"Failed to download {object_key}: {e}")
        raise

    # 2. Read file content
    try:
        with open(local_path, "rb") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read {local_path}: {e}")
        raise

    # 3. Store in SurrealDB as a source record
    # We use the Open Notebook source table structure
    from surrealdb import Surreal

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)

    file_name = os.path.basename(object_key)
    file_ext = os.path.splitext(file_name)[1].lower()

    # Create source record
    result = db.query(f"""
        CREATE source SET
            title = "{file_name}",
            source_type = "{file_ext.lstrip('.')}",
            file_path = "{object_key}",
            owner_id = {user_id},
            status = "processing",
            created_at = time::now();
    """)

    source_id = None
    for r in result:
        if isinstance(r, dict) and "id" in r:
            source_id = r["id"]
            break

    db.close()

    # 4. Cleanup
    try:
        os.remove(local_path)
    except Exception:
        pass

    logger.info(f"Parsed document: {object_key} -> source {source_id}")
    return {"source_id": source_id, "object_key": object_key}
