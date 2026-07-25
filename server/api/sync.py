from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncConfig(BaseModel):
    directory: str


@router.get("/status")
async def sync_status(current_user: User = Depends(get_current_user)):
    """Get sync status for current user."""
    result = await db_query(
        "SELECT * FROM sync_state WHERE user_id = $user_id;",
        {"user_id": current_user.id}
    )
    if result:
        return result[0]
    return {"directory": "", "running": False, "lastSync": "从未同步", "fileCount": 0}


@router.post("/config")
async def sync_config(data: SyncConfig, current_user: User = Depends(get_current_user)):
    """Set sync directory for current user."""
    existing = await db_query(
        "SELECT * FROM sync_state WHERE user_id = $user_id;",
        {"user_id": current_user.id}
    )
    if existing:
        await db_query(
            "UPDATE $id MERGE { directory: $dir };",
            {"id": existing[0]["id"], "dir": data.directory}
        )
    else:
        await db_query(
            "CREATE sync_state CONTENT { user_id: $user_id, directory: $dir, running: false, lastSync: '从未同步', fileCount: 0 };",
            {"user_id": current_user.id, "dir": data.directory}
        )
    return {"status": "ok", "directory": data.directory}


@router.post("/start")
async def sync_start(current_user: User = Depends(get_current_user)):
    """Start rclone sync for current user."""
    state = await db_query(
        "SELECT * FROM sync_state WHERE user_id = $user_id;",
        {"user_id": current_user.id}
    )
    if not state or not state[0].get("directory"):
        raise HTTPException(400, "请先配置同步目录")

    # Update state
    await db_query(
        "UPDATE $id MERGE { running: true };",
        {"id": state[0]["id"]}
    )

    # The actual rclone process is managed by the Tauri desktop app
    # This endpoint just records the intent
    return {"status": "ok", "running": True}


@router.post("/stop")
async def sync_stop(current_user: User = Depends(get_current_user)):
    """Stop rclone sync for current user."""
    state = await db_query(
        "SELECT * FROM sync_state WHERE user_id = $user_id;",
        {"user_id": current_user.id}
    )
    if state:
        await db_query(
            "UPDATE $id MERGE { running: false };",
            {"id": state[0]["id"]}
        )
    return {"status": "ok", "running": False}
