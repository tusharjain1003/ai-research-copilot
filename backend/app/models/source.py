import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class ResearchSource(Base):
    __tablename__ = "research_sources"

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
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    source_type = Column(String(64), nullable=True)
    fetched_at = Column(DateTime, nullable=True)
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

    session = relationship("ResearchSession", back_populates="sources")

    def __repr__(self):
        return f"<ResearchSource {self.id} {self.url[:50]}>"
