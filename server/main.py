from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from server.api import auth, users, categories, approvals, audit, teams, search, notifications, sync, permissions, auth_verify, curation
from server.core.config import CORS_ORIGINS, RATE_LIMIT
from server.core.database import check_db_health, close_db

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])

app = FastAPI(title="Enterprise KM Server", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(teams.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(sync.router)
app.include_router(permissions.router)
app.include_router(auth_verify.router)
app.include_router(curation.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": str(id(exc))},
    )


@app.get("/health")
async def health():
    db_ok = await check_db_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "enterprise-km-server",
        "database": "connected" if db_ok else "disconnected",
    }


@app.get("/metrics")
@limiter.exempt
async def metrics():
    from server.core.database import db_query
    try:
        users = await db_query("SELECT count() FROM user GROUP ALL;")
        sources = await db_query("SELECT count() FROM source GROUP ALL;")
        return {
            "users": users[0]["count"] if users else 0,
            "sources": sources[0]["count"] if sources else 0,
        }
    except Exception:
        return {"users": 0, "sources": 0}


@app.on_event("shutdown")
async def shutdown():
    await close_db()


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Enterprise KM Server on port 5056")
    uvicorn.run(app, host="0.0.0.0", port=5056)
