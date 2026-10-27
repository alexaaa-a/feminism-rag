from pydantic import BaseModel, Field

from src.presentation.api.v1.common import FiltersIn


class SearchIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    mode: str | None = Field(default=None, description="dense, sparse или hybrid")
    filters: FiltersIn = Field(default_factory=FiltersIn)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    rerank: bool | None = None
    route: bool | None = None
    expand_to_parents: bool | None = None


class SearchHitOut(BaseModel):
    chunk_id: str
    source: str
    text: str
    score: float
    dense_score: float | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rerank_score: float | None = None
    section: str | None = None
    page: int | None = None
    block_type: str | None = None
    lang: str | None = None
    title: str | None = None
    source_url: str | None = None


class SearchOut(BaseModel):
    query: str
    search_query: str
    mode: str
    filters: dict[str, str] = Field(default_factory=dict)
    candidates_seen: int = 0
    best_dense_score: float | None = None
    answerable: float | None = None
    reranked: bool = False
    route_intent: str | None = None
    route_in_domain: float | None = None
    hits: list[SearchHitOut] = Field(default_factory=list)
    context: str = ""
