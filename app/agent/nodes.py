"""
app/agent/nodes.py
==================
Responsibility: Defines the individual functions (nodes) executed by LangGraph.
Pipeline Position: AI Workflow - Execution Nodes
"""
import os
import logging
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.agent.prompts import GENERATION_PROMPT
from app.agent.state import AgentState
from app.core.lancedb_client import search_similar_products
from sqlalchemy.future import select
from app.core.postgres_db import AsyncSessionLocal
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.behavioral_rule import BehavioralRule

logger = logging.getLogger(__name__)

async def analyze_behavior(state: AgentState):
    """
    Node 1: Analyzes raw events and anchors RAG intent to current enrollments.
    """
    recent_events = state.get("recent_events", [])
    user_id = state.get("user_id")
    keywords = []
    
    # 1. Extract recent clicks/searches
    for event in recent_events:
        if not isinstance(event, dict): 
            continue
        meta = event.get("metadata", {})
        if not isinstance(meta, dict): 
            meta = {}
        for key in ["search_query", "search_term", "topic_clicked", "category", "product_title"]:
            if key in meta and meta[key]:
                keywords.append(str(meta[key]))
                
    seen = set()
    unique_keywords = [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))]

    enrolled_summary = "User is not currently enrolled in any courses."
    smartreco_rules_summary = "No specific structural rules discovered yet."
    enrolled_titles = []
    
    async with AsyncSessionLocal() as session:
        if user_id:
            # 2. Fetch Active Enrollments
            enroll_stmt = select(Product.title, Product.category).join(Enrollment).where(Enrollment.user_id == user_id)
            enroll_res = await session.execute(enroll_stmt)
            enrolled_courses = enroll_res.fetchall()
            
            if enrolled_courses:
                enrolled_titles = [c.title for c in enrolled_courses]
                enrolled_summary = ", ".join([f"'{c.title}' ({c.category})" for c in enrolled_courses])
                
        # 3. Fetch smartreco Rules
        rule_stmt = select(BehavioralRule).order_by(BehavioralRule.weight.desc()).limit(5)
        rule_res = await session.execute(rule_stmt)
        rules = rule_res.scalars().all()
        if rules:
            smartreco_rules_summary = "\n".join([f"- Pattern: {r.source_behavior} strongly predicts {r.target_behavior}. Insight: {r.direction_meaning}" for r in rules])

    # 4. Anchor LanceDB Vector Search Intent
    if enrolled_titles and unique_keywords:
        intent_summary = f"Core subjects: {', '.join(enrolled_titles)}. Recent secondary interests: {', '.join(unique_keywords)}."
    elif enrolled_titles:
        intent_summary = f"Advanced subjects related to: {', '.join(enrolled_titles)}."
    elif unique_keywords:
        intent_summary = f"User actively explored: {', '.join(unique_keywords)}."
    else:
        intent_summary = "Modern skills in Data Science, Web Development, and AI."

    return {
        "user_intent_summary": intent_summary,
        "enrolled_courses": enrolled_summary,
        "smartreco_rules": smartreco_rules_summary
    }

# app/agent/nodes.py

async def retrieve_products(state: AgentState):
    """
    Node 2: Performs Semantic Vector Search via LanceDB.
    If LanceDB returns fewer than 3 products, uses targeted keyword/category 
    matching in Postgres instead of pulling random arbitrary products.
    """
    user_id = state.get("user_id")
    user_intent = state.get("user_intent_summary", "")
    logger.info(f"Retrieving non-enrolled products for intent: '{user_intent}' (User ID: {user_id})")
    
    enrolled_ids = set()
    if user_id:
        async with AsyncSessionLocal() as session:
            stmt = select(Enrollment.product_id).where(Enrollment.user_id == user_id)
            result = await session.execute(stmt)
            enrolled_ids = set(result.scalars().all())

    # 1. Semantic Vector Search via LanceDB
    retrieved_records = await search_similar_products(user_intent, limit=10)
    
    matched_products = []
    for record in retrieved_records:
        if "id" in record:
            try:
                pid = int(record["id"])
                if pid not in enrolled_ids:
                    matched_products.append({
                        "id": pid,
                        "title": record.get("title"),
                        "category": record.get("category"),
                        "description": record.get("text", "")[:150]
                    })
            except (ValueError, TypeError):
                pass

    # 2. Smart Targeted Fallback (if LanceDB yields < 3 non-enrolled items)
    if len(matched_products) < 3:
        # Extract potential subject keywords from the intent summary
        known_topics = ["Data Science", "Machine Learning", "Python", "AI Agents", "Web Development", "Cloud", "Cybersecurity", "DevOps"]
        detected_terms = [t for t in known_topics if t.lower() in user_intent.lower()]

        async with AsyncSessionLocal() as session:
            already_selected_ids = enrolled_ids.union({p["id"] for p in matched_products})
            
            stmt = select(Product)
            if already_selected_ids:
                stmt = stmt.where(Product.id.not_in(already_selected_ids))
            
            # Filter Postgres fallback using detected intent terms
            if detected_terms:
                from sqlalchemy import or_
                conditions = []
                for term in detected_terms:
                    conditions.append(Product.category.ilike(f"%{term}%"))
                    conditions.append(Product.title.ilike(f"%{term}%"))
                stmt = stmt.where(or_(*conditions))

            stmt = stmt.limit(3 - len(matched_products))
            res = await session.execute(stmt)
            fallback_prods = res.scalars().all()

            # If keyword filter was too strict, grab remaining available items as last resort
            if len(matched_products) + len(fallback_prods) < 3:
                needed = 3 - (len(matched_products) + len(fallback_prods))
                existing_ids = already_selected_ids.union({p.id for p in fallback_prods})
                extra_stmt = select(Product).where(Product.id.not_in(existing_ids) if existing_ids else True).limit(needed)
                extra_res = await session.execute(extra_stmt)
                fallback_prods.extend(extra_res.scalars().all())

            for p in fallback_prods:
                matched_products.append({
                    "id": p.id, 
                    "title": p.title, 
                    "category": p.category, 
                    "description": p.description[:150]
                })

    return {
        "retrieved_products": matched_products[:3],
        "recommended_product_ids": [p["id"] for p in matched_products[:3]]
    }

async def generate_recommendation(state: AgentState):
    """
    Node 3: Generates the personalized narrative using the Mesh API LLM and rich context.
    """
    retrieved_products = state.get("retrieved_products", [])
    user_intent = state.get("user_intent_summary", "")
    enrolled_courses = state.get("enrolled_courses", "None")
    smartreco_rules = state.get("smartreco_rules", "None")
    retrieved_ids = state.get("recommended_product_ids", [])
    
    # Format the recommended products nicely for the LLM prompt
    product_context = json.dumps([{k: v for k, v in p.items() if k != "id"} for p in retrieved_products], indent=2)

    try:
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "openai/gpt-4o"),
            api_key=os.getenv("MESH_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.meshapi.ai/v1"),
            temperature=0.7
        )
        
        prompt = PromptTemplate.from_template(GENERATION_PROMPT)
        chain = prompt | llm
        
        response = await chain.ainvoke({
            "events": user_intent,
            "enrolled_courses": enrolled_courses,
            "smartreco_rules": smartreco_rules,
            "products": product_context
        })
        
        narrative = response.content.strip()
        
    except Exception as e:
        logger.error(f"Mesh API Recommendation Generation Error: {e}")
        narrative = f"We noticed your interest in {user_intent}. Based on your current enrollments, here are our top curated picks to accelerate your learning journey!"

    return {
        "narrative": narrative,
        "recommended_product_ids": retrieved_ids
    }