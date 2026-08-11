"""
core/ontology.py
================
Responsibility : Defines the strict Pydantic contracts for the Agentic Knowledge Graph (AKG).
                 It acts as the universal schema blueprint, supporting both flat, deterministic 
                 relational database tables and deeply nested, unconstrained data (like forms). 
                 This ensures seamless and type-safe data handoffs between the Cartographer, 
                 the DSPy Neural Agents, and the NetworkX Graph Manager.              
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# 1. KEY MANAGEMENT (Original Flavor)
# ═══════════════════════════════════════════════════════════════════════════

class PrimaryKey(BaseModel):
    """Represents a Primary Key entity."""
    column_name: str

class ForiegnKey(BaseModel):
    """Represents a Foriegn Key entity."""
    source_column: str
    target_table: str
    target_column: str

class NullableField(BaseModel):
    """Represents a field that allows NULL values."""
    column_name: str

class DataTypeField(BaseModel):
    """Represents the data type of a column."""
    data_type: str

class KeyManager:
    """
    Called by the schema extractor to generate and manage keys. 
    If you need to add logic later for inferring missing keys (e.g., guessing based on column names), 
    it will live here.
    """
    @staticmethod
    def build_primary_key(column_name: str) -> PrimaryKey:
        return PrimaryKey(column_name=column_name)

    @staticmethod
    def build_foriegn_key(src_col: str, tgt_table: str, tgt_col: str) -> ForiegnKey:
        return ForiegnKey(
            source_column=src_col, 
            target_table=tgt_table, 
            target_column=tgt_col
        )

    @staticmethod
    def build_nullable_field(column_name: str) -> NullableField:
        return NullableField(column_name=column_name)


# ═══════════════════════════════════════════════════════════════════════════
# 2. UNSTRUCTURED NESTING (The New Superpower)
# ═══════════════════════════════════════════════════════════════════════════

class NestedField(BaseModel):
    """
    Recursive model used strictly for unconstrained, unstructured data 
    (e.g., JSON documents, Onboarding Forms where contact_details -> phone).
    """
    field_name: str = Field(..., description="The name of the nested property.")
    data_type: str = Field(..., description="The type of data (e.g., Object, Array, String).")
    sub_fields: Optional[List['NestedField']] = Field(
        default=None, 
        description="Allows infinite nesting for complex hierarchies."
    )

# Required by Pydantic to resolve the recursive type hint above
NestedField.update_forward_refs()


# ═══════════════════════════════════════════════════════════════════════════
# 3. GRAPH NODES & EDGES
# ═══════════════════════════════════════════════════════════════════════════

class TableNode(BaseModel):
    """
    Represents a distinct entity in the graph. 
    Can handle flat SQL schemas OR nested unstructured forms.
    """
    node_id: str = Field(..., description="Unique identifier (e.g., table name or document name)")
    table_name: str = Field(..., description="The physical table or document name")
    
    # --- FLAT RELATIONAL DATA (Original Flavor) ---
    fields_names: List[str] = Field(default_factory=list, description="The names of the columns in the table.")
    datatypes: List[str] = Field(default_factory=list, description="The data types of the columns in the table.")
    null_allowed_fields: List[str] = Field(default_factory=list, description="Whether the columns are allowed to have null values.")
    primary_key: Optional[str] = None
    foriegn_keys: List[str] = Field(default_factory=list, description="The foriegn keys of the table.")
    
    # --- NESTED DATA CAPABILITY ---
    complex_schema: Optional[List[NestedField]] = Field(
        default=None,
        description="Populate this instead of 'fields_names' for unstructured nested documents."
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="System-level tracking (e.g., row_count, schema_name)")

class JoinEdge(BaseModel):
    """
    Replaces BaseEdge. Represents a Foriegn Key constraint connecting two tables.
    This is what the K-Shortest Paths algorithm will treat as an Edge.
    """
    source_id: str = Field(..., description="The table where the foriegn key lives.")
    target_id: str = Field(..., description="The table being referenced (usually the primary key table).")
    source_column: str = Field(..., description="The specific FK column in the source table.")
    target_column: str = Field(..., description="The specific PK column in the target table.")
    cost_weight: float = Field(
        default=1.0, 
        description="The traversal cost. 1.0 = direct indexed PK/FK. Higher = penalized join."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., constraint_name, on_delete_behavior)"
    )