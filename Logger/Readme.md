# Generic Execution Logger

**Location:** `~/Logger` (User Home Directory)  
**Responsibility:** A centralized, application-agnostic logging microservice designed to handle logs from multiple enterprise applications simultaneously without cluttering project repositories.

## Key Features
- **Autonomous Garbage Collection:** Automatically purges log files older than 7 days to protect disk space (`_cleanup_old_logs`).
- **Audit Delimiters:** Wraps JSON payloads in strict `@@success@@` and `@@failed@@` delimiters for easy log parsing, observability, and downstream ingestion.
- **Fail-Safe Parsing:** Silently catches exceptions in data extraction layers to ensure pipeline continuity.
- **Daily Rotation:** Generates date-stamped log files automatically (e.g., `2026-05-20.log`).
- **Zero-Config Portability:** Automatically anchors to the active user's home directory across Linux, Windows, and AWS environments without requiring `.env` variables.

---

## Project Mapping

Currently, the logger is providing telemetry for the following registered applications:

### 1. APEx Analytics Framework
APEx heavily relies on the generic logger to track the journey of dynamic SQL execution, Polars LazyFrame transformations, and LLM orchestration. 

**Integration Areas within APEx:**

| Module | Logger Function Used | Purpose |
| :--- | :--- | :--- |
| `api.py` | `get_app_logger` | Tracks frontend REST API requests, SQL inputs, and HTTP response states. |
| `Agent/Analytics_Agent.py` | `@audit_logger` | Wraps the main execution pipeline. Captures the final processed JSON result dict and tags it with success/failure delimiters. |
| `Loader/SQL_Parser_Agent.py` | `@safe_parse_logger`, `get_app_logger` | Wraps AST deconstruction. If SQLGlot fails to parse a hallucinated SQL string, it silently catches the error and returns a safe fallback. |
| `Agent/Summary_Agent.py` | `get_app_logger` | Tracks the execution of the LLM Groq client during natural language summarization. |

---

## Developer Usage Guide

To connect a new project or module to this centralized logger, you must bootstrap the path dynamically before importing. 

### 1. The Bootstrap (Recommended)
Create a `Logger_Bootstrap.py` in your project to dynamically locate the logger:
```python
import os
import sys

def setup_external_logger():
    logger_dir = os.path.join(os.path.expanduser("~"), "Logger")
    if logger_dir not in sys.path:
        sys.path.insert(0, logger_dir)

setup_external_logger()
from Execution_Logger import get_app_logger, audit_logger, safe_parse_logger