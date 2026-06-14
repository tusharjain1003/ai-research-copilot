import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id = Column(
        String(36),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    company_overview = Column(Text, default="")
    products_services = Column(Text, default="")
    target_customers = Column(Text, default="")
    business_signals = Column(Text, default="")
    risks_challenges = Column(Text, default="")
    discovery_questions = Column(Text, default="")
    outreach_strategy = Column(Text, default="")
    unknowns = Column(Text, default="")
    sources = Column(Text, default="")
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

    session = relationship("ResearchSession", back_populates="report")

    def __repr__(self):
        return f"<ResearchReport {self.id} session={self.session_id}>"
