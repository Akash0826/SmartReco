"""
app/models/__init__.py
=======================

Responsibility:  Aggregates all SQLAlchemy models so Alembic can detect them for migrations.

Pipeline Position: Data Layer - Schema Registry
"""

# Import Base and all models here so Alembic can discover them easily
from app.core.postgres_db import Base
from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.recommendation import Recommendation
from app.models.enrollment import Enrollment # <-- ADD THIS

__all__ = ["Base", "User", "Product", "Event", "Recommendation", "BehavioralRule", "Enrollment"]