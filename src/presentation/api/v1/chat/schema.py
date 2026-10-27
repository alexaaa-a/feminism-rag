from datetime import datetime

from pydantic import BaseModel, Field

from src.presentation.api.v1.common import CitationOut, DiagnosticsOut, FiltersIn


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    filters: FiltersIn = Field(default_factory=FiltersIn)
    use_history: bool = True


class CreateSessionIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class SessionOut(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages_count: int = 0


class MessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime
    refused: bool = False
    citations: list[CitationOut] = Field(default_factory=list)
    diagnostics: DiagnosticsOut | None = None


class SessionDetailOut(BaseModel):
    session: SessionOut
    messages: list[MessageOut] = Field(default_factory=list)


class SessionsOut(BaseModel):
    sessions: list[SessionOut] = Field(default_factory=list)
