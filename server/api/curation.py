"""
管理员策展 API — 审核队列、批量操作、发布
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
from surrealdb import Surreal

from server.core.config import SURREAL_URL, SURREAL_USER, SURREAL_PASSWORD, SURREAL_NAMESPACE, SURREAL_DATABASE
from server.api.auth import get_current_user

router = APIRouter(prefix="/api/curation", tags=["curation"])


class ReviewAction(BaseModel):
    source_id: str
    action: str  # approve / reject
    doc_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    visibility: Optional[str] = "public"
    team_ids: Optional[List[str]] = None
    comment: Optional[str] = None


class BatchReviewAction(BaseModel):
    source_ids: List[str]
    action: str  # approve_all / reject_all
    visibility: Optional[str] = "public"


def get_db():
    db = Surreal(SURREAL_URL)
    db.signin({"user": SURREAL_USER, "pass": SURREAL_PASSWORD})
    db.use(SURREAL_NAMESPACE, SURREAL_DATABASE)
    return db


@router.get("/queue")
async def get_review_queue(
    status: Optional[str] = "pending_review",
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """
    获取待审核文档列表。
    """
    db = get_db()
    try:
        query = f"SELECT * FROM source WHERE status = '{status}'"
        if doc_type:
            query += f" AND source_type = '{doc_type}'"
        query += f" ORDER BY created_at DESC LIMIT {limit} START {offset};"

        result = db.query(query)
        items = []
        for r in result:
            if isinstance(r, dict) and "id" in r:
                items.append(r)

        # Count total
        count_result = db.query(f"SELECT count() FROM source WHERE status = '{status}' GROUP BY status;")
        total = 0
        for r in count_result:
            if isinstance(r, dict):
                total = r.get("count", 0)
                break

        return {"total": total, "items": items}
    finally:
        db.close()


@router.post("/review")
async def review_document(
    action: ReviewAction,
    user: dict = Depends(get_current_user),
):
    """
    审核单个文档：通过或驳回。
    通过后自动发布到搜索服务。
    """
    db = get_db()
    try:
        if action.action == "approve":
            # Update source status
            db.query(f"""
                UPDATE {action.source_id} SET
                    status = 'approved',
                    visibility = '{action.visibility}',
                    team_ids = {action.team_ids or []},
                    updated_at = time::now();
            """)

            # Publish to search
            from worker.tasks.publish import publish_to_search
            publish_to_search(
                source_id=action.source_id,
                doc_type=action.doc_type or "general",
                fields={},
                classification={},
                owner_id=user.get("sub", ""),
                visibility=action.visibility,
                team_ids=action.team_ids or [],
            )

            logger.info(f"Approved and published: {action.source_id}")
            return {"status": "approved", "source_id": action.source_id}

        elif action.action == "reject":
            db.query(f"""
                UPDATE {action.source_id} SET
                    status = 'rejected',
                    updated_at = time::now();
            """)
            logger.info(f"Rejected: {action.source_id}")
            return {"status": "rejected", "source_id": action.source_id}

        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action.action}")
    finally:
        db.close()


@router.post("/review/batch")
async def batch_review(
    action: BatchReviewAction,
    user: dict = Depends(get_current_user),
):
    """
    批量审核：全部通过或全部驳回。
    """
    db = get_db()
    results = []
    try:
        for source_id in action.source_ids:
            if action.action == "approve_all":
                db.query(f"""
                    UPDATE {source_id} SET
                        status = 'approved',
                        visibility = '{action.visibility}',
                        updated_at = time::now();
                """)
                results.append({"source_id": source_id, "status": "approved"})
            elif action.action == "reject_all":
                db.query(f"""
                    UPDATE {source_id} SET
                        status = 'rejected',
                        updated_at = time::now();
                """)
                results.append({"source_id": source_id, "status": "rejected"})

        logger.info(f"Batch review: {len(results)} documents")
        return {"processed": len(results), "results": results}
    finally:
        db.close()


@router.get("/stats")
async def curation_stats(user: dict = Depends(get_current_user)):
    """
    策展统计：各状态文档数量。
    """
    db = get_db()
    try:
        result = db.query("""
            SELECT status, count() AS count
            FROM source
            GROUP BY status;
        """)
        stats = {}
        for r in result:
            if isinstance(r, dict):
                stats[r.get("status", "unknown")] = r.get("count", 0)
        return stats
    finally:
        db.close()
