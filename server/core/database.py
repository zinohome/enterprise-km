from contextlib import asynccontextmanager
from typing import Optional
from surrealdb import AsyncSurreal
from .config import SURREAL_URL, SURREAL_USER, SURREAL_PASSWORD, SURREAL_NAMESPACE, SURREAL_DATABASE

_db: Optional[AsyncSurreal] = None


async def get_db() -> AsyncSurreal:
    global _db
    if _db is None:
        _db = AsyncSurreal(SURREAL_URL)
        await _db.signin({"username": SURREAL_USER, "password": SURREAL_PASSWORD})
        await _db.use(SURREAL_NAMESPACE, SURREAL_DATABASE)
    return _db


async def check_db_health() -> bool:
    try:
        db = await get_db()
        result = await db.query("RETURN true;")
        return bool(result)
    except Exception:
        return False


async def db_query(query: str, vars: dict = None):
    db = await get_db()
    return await db.query(query, vars or {})


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
