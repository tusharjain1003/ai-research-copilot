from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
)
from app.services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    return SessionService.create_session(db, data)


@router.get("", response_model=SessionListResponse)
def list_sessions(db: Session = Depends(get_db)):
    return SessionService.list_sessions(db)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return SessionService.get_session(db, session_id)
