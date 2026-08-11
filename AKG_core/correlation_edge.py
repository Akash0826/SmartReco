"""
AKG_Core/correlation_edge.py
=============================
Responsibility : Defines the strict Pydantic contracts for dynamically discovered 
                 structural relationships validated via the Merlin-Arthur protocol.
                 
                 This extends the existing AKG_Core ontology (TableNode + JoinEdge)
                 with a new edge class representing DISCOVERED correlations — as opposed
                 to PHYSICAL FK constraints.

                 JoinEdge = schema-defined, immutable, column-level.
                 CorrelationEdge = execution-discovered, ephemeral, entity-level.

Integration   : Shares the same node identity space as AKG_Core's TableNode.node_id.
                Both edge types coexist in a unified graph (Late-Binding Intent).
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════════════
# 1. VALIDATION STATUS (Arthur Protocol State Machine)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ValidationStatus(str, Enum):
    """
    Tracks the lifecycle of a discovered edge through the Merlin-Arthur protocol.
    
    State Machine:
        pending_arthur  →  verified_root     (arthur_cascade_impact > MLE threshold, root in DAG)
        pending_arthur  →  derived_insight   (cascade impact > 0, interior/leaf in DAG)
        pending_arthur  →  discarded_noise   (cascade impact ≈ 0, isolated node)
        verified_root   →  discarded_noise   (RL decay over N drops — pattern stopped appearing)
        derived_insight →  discarded_noise   (RL decay over N drops)
    """
    pending_arthur = "pending_arthur"
    verified_root = "verified_root"
    derived_insight = "derived_insight"
    discarded_noise = "discarded_noise"


# ═══════════════════════════════════════════════════════════════════════════════════════
# 2. CORRELATION EDGE (The  Discovery Contract)
# ═══════════════════════════════════════════════════════════════════════════════════════

class CorrelationEdge(BaseModel):
    """
    Represents a dynamically discovered structural relationship,
    validated via the Merlin-Arthur protocol (Cascading Negligence).
    
    This is the counterpart to AKG_Core's JoinEdge:
        - JoinEdge: Physical FK constraint (immutable, column-level, schema-defined)
        - CorrelationEdge: Statistical discovery (ephemeral, entity-level, execution-derived)
    
    Both coexist in the same graph. Late-Binding Intent ensures neither is pre-filtered
    during traversal — edge type is metadata on the output, not a filter on the input.
    """
    
    # --- IDENTITY ---
    source_entity: str = Field(
        ..., 
        description="The originating node (maps to TableNode.node_id in AKG_Core)."
    )
    target_entity: str = Field(
        ..., 
        description="The dependent node (maps to TableNode.node_id in AKG_Core)."
    )
    
    # --- MERLIN'S PROPOSAL (Discovery Phase) ---
    merlin_chi_squared: float = Field(
        ..., 
        description="The initial chi_squared statistical significance proposed by the discovery engine."
    )
    merlin_p_value: Optional[float] = Field(
        default=None,
        description="p_value associated with the chi_squared test. Lower = more significant."
    )
    
    # --- ARTHUR'S VERIFICATION (Validation Phase) ---
    arthur_cascade_impact: Optional[float] = Field(
        default=None, 
        description="The measurable delta_chi_squared collapse of the graph when this edge's equivalence class is removed."
    )
    arthur_compensation_signal: Optional[float] = Field(
        default=None,
        description="Load transfer signal: positive delta indicates another class absorbed this edge's role."
    )
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.pending_arthur, 
        description="Current lifecycle state in the Merlin-Arthur protocol."
    )
    
    # --- TOPOLOGY (DAG Position) ---
    equivalence_class_id: Optional[str] = Field(
        default=None,
        description="Which logical group this edge belongs to (endpoint reachability grouping)."
    )
    dag_depth: Optional[int] = Field(
        default=None,
        description="Topological position in Arthur's output DAG (0 = root, higher = deeper)."
    )
    
    # --- TEMPORAL (RL Lifecycle) ---
    first_observed: datetime = Field(
        default_factory=datetime.now,
        description="Data drop where this edge was first discovered."
    )
    last_observed: datetime = Field(
        default_factory=datetime.now,
        description="Most recent data drop where this edge was still significant."
    )
    observation_count: int = Field(
        default=1,
        description="Number of consecutive data drops where this edge appeared."
    )
    rl_weight: float = Field(
        default=1.0,
        description="Current reinforcement weight. Decays via EMA (alpha=0.2) across drops."
    )
    
    # --- METADATA ---
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g., discovery context, source data drop id)."
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# 3. EQUIVALENCE CLASS (Grouping Contract)
# ═══════════════════════════════════════════════════════════════════════════════════════

class EquivalenceClass(BaseModel):
    """
    Represents a group of CorrelationEdges that connect the same logical endpoints
    (directly or transitively). Identified via Union-Find on endpoint reachability.
    
    Arthur's Cascading Negligence operates on equivalence classes, not individual edges.
    Removing the entire class reveals true structural impact without redundancy masking.
    """
    
    class_id: str = Field(
        ..., 
        description="Unique identifier for this equivalence class."
    )
    member_edges: List[str] = Field(
        default_factory=list,
        description="List of (source_entity, target_entity) tuples belonging to this class."
    )
    logical_source: str = Field(
        ..., 
        description="The abstract source endpoint this class connects."
    )
    logical_target: str = Field(
        ..., 
        description="The abstract target endpoint this class connects."
    )
    edge_count: int = Field(
        default=0,
        description="Number of individual edges in this class."
    )
    aggregate_chi_squared: Optional[float] = Field(
        default=None,
        description="Combined chi_squared significance of the class (max or mean of member edges)."
    )