"""
app/core/celery_app.py
=======================

Responsibility:  Configures the Celery worker queue and Redis broker connection.

Pipeline Position: Infrastructure - Task Queue (Bonus)
"""

from celery import Celery
from app.config import settings

# Initialize Celery with Redis as both broker and backend
celery_app = Celery(
    "smartreco_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)