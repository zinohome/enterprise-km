import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.66.163:11434")
OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_URL", "http://192.168.66.40:5055")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://192.168.66.40:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "enterprise-km")
