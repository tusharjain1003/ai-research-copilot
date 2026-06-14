import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy.orm import relationship

from app.database.session import Base
from app.models.enums import SessionStatus


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    company_name = Column(String(255), nullable=False)
    website = Column(String(1024), nullable=False)
    research_objective = Column(TEXT, nullable=False)
    status = Column(
        Enum(SessionStatus),
        default=SessionStatus.draft,
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

    workflow_runs = relationship(
        "WorkflowRun", back_populates="session", cascade="all, delete-orphan"
    )
    sources = relationship(
        "ResearchSource", back_populates="session", cascade="all, delete-orphan"
    )
    report = relationship(
        "ResearchReport", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ResearchSession {self.id} [{self.status.value}] {self.company_name}>"
