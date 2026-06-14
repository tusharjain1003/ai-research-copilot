from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkflowStepResponse(BaseModel):
    id: str
    node_name: str
    status: str
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkflowRunResponse(BaseModel):
    id: str
    session_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class RunStartResponse(BaseModel):
    run_id: str
    session_id: str
    status: str


class WorkflowStatusResponse(BaseModel):
    run: Optional[WorkflowRunResponse] = None
    steps: list[WorkflowStepResponse] = []


class ReportResponse(BaseModel):
    company_overview: str
    products_services: str
    target_customers: str
    business_signals: str
    risks_challenges: str
    discovery_questions: str
    outreach_strategy: str
    unknowns: str
    sources: str
