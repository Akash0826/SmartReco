"""
app/config.py
=============

Responsibility:  Loads and validates environment variables (API keys, DB URIs) via Pydantic.

Pipeline Position: Configuration Layer (Accessed globally)
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MESH_API_KEY: str = "rsk_01KZ6SG0CST2XDQQR9FZR9MPSJ"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:infiniti@localhost:5432/smartreco"
    LANCEDB_URI: str = "./.lancedb_data"
    SECRET_KEY: str = "super-secret-hackathon-key"
    REDIS_URL: str = "redis://localhost:6379/0"  # For Celery (Bonus)
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()