from dataclasses import dataclass, field

from src.domain.entities.retrieval import RetrievalFilters, SearchMode


@dataclass(slots=True)
class SearchRequest:
    question: str
    top_k: int | None = None
    mode: SearchMode | None = None
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    score_threshold: float | None = None
    rerank: bool | None = None
    route: bool | None = None
    expand_to_parents: bool | None = None
