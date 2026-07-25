"""
Enterprise KM Worker — 异步任务处理
处理文档解析、向量化、分类、发布
"""
import os
import sys
from rq import Worker, Queue, Connection
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.core.config import REDIS_URL

# Import tasks so they are registered
import worker.tasks.parse       # noqa: F401
import worker.tasks.vectorize   # noqa: F401
import worker.tasks.classify    # noqa: F401
import worker.tasks.identify    # noqa: F401
import worker.tasks.extract     # noqa: F401
import worker.tasks.graph       # noqa: F401
import worker.tasks.publish     # noqa: F401

logger.info(f"Worker starting, connecting to Redis: {REDIS_URL}")

if __name__ == "__main__":
    with Connection.from_url(REDIS_URL):
        queues = [
            Queue("default"),
            Queue("high"),
            Queue("low"),
        ]
        worker = Worker(queues)
        logger.info("Worker started, listening for tasks...")
        worker.work()
