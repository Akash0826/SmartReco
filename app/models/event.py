"""
app/models/event.py
===================

Responsibility:  SQLAlchemy schema for storing high-frequency behavioral tracking payloads.

Pipeline Position: Data Layer - Relational Schema
"""

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.postgres_db import Base
from datetime import datetime, UTC

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    
    # e.g., 'page_view', 'product_click', 'search', 'time_on_page'
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    
    # Optional: If the event is specifically tied to a product
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True, nullable=True)
    
    # Flexible payload for varying event data (e.g., {"search_term": "python", "scroll_depth": 80})
    metadata_payload: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    # Relationships
    user = relationship("User", back_populates="events")
    product = relationship("Product")