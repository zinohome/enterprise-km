from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user
from server.api.notifications import notify_user
import httpx
from loguru import logger

router = APIRouter(prefix="/curation", tags=["curation"])

ENTERPRISE_NOTEBOOK = "http://127.0.0.1:5058"


class CurateRequest(BaseModel):
    source_id: str
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    visibility: str = "enterprise"


@router.get("/sources")
async def list_curatable_sources(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """List all sources available for curation (admin only)."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(403, "Admin or manager only")

    result = await db_query(
        "SELECT * FROM source ORDER BY created_at DESC LIMIT $limit START $offset;",
        {"limit": limit, "offset": offset}
    )
    return result


@router.post("/publish")
async def publish_to_enterprise(
    data: CurateRequest,
    current_user: User = Depends(get_current_user),
):
    """Publish a source to the enterprise knowledge base."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(403, "Admin or manager only")

    # Get source from our DB
    source = await db_query("SELECT * FROM $id;", {"id": data.source_id})
    if not source:
        raise HTTPException(404, "Source not found")

    s = source[0]

    # Create source in enterprise Open Notebook
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Create source
            resp = await client.post(
                f"{ENTERPRISE_NOTEBOOK}/api/sources",
                json={
                    "title": s.get("title", "Untitled"),
                    "content": s.get("full_text", "") or s.get("content", ""),
                    "type": "text",
                }
            )
            if resp.status_code != 200:
                logger.error(f"Enterprise notebook create source failed: {resp.status_code} {resp.text}")
                raise HTTPException(500, f"Failed to create source: {resp.text}")

            enterprise_source = resp.json()
            enterprise_id = enterprise_source.get("id")

            # Trigger processing
            await client.post(f"{ENTERPRISE_NOTEBOOK}/api/sources/{enterprise_id}/retry", timeout=300)

            # Update our source visibility
            await db_query(
                "UPDATE $id MERGE { visibility: 'enterprise', enterprise_source_id: $eid, curated_by: $curator, curated_at: time::now() };",
                {"id": data.source_id, "eid": enterprise_id, "curator": current_user.id}
            )

            # Notify admins
            from server.api.notifications import notify_admins
            await notify_admins(
                "知识已发布",
                f"文档 '{s.get('title', 'Untitled')}' 已发布到企业知识库",
                "success"
            )

            return {
                "status": "ok",
                "enterprise_source_id": enterprise_id,
                "message": "Published to enterprise knowledge base",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        raise HTTPException(500, f"Publish failed: {e}")


@router.get("/enterprise/sources")
async def list_enterprise_sources(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """List sources in the enterprise knowledge base."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ENTERPRISE_NOTEBOOK}/api/sources?limit={limit}")
            if resp.status_code == 200:
                return resp.json()
            return []
    except Exception as e:
        logger.error(f"Failed to list enterprise sources: {e}")
        return []


@router.delete("/enterprise/sources/{enterprise_id}")
async def remove_from_enterprise(
    enterprise_id: str,
    current_user: User = Depends(get_current_user),
):
    """Remove a source from the enterprise knowledge base."""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(f"{ENTERPRISE_NOTEBOOK}/api/sources/{enterprise_id}")
            if resp.status_code == 200:
                return {"status": "ok", "message": "Removed from enterprise"}
            raise HTTPException(resp.status_code, resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed: {e}")
