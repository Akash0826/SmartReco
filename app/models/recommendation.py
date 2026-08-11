"""
app/models/recommendation.py
============================

Responsibility:  SQLAlchemy schema caching the AI's generated narratives and product IDs.

Pipeline Position: Data Layer - Relational Schema
"""

from sqlalchemy import Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.postgres_db import Base
from datetime import datetime, UTC

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    
    # The AI-generated persuasive story targeting this specific user
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    
    # List of integer product IDs retrieved from LanceDB (e.g., [12, 45, 9])
    recommended_product_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)
    
    # For the proactive delivery bonus: track if this has been emailed yet
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="recommendations")