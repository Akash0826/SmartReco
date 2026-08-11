"""
app/api/routes_auth.py
======================
Responsibility: Handles user login, password verification, session cookies, and user retrieval dependencies.
Pipeline Position: Authentication / Security Gate
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.postgres_db import get_db
from app.models.user import User, UserRole
from app.services.auth_service import verify_password

# Mounts under the /auth prefix in __init__.py
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency that reads the user_id cookie set during login
    and fetches the corresponding User model from PostgreSQL.
    """
    user_id_str = request.cookies.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in."
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session format."
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists."
        )

    return user


@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies user credentials, sets session cookies, and routes to the correct dashboard.
    """
    # 1. Fetch user from the database by email
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # 2. Verify existence and password match safely
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password."
        )

    # 3. Safely determine role (Handles both Enum objects and raw strings)
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role).lower()
    redirect_url = "/admin" if role_str == "admin" else "/"

    # 4. Construct the response and set HTTP-only cookies
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    
    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    response.set_cookie(key="user_role", value=role_str, httponly=True)

    return response


@router.get("/logout")
async def logout():
    """
    Clears the session cookies and redirects to the login screen.
    """
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Obliterate the session data
    response.delete_cookie("user_id")
    response.delete_cookie("user_role")
    
    return response