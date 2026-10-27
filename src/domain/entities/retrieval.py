from dataclasses import dataclass, field
from enum import StrEnum


class SearchMode(StrEnum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    source: str | None = None
    lang: str | None = None
    block_type: str | None = None
    document_format: str | None = None
    document_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        mapping = {
            "source": self.source,
            "lang": self.lang,
            "block_type": self.block_type,
            "format": self.document_format,
            "document_id": self.document_id,
        }
        return {key: value for key, value in mapping.items() if value}

    @property
    def empty(self) -> bool:
        return not self.as_dict()


@dataclass(slots=True)
class ScoredChunk:
    chunk_id: str
    text: str
    payload: dict
    score: float = 0.0
    dense_score: float | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rerank_score: float | None = None
    vector: list[float] = field(default_factory=list)

    @property
    def source(self) -> str:
        return str(self.payload.get("source") or "")

    @property
    def section(self) -> str | None:
        section = self.payload.get("section")
        return str(section) if section else None

    @property
    def parent_id(self) -> str | None:
        parent_id = self.payload.get("parent_id")
        return str(parent_id) if parent_id else None


@dataclass(slots=True)
class QueryRoute:
    in_domain: float = 1.0
    needs_table: float = 0.0
    lang_preference: str | None = None
    intent: str = "factual"
    confidence: float = 0.0
    used: bool = False

    @property
    def out_of_domain(self) -> bool:
        return self.used and self.in_domain < 0.5


@dataclass(slots=True)
class RetrievalResult:
    query: str
    search_query: str
    chunks: list[ScoredChunk] = field(default_factory=list)
    context: str = ""
    mode: SearchMode = SearchMode.HYBRID
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    route: QueryRoute = field(default_factory=QueryRoute)
    answerable: float | None = None
    best_dense_score: float | None = None
    candidates_seen: int = 0
    reranked: bool = False

    @property
    def found(self) -> bool:
        return bool(self.chunks)
