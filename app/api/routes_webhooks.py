"""
app/api/routes_webhooks.py
==========================

Responsibility:  FastAPI endpoints to ingest external 3rd-party events into our behavioral DB.

Pipeline Position: Routing Layer
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_db
from app.services.tracking_service import process_event_batch

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/external", status_code=status.HTTP_202_ACCEPTED)
async def external_event_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Receives external events (e.g., from an email provider or payment gateway)
    and treats them as behavioral data for the AI agent.
    """
    user_id = payload.get("user_id")
    event_data = payload.get("event")
    
    if user_id and event_data:
        # Format the single event into the batch format expected by our service
        formatted_event = {
            "event_type": "external_integration",
            "metadata_payload": event_data
        }
        await process_event_batch(db, user_id, [formatted_event])
        
    return {"status": "received"}