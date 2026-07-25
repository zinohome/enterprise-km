import os
import secrets

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(64))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "480"))

SURREAL_URL = os.getenv("SURREAL_URL", "ws://192.168.66.40:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASSWORD = os.getenv("SURREAL_PASSWORD", "root")
SURREAL_NAMESPACE = os.getenv("SURREAL_NAMESPACE", "open_notebook")
SURREAL_DATABASE = os.getenv("SURREAL_DATABASE", "open_notebook")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")
