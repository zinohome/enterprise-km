"""Analytics configuration."""
import os

SURREAL_URL = os.getenv("SURREAL_URL", "ws://192.168.66.40:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASSWORD = os.getenv("SURREAL_PASSWORD", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "open_notebook")
SURREAL_DB = os.getenv("SURREAL_DB", "open_notebook")
