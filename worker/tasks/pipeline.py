"""
文档处理全链路 — 解析 → 识别 → 提取 → 向量化 → 分类 → 图谱 → 审核
作为单个 RQ 任务运行，避免 fork 后 Redis 连接问题。
"""
import os
import json
import tempfile
import httpx
from minio import Minio
from surrealdb import Surreal
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from loguru import logger
from rq import get_current_job

from worker.core.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET,
    SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    OLLAMA_URL, OLLAMA_MODEL, EMBEDDING_MODEL,
    QDRANT_URL, MEILISEARCH_URL, MEILISEARCH_KEY,
)

COLLECTION_NAME = "enterprise_km"
VECTOR_SIZE = 1024


def process_document(object_key: str, user_id: str):
    """
    完整处理链路：下载 → 解析 → 识别 → 提取 → 向量化 → 分类 → 图谱 → 审核。
    所有步骤在同一个 Worker 进程中同步执行。
    """
    job = get_current_job()
    logger.info(f"=== Pipeline start: {object_key} (user: {user_id}) ===")

    # ── Step 1: Download from MinIO ──
    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    local_path = os.path.join(tempfile.gettempdir(), os.path.basename(object_key))
    try:
        minio_client.fget_object(MINIO_BUCKET, object_key, local_path)
        logger.info(f"[1/7] Downloaded: {object_key}")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise

    # ── Step 2: Parse & store in SurrealDB ──
    with open(local_path, "rb") as f:
        content_bytes = f.read()
    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_text = content_bytes.decode("utf-8", errors="replace")

    file_name = os.path.basename(object_key)
    file_ext = os.path.splitext(file_name)[1].lower()

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)

    # Use db.create() for reliable field storage
    import uuid as _uuid
    raw_id = _uuid.uuid4().hex[:20]
    source_id_str = f"source:{raw_id}"
    meili_id = f"source-{raw_id}"
    result = db.create(source_id_str, {
        "title": file_name,
        "source_type": file_ext.lstrip("."),
        "file_path": object_key,
        "owner_id": user_id,
        "status": "processing",
    })
    logger.info(f"[2/7] Parsed: {source_id_str}")

    # ── Step 3: Identify document type ──
    doc_type = "general"
    try:
        truncated = content_text[:3000]
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": f"识别文档类型（fa_report/ecn/process_spec/quality_standard/sop/general）：\n{truncated}", "stream": False},
            timeout=60,
        )
        if resp.status_code == 200:
            doc_type = resp.json()["response"].strip().lower()
            valid = ["fa_report", "ecn", "process_spec", "quality_standard", "sop", "general"]
            if doc_type not in valid:
                doc_type = "general"
    except Exception as e:
        logger.warning(f"Identify failed: {e}, using general")
    logger.info(f"[3/7] Identified: {doc_type}")

    # ── Step 4: Extract fields ──
    fields = {}
    try:
        truncated = content_text[:4000]
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": f"提取结构化字段（JSON）：\n{truncated}", "stream": False, "format": "json"},
            timeout=120,
        )
        if resp.status_code == 200:
            result_text = resp.json()["response"].strip()
            try:
                fields = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if match:
                    fields = json.loads(match.group())
    except Exception as e:
        logger.warning(f"Extract failed: {e}")
    logger.info(f"[4/7] Extracted: {list(fields.keys())}")

    # ── Step 5: Vectorize → Qdrant + Meilisearch ──
    safe_fields = {}
    if fields:
        for k, v in fields.items():
            try:
                json.dumps({k: v})
                safe_fields[k] = v
            except (TypeError, ValueError):
                safe_fields[k] = str(v)

    try:
        qdrant = QdrantClient(url=QDRANT_URL)
        collections = qdrant.get_collections().collections
        if COLLECTION_NAME not in [c.name for c in collections]:
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

        text_to_embed = content_text[:2000]
        if safe_fields:
            text_to_embed += "\n" + json.dumps(safe_fields, ensure_ascii=False)

        resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text_to_embed},
            timeout=60,
        )
        if resp.status_code == 200:
            embedding = resp.json()["embedding"]
            import uuid
            point_id = str(uuid.uuid4())
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=point_id, vector=embedding, payload={
                    "source_id": source_id_str, "doc_type": doc_type, "fields": safe_fields,
                })],
            )
            logger.info(f"[5a/7] Vectorized: {len(embedding)} dims")
    except Exception as e:
        logger.warning(f"Vectorize failed: {e}")

    # ── Step 5b: Meilisearch index ──
    try:
        meili_doc = {
            "id": meili_id,
            "title": file_name,
            "content": content_text[:5000],
            "doc_type": doc_type,
            "fields": safe_fields,
        }
        resp = httpx.post(
            f"{MEILISEARCH_URL}/indexes/documents/documents",
            headers={"Authorization": f"Bearer {MEILISEARCH_KEY}"},
            json=[meili_doc],
            timeout=10,
        )
        if resp.status_code in (200, 201, 202):
            logger.info(f"[5b/7] Meilisearch indexed: {source_id_str}")
        else:
            logger.warning(f"Meilisearch index failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Meilisearch index failed: {e}")

    # ── Step 6: Classify ──
    classification = {}
    try:
        truncated = content_text[:3000]
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": f"建议知识树分类（JSON: category/subcategory/keywords）：\n{truncated}", "stream": False, "format": "json"},
            timeout=60,
        )
        if resp.status_code == 200:
            result_text = resp.json()["response"].strip()
            try:
                classification = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if match:
                    classification = json.loads(match.group())
    except Exception as e:
        logger.warning(f"Classify failed: {e}")
    logger.info(f"[6/7] Classified: {classification.get('category', 'unknown')}")

    # ── Step 7: Update status → pending_review ──
    db.query(f"UPDATE {source_id_str} SET status = 'pending_review', updated_at = time::now();")
    db.close()
    logger.info(f"[7/7] Status: pending_review")

    # Cleanup
    try:
        os.remove(local_path)
    except Exception:
        pass

    logger.info(f"=== Pipeline complete: {source_id_str} ===")
    return {
        "source_id": source_id_str,
        "doc_type": doc_type,
        "fields": fields,
        "classification": classification,
        "status": "pending_review",
    }
