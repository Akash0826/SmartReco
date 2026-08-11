"""
app/services/tracking_service.py
================================

Responsibility:  Receives batched frontend events, bulk inserts to DB, and checks AI triggers.

Pipeline Position: Business Logic Layer
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.event import Event
from datetime import datetime, UTC, timedelta

logger = logging.getLogger(__name__)

# Configurable threshold: How many events trigger a new AI recommendation?
AI_TRIGGER_THRESHOLD = 10 

async def process_event_batch(session: AsyncSession, user_id: int, events_data: List[Dict[str, Any]]) -> bool:
    """
    Bulk inserts behavioral events.
    Returns True if the user's recent activity crosses the threshold to trigger the AI agent.
    """
    if not events_data:
        return False
        
    try:
        # 1. Bulk insert events for efficiency
        db_events = [
            Event(
                user_id=user_id,
                event_type=event["event_type"],
                product_id=event.get("product_id"),
                metadata_payload=event.get("metadata_payload", {}),
                # Parse frontend timestamp, fallback to UTC now
                timestamp=datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00')) 
                          if "timestamp" in event else datetime.now(UTC)
            )
            for event in events_data
        ]
        
        session.add_all(db_events)
        await session.commit()
        
        # 2. Check if we should trigger the Agent
        should_trigger = await _check_agent_trigger_threshold(session, user_id)
        return should_trigger
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to process event batch for user {user_id}. Error: {e}")
        raise e


async def _check_agent_trigger_threshold(session: AsyncSession, user_id: int) -> bool:
    """
    Evaluates if the user has enough recent meaningful activity to generate a new recommendation.
    For production, this could be weighted (e.g., a purchase = 10 points, a view = 1 point).
    """
    # Look at activity in the last 5 minutes
    time_window = (datetime.now(UTC) - timedelta(minutes=5)).replace(tzinfo=None)
    
    query = select(func.count(Event.id)).where(
        Event.user_id == user_id,
        Event.timestamp >= time_window
    )
    
    result = await session.execute(query)
    recent_event_count = result.scalar() or 0
    
    if recent_event_count >= AI_TRIGGER_THRESHOLD:
        logger.info(f"User {user_id} crossed activity threshold ({recent_event_count} events). AI trigger primed.")
        return True
        
    return False