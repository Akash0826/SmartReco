"""
app/core/postgres_db.py
=======================

Responsibility:  Manages the async SQLAlchemy engine and session factory for PostgreSQL.

Pipeline Position: Infrastructure - Relational DB Connection
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Ensure the URL uses the asyncpg driver (e.g., postgresql+asyncpg://user:pass@localhost/db)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/smartreco"
)

# Create the async engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,           # Set to True for debugging SQL queries
    pool_size=10,         # Connection pool size optimized for async workers
    max_overflow=20
)

# Session factory for creating new DB sessions per request
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Base class for all our SQLAlchemy models
Base = declarative_base()

async def get_db():
    """
    Dependency function to be used in FastAPI routes.
    Yields a database session and safely closes it after the request completes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()