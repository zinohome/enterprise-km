from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user
import httpx
from loguru import logger

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "info"
    link: Optional[str] = None


@router.post("")
async def create_notification(data: NotificationCreate, current_user: User = Depends(get_current_user)):
    result = await db_query(
        "CREATE notification CONTENT { user_id: $user_id, title: $title, message: $message, type: $type, link: $link, read: false, created_at: time::now() } RETURN AFTER;",
        {"user_id": data.user_id, "title": data.title, "message": data.message, "type": data.type, "link": data.link}
    )
    return result[0] if result else {}


@router.get("")
async def list_notifications(unread_only: bool = False, limit: int = 50, current_user: User = Depends(get_current_user)):
    filter_clause = "AND read = false" if unread_only else ""
    result = await db_query(
        f"SELECT * FROM notification WHERE user_id = $user_id {filter_clause} ORDER BY created_at DESC LIMIT $limit;",
        {"user_id": current_user.id, "limit": limit}
    )
    return result


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: User = Depends(get_current_user)):
    await db_query(
        "UPDATE $id MERGE { read: true };",
        {"id": notification_id}
    )
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    await db_query(
        "UPDATE notification SET read = true WHERE user_id = $user_id;",
        {"user_id": current_user.id}
    )
    return {"status": "ok"}


@router.get("/unread-count")
async def unread_count(current_user: User = Depends(get_current_user)):
    result = await db_query(
        "SELECT count() FROM notification WHERE user_id = $user_id AND read = false GROUP ALL;",
        {"user_id": current_user.id}
    )
    return {"count": result[0]["count"] if result else 0}


async def notify_user(user_id: str, title: str, message: str, type: str = "info", link: str = None):
    """Send notification to a user (called from other services)."""
    try:
        await db_query(
            "CREATE notification CONTENT { user_id: $user_id, title: $title, message: $message, type: $type, link: $link, read: false, created_at: time::now() };",
            {"user_id": user_id, "title": title, "message": message, "type": type, "link": link}
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


async def notify_admins(title: str, message: str, type: str = "info"):
    """Notify all admin users."""
    admins = await db_query("SELECT id FROM user WHERE role = 'admin';")
    for admin in admins:
        await notify_user(admin["id"], title, message, type)
