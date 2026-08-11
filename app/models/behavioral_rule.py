"""app/models/behavioral_rule.py
==========================
Responsibility: SQLAlchemy schema for storing smartreco's validated behavioral DAG edges.
Pipeline Position: Data Layer - Relational Schema
"""

from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.postgres_db import Base
from datetime import datetime, UTC

class BehavioralRule(Base):
    __tablename__ = "behavioral_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_behavior: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    target_behavior: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    # smartreco DAG metadata
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'asymmetric_compensation', 'degradation'
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    direction_meaning: Mapped[str] = mapped_column(String(500), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))