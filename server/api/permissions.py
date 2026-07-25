from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user

router = APIRouter(prefix="/permissions", tags=["permissions"])


class VisibilityUpdate(BaseModel):
    visibility: str  # private, team, enterprise
    team_id: Optional[str] = None


@router.put("/source/{source_id}/visibility")
async def set_source_visibility(
    source_id: str,
    data: VisibilityUpdate,
    current_user: User = Depends(get_current_user),
):
    """Set document visibility. Only owner or admin can change."""
    source = await db_query("SELECT * FROM $id;", {"id": source_id})
    if not source:
        raise HTTPException(404, "Document not found")

    s = source[0]
    if current_user.role != "admin" and s.get("owner_id") != current_user.id:
        raise HTTPException(403, "Only owner or admin can change visibility")

    if data.visibility not in ("private", "team", "enterprise"):
        raise HTTPException(400, "Invalid visibility")

    update_data = {"visibility": data.visibility}
    if data.visibility == "team" and data.team_id:
        update_data["team_id"] = data.team_id

    try:
        await db_query(
            "UPDATE $id MERGE $data;",
            {"id": source_id, "data": update_data}
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to update: {e}")

    return {"status": "ok", "visibility": data.visibility}


@router.get("/source/{source_id}/access")
async def check_source_access(
    source_id: str,
    current_user: User = Depends(get_current_user),
):
    """Check if current user can access a document."""
    source = await db_query("SELECT * FROM $id;", {"id": source_id})
    if not source:
        raise HTTPException(404, "Document not found")

    s = source[0]
    if current_user.role == "admin":
        return {"access": True, "reason": "admin"}

    if s.get("owner_id") == current_user.id:
        return {"access": True, "reason": "owner"}

    if s.get("visibility") == "enterprise":
        return {"access": True, "reason": "enterprise_visible"}

    if s.get("visibility") == "team":
        team_id = s.get("team_id")
        if team_id:
            member = await db_query(
                "SELECT * FROM team_member WHERE team_id = $team_id AND user_id = $user_id;",
                {"team_id": team_id, "user_id": current_user.id}
            )
            if member:
                return {"access": True, "reason": "team_member"}

    return {"access": False, "reason": "no_permission"}
