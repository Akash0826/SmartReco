"""
app/api/routes_views.py
=======================
Responsibility: Serves Jinja2 HTML templates and handles frontend routing.
Pipeline Position: UI Controller
"""
from datetime import datetime, UTC
from fastapi import APIRouter, Request, Depends, status, HTTPException, Body, BackgroundTasks, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from app.core.postgres_db import get_db
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.user import User
from app.models.event import Event
from app.services.recommendation_service import get_latest_recommendation, generate_and_store_recommendation
from app.api.routes_auth import get_current_user
from sqlalchemy import delete

router = APIRouter(tags=["Views"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def homepage(request: Request, category: str = None, db: AsyncSession = Depends(get_db)):
    """Renders the main user dashboard."""
    user_id_cookie = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    
    if not user_id_cookie:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    recommendation = None
    recommended_products = []
    category_products = []
    
    # FETCH ENROLLED IDs FOR UI STATE
    enroll_query = await db.execute(select(Enrollment.product_id).where(Enrollment.user_id == user_id))
    enrolled_product_ids = enroll_query.scalars().all()
    
    reco = await get_latest_recommendation(db, user_id)
    if reco:
        recommendation = reco
        query = select(Product).where(Product.id.in_(reco.recommended_product_ids))
        result = await db.execute(query)
        recommended_products = result.scalars().all()
        
    # Inside async def homepage(...)
    
    if category:
        # Extract the core text (e.g., "🚀 AI Agents" -> "AI Agents")
        core_text = category.split(" ", 1)[1] if " " in category else category
        
        # Use ILIKE to match the category text, regardless of the emoji in the DB
        query = select(Product).where(Product.category.ilike(f"%{core_text}%"))
        
        result = await db.execute(query)
        category_products = result.scalars().all()

    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "user_id": user_id, 
            "user_role": user_role,
            "recommendation": recommendation,
            "recommended_products": recommended_products,
            "category_products": category_products,
            "selected_category": category,
            "enrolled_product_ids": enrolled_product_ids
        }
    )

@router.get("/products")
async def catalog(request: Request, db: AsyncSession = Depends(get_db)):
    """Renders the full course catalog."""
    user_id_cookie = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    
    if not user_id_cookie:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    enroll_query = await db.execute(select(Enrollment.product_id).where(Enrollment.user_id == user_id))
    enrolled_product_ids = enroll_query.scalars().all()
    
    query = select(Product)
    result = await db.execute(query)
    products = result.scalars().all()
    
    return templates.TemplateResponse(
        "product_list.html", 
        {
            "request": request, 
            "products": products, 
            "user_id": user_id, 
            "user_role": user_role,
            "enrolled_product_ids": enrolled_product_ids
        }
    )

