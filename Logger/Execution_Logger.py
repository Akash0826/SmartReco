"""
execution_logger.py
===================
Responsibility: Centralized, application-agnostic logging configuration.
Autonomously purges logs older than 7 days to protect disk space.
Dynamically routes ONLY SUCCESS to Output folder, and ALL steps/results (Success/Fail) to Logger folder.
"""

import os
import json
import logging
import functools
import time
from datetime import datetime
from contextlib import contextmanager
import gzip
import shutil

# ═══════════════════════════════════════════════════════════════════════════
# CORE LOGGING MECHANICS (GENERIC)
# ═══════════════════════════════════════════════════════════════════════════

# ── 1. Dynamic Project-Level Path ──
# Instead of saving in the shared utility folder, it routes to a 'logs' 
# directory inside the root of whatever project is currently running.
# Uses an env variable for Docker safety, with os.getcwd() as the standard fallback.
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())
LOG_BASE_DIR = os.path.join(PROJECT_ROOT, "logs")
LOGGER_DIR = os.path.join(os.getcwd(), 'logs')
OUTPUT_DIR = os.path.join(os.getcwd(), 'outputs')

# Delegate retention policy to the project (Defaults to 30 if undeclared)
PROJECT_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", 30))
LOG_COMPRESSION_DAYS = int(os.environ.get("LOG_COMPRESSION_DAYS", 3))


class LLMTokenTracker:
    """
    Dedicated state manager for tracking LLM token consumption.
    """
    def __init__(self, model_name: str = "default_model"):
        self.model_name = model_name
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.is_completed = False

    def record_input(self, tokens: int):
        self.prompt_tokens = tokens

    def record_output(self, tokens: int):
        self.completion_tokens = tokens
        self.is_completed = True

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_log_string(self) -> str:
        return (f"| Model: {self.model_name} "
                f"| Prompt Tokens: {self.prompt_tokens} "
                f"| Completion Tokens: {self.completion_tokens} "
                f"| Total Tokens: {self.total_tokens}")
                
def _compress_old_logs(log_dir=LOG_BASE_DIR, compression_days=LOG_COMPRESSION_DAYS):
    """Compresses .log files older than the threshold into .log.gz to save space."""
    if not os.path.exists(log_dir):
        return
        
    current_time = time.time()
    cutoff_time = current_time - (compression_days * 86400) 
    
    for filename in os.listdir(log_dir):
        if filename.endswith(".log"):
            filepath = os.path.join(log_dir, filename)
            
            # Compress if the file is older than 3 days
            if os.path.getmtime(filepath) < cutoff_time:
                gz_filepath = f"{filepath}.gz"
                try:
                    with open(filepath, 'rb') as f_in:
                        with gzip.open(gz_filepath, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove the original uncompressed file
                    os.remove(filepath)
                    print(f">>> [Generic_Logger] Storage Maintenance: Compressed '{filename}'")
                except Exception as e:
                    print(f">>> [Generic_Logger] Failed to compress '{filename}': {e}")

def _cleanup_old_logs(log_dir=LOG_BASE_DIR, retention_days=7):
    """Deletes log files older than the specified retention period."""
    if not os.path.exists(log_dir):
        return
        
    current_time = time.time()
    cutoff_time = current_time - (retention_days * 86400) 
    
    for filename in os.listdir(log_dir):
        if filename.endswith(".log"):
            filepath = os.path.join(log_dir, filename)
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f">>> [Generic_Logger] Storage Maintenance: Purged old log '{filename}' in {log_dir}")
                except OSError:
                    pass

def _setup_daily_file_handler(target_dir: str = LOG_BASE_DIR) -> logging.FileHandler:
    os.makedirs(target_dir, exist_ok=True)
    
    # ── 2. Run Maintenance Triggers ──
    _compress_old_logs(log_dir=target_dir, compression_days=LOG_COMPRESSION_DAYS)
    _cleanup_old_logs(log_dir=target_dir, retention_days=PROJECT_RETENTION_DAYS)
    
    log_filename = os.path.join(target_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    handler = logging.FileHandler(log_filename)
    handler.setFormatter(logging.Formatter('%(message)s'))
    return handler

# ── CHANGE 2: Accept retention_days and pass it down to the handler ──
def get_app_logger(name: str, target_dir: str = LOGGER_DIR, retention_days: int = 7) -> logging.Logger:
    """Generic logger instantiation routed to a specific folder and the console."""
    logger_key = f"{name}_{os.path.basename(target_dir)}"
    logger = logging.getLogger(logger_key)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    if not logger.handlers:
        # 1. Write to the physical files (.log)
        logger.addHandler(_setup_daily_file_handler(target_dir))
        
        # 2. --- NEW: Echo the output to the Terminal ---
        import sys
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)
        
    return logger
    
# ═══════════════════════════════════════════════════════════════════════════
# TELEMETRY & ANALYTICS FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

@contextmanager
def telemetry_span(phase_name: str, logger_name: str, model_name: str = "default_model"):
    """Context Manager: Safely wraps an execution block to capture latency,
    token metrics, and errors, routing them to the appropriate folders."""
    logger_out = get_app_logger(logger_name, OUTPUT_DIR)
    logger_err = get_app_logger(logger_name, LOGGER_DIR)
    
    # Initialize our new token tracker
    token_tracker = LLMTokenTracker(model_name=model_name)
    
    start_time = time.time()
    dt_str_ingress = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger_err.info(f"{dt_str_ingress} | [{phase_name} INGRESS] Initiating...")
    try:
        # Yield BOTH the logger and the token tracker to the executing block
        yield logger_out, token_tracker
        
        duration = time.time() - start_time
        dt_str_egress = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success_msg = f"@@success@@ {dt_str_egress} | [{phase_name} EGRESS] finished | Latency: {duration:.4f}s {token_tracker.to_log_string()}"
        logger_out.info(success_msg)
        logger_err.info(success_msg)
    except Exception as e:
        duration = time.time() - start_time
        dt_str_fail = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fail_msg = f"@@failures@@ {dt_str_fail} | [{phase_name} CRITICAL] Crash after {duration:.4f}s {token_tracker.to_log_string()} | Error: {str(e)}"
        logger_err.error(fail_msg, exc_info=True)
        raise

