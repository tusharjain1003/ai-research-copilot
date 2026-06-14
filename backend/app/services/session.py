from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.models.enums import SessionStatus
from app.models.session import ResearchSession
from app.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
)


class SessionService:

    @staticmethod
    def create_session(db: DBSession, data: SessionCreate) -> SessionResponse:
        session = ResearchSession(
            company_name=data.company_name,
            website=data.website_url,
            research_objective=data.research_objective,
            status=SessionStatus.draft,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return SessionService._to_response(session)

    @staticmethod
    def get_session(db: DBSession, session_id: str) -> SessionResponse:
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
        return SessionService._to_response(session)

    @staticmethod
    def list_sessions(db: DBSession) -> SessionListResponse:
        sessions = (
            db.query(ResearchSession)
            .order_by(ResearchSession.created_at.desc())
            .all()
        )
        return SessionListResponse(
            sessions=[SessionService._to_response(s) for s in sessions]
        )

    @staticmethod
    def _to_response(session: ResearchSession) -> SessionResponse:
        return SessionResponse(
            id=session.id,
            company_name=session.company_name,
            website_url=session.website,
            research_objective=session.research_objective,
            status=session.status.value,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
