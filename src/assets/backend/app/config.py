"""Startup configuration loaded from environment variables and the local .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]

CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:4173', 'http://127.0.0.1:4173']


def load_config():
    load_dotenv(BACKEND_ROOT / ".env")
    return {
        "MONGO_URI": os.getenv("MONGO_URI"),
        "OPENROUTER_KEY": os.getenv("openrouter_key"),
        "TOKEN_SECRET": os.getenv("Token_secret_key"),
        "ADMIN_SECRET": os.getenv("ADMIN_SECRET_KEY"),
        "CORS_ORIGINS": [origin.strip() for origin in os.getenv("CORS_ORIGINS", ",".join(CORS_ORIGINS)).split(",") if origin.strip()],
        "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
    }
