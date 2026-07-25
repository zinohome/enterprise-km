"""
Enterprise KM Analytics — 知识分析服务
知识仪表盘、缺口分析、智能推荐、学习路径
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from surrealdb import Surreal
from loguru import logger

from analytics.core.config import SURREAL_URL, SURREAL_USER, SURREAL_PASSWORD, SURREAL_NS, SURREAL_DB

app = FastAPI(title="Enterprise KM Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = Surreal(SURREAL_URL)
    db.signin({"user": SURREAL_USER, "pass": SURREAL_PASSWORD})
    db.use(SURREAL_NS, SURREAL_DB)
    return db


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics"}


@app.get("/api/analytics/dashboard")
async def dashboard():
    """知识仪表盘：文档总量、分类分布、热门文档、知识缺口"""
    db = get_db()
    try:
        # Total docs
        result = db.query("SELECT count() FROM source GROUP ALL;")
        total = 0
        for r in result:
            if isinstance(r, dict):
                total = r.get("count", 0)
                break

        # By type
        result = db.query("SELECT source_type, count() FROM source GROUP BY source_type;")
        by_type = {}
        for r in result:
            if isinstance(r, dict):
                by_type[r.get("source_type", "unknown")] = r.get("count", 0)

        # By status
        result = db.query("SELECT status, count() FROM source GROUP BY status;")
        by_status = {}
        for r in result:
            if isinstance(r, dict):
                by_status[r.get("status", "unknown")] = r.get("count", 0)

        # Knowledge gaps (categories with < 5 docs)
        gaps = []
        for cat, count in by_type.items():
            if count < 5:
                gaps.append({"category": cat, "count": count, "threshold": 5})

        return {
            "total_docs": total,
            "by_type": by_type,
            "by_status": by_status,
            "gaps": gaps,
        }
    finally:
        db.close()


@app.get("/api/analytics/usage")
async def usage():
    """使用统计"""
    return {
        "searches_today": 0,
        "questions_today": 0,
        "active_users": 0,
        "total_docs": 0,
    }


@app.get("/api/analytics/recommendations")
async def recommendations(
    doc_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """智能推荐：处理过这个故障的人还看了..."""
    return {
        "doc_id": doc_id,
        "recommendations": [],
        "message": "推荐引擎将在更多数据积累后启用",
    }


@app.get("/api/analytics/learning-path")
async def learning_path(
    position: str = Query(..., description="岗位名称"),
):
    """学习路径推荐"""
    paths = {
        "注塑操作员": [
            {"order": 1, "title": "注塑机操作标准流程", "doc_id": "SOP-INJ-001", "priority": "high"},
            {"order": 2, "title": "注塑工艺规范", "doc_id": "PS-INJ-003", "priority": "high"},
            {"order": 3, "title": "注塑件外观检验标准", "doc_id": "QS-VIS-012", "priority": "medium"},
            {"order": 4, "title": "注塑缩痕故障分析", "doc_id": "FA-2024-056", "priority": "medium"},
        ],
        "质量检验员": [
            {"order": 1, "title": "注塑件外观检验标准", "doc_id": "QS-VIS-012", "priority": "high"},
            {"order": 2, "title": "注塑缩痕故障分析", "doc_id": "FA-2024-056", "priority": "high"},
            {"order": 3, "title": "注塑工艺规范", "doc_id": "PS-INJ-003", "priority": "medium"},
        ],
        "工艺工程师": [
            {"order": 1, "title": "注塑工艺规范", "doc_id": "PS-INJ-003", "priority": "high"},
            {"order": 2, "title": "模具修改 ECN", "doc_id": "ECN-2024-056", "priority": "high"},
            {"order": 3, "title": "注塑缩痕故障分析", "doc_id": "FA-2024-056", "priority": "medium"},
            {"order": 4, "title": "注塑机操作标准流程", "doc_id": "SOP-INJ-001", "priority": "low"},
        ],
    }

    return {
        "position": position,
        "path": paths.get(position, []),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5060)