def telemetry_tracker(phase_name: str):
    """Decorator: Captures performance metrics, token footprints, graph execution routing, AND response payloads."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger_out = get_app_logger(f"APEx_Telemetry_{phase_name}", OUTPUT_DIR)
            logger_err = get_app_logger(f"APEx_Telemetry_{phase_name}", LOGGER_DIR)
            start_time = time.time()
            dt_str_ingress = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger_err.info(f"{dt_str_ingress} | [{phase_name} INGRESS] Initiating execution of {func.__name__}...")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # --- 1. Extract Token Metrics ---
                token_metrics = ""
                if hasattr(result, "_metadata") and "usage" in getattr(result, "_metadata", {}):
                    usage = result._metadata["usage"]
                    token_metrics = f" | Prompt Tokens: {usage.get('prompt_tokens')} | Completion Tokens: {usage.get('completion_tokens')}"
                
                # --- 2. SAFELY SERIALIZE RESPONSE VALUE ---
                try:
                    if hasattr(result, "model_dump_json"):
                        response_val = result.model_dump_json(indent=2)
                    elif hasattr(result, "toDict"): # Catches DSPy Prediction objects
                        response_val = json.dumps(result.toDict(), indent=2, default=str)
                    elif isinstance(result, (dict, list)):
                        response_val = json.dumps(result, indent=2, default=str)
                    else:
                        response_val = str(result)
                except Exception as e:
                    response_val = f"<Unserializable Response Object: {e}>"

                # --- 3. Format the final Log Message ---
                dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                success_msg = (
                    f"@@success@@ {dt_str} | [{phase_name} EGRESS] {func.__name__} finished | Latency: {duration:.4f}s{token_metrics}\n"
                    f"=== AI RESPONSE PAYLOAD ===\n{response_val}\n==========================="
                )
                
                logger_out.info(success_msg)
                logger_err.info(success_msg)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger_err.error(
                    f"@@failures@@ {dt_str} | [{phase_name} CRITICAL] Crash detected in {func.__name__} "
                    f"after {duration:.4f}s | Error: {str(e)}", exc_info=True
                )
                raise
        return wrapper
    return decorator

def audit_logger(func):
    """Decorator: Wraps execution to log final JSON payloads with structured indentation."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger_out = get_app_logger(func.__name__, OUTPUT_DIR)
        logger_err = get_app_logger(func.__name__, LOGGER_DIR)
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict):
                payload_str = json.dumps(result, indent=2)
                dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if result.get("status") == "success":
                    msg = f"@@success@@ {dt_str}\n{payload_str}"
                    logger_out.info(msg)
                    logger_err.info(msg)
                else:
                    msg = f"@@failures@@ {dt_str}\n{payload_str}"
                    logger_err.error(msg)
            return result
        except Exception as e:
            error_payload = {"status": "failed", "error": str(e)}
            payload_str = json.dumps(error_payload, indent=2)
            dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger_err.error(f"@@failures@@ {dt_str}\n{payload_str}")
            return error_payload
    return wrapper

def safe_parse_logger(fallback_return="Sorry! ***No summary obtained at this point in time**"):
    """Decorator: Wraps Parser functions to catch exceptions and log them silently."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_app_logger(func.__name__, LOGGER_DIR)
                dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.error(f"@@failures@@ {dt_str} | Error in {func.__name__}: {e}")
                return fallback_return
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════════════════
# ADAPT FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

def adapt_rl_tracker(func):
    """Decorator: Silently tracks Reinforcement Learning Q-Weight updates."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger_out = get_app_logger("ADAPT_RL_Engine", OUTPUT_DIR)
        logger_err = get_app_logger("ADAPT_RL_Engine", LOGGER_DIR)
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict) and "new_weight" in result:
                dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                msg = (
                    f"@@success@@ {dt_str} | [RL_UPDATE] Edge ({result.get('source_id')} -> {result.get('target_id')}) "
                    f"| Weight Shift: {result.get('old_weight', 'N/A')} -> {result.get('new_weight')}"
                )
                logger_out.info(msg)
                logger_err.info(msg)
            return result
        except Exception as e:
            dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger_err.error(f"@@failures@@ {dt_str} | [RL_UPDATE_FAILED] {e}")
            raise
    return wrapper

def adapt_constraint_logger(func):
    """Decorator: Logs the Pass/Fail evaluations of our Deterministic Constraint Gates."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger_out = get_app_logger("ADAPT_Constraint_Gate", OUTPUT_DIR)
        logger_err = get_app_logger("ADAPT_Constraint_Gate", LOGGER_DIR)
        result = func(*args, **kwargs)
        dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if result:
            msg = f"@@success@@ {dt_str} | [CONSTRAINT_PASSED] {func.__name__}"
            logger_out.info(msg)
            logger_err.info(msg)
        else:
            logger_err.warning(f"@@failures@@ {dt_str} | [CONSTRAINT_FAILED] {func.__name__} rejected the proposed state.")
        return result
    return wrapper