"""
向量化任务 — 调用 bge-m3 生成 embedding，写入 Qdrant
"""
import json
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from loguru import logger
from rq import get_current_job

from worker.core.config import OLLAMA_URL, QDRANT_URL, EMBEDDING_MODEL

COLLECTION_NAME = "enterprise_km"
VECTOR_SIZE = 1024  # bge-m3 dimension

qdrant = QdrantClient(url=QDRANT_URL)


def ensure_collection():
    """确保 Qdrant collection 存在"""
    collections = qdrant.get_collections().collections
    names = [c.name for c in collections]
    if COLLECTION_NAME not in names:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")


def vectorize_document(source_id: str, content: str, doc_type: str, fields: dict):
    """
    生成文档向量并写入 Qdrant。
    """
    job = get_current_job()
    logger.info(f"Vectorizing document {source_id}")

    ensure_collection()

    # Combine content + extracted fields for better embedding
    text_to_embed = content[:2000] if len(content) > 2000 else content
    if fields:
        text_to_embed += "\n" + json.dumps(fields, ensure_ascii=False)

    try:
        # Generate embedding via Ollama
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text_to_embed},
            timeout=60,
        )
        resp.raise_for_status()
        embedding = resp.json()["embedding"]

        # Write to Qdrant
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=source_id,
                    vector=embedding,
                    payload={
                        "source_id": source_id,
                        "doc_type": doc_type,
                        "fields": fields,
                    },
                )
            ],
        )

        logger.info(f"Vectorized {source_id} ({len(embedding)} dims)")
        return {"source_id": source_id, "vector_size": len(embedding)}

    except Exception as e:
        logger.error(f"Failed to vectorize {source_id}: {e}")
        raise
