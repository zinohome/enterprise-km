from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("")
async def list_users(current_user: User = Depends(get_current_user)):
    users = await User.get_all()
    return [{"id": u.id, "username": u.username, "email": u.email, "display_name": u.display_name, "role": u.role, "department": u.department} for u in users]


@router.get("/{user_id}")
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name, "role": user.role, "department": user.department}


@router.put("/{user_id}")
async def update_user(user_id: str, data: UserUpdate, admin: User = Depends(require_admin)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    await user.update(**update_data)
    return {"id": user.id, "username": user.username, "role": user.role}


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    user = await User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
    return {"message": "User deleted"}
