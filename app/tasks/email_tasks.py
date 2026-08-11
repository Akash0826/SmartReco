"""
app/tasks/email_tasks.py
========================

Responsibility:  APScheduler job to proactively email unread AI recommendations as a daily digest.

Pipeline Position: Scheduled CRON Job
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.postgres_db import AsyncSessionLocal
from app.models.recommendation import Recommendation
from app.models.user import User
from app.models.product import Product

logger = logging.getLogger(__name__)

async def send_daily_digests():
    """
    Background job to send proactive emails to users with new AI recommendations.
    """
    logger.info("Starting scheduled daily digest delivery...")
    
    # Open a fresh database session for the background task
    async with AsyncSessionLocal() as session:
        try:
            # Fetch all recommendations that haven't been delivered yet, alongside user data
            query = (
                select(Recommendation)
                .options(selectinload(Recommendation.user))
                .where(Recommendation.is_delivered == False)
            )
            result = await session.execute(query)
            pending_recos = result.scalars().all()
            
            if not pending_recos:
                logger.info("No pending recommendations to send today.")
                return

            for reco in pending_recos:
                # 1. Fetch the actual product details for the email body
                product_query = select(Product).where(Product.id.in_(reco.recommended_product_ids))
                product_result = await session.execute(product_query)
                products = product_result.scalars().all()
                
                product_bullet_points = "\n".join([f"- {p.title} (${p.price})" for p in products])
                
                # 2. Construct the email (Simulating SMTP delivery via Logger)
                email_body = f"""
                =================================================
                TO: {reco.user.email}
                SUBJECT: Your Personalized Learning Path is Ready
                
                Hi there,
                
                {reco.narrative}
                
                Here is what we curated for you today:
                {product_bullet_points}
                
                Log in to start learning!
                =================================================
                """
                
                # In a real app, you'd use aiosmtplib or SendGrid API here.
                # For the hackathon, logging proves the agentic pipeline works end-to-end.
                logger.info(f"Delivered Email to {reco.user.email}:\n{email_body}")
                
                # 3. Mark as delivered so we don't spam the user tomorrow
                reco.is_delivered = True
            
            await session.commit()
            logger.info(f"Successfully processed {len(pending_recos)} daily digests.")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to execute daily digest task: {str(e)}")


def start_scheduler():
    """
    Initializes and starts the APScheduler instance.
    """
    scheduler = AsyncIOScheduler()
    
    # For hackathon demonstration purposes, you might want to run this every minute.
    # To do that, change to: trigger=CronTrigger(minute="*")
    # For a real daily digest, schedule it for 9:00 AM:
    scheduler.add_job(
        send_daily_digests,
        trigger=CronTrigger(hour=9, minute=0), 
        id="daily_email_digest",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started. Daily digest job registered.")