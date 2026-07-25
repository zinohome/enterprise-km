from fastapi import APIRouter, Depends
from server.domain.user import User
from server.api.deps import get_current_user
from server.core.database import db_query

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_logs(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Permission denied")
    result = await db_query("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 100;")
    return result


@router.get("/stats")
async def audit_stats(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("admin", "manager"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Permission denied")
    total_users = await db_query("SELECT count() FROM user GROUP ALL;")
    total_sources = await db_query("SELECT count() FROM source GROUP ALL;")
    total_notes = await db_query("SELECT count() FROM note GROUP ALL;")
    return {
        "users": total_users[0]["count"] if total_users else 0,
        "sources": total_sources[0]["count"] if total_sources else 0,
        "notes": total_notes[0]["count"] if total_notes else 0,
    }
