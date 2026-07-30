"""
MinIO Webhook 接收器 — 接收 MinIO 事件，启动处理链路
"""
from fastapi import APIRouter, Request, HTTPException
from loguru import logger
import json

from worker.orchestrator import start_pipeline

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/minio")
async def minio_webhook(request: Request):
    """接收 MinIO bucket 事件通知。"""
    try:
        body = await request.json()
        logger.info(f"MinIO webhook received: {json.dumps(body, default=str)[:500]}")
    except Exception:
        body = await request.body()
        logger.info(f"MinIO webhook raw: {body[:500]}")

    records = body.get("Records", []) if isinstance(body, dict) else []
    results = []
    for record in records:
        s3 = record.get("s3", {})
        bucket_name = s3.get("bucket", {}).get("name", "")
        object_key = s3.get("object", {}).get("key", "")
        if not object_key:
            continue

        user_id = "system"
        parts = object_key.split("/")
        if parts and parts[0].startswith("user_"):
            user_id = parts[0].replace("user_", "")

        logger.info(f"Processing: bucket={bucket_name}, key={object_key}, user={user_id}")
        result = start_pipeline(object_key, user_id)
        results.append(result)

    return {"status": "ok", "processed": len(results), "results": results}


@router.post("/minio/test")
async def minio_webhook_test(request: Request):
    """测试端点：手动触发处理链路。"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    object_key = body.get("object_key", "")
    user_id = body.get("user_id", "system")

    if not object_key:
        raise HTTPException(status_code=400, detail="object_key required")

    result = start_pipeline(object_key, user_id)
    return {"status": "ok", "result": result}
