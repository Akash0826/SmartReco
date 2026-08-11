"""
app/api/routes_admin.py
=======================

Responsibility:  FastAPI endpoints for adding/deleting products via the admin dashboard.

Pipeline Position: Routing Layer
"""

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_db
from app.services.catalog_service import create_product, delete_product, update_product

router = APIRouter(prefix="/admin/api/products", tags=["Admin"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_new_product(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Adds a new product to both Postgres and LanceDB (Dual-write)."""
    try:
        product = await create_product(
            session=db, 
            title=title, 
            description=description, 
            category=category, 
            price=price
        )
        return {"message": "Product successfully added and embedded.", "id": product.id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )

@router.put("/{product_id}")
async def edit_product(
    product_id: int,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Updates a product in the catalog and syncs the vector DB."""
    updated_product = await update_product(db, product_id, title, description, category, price)
    
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return {"status": "success", "product_id": updated_product.id}

@router.delete("/{product_id}")
async def remove_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Deletes a product from both databases."""
    success = await delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product successfully deleted."}