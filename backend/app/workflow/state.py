from typing import TypedDict


class GraphState(TypedDict):
    session_id: str
    company_name: str
    website_url: str
    research_objective: str
    plan: dict
    source_text: str
    source_metadata: list
    analysis_output: dict
    risks_and_unknowns: dict
    quality_result: dict
    final_report: dict
    warnings: list[str]
    errors: list[str]
    workflow_status: str
