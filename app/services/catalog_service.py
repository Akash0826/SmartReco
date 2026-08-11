"""
app/services/catalog_service.py
===============================

Responsibility:  Handles the atomic dual-write of products to both Postgres and LanceDB.

Pipeline Position: Business Logic Layer
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models.product import Product
from app.core.lancedb_client import add_product_embedding
from app.models.event import Event

logger = logging.getLogger(__name__)

async def create_product(
    session: AsyncSession, 
    title: str, 
    description: str, 
    category: str, 
    price: float
) -> Product:
    """Creates a new product in PostgreSQL with naive UTC timestamps and dual-writes to Vector DB."""
    
    # Strip timezone offset to match TIMESTAMP WITHOUT TIME ZONE in Postgres[cite: 3]
    now_naive = datetime.now().replace(tzinfo=None)
    
    product = Product(
        title=title,
        description=description,
        category=category,
        price=price,
        created_at=now_naive,
        updated_at=now_naive
    )
    
    # 1. Write to Primary Database (PostgreSQL)[cite: 3]
    session.add(product)
    await session.commit()
    await session.refresh(product)

    # 2. Dual-Write to Semantic Database (LanceDB)
    try:
        await add_product_embedding(product)
    except Exception as e:
        logger.error(f"Vector DB dual-write failed for Product ID {product.id}: {str(e)}")

    return product

async def update_product(
    session: AsyncSession, 
    product_id: int, 
    title: str, 
    description: str, 
    category: str, 
    price: float
):
    """Updates an existing product in Postgres and syncs it with LanceDB."""
    query = select(Product).where(Product.id == product_id)
    result = await session.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        return None
        
    # Update Postgres fields
    product.title = title
    product.description = description
    product.category = category
    product.price = price
    product.updated_at = datetime.now().replace(tzinfo=None)
    
    await session.commit()
    await session.refresh(product)
    
    # Sync with LanceDB (Delete old vector, insert new one)
    try:
        from app.core.lancedb_client import get_catalog_table, get_mesh_embedding
        table = get_catalog_table()
        
        # Delete old semantic record
        table.delete(f"id = '{product.id}'")
        
        # Create and embed new semantic record
        text_to_embed = f"Course Title: {product.title}. Category: {product.category}. Description: {product.description}"
        vector = await get_mesh_embedding(text_to_embed)
        
        table.add([{
            "id": str(product.id),
            "vector": vector,
            "text": text_to_embed,
            "category": product.category or "Uncategorized",
            "title": product.title
        }])
    except Exception as e:
        logger.error(f"Vector DB sync failed for Product ID {product.id}: {str(e)}")

    return product

from sqlalchemy import delete
from app.models.enrollment import Enrollment
from app.models.event import Event
from app.models.product import Product

async def delete_product(session: AsyncSession, product_id: int) -> bool:
    """
    Deletes a product by first clearing its associated foreign key references
    in the events and enrollments tables.
    """
    try:
        # 1. Clear tracking event records linked to this product
        await session.execute(
            delete(Event).where(Event.product_id == product_id)
        )

        # 2. Clear enrollment records linked to this product
        await session.execute(
            delete(Enrollment).where(Enrollment.product_id == product_id)
        )

        # 3. Delete the product from the catalog
        stmt = delete(Product).where(Product.id == product_id)
        result = await session.execute(stmt)

        # 4. Commit changes
        await session.commit()

        return result.rowcount > 0

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        raise e