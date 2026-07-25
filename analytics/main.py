"""
Enterprise KM Analytics — 知识分析服务
知识仪表盘、缺口分析、智能推荐、学习路径
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Enterprise KM Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics"}

@app.get("/api/analytics/dashboard")
async def dashboard():
    return {
        "total_docs": 0,
        "by_type": {},
        "by_category": {},
        "hot_docs": [],
        "gaps": [],
    }

@app.get("/api/analytics/usage")
async def usage():
    return {
        "searches": 0,
        "questions": 0,
        "active_users": 0,
    }
