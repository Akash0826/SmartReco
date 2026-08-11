"""
app/api/routes_tracking.py
==========================

Responsibility:  FastAPI webhook endpoint to ingest batched tracking payloads from JavaScript.

Pipeline Position: Routing Layer
"""

import json
from fastapi import APIRouter, Depends, BackgroundTasks, status, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_db
from app.services.tracking_service import process_event_batch

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])

# Pydantic schema to validate incoming JavaScript tracker payload
class EventBatchPayload(BaseModel):
    user_id: int
    events: List[Dict[str, Any]]

@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def receive_event_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receives batched behavioral events from the frontend, bypassing header strictness."""
    
    try:
        raw_body = await request.body()
        data = json.loads(raw_body)
        
        # --- THE FIX: Sanitize incoming timestamps AND product IDs ---
        for evt in data.get("events", []):
            # 1. Fix timezone mismatch
            if "timestamp" in evt and isinstance(evt["timestamp"], str) and evt["timestamp"].endswith("Z"):
                evt["timestamp"] = evt["timestamp"][:-1]
                
            # 2. Fix integer mismatch for product_id
            pid = evt.get("product_id")
            if pid is not None:
                # If it's a string that can't be an int (like "ai_agents")
                if isinstance(pid, str) and not pid.isdigit():
                    # Move the string into metadata so we don't lose it
                    if "metadata_payload" not in evt:
                        evt["metadata_payload"] = {}
                    evt["metadata_payload"]["topic_clicked"] = pid
                    # Set the actual product_id column to None
                    evt["product_id"] = None
                else:
                    # Cast valid strings ("123") to integers
                    evt["product_id"] = int(pid)
                    
        payload = EventBatchPayload(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON payload: {str(e)}")

    # 2. Process events and check if the user hit the activity threshold
    should_trigger_ai = await process_event_batch(db, payload.user_id, payload.events)
    
    if should_trigger_ai:
        from app.services.recommendation_service import generate_and_store_recommendation
        background_tasks.add_task(generate_and_store_recommendation, payload.user_id)
        
    return {"status": "accepted", "events_processed": len(payload.events)}