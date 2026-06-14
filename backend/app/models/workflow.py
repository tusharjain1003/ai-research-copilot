import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from app.database.session import Base
from app.models.enums import WorkflowRunStatus, WorkflowStepStatus


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id = Column(
        String(36),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(WorkflowRunStatus),
        default=WorkflowRunStatus.pending,
        nullable=False,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="workflow_runs")
    steps = relationship(
        "WorkflowStep", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<WorkflowRun {self.id} [{self.status.value}]>"


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_id = Column(
        String(36),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_name = Column(String(128), nullable=False)
    status = Column(
        Enum(WorkflowStepStatus),
        default=WorkflowStepStatus.pending,
        nullable=False,
    )
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    run = relationship("WorkflowRun", back_populates="steps")

    def __repr__(self):
        return f"<WorkflowStep {self.id} {self.node_name} [{self.status.value}]>"
