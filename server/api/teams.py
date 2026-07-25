from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamMemberAdd(BaseModel):
    user_id: str
    role: str = "member"


@router.post("")
async def create_team(data: TeamCreate, current_user: User = Depends(get_current_user)):
    result = await db_query(
        "CREATE team CONTENT { name: $name, description: $description, owner_id: $owner_id, created_at: time::now() } RETURN AFTER;",
        {"name": data.name, "description": data.description, "owner_id": current_user.id}
    )
    return result[0] if result else {}


@router.get("")
async def list_teams(current_user: User = Depends(get_current_user)):
    result = await db_query(
        "SELECT * FROM team WHERE owner_id = $user_id OR id IN (SELECT team_id FROM team_member WHERE user_id = $user_id);",
        {"user_id": current_user.id}
    )
    return result


@router.get("/{team_id}")
async def get_team(team_id: str, current_user: User = Depends(get_current_user)):
    result = await db_query("SELECT * FROM $id;", {"id": team_id})
    if not result:
        raise HTTPException(404, "Team not found")
    members = await db_query(
        "SELECT *, user.username, user.display_name FROM team_member WHERE team_id = $team_id FETCH user;",
        {"team_id": team_id}
    )
    team = result[0]
    team["members"] = members
    return team


@router.post("/{team_id}/members")
async def add_member(team_id: str, data: TeamMemberAdd, current_user: User = Depends(get_current_user)):
    result = await db_query(
        "CREATE team_member CONTENT { team_id: $team_id, user_id: $user_id, role: $role, joined_at: time::now() } RETURN AFTER;",
        {"team_id": team_id, "user_id": data.user_id, "role": data.role}
    )
    return result[0] if result else {}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(team_id: str, user_id: str, current_user: User = Depends(get_current_user)):
    await db_query(
        "DELETE FROM team_member WHERE team_id = $team_id AND user_id = $user_id;",
        {"team_id": team_id, "user_id": user_id}
    )
    return {"status": "ok"}


@router.delete("/{team_id}")
async def delete_team(team_id: str, current_user: User = Depends(get_current_user)):
    await db_query("DELETE FROM team_member WHERE team_id = $team_id;", {"team_id": team_id})
    await db_query("DELETE FROM $id;", {"id": team_id})
    return {"status": "ok"}
