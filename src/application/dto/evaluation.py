from dataclasses import dataclass, field

from src.domain.entities.evaluation import EvalCase


@dataclass(slots=True)
class EvaluationRequest:
    cases: list[EvalCase] = field(default_factory=list)
    top_k: int = 10
    hit_at_k: list[int] = field(default_factory=lambda: [1, 3, 5, 10])
    with_generation: bool = False
