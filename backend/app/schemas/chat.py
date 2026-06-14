from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
