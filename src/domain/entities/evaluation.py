import datetime
from dataclasses import dataclass, field


@dataclass(slots=True)
class EvalCase:
    question: str
    gold_sources: list[str] = field(default_factory=list)
    evidence: str | None = None
    has_answer: bool = True


@dataclass(slots=True)
class EvalCaseResult:
    question: str
    has_answer: bool
    rank_gold_source: int | None = None
    rank_evidence: int | None = None
    top1_source: str | None = None
    top1_score: float | None = None
    best_dense_score: float | None = None
    answerable: float | None = None
    refused: bool = False
    correct: bool = False


@dataclass(slots=True)
class EvalReport:
    run_id: str
    started_at: datetime.datetime
    finished_at: datetime.datetime | None = None
    mode: str = "hybrid"
    top_k: int = 10
    cases: int = 0
    hit_at: dict[int, float] = field(default_factory=dict)
    evidence_hit_at: dict[int, float] = field(default_factory=dict)
    answered_when_no_answer: int = 0
    refused_when_answerable: int = 0
    results: list[EvalCaseResult] = field(default_factory=list)
