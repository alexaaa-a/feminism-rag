from dataclasses import dataclass, field

from src.domain.entities.retrieval import RetrievalFilters


@dataclass(slots=True)
class AskRequest:
    question: str
    session_id: str | None = None
    client_id: str | None = None
    top_k: int | None = None
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    use_history: bool = True
