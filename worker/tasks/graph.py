"""
知识图谱关联 — 构建文档间关联关系
"""
from loguru import logger
from rq import get_current_job
from surrealdb import Surreal

from worker.core.config import (
    SURREALDB_URL, SURREALDB_USER, SURREALDB_PASS, SURREALDB_NS, SURREALDB_DB,
)


def build_graph_relations(source_id: str, doc_type: str, fields: dict):
    """
    根据文档类型和提取的字段，构建知识图谱关联。
    """
    job = get_current_job()
    logger.info(f"Building graph relations for {source_id} (type: {doc_type})")

    db = Surreal(SURREALDB_URL)
    db.signin({"user": SURREALDB_USER, "pass": SURREALDB_PASS})
    db.use(SURREALDB_NS, SURREALDB_DB)

    relations_created = []

    try:
        if doc_type == "fa_report":
            part_number = fields.get("part_number")
            if part_number:
                result = db.query(f"""
                    SELECT id FROM fa_report
                    WHERE part_number = "{part_number}" AND id != {source_id}
                    LIMIT 5;
                """)
                for r in result:
                    if isinstance(r, dict) and "id" in r:
                        db.query(f"RELATE {source_id}->similar_to->{r['id']};")
                        relations_created.append(f"similar_to:{r['id']}")

                result = db.query(f"""
                    SELECT id FROM ecn
                    WHERE related_parts CONTAINS "{part_number}"
                    LIMIT 5;
                """)
                for r in result:
                    if isinstance(r, dict) and "id" in r:
                        db.query(f"RELATE {source_id}->relates_to->{r['id']};")
                        relations_created.append(f"relates_to:{r['id']}")

        elif doc_type == "ecn":
            related_parts = fields.get("related_parts", [])
            for part in related_parts:
                result = db.query(f"""
                    SELECT id FROM fa_report
                    WHERE part_number = "{part}"
                    LIMIT 5;
                """)
                for r in result:
                    if isinstance(r, dict) and "id" in r:
                        db.query(f"RELATE {source_id}->affects_part->{r['id']};")
                        relations_created.append(f"affects_part:{r['id']}")

        elif doc_type == "process_spec":
            result = db.query("SELECT id FROM quality_standard LIMIT 10;")
            for r in result:
                if isinstance(r, dict) and "id" in r:
                    db.query(f"RELATE {source_id}->has_quality_standard->{r['id']};")
                    relations_created.append(f"has_quality_standard:{r['id']}")

        elif doc_type == "sop":
            result = db.query("SELECT id FROM process_spec LIMIT 10;")
            for r in result:
                if isinstance(r, dict) and "id" in r:
                    db.query(f"RELATE {source_id}->follows_spec->{r['id']};")
                    relations_created.append(f"follows_spec:{r['id']}")

        logger.info(f"Created {len(relations_created)} relations for {source_id}")

    except Exception as e:
        logger.error(f"Failed to build graph for {source_id}: {e}")

    finally:
        db.close()

    result = {"source_id": source_id, "relations": relations_created}

    # Trigger next step
    try:
        from worker.orchestrator import on_graph_complete
        on_graph_complete(result)
    except Exception as e:
        logger.error(f"Failed to trigger next step: {e}")

    return result
