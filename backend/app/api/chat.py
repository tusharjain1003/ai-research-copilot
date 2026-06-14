from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.chat import ChatRequest, ChatHistoryResponse, ChatMessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/sessions", tags=["chat"])


@router.get("/{session_id}/chat", response_model=ChatHistoryResponse)
def get_chat_messages(session_id: str, db: Session = Depends(get_db)):
    return ChatService.get_messages(db, session_id)


@router.post("/{session_id}/chat", response_model=ChatMessageResponse, status_code=201)
def send_chat_message(session_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    return ChatService.send_message(db, session_id, body.message)
