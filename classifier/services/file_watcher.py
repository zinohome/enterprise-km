import httpx
import asyncio
from loguru import logger
from classifier.core.config import OPEN_NOTEBOOK_URL, MINIO_ENDPOINT, MINIO_BUCKET, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
from classifier.services.classifier import classify_document, extract_keywords


async def process_new_file(file_key: str, user_id: str = None) -> dict | None:
    """Create Open Notebook source from MinIO file, trigger processing, then auto-classify."""
    try:
        # 1. Create source in Open Notebook
        file_name = file_key.split("/")[-1]
        source_payload = {
            "title": file_name,
            "type": "minio",
            "config": {
                "endpoint": MINIO_ENDPOINT.replace("http://", ""),
                "bucket": MINIO_BUCKET,
                "key": file_key,
                "access_key": MINIO_ACCESS_KEY,
                "secret_key": MINIO_SECRET_KEY,
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OPEN_NOTEBOOK_URL}/api/sources",
                json=source_payload
            )
            if resp.status_code != 200:
                logger.error(f"Failed to create source: {resp.status_code} {resp.text}")
                return None
            source = resp.json()
            source_id = source.get("id")
            logger.info(f"Source created: {source_id} for {file_key}")

            # 2. Trigger processing
            resp = await client.post(
                f"{OPEN_NOTEBOOK_URL}/api/sources/{source_id}/retry",
                timeout=300
            )
            logger.info(f"Processing triggered for {source_id}: {resp.status_code}")

            # 3. Wait a bit then auto-classify
            await asyncio.sleep(5)
            try:
                resp = await client.get(f"{OPEN_NOTEBOOK_URL}/api/sources/{source_id}")
                if resp.status_code == 200:
                    source_data = resp.json()
                    content = source_data.get("content", "") or source_data.get("text", "") or file_name
                    classification = await classify_document(content)
                    keywords = await extract_keywords(content)

                    return {
                        "source_id": source_id,
                        "file_key": file_key,
                        "user_id": user_id,
                        "classification": classification,
                        "keywords": keywords,
                    }
            except Exception as e:
                logger.warning(f"Auto-classify failed for {source_id}: {e}")

            return {"source_id": source_id, "file_key": file_key, "user_id": user_id}
    except Exception as e:
        logger.error(f"process_new_file failed: {e}")
        return None


async def process_batch_files(files: list[dict]) -> list[dict]:
    """Process multiple files in parallel."""
    tasks = [process_new_file(f["key"], f.get("user_id")) for f in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]
