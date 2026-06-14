from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.workflow import (
    RunStartResponse,
    WorkflowStatusResponse,
    ReportResponse,
)
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/sessions", tags=["workflow"])


@router.post("/{session_id}/run", response_model=RunStartResponse, status_code=201)
def start_workflow(session_id: str, db: Session = Depends(get_db)):
    return WorkflowService.start_run(db, session_id)


@router.get("/{session_id}/workflow", response_model=WorkflowStatusResponse)
def get_workflow_status(session_id: str, db: Session = Depends(get_db)):
    return WorkflowService.get_workflow_status(db, session_id)


@router.get("/{session_id}/report", response_model=ReportResponse)
def get_report(session_id: str, db: Session = Depends(get_db)):
    return WorkflowService.get_report(db, session_id)
