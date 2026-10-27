from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VectorPoint:
    point_id: str
    dense: list[float]
    payload: dict
    sparse_indices: list[int] = field(default_factory=list)
    sparse_values: list[float] = field(default_factory=list)
