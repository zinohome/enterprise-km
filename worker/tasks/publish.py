"""
发布任务 — 审核通过后发布到 Meilisearch + Qdrant
"""
import json
import meilisearch
from loguru import logger
from rq import get_current_job
from surrealdb import Surreal

from worker.core.config import (
    SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
    MEILISEARCH_URL, MEILISEARCH_KEY,
)

meili = meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_KEY)
INDEX_NAME = "enterprise_km"


def ensure_index():
    """确保 Meilisearch 索引存在，配置中文分词"""
    try:
        meili.get_index(INDEX_NAME)
    except Exception:
        meili.create_index(INDEX_NAME, {"primaryKey": "id"})
        # Configure Chinese search
        meili.index(INDEX_NAME).update_settings({
            "searchableAttributes": ["title", "content", "keywords", "part_number", "phenomenon", "root_cause"],
            "filterableAttributes": ["doc_type", "visibility", "owner_id", "team_ids", "category", "status"],
            "sortableAttributes": ["created_at", "updated_at"],
        })
        logger.info(f"Created Meilisearch index: {INDEX_NAME}")


def publish_to_search(source_id: str, doc_type: str, fields: dict, classification: dict, owner_id: str, visibility: str, team_ids: list):
    """
    发布文档到 Meilisearch 全文索引。
    Qdrant 向量已在 vectorize 步骤写入。
    """
    job = get_current_job()
    logger.info(f"Publishing {source_id} to search")

    ensure_index()

    # Build search document
    doc = {
        "id": source_id,
        "doc_type": doc_type,
        "title": fields.get("title", source_id),
        "content": json.dumps(fields, ensure_ascii=False),
        "keywords": classification.get("keywords", []),
        "category": classification.get("category", ""),
        "subcategory": classification.get("subcategory", ""),
        "visibility": visibility,
        "owner_id": owner_id,
        "team_ids": team_ids or [],
        "status": "published",
        "created_at": None,  # Will be set from SurrealDB
    }

    # Add type-specific fields
    if doc_type == "fa_report":
        doc["part_number"] = fields.get("part_number", "")
        doc["phenomenon"] = fields.get("phenomenon", "")
        doc["root_cause"] = fields.get("root_cause", "")
        doc["production_line"] = fields.get("production_line", "")
    elif doc_type == "ecn":
        doc["change_reason"] = fields.get("change_reason", "")
        doc["related_parts"] = fields.get("related_parts", [])

    try:
        meili.index(INDEX_NAME).add_documents([doc])
        logger.info(f"Published {source_id} to Meilisearch")

        # Update SurrealDB status
        db = Surreal(SURREALDB_URL)
        db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
        db.use(SURREALDB_NS, SURREALDB_DB)

        table_map = {
            "fa_report": "fa_report",
            "ecn": "ecn",
            "process_spec": "process_spec",
            "quality_standard": "quality_standard",
            "sop": "sop",
        }
        table = table_map.get(doc_type, "fa_report")
        db.query(f"UPDATE {source_id} SET status = 'published', updated_at = time::now();")
        db.close()

        return {"source_id": source_id, "published": True}

    except Exception as e:
        logger.error(f"Failed to publish {source_id}: {e}")
        raise
