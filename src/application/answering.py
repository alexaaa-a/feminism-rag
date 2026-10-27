import re

from src.domain.entities.chat import AnswerDiagnostics, ChatMessage, Citation, RagAnswer
from src.domain.entities.retrieval import RetrievalResult
from src.domain.services.prompting import NO_ANSWER_TEXT, extract_citation_indices

CITATION_SNIPPET_CHARS = 700
_CITATION_MARKER = re.compile(r"(\s*)\[(\d{1,2})\]")


def build_citations(result: RetrievalResult) -> list[Citation]:
    return [
        Citation(
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            text=chunk.text[:CITATION_SNIPPET_CHARS],
            score=chunk.score,
            section=chunk.section,
            page=chunk.payload.get("page"),
            title=chunk.payload.get("title"),
            source_url=chunk.payload.get("source_url"),
            lang=chunk.payload.get("lang"),
        )
        for chunk in result.chunks
    ]


def align_citations(answer: str, citations: list[Citation]) -> tuple[str, list[Citation]]:
    used = [index for index in extract_citation_indices(answer) if 1 <= index <= len(citations)]
    renumbered = {old: new for new, old in enumerate(used, start=1)}
    picked = [citations[old - 1] for old in used] if used else citations

    def replace(match: re.Match) -> str:
        space, old = match.group(1), int(match.group(2))
        if old in renumbered:
            return f"{space}[{renumbered[old]}]"
        return ""

    return _CITATION_MARKER.sub(replace, answer), picked


def build_diagnostics(
        result: RetrievalResult,
        llm_model: str | None = None,
        latency_ms: int | None = None,
        groundedness: float | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
) -> AnswerDiagnostics:
    return AnswerDiagnostics(
        mode=str(result.mode),
        candidates_seen=result.candidates_seen,
        chunks_used=len(result.chunks),
        best_dense_score=result.best_dense_score,
        answerable=result.answerable,
        groundedness=groundedness,
        reranked=result.reranked,
        route_intent=result.route.intent if result.route.used else None,
        route_in_domain=result.route.in_domain if result.route.used else None,
        filters=result.filters.as_dict(),
        search_query=result.search_query if result.search_query != result.query else None,
        latency_ms=latency_ms,
        llm_model=llm_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def refusal_answer(
        question: str,
        result: RetrievalResult,
        latency_ms: int | None = None,
        groundedness: float | None = None,
) -> RagAnswer:
    return RagAnswer(
        question=question,
        answer=NO_ANSWER_TEXT,
        citations=build_citations(result),
        refused=True,
        diagnostics=build_diagnostics(
            result,
            latency_ms=latency_ms,
            groundedness=groundedness,
        ),
    )


def history_to_messages(messages: list[ChatMessage], limit: int) -> list[dict[str, str]]:
    if limit <= 0:
        return []
    return [
        {"role": str(message.role), "content": message.content}
        for message in messages[-limit:]
    ]
