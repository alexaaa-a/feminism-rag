from dataclasses import asdict

from pydantic import BaseModel, Field

from src.domain.entities.chat import RagAnswer
from src.domain.entities.retrieval import RetrievalFilters


class FiltersIn(BaseModel):
    source: str | None = None
    lang: str | None = Field(default=None, description="ru или en")
    block_type: str | None = Field(
        default=None,
        description="text, table или table_row",
    )
    document_format: str | None = Field(default=None, description=".txt, .md, .docx, .pdf")
    document_id: str | None = None

    def to_entity(self) -> RetrievalFilters:
        return RetrievalFilters(
            source=self.source,
            lang=self.lang,
            block_type=self.block_type,
            document_format=self.document_format,
            document_id=self.document_id,
        )


class CitationOut(BaseModel):
    chunk_id: str
    source: str
    text: str
    score: float
    section: str | None = None
    page: int | None = None
    title: str | None = None
    source_url: str | None = None
    lang: str | None = None


class DiagnosticsOut(BaseModel):
    mode: str
    candidates_seen: int
    chunks_used: int
    best_dense_score: float | None = None
    answerable: float | None = None
    groundedness: float | None = None
    reranked: bool = False
    route_intent: str | None = None
    route_in_domain: float | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    search_query: str | None = None
    latency_ms: int | None = None
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class AnswerOut(BaseModel):
    question: str
    answer: str
    refused: bool = False
    citations: list[CitationOut] = Field(default_factory=list)
    diagnostics: DiagnosticsOut


def answer_to_response(answer: RagAnswer) -> AnswerOut:
    return AnswerOut(
        question=answer.question,
        answer=answer.answer,
        refused=answer.refused,
        citations=[CitationOut(**asdict(citation)) for citation in answer.citations],
        diagnostics=DiagnosticsOut(**asdict(answer.diagnostics)),
    )
