"""
Enterprise_Trace_Writer.py
==========================
Responsibility: Centralized, application-agnostic utility to generate physical 
                execution trace artifacts. Uses a strict DTO to dynamically 
                format the output based on the calling project.
                Retention policy is dynamically controlled by the project environment.
"""

import os
import time
import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════
# 1. THE ENTERPRISE TRACE CONTRACT (DTO)
# ═══════════════════════════════════════════════════════════════════════════

class EnterpriseTraceDTO(BaseModel):
    """
    Strict contract dictating the structure of a physical trace file.
    Populated dynamically by the executing project (e.g., ADAPT, APEx).
    """
    project_name: str = Field(..., description="The name of the calling framework (e.g., 'ADAPT Framework')")
    user_prompt: str = Field(..., description="The raw input query, prompt, or ingress trigger")
    execution_result: Any = Field(..., description="The final optimized nodes, JSON payload, or string output")
    status: str = Field(default="SUCCESS", description="The final execution status")
    session_id: str = Field(default="unknown_session", description="The active session ID for grouping.")

# ═══════════════════════════════════════════════════════════════════════════
# 2. TRACE WRITER LOGIC & RETENTION
# ═══════════════════════════════════════════════════════════════════════════

# Delegate paths and retention policy to the local project environment
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())
TRACE_RETENTION_DAYS = int(os.environ.get("TRACE_RETENTION_DAYS", 3))

def _dynamic_cleanup(target_dir: str, env_var: str, default_hours: float):
    """
    Dynamically re-reads the .env file to check the purge time in HOURS.
    This allows tweaking the retention time on the fly without restarting Celery.
    """
    if not os.path.exists(target_dir):
        return
        
    # Force Python to grab live values from the .env file right now
    load_dotenv(override=True)
    retention_hours = float(os.environ.get(env_var, default_hours))
    
    current_time = time.time()
    cutoff_time = current_time - (retention_hours * 3600) # Convert hours to seconds
    
    for filename in os.listdir(target_dir):
        filepath = os.path.join(target_dir, filename)
        if os.path.isfile(filepath):
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                except Exception:
                    pass

# def _cleanup_old_traces(output_dir: str, retention_days: int = TRACE_RETENTION_DAYS):
#     """Silently deletes trace files older than the project-defined retention period."""
#     if not os.path.exists(output_dir):
#         return
        
#     current_time = time.time()
#     cutoff_time = current_time - (retention_days * 86400) 
    
#     for filename in os.listdir(output_dir):
#         if filename.startswith("trace_result_") or filename.startswith("api_execution_trace"):
#             filepath = os.path.join(output_dir, filename)
#             if os.path.getmtime(filepath) < cutoff_time:
#                 try:
#                     os.remove(filepath)
#                 except Exception:
#                     pass

def save_enterprise_trace(payload: EnterpriseTraceDTO) -> str:
    """
    Creates the project-specific output directory, cleans old traces, 
    and generates a strictly formatted physical artifact based on the DTO.
    """
    # Dynamically target the executing project's script_output folder
    #output_dir = os.path.join(PROJECT_ROOT, 'script_output')
    #os.makedirs(output_dir, exist_ok=True)
    
    # Run the retention cleanup before writing new files
    #_cleanup_old_traces(output_dir, retention_days=TRACE_RETENTION_DAYS)

    trace_dir = os.path.join(PROJECT_ROOT, 'script_output', 'traces')
    rec_dir = os.path.join(PROJECT_ROOT, 'script_output', 'recommendations')
    os.makedirs(trace_dir, exist_ok=True)
    os.makedirs(rec_dir, exist_ok=True)

    _dynamic_cleanup(trace_dir, "TRACE_RETENTION_HOURS", 72.0)
    _dynamic_cleanup(rec_dir, "REC_RETENTION_HOURS", 24.0)
    
    timestamp_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp_file = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    #file_path = os.path.join(output_dir, f"trace_result_{timestamp_file}.txt")
    
    # Safely stringify the result regardless of whether it's a dict, list, or string
    if isinstance(payload.execution_result, (dict, list)):
        formatted_result = json.dumps(payload.execution_result, indent=2)
    else:
        formatted_result = str(payload.execution_result)
    
    # Generate the agnostic formatted file
    trace_file_path = os.path.join(trace_dir, f"trace_{payload.session_id}_{timestamp_file}.txt")
    with open(trace_file_path, 'w', encoding='utf-8') as f:
        f.write(f"{payload.project_name}: Execution Trace Output\n")
        f.write("=======================================\n")
        f.write(f"Timestamp    : {timestamp_display}\n")
        f.write(f"Session ID   : {payload.session_id}\n")
        f.write(f"User Prompt  : {payload.user_prompt}\n")
        f.write(f"Final Output : {formatted_result}\n")
        f.write("=======================================\n")
        f.write(f"Status: {payload.status}\n")
    
    rec_file_path = os.path.join(rec_dir, f"rec_{payload.session_id}_{timestamp_file}.json")
    with open(rec_file_path, 'w', encoding='utf-8') as f:
        f.write(formatted_result)
        
    return trace_file_path