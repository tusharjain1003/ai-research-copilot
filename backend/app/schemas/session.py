from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.url_validation import validate_external_url


class SessionCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(..., min_length=1, max_length=1024)
    research_objective: str = Field(..., min_length=1)

    @field_validator("website_url")
    @classmethod
    def validate_website_url(cls, v: str) -> str:
        return validate_external_url(v)


class SessionResponse(BaseModel):
    id: str
    company_name: str
    website_url: str
    research_objective: str
    status: str
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
