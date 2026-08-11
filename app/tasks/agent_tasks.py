"""
app/tasks/agent_tasks.py
========================

Responsibility:  Celery worker task that executes the LangGraph workflow out-of-band.

Pipeline Position: Background Worker Queue
"""

import asyncio
from app.core.celery_app import celery_app
from app.services.recommendation_service import generate_and_store_recommendation

@celery_app.task(name="trigger_agent_workflow", bind=True, max_retries=3)
def trigger_agent_workflow(self, user_id: int):
    """
    Celery task that safely executes the async LangGraph AI agent.
    """
    try:
        # Celery workers run synchronously, so we must start an async event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(generate_and_store_recommendation(user_id))
    except Exception as exc:
        # Retry with exponential backoff if the Mesh API fails
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)