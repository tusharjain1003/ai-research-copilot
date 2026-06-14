import logging

from langgraph.graph import StateGraph, START, END

from app.workflow.state import GraphState
from app.workflow.nodes import (
    planner,
    source_collection,
    analysis,
    risk_unknowns,
    quality_check,
    enrich_unknowns,
    report_generation,
    failure_handler,
)

logger = logging.getLogger(__name__)

MAX_ENRICH_RETRIES = 1


def route_after_quality(state: GraphState) -> str:
    if state.get("errors"):
        return "errors"

    quality_result = state.get("quality_result", {})
    passed = quality_result.get("passed", False)

    if passed:
        return "sufficient"

    enrich_retries = quality_result.get("enrich_retries", 0)
    if enrich_retries < MAX_ENRICH_RETRIES:
        return "enrich"

    return "sufficient"


def build_research_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner)
    graph.add_node("source_collection", source_collection)
    graph.add_node("analysis", analysis)
    graph.add_node("risk_unknowns", risk_unknowns)
    graph.add_node("quality_check", quality_check)
    graph.add_node("enrich_unknowns", enrich_unknowns)
    graph.add_node("report_generation", report_generation)
    graph.add_node("failure_handler", failure_handler)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "source_collection")
    graph.add_edge("source_collection", "analysis")
    graph.add_edge("analysis", "risk_unknowns")
    graph.add_edge("risk_unknowns", "quality_check")

    graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {
            "sufficient": "report_generation",
            "enrich": "enrich_unknowns",
            "errors": "failure_handler",
        },
    )

    graph.add_edge("enrich_unknowns", "quality_check")

    graph.add_edge("report_generation", END)
    graph.add_edge("failure_handler", END)

    return graph


research_graph = build_research_graph()
compiled_graph = research_graph.compile()
