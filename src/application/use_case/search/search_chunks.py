from dataclasses import dataclass

from src.application.dto.search import SearchRequest
from src.application.retrieval.pipeline import RetrievalPipeline
from src.domain.entities.retrieval import RetrievalResult


@dataclass(frozen=True, slots=True)
class SearchResult:
    retrieval: RetrievalResult | None = None
    error: str | None = None
    message: str | None = None


class SearchChunksUseCase:
    def __init__(self, pipeline: RetrievalPipeline) -> None:
        self._pipeline = pipeline

    async def __call__(self, request: SearchRequest) -> SearchResult:
        if not request.question.strip():
            return SearchResult(error="empty_question", message="Вопрос не может быть пустым")

        retrieval = await self._pipeline.retrieve(request)
        return SearchResult(retrieval=retrieval)
