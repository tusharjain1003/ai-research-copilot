import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.database.session import SessionLocal
from app.models.enums import WorkflowRunStatus, WorkflowStepStatus
from app.models.workflow import WorkflowRun, WorkflowStep

logger = logging.getLogger(__name__)


def get_db() -> DBSession:
    return SessionLocal()


def resolve_active_run(db: DBSession, session_id: str) -> Optional[WorkflowRun]:
    return (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.session_id == session_id,
            WorkflowRun.status.in_(
                [WorkflowRunStatus.pending, WorkflowRunStatus.running]
            ),
        )
        .order_by(WorkflowRun.created_at.desc())
        .first()
    )


def create_step(
    db: DBSession, run_id: str, node_name: str, input_data: dict
) -> WorkflowStep:
    step = WorkflowStep(
        run_id=run_id,
        node_name=node_name,
        status=WorkflowStepStatus.running,
        input_data=input_data,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def complete_step(db: DBSession, step: WorkflowStep, output_data: dict) -> None:
    step.status = WorkflowStepStatus.completed
    step.output_data = output_data
    step.updated_at = datetime.now(timezone.utc)
    db.commit()


def fail_step(
    db: DBSession, step: Optional[WorkflowStep], error_message: str
) -> None:
    if step is None:
        return
    step.status = WorkflowStepStatus.failed
    step.error_message = error_message
    step.updated_at = datetime.now(timezone.utc)
    db.commit()


def fail_run(db: DBSession, run: Optional[WorkflowRun], error_message: str) -> None:
    if run is None:
        return
    run.status = WorkflowRunStatus.failed
    run.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.error("Workflow run %s failed: %s", run.id, error_message)


def run_started(db: DBSession, run: WorkflowRun) -> None:
    run.status = WorkflowRunStatus.running
    run.updated_at = datetime.now(timezone.utc)
    db.commit()


def run_completed(db: DBSession, run: WorkflowRun) -> None:
    run.status = WorkflowRunStatus.completed
    run.updated_at = datetime.now(timezone.utc)
    db.commit()
