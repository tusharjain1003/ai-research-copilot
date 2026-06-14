import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

from app.database.session import Base
from app.models.enums import MessageRole


class ChatMessage(Base):
    __tablename__ = "chat_messages"

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
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage {self.id} {self.role.value}>"
