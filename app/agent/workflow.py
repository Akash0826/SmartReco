"""
app/agent/workflow.py
=====================

Responsibility:  Compiles the nodes and edges into the final executable LangGraph state machine.

Pipeline Position: AI Workflow - Graph Assembly
"""

from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import analyze_behavior, retrieve_products, generate_recommendation

def build_recommendation_graph():
    """Compiles the LangGraph workflow for the recommendation agent."""
    workflow = StateGraph(AgentState)
    
    # Define the nodes (the steps)
    workflow.add_node("analyze", analyze_behavior)
    workflow.add_node("retrieve", retrieve_products)
    workflow.add_node("generate", generate_recommendation)
    
    # Define the edges (the flow)
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()

# This executor will be imported and called by our background task or API route
agent_executor = build_recommendation_graph()