@router.get("/products/{product_id}")
async def product_detail_page(product_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Renders a single product page for enrollment."""
    user_id_cookie = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role", "user")
    
    if not user_id_cookie:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        return RedirectResponse(url="/products")
        
    is_enrolled = False
    if user_role == "user":
        enroll_query = select(Enrollment).where(
            Enrollment.user_id == user_id, 
            Enrollment.product_id == product_id
        )
        enroll_result = await db.execute(enroll_query)
        if enroll_result.scalar_one_or_none():
            is_enrolled = True
            
    return templates.TemplateResponse(
        "product_detail.html", 
        {
            "request": request, 
            "product": product,
            "user_id": user_id,
            "user_role": user_role,
            "is_enrolled": is_enrolled
        }
    )

class EnrollRequest(BaseModel):
    product_id: int

@router.post("/api/enroll")
async def enroll_in_course(
    payload: EnrollRequest, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """API Endpoint to securely enroll a user in a course and refresh AI recommendations."""
    try:
        user_id_cookie = request.cookies.get("user_id")
        if not user_id_cookie:
            raise HTTPException(status_code=401, detail="Unauthorized")
            
        user_id = int(user_id_cookie)
        product_id = payload.product_id
        
        query = select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.product_id == product_id)
        result = await db.execute(query)
        
        if not result.scalar_one_or_none():
            new_enrollment = Enrollment(user_id=user_id, product_id=product_id)
            db.add(new_enrollment)
            await db.commit()
            
            # Asynchronously refresh the user's learning path
            background_tasks.add_task(generate_and_store_recommendation, user_id)
            
        return {"status": "success"}
    except Exception as e:
        print(f"ENROLLMENT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/enrolled")
async def enrolled_courses_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Renders the courses the user has enrolled in."""
    user_id_cookie = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    
    if not user_id_cookie or user_role != "user":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    query = select(Product).join(Enrollment).where(Enrollment.user_id == user_id)
    result = await db.execute(query)
    enrolled_products = result.scalars().all()
    
    return templates.TemplateResponse(
        "enrolled_courses.html", 
        {
            "request": request, 
            "products": enrolled_products, 
            "user_id": user_id, 
            "user_role": user_role
        }
    )

@router.get("/login")
async def login_page(request: Request):
    """Renders the glassmorphic login screen."""
    user_role = request.cookies.get("user_role")
    if user_role == "admin":
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    elif user_role == "user":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/admin")
async def admin_page(request: Request, category: str = None, db: AsyncSession = Depends(get_db)):
    """Renders the Admin dashboard and protects it from unauthorized access."""
    user_id_cookie = request.cookies.get("user_id")
    user_role = request.cookies.get("user_role")
    
    if not user_id_cookie or user_role != "admin":
        return RedirectResponse(url="/login" if not user_id_cookie else "/", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    query = select(Product)
    # Inside async def admin_page(...)
    
    query = select(Product)
    
    if category:
        # Extract the core text (e.g., "☁️ Cloud Computing" -> "Cloud Computing")
        core_text = category.split(" ", 1)[1] if " " in category else category
        
        # Use ILIKE to match the category text, regardless of the emoji in the DB
        query = query.where(Product.category.ilike(f"%{core_text}%"))
        
    result = await db.execute(query)
    products = result.scalars().all()

    return templates.TemplateResponse(
        "admin.html", 
        {
            "request": request, 
            "user_id": user_id, 
            "user_role": user_role,
            "products": products,
            "selected_category": category
        }
    )

@router.get("/recommended")
@router.get("/recommendations")
async def view_recommendations(
    request: Request, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Single unified route to render AI-curated recommendations and candidate course cards."""
    enroll_stmt = select(Enrollment.product_id).where(Enrollment.user_id == current_user.id)
    enroll_res = await db.execute(enroll_stmt)
    enrolled_ids = set(enroll_res.scalars().all())
    
    recommendation = await get_latest_recommendation(db, current_user.id)
    recommended_courses = []
    
    if recommendation and recommendation.recommended_product_ids:
        target_ids = []
        for pid in recommendation.recommended_product_ids:
            try:
                int_id = int(pid)
                if int_id not in enrolled_ids:
                    target_ids.append(int_id)
            except (ValueError, TypeError):
                continue
                
        if target_ids:
            prod_stmt = select(Product).where(Product.id.in_(target_ids))
            prod_res = await db.execute(prod_stmt)
            recommended_courses = list(prod_res.scalars().all())
            
    if not recommended_courses:
        fallback_stmt = select(Product)
        if enrolled_ids:
            fallback_stmt = fallback_stmt.where(Product.id.not_in(enrolled_ids))
        fallback_stmt = fallback_stmt.limit(3)
        
        fallback_res = await db.execute(fallback_stmt)
        recommended_courses = list(fallback_res.scalars().all())
        
    template_name = "recommended_courses.html"
    narrative_text = recommendation.narrative if recommendation else "Explore our curated picks for you!"
    
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "narrative": narrative_text,
            "recommendation": recommendation,
            "courses": recommended_courses,
            "products": recommended_courses,
            "user": current_user,
            "user_id": current_user.id,
            "user_role": getattr(current_user.role, "value", str(current_user.role))
        }
    )

@router.post("/unenroll")
async def unenroll_from_course(
    request: Request,
    background_tasks: BackgroundTasks,
    product_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Safely removes a user's enrollment record from PostgreSQL.
    Triggers an AI path recalculation and redirects back to the enrolled courses page.
    """
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    user_id = int(user_id_cookie)
    
    try:
        stmt = delete(Enrollment).where(
            Enrollment.user_id == user_id, 
            Enrollment.product_id == product_id
        )
        await db.execute(stmt)
        await db.commit()
        
        # Asynchronously refresh the user's learning path
        background_tasks.add_task(generate_and_store_recommendation, user_id)
        
    except Exception as e:
        print(f"UNENROLL ERROR: {str(e)}")
        await db.rollback()
        
    return RedirectResponse(url="/enrolled", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/ask_assistant")
async def ask_assistant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Captures explicit user input via AJAX, logs the behavioral event, 
    forces the LangGraph agent to generate a path, and returns success to the UI.
    """
    # 1. Flexibly parse the payload (handles both JSON and Form Data)
    try:
        payload = await request.json()
        user_prompt = payload.get("user_prompt") or payload.get("prompt") or ""
    except Exception:
        form = await request.form()
        user_prompt = form.get("user_prompt") or form.get("prompt") or ""

    if not user_prompt:
        raise HTTPException(status_code=422, detail="Prompt is missing or empty")

    # 2. Process the valid prompt
    try:
        new_event = Event(
            user_id=current_user.id,
            event_type="explicit_prompt",
            metadata_payload={"search_query": user_prompt},
            # Fixed timezone mismatch for Postgres
            timestamp=datetime.now(UTC).replace(tzinfo=None) 
        )
        db.add(new_event)
        await db.commit()
        
        # Synchronously trigger the LangGraph AI Agent to process this new intent
        await generate_and_store_recommendation(current_user.id)
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Assistant Prompt Error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process prompt")