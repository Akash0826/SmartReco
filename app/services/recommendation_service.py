"""
app/services/recommendation_service.py
======================================

Responsibility:  Bridges the database to the LangGraph AI to generate and save recommendations.

Pipeline Position: Business Logic Layer
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.recommendation import Recommendation
from app.models.event import Event
from app.agent.workflow import agent_executor


logger = logging.getLogger(__name__)

async def get_latest_recommendation(session: AsyncSession, user_id: int):
    """Fetches the most recent AI recommendation for a given user."""
    query = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


from sqlalchemy.orm import selectinload
from app.models.event import Event

async def generate_and_store_recommendation(user_id: int):
    """Triggers the LangGraph agent with rich behavioral history."""
    from app.core.postgres_db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            # Fetch recent user events with associated product data
            query = (
                select(Event)
                .options(selectinload(Event.product))
                .where(Event.user_id == user_id)
                .order_by(Event.timestamp.desc())
                .limit(15)
            )
            result = await session.execute(query)
            events = result.scalars().all()
            
            event_list = []
            for e in events:
                payload = dict(e.metadata_payload) if e.metadata_payload else {}
                if e.product:
                    payload["product_title"] = e.product.title
                    payload["category"] = e.product.category
                
                event_list.append({
                    "event_type": e.event_type,
                    "metadata": payload
                })
            
            # Execute the LangGraph Agent workflow
            agent_input = {"user_id": user_id, "recent_events": event_list}
            agent_output = await agent_executor.ainvoke(agent_input)
            
            narrative = agent_output.get("narrative", "Here are custom recommendations based on your activity.")
            rec_ids = agent_output.get("recommended_product_ids", [])
            
        except Exception as e:
            logger.error(f"LLM/Agent failed (using fallback reco): {str(e)}")
            narrative = "Based on your recent activity, here are top picks tailored for you!"
            rec_ids = [1, 2]
            
        try:
            new_reco = Recommendation(
                user_id=user_id,
                narrative=narrative,
                recommended_product_ids=rec_ids,
                created_at=datetime.now().replace(tzinfo=None)
            )
            session.add(new_reco)
            await session.commit()
            
        except Exception as db_err:
            await session.rollback()
            logger.error(f"Failed to save recommendation to DB: {str(db_err)}")