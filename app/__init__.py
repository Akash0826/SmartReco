"""
app/__init__.py
===============

Responsibility:  FastAPI app factory, mounts static files, templates, routers, and lifespans.

Pipeline Position: Web Server Initialization
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.tasks.email_tasks import start_scheduler
import os
from app.api import routes_views, routes_admin, routes_auth, routes_tracking

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    print("Starting up SmartReco services...")
    start_scheduler()
    yield
    # --- Shutdown Logic ---
    print("Shutting down SmartReco...")

def create_app() -> FastAPI:
    app = FastAPI(title="SmartReco API")

    # Static files mount
    app_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(app_dir, "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(routes_views.router)
    app.include_router(routes_admin.router)
    app.include_router(routes_auth.router) 
    app.include_router(routes_tracking.router)

    return app