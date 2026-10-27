from abc import abstractmethod
from typing import Protocol

from src.domain.entities.evaluation import EvalReport


class EvaluationDBInterface(Protocol):
    @abstractmethod
    async def save_report(self, report: EvalReport) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_report(self, run_id: str) -> EvalReport | None:
        raise NotImplementedError

    @abstractmethod
    async def list_reports(self, limit: int = 20) -> list[EvalReport]:
        raise NotImplementedError
