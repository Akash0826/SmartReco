"""
init_db.py
==========

Responsibility:  Initializes the PostgreSQL database by dropping old data and creating new tables based on SQLAlchemy models.

Pipeline Position: Database Setup/Initialization Script
"""

import asyncio
from app.core.postgres_db import engine, Base
# Importing models ensures they are registered with Base.metadata
from app.models.user import User
from app.models.product import Product
from app.models.event import Event
from app.models.recommendation import Recommendation

async def setup_database():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Clears old data for testing
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Postgres Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(setup_database())