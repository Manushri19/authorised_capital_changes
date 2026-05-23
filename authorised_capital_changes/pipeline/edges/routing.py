"""
Main Pipeline Runner (routing.py)
================================
Orchestrates the execution of nodes using LangGraph based on the strict routing logic.
Human review has been removed — unconfirmed fields are flagged in the output instead.
"""

from typing import Sequence
from langgraph.graph import StateGraph, END

from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.pipeline.nodes import (
    run_ingestion,
    run_classifier,
    run_relationship_resolver,
    run_attachment_extractor,
    run_sh7_extractor,
    run_validator,
    run_assembler,
    run_narrative_generator,
)


def route_after_classifier(state: PipelineState) -> str:
    """
    classifier_node
        → [terminate with error] if sh7_documents empty after dedup
        → relationship_resolver_node (sh7_documents)
    """
    sh7s = state.get("sh7_documents") or []
    if not sh7s:
        return END
    return "relationship_resolver_node"


def route_after_sh7_extractor(state: PipelineState) -> str:
    """
    sh7_extractor_node
        → [terminate with error] if zero successful extractions
        → validator_node (at least one extraction succeeded)
    """
    extracted_sh7s = state.get("extracted_sh7s") or []
    if not extracted_sh7s:
        return END
    return "validator_node"


def route_after_validator(state: PipelineState) -> str:
    """
    validator_node
        → [terminate with partial error] if zero passed validation
        → assembler_node (at least one passed)
    """
    passed = state.get("sh7s_passed_validation") or []
    if not passed:
        return END
    return "assembler_node"


def build_pipeline_graph():
    """
    Constructs the directed acyclic graph (DAG) for the capital intelligence pipeline.
    Linear flow: ingestion → classifier → resolver → attachment_extractor →
    sh7_extractor → validator → assembler → narrative_generator
    """
    workflow = StateGraph(PipelineState)

    # 1. Add all nodes
    workflow.add_node("ingestion_node", run_ingestion)
    workflow.add_node("classifier_node", run_classifier)
    workflow.add_node("relationship_resolver_node", run_relationship_resolver)
    workflow.add_node("attachment_extractor_node", run_attachment_extractor)
    workflow.add_node("sh7_extractor_node", run_sh7_extractor)
    workflow.add_node("validator_node", run_validator)
    workflow.add_node("assembler_node", run_assembler)
    workflow.add_node("narrative_generator_node", run_narrative_generator)

    # 2. Set Entry Point
    workflow.set_entry_point("ingestion_node")

    # 3. Add Standard Edges
    workflow.add_edge("ingestion_node", "classifier_node")
    workflow.add_edge("relationship_resolver_node", "attachment_extractor_node")
    workflow.add_edge("attachment_extractor_node", "sh7_extractor_node")
    workflow.add_edge("assembler_node", "narrative_generator_node")

    # 4. Add Terminal Edges
    workflow.add_edge("narrative_generator_node", END)

    # 5. Add Conditional Edges (single-destination, no parallel branching)
    workflow.add_conditional_edges(
        "classifier_node",
        route_after_classifier,
        {
            "relationship_resolver_node": "relationship_resolver_node",
            END: END
        }
    )
    workflow.add_conditional_edges(
        "sh7_extractor_node",
        route_after_sh7_extractor,
        {
            "validator_node": "validator_node",
            END: END
        }
    )
    workflow.add_conditional_edges(
        "validator_node",
        route_after_validator,
        {
            "assembler_node": "assembler_node",
            END: END
        }
    )

    # 6. Compile and return
    return workflow.compile()
