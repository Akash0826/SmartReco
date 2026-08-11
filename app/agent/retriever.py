"""
app/agent/retriever.py
======================

Responsibility: Embeds search queries and fetches semantic matches from LanceDB.

Pipeline Position: AI Workflow - RAG / Vector Retrieval
"""

import logging
from typing import List, Dict, Any
import lancedb

from app.config import settings
from app.core.mesh_client import mesh_client, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

async def get_embedding(text: str) -> List[float]:
    """Generates a vector embedding for the search query using the Mesh API."""
    try:
        response = await mesh_client.embeddings.create(
            input=text,
            model=DEFAULT_EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        return []
        
async def retrieve_products(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Embeds the LangGraph search query and retrieves the top_k most relevant 
    products from the LanceDB vector database.
    """
    if not query:
        return []
        
    logger.info(f"Executing LanceDB vector search for: '{query}'")
    
    try:
        # Connect to the embedded LanceDB instance
        db = lancedb.connect(settings.LANCEDB_URI)
        
        # Gracefully handle the case where the admin hasn't added any products yet
        if "products" not in db.table_names():
            logger.warning("LanceDB 'products' table does not exist yet. Add products via Admin panel.")
            return []
            
        table = db.open_table("products")
        
        # Generate the vector for the AI's search query
        query_vector = await get_embedding(query)
        if not query_vector:
            return []
            
        # Execute the vector search
        results = table.search(query_vector).limit(top_k).to_list()
        
        # Clean up the results to pass back into the LangGraph state
        retrieved = []
        for r in results:
            retrieved.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "category": r.get("category"),
                "description": r.get("description"),
                "price": r.get("price")
            })
            
        return retrieved
        
    except Exception as e:
        logger.error(f"LanceDB retrieval failed: {str(e)}")
        return []