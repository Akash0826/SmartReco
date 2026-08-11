"""
app/tasks/pattern_tasks.py
==========================
Responsibility: Extracts Postgres event data into Polars, runs the SmartReco pipeline,
                saves validated DAG rules, and generates physical execution traces.
Pipeline Position: Background Worker / Data Pipeline
"""
import os
import sys
import polars as pl
from sqlalchemy.future import select
from datetime import datetime
from app.core.postgres_db import AsyncSessionLocal
from app.models.event import Event
from app.models.behavioral_rule import BehavioralRule
from app.core.smartreco_engine import SmartRecoPipeline, SmartRecoConfig

def setup_external_logger():
    logger_dir = os.path.join(os.path.expanduser("~"), "Logger")
    if logger_dir not in sys.path:
        sys.path.insert(0, logger_dir)
setup_external_logger()

from Logger.Execution_Logger import get_app_logger, telemetry_span
from Logger.enterprise_trace_writer import save_enterprise_trace, EnterpriseTraceDTO

logger = get_app_logger("SmartReco_Task")

async def extract_events_to_polars(session) -> pl.DataFrame:
    query = select(Event)
    result = await session.execute(query)
    events = result.scalars().all()
    if not events: return pl.DataFrame()
    
    user_behavior_map = {}
    for event in events:
        uid = event.user_id
        if uid not in user_behavior_map: user_behavior_map[uid] = {"user_id": uid}
        event_col = f"event_{event.event_type}"
        user_behavior_map[uid][event_col] = user_behavior_map[uid].get(event_col, 0) + 1
        if event.product_id: user_behavior_map[uid][f"viewed_product_{event.product_id}"] = 1
        
    return pl.DataFrame(list(user_behavior_map.values())).fill_null(0)

async def run_behavioral_sweep():
    logger.info("Starting behavioral pattern discovery sweep...")
    async with AsyncSessionLocal() as session:
        try:
            df = await extract_events_to_polars(session)
            if df.is_empty() or df.height < 30: return
            
            with telemetry_span("SmartReco_Execution", "SmartReco_Logger") as (logger_out, token_tracker):
                pipeline = SmartRecoPipeline(SmartRecoConfig())
                pipeline.initialize()
                result = pipeline.execute(df=df, entity_prefix="user_behavior")
                
            if not result.dag or not result.dag.edges: return
            
            await session.run_sync(lambda sync_session: sync_session.query(BehavioralRule).delete())
            
            new_rules = [
                BehavioralRule(
                    source_behavior=edge.source, target_behavior=edge.target,
                    signal_type=edge.signal_type, weight=edge.weight, direction_meaning=edge.direction_meaning
                ) for edge in result.dag.edges
            ]
            session.add_all(new_rules)
            await session.commit()
            
            trace_payload = EnterpriseTraceDTO(
                project_name="SmartReco AI",
                user_prompt="CRON Trigger: Nightly Pattern Sweep",
                execution_result={
                    "verified_root_count": result.verified_root_count,
                    "edges_saved": len(new_rules)
                },
                session_id=f"sweep_{datetime.now().strftime('%Y%m%d')}"
            )
            save_enterprise_trace(trace_payload)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"@@failures@@ Sweep encountered a critical error: {str(e)}")