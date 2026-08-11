"""
app/models/product.py
=====================

Responsibility:  SQLAlchemy schema for the product catalog (source of truth).

Pipeline Position: Data Layer - Relational Schema
"""

from sqlalchemy import String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.core.postgres_db import Base
from datetime import datetime, UTC

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))