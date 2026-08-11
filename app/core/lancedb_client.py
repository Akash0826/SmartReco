"""
app/core/lancedb_client.py
==========================
Responsibility: Handles local embedding generation via HuggingFace and LanceDB dual-writes/retrieval.
Pipeline Position: Core Data Layer
"""

import os
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.vector_db import get_catalog_table

logger = logging.getLogger(__name__)

# Initialize free local embedding model (runs 100% locally on your CPU)
hf_embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
)

async def get_mesh_embedding(text: str) -> list[float]:
    """Generates an embedding locally using Sentence Transformers instead of network calls."""
    try:
        return hf_embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"Local Embedding generation failed: {str(e)}")
        dimension = int(os.getenv("VECTOR_DIMENSION", "384"))
        return [0.0] * dimension


async def add_product_embedding(product):
    """
    Creates a semantic document from a product and dual-writes it to LanceDB.
    """
    try:
        text_to_embed = f"Course Title: {product.title}. Category: {product.category}. Description: {product.description}"
        
        # Generate vector locally
        vector = await get_mesh_embedding(text_to_embed)
        
        # Add to LanceDB
        table = get_catalog_table()
        table.add([{
            "id": str(product.id),
            "vector": vector,
            "text": text_to_embed,
            "category": product.category or "Uncategorized",
            "title": product.title
        }])
        
        logger.info(f"✅ Successfully dual-written Product ID {product.id} to LanceDB.")
        
    except Exception as e:
        logger.error(f"❌ LanceDB dual-write failed for Product ID {product.id}: {str(e)}")


async def search_similar_products(query_text: str, limit: int = 3):
    """
    Performs a semantic search (RAG) against the catalog using LanceDB.
    """
    try:
        query_vector = await get_mesh_embedding(query_text)
        table = get_catalog_table()
        results = table.search(query_vector).limit(limit).to_list()
        return results
    except Exception as e:
        logger.error(f"LanceDB search failed: {str(e)}")
        return []