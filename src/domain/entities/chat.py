import datetime
from dataclasses import dataclass, field
from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Citation:
    chunk_id: str
    source: str
    text: str
    score: float
    section: str | None = None
    page: int | None = None
    title: str | None = None
    source_url: str | None = None
    lang: str | None = None


@dataclass(slots=True)
class AnswerDiagnostics:
    mode: str = "hybrid"
    candidates_seen: int = 0
    chunks_used: int = 0
    best_dense_score: float | None = None
    answerable: float | None = None
    groundedness: float | None = None
    reranked: bool = False
    route_intent: str | None = None
    route_in_domain: float | None = None
    filters: dict[str, str] = field(default_factory=dict)
    search_query: str | None = None
    latency_ms: int | None = None
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(slots=True)
class RagAnswer:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    diagnostics: AnswerDiagnostics = field(default_factory=AnswerDiagnostics)


@dataclass(slots=True)
class ChatMessage:
    message_id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime.datetime
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    diagnostics: AnswerDiagnostics | None = None


@dataclass(slots=True)
class ChatSession:
    session_id: str
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages_count: int = 0
    client_id: str | None = None
