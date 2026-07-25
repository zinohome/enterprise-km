from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from server.domain.user import User
from server.core.database import db_query
from server.api.deps import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
):
    """Unified search across all accessible knowledge."""
    conditions = []
    params = {"query": f"%{q}%", "user_id": current_user.id, "limit": limit}

    if current_user.role == "admin":
        conditions.append("(title ~ $query OR content ~ $query)")
    else:
        conditions.append("""
            (title ~ $query OR content ~ $query)
            AND (
                owner_id = $user_id
                OR visibility = 'team'
                OR visibility = 'enterprise'
            )
        """)

    if category:
        conditions.append(f"category = '{category}'")
    if visibility:
        conditions.append(f"visibility = '{visibility}'")

    where = " AND ".join(conditions) if conditions else "true"
    query = f"SELECT * FROM source WHERE {where} LIMIT $limit;"

    results = await db_query(query, params)
    return {"query": q, "total": len(results), "results": results}


@router.get("/suggest")
async def search_suggest(
    q: str = Query(..., min_length=2),
    limit: int = Query(5, le=20),
    current_user: User = Depends(get_current_user),
):
    """Autocomplete suggestions."""
    results = await db_query(
        "SELECT title FROM source WHERE title ~ $query LIMIT $limit;",
        {"query": f"%{q}%", "limit": limit}
    )
    return [r["title"] for r in results]


@router.get("/stats")
async def search_stats(current_user: User = Depends(get_current_user)):
    """Knowledge base statistics."""
    total = await db_query("SELECT count() FROM source GROUP ALL;")
    by_category = await db_query("SELECT category, count() FROM source GROUP BY category;")
    by_visibility = await db_query("SELECT visibility, count() FROM source GROUP BY visibility;")
    recent = await db_query("SELECT count() FROM source WHERE created_at > time::now() - 7d GROUP ALL;")

    return {
        "total_documents": total[0]["count"] if total else 0,
        "by_category": {r["category"]: r["count"] for r in by_category} if by_category else {},
        "by_visibility": {r["visibility"]: r["count"] for r in by_visibility} if by_visibility else {},
        "recent_7d": recent[0]["count"] if recent else 0,
    }
