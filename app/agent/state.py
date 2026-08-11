"""
app/agent/state.py
==================
Responsibility:  Defines the TypedDict schema passed between nodes in the LangGraph workflow.
Pipeline Position: AI Workflow - State Definition
"""
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    user_id: int
    recent_events: List[Dict[str, Any]]
    
    # Context fields for the LLM
    smartreco_rules: str
    enrolled_courses: str 
    
    search_query: str
    retrieved_products: List[Dict[str, Any]]
    narrative: str
    recommended_product_ids: List[int]