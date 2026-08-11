import asyncio
from datetime import datetime
from sqlalchemy import select
from app.core.postgres_db import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

async def seed_mock_users():

    from app.core.postgres_db import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        print("Checking for existing users...")
        
        # 1. Create Admin
        admin_query = await session.execute(select(User).where(User.email == "admin@smartreco.com"))
        if not admin_query.scalar_one_or_none():
            admin = User(
                id=99,  # <-- Explicit ID to avoid Postgres sequence collision
                email="admin@smartreco.com", 
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                created_at=datetime.now().replace(tzinfo=None)
            )
            session.add(admin)
            print("✅ Admin user staged.")

        # 2. Create Normal User
        user_query = await session.execute(select(User).where(User.email == "user@smartreco.com"))
        if not user_query.scalar_one_or_none():
            normal_user = User(
                id=100,  # <-- Explicit ID to avoid Postgres sequence collision
                email="user@smartreco.com", 
                hashed_password=hash_password("user123"),
                role=UserRole.USER,
                created_at=datetime.now().replace(tzinfo=None)
            )
            session.add(normal_user)
            print("✅ Standard user staged.")

        try:
            await session.commit()
            print("✅ Database seeding complete!")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error during seeding: {e}")

if __name__ == "__main__":
    asyncio.run(seed_mock_users())