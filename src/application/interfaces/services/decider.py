from abc import abstractmethod
from typing import Protocol

from src.domain.entities.retrieval import QueryRoute


class QueryRouterInterface(Protocol):
    @abstractmethod
    async def route(self, question: str) -> QueryRoute | None:
        raise NotImplementedError


class RerankerInterface(Protocol):
    @abstractmethod
    async def score_candidates(
            self,
            question: str,
            candidates: list[str],
    ) -> list[float] | None:
        raise NotImplementedError


class AnswerJudgeInterface(Protocol):
    @abstractmethod
    async def is_answerable(self, question: str, context: str) -> float | None:
        raise NotImplementedError

    @abstractmethod
    async def is_grounded(
            self,
            question: str,
            context: str,
            answer: str,
    ) -> float | None:
        raise NotImplementedError
