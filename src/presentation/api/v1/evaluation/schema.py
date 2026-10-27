from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.entities.evaluation import EvalCase


class EvalCaseIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    gold_sources: list[str] = Field(default_factory=list)
    evidence: str | None = None
    has_answer: bool = True

    def to_entity(self) -> EvalCase:
        return EvalCase(
            question=self.question,
            gold_sources=self.gold_sources,
            evidence=self.evidence,
            has_answer=self.has_answer,
        )


class EvaluationIn(BaseModel):
    cases: list[EvalCaseIn] = Field(
        default_factory=list,
        description="Пусто - берём набор вопросов из домашки",
    )
    top_k: int = Field(default=10, ge=1, le=50)
    hit_at_k: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])


class EvalCaseResultOut(BaseModel):
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


class EvalReportOut(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    mode: str
    top_k: int
    cases: int
    hit_at: dict[int, float] = Field(default_factory=dict)
    evidence_hit_at: dict[int, float] = Field(default_factory=dict)
    answered_when_no_answer: int = 0
    refused_when_answerable: int = 0
    results: list[EvalCaseResultOut] = Field(default_factory=list)


class EvalReportsOut(BaseModel):
    runs: list[EvalReportOut] = Field(default_factory=list)
