import logging
import threading
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database.session import SessionLocal
from app.models.enums import SessionStatus, WorkflowRunStatus
from app.models.session import ResearchSession
from app.models.workflow import WorkflowRun, WorkflowStep
from app.models.report import ResearchReport
from app.schemas.workflow import (
    RunStartResponse,
    WorkflowRunResponse,
    WorkflowStepResponse,
    WorkflowStatusResponse,
    ReportResponse,
)
from app.workflow.graph import compiled_graph
from app.workflow.state import GraphState

logger = logging.getLogger(__name__)


def check_no_active_run(db: DBSession, session_id: str) -> None:
    """Raise 409 if the latest WorkflowRun for the session is pending/running."""
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.session_id == session_id)
        .order_by(WorkflowRun.created_at.desc())
        .first()
    )
    if run and run.status in (WorkflowRunStatus.pending, WorkflowRunStatus.running):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Research is currently running. "
                "Please wait until the workflow completes."
            ),
        )


class WorkflowService:

    @staticmethod
    def _get_session_or_404(db: DBSession, session_id: str) -> ResearchSession:
        session = (
            db.query(ResearchSession)
            .filter(ResearchSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        return session

    @staticmethod
    def start_run(db: DBSession, session_id: str) -> RunStartResponse:
        session = WorkflowService._get_session_or_404(db, session_id)

        active_run = (
            db.query(WorkflowRun)
            .filter(
                WorkflowRun.session_id == session_id,
                WorkflowRun.status.in_(
                    [WorkflowRunStatus.pending, WorkflowRunStatus.running]
                ),
            )
            .first()
        )
        if active_run:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Session {session_id} already has an active workflow run "
                    f"({active_run.id})"
                ),
            )

        run = WorkflowRun(
            session_id=session_id,
            status=WorkflowRunStatus.pending,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        thread = threading.Thread(
            target=_execute_workflow,
            args=(session_id,),
            daemon=True,
        )
        thread.start()

        return RunStartResponse(
            run_id=run.id,
            session_id=run.session_id,
            status=run.status.value,
        )

    @staticmethod
    def get_workflow_status(
        db: DBSession, session_id: str
    ) -> WorkflowStatusResponse:
        WorkflowService._get_session_or_404(db, session_id)

        run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.session_id == session_id)
            .order_by(WorkflowRun.created_at.desc())
            .first()
        )

        steps: list[WorkflowStepResponse] = []
        if run:
            db_steps = (
                db.query(WorkflowStep)
                .filter(WorkflowStep.run_id == run.id)
                .order_by(WorkflowStep.created_at.asc())
                .all()
            )
            steps = [WorkflowService._step_to_response(s) for s in db_steps]

        return WorkflowStatusResponse(
            run=WorkflowService._run_to_response(run) if run else None,
            steps=steps,
        )

    @staticmethod
    def get_report(db: DBSession, session_id: str) -> ReportResponse:
        WorkflowService._get_session_or_404(db, session_id)
        check_no_active_run(db, session_id)

        report = (
            db.query(ResearchReport)
            .filter(ResearchReport.session_id == session_id)
            .first()
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found for session {session_id}",
            )

        return ReportResponse(
            company_overview=report.company_overview or "",
            products_services=report.products_services or "",
            target_customers=report.target_customers or "",
            business_signals=report.business_signals or "",
            risks_challenges=report.risks_challenges or "",
            discovery_questions=report.discovery_questions or "",
            outreach_strategy=report.outreach_strategy or "",
            unknowns=report.unknowns or "",
            sources=report.sources or "",
        )

    @staticmethod
    def _run_to_response(run: WorkflowRun) -> WorkflowRunResponse:
        return WorkflowRunResponse(
            id=run.id,
            session_id=run.session_id,
            status=run.status.value,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _step_to_response(step: WorkflowStep) -> WorkflowStepResponse:
        return WorkflowStepResponse(
            id=step.id,
            node_name=step.node_name,
            status=step.status.value,
            input_data=step.input_data,
            output_data=step.output_data,
            error_message=step.error_message,
            created_at=step.created_at,
            updated_at=step.updated_at,
        )


def _execute_workflow(session_id: str) -> None:
    db = SessionLocal()
    try:
        session = (
            db.query(ResearchSession)
            .filter(ResearchSession.id == session_id)
            .first()
        )
        if not session:
            logger.error("Session %s not found for workflow execution", session_id)
            return

        session.status = SessionStatus.in_progress
        db.commit()
        logger.info("Workflow execution started for session %s", session_id)

        initial_state: GraphState = {
            "session_id": session.id,
            "company_name": session.company_name,
            "website_url": session.website,
            "research_objective": session.research_objective,
            "plan": {},
            "source_text": "",
            "source_metadata": [],
            "analysis_output": {},
            "risks_and_unknowns": {},
            "quality_result": {},
            "final_report": {},
            "warnings": [],
            "errors": [],
            "workflow_status": "running",
        }

        final_state = compiled_graph.invoke(initial_state)

        workflow_status = final_state.get("workflow_status", "completed")
        if workflow_status == "failed":
            session.status = SessionStatus.failed
        else:
            session.status = SessionStatus.completed

        db.commit()
        logger.info(
            "Workflow finished for session %s, status=%s",
            session_id,
            session.status.value,
        )

    except Exception:
        logger.exception("Workflow execution failed for session %s", session_id)
        try:
            session = (
                db.query(ResearchSession)
                .filter(ResearchSession.id == session_id)
                .first()
            )
            if session:
                session.status = SessionStatus.failed
                db.commit()
        except Exception:
            logger.exception(
                "Failed to update session status for %s", session_id
            )
    finally:
        db.close()
