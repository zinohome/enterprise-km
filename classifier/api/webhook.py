from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from classifier.services.file_watcher import process_new_file

router = APIRouter(prefix="/webhook", tags=["webhook"])


class MinioEvent(BaseModel):
    EventName: str
    Key: str
    Records: Optional[list] = None


@router.post("/minio")
async def minio_webhook(request: Request, background_tasks: BackgroundTasks):
    """MinIO bucket notification webhook. Triggers on s3:ObjectCreated:* events."""
    try:
        body = await request.json()
        logger.info(f"MinIO webhook received: {str(body)[:200]}")

        records = body.get("Records", [body])
        for record in records:
            event_name = record.get("eventName", "")
            key = record.get("s3", {}).get("object", {}).get("key", "")
            user_meta = record.get("userMetadata", {})
            user_id = user_meta.get("X-Amz-Meta-User-Id", "unknown")

            if not key:
                continue

            if "ObjectCreated" in event_name:
                background_tasks.add_task(process_new_file, key, user_id)
                logger.info(f"Queued processing for: {key} (user: {user_id})")

        return {"status": "ok", "message": "Webhook received"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/process")
async def manual_process(key: str, user_id: str = None):
    """Manually trigger file processing."""
    result = await process_new_file(key, user_id)
    return {"status": "ok", "result": result}
