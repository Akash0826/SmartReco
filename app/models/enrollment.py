"""
app/models/enrollment.py
========================
Responsibility: SQLAlchemy schema linking Users to the Courses they are enrolled in.
Pipeline Position: Data Layer - Relational Schema
"""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.postgres_db import Base
from datetime import datetime, UTC

class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    
    enrolled_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now().replace(tzinfo=None))   
     
    # Prevent a user from enrolling in the same course twice
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uix_user_product_enrollment'),)

    # Relationships
    user = relationship("User")
    product = relationship("Product")