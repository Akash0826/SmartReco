"""
app/core/mesh_client.py
=======================

Responsibility:  Initializes a singleton AsyncOpenAI client routed to the Mesh API gateway.

Pipeline Position: Infrastructure - External LLM Connection
"""

import logging
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Verify the API key is present before starting
if not settings.MESH_API_KEY:
    logger.error("MESH_API_KEY is missing from environment variables!")
    raise ValueError("MESH_API_KEY must be set in the .env file.")

# Initialize the asynchronous OpenAI client to route through the Mesh API Gateway
try:
    mesh_client = AsyncOpenAI(
        base_url="https://api.meshapi.ai/v1",
        api_key=settings.MESH_API_KEY,
        # Optional: Set timeout/retries for robust background task processing
        timeout=60.0,
        max_retries=3
    )
    logger.info("Mesh API client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Mesh API client: {str(e)}")
    raise e

# Define default model strings here so they can be easily updated in one place
# Mesh API requires the provider prefix (e.g., 'openai/', 'anthropic/')
DEFAULT_LLM_MODEL = "openai/gpt-4o"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"