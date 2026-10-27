from abc import abstractmethod
from typing import Protocol

from src.application.dto.vector import VectorPoint
from src.domain.entities.retrieval import RetrievalFilters, ScoredChunk


class VectorStoreInterface(Protocol):
    @abstractmethod
    async def ensure_collection(self, vector_size: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def upsert_points(self, points: list[VectorPoint]) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def search_dense(
            self,
            vector: list[float],
            limit: int,
            filters: RetrievalFilters | None = None,
            score_threshold: float | None = None,
            with_vectors: bool = False,
    ) -> list[ScoredChunk]:
        raise NotImplementedError

    @abstractmethod
    async def search_sparse(
            self,
            indices: list[int],
            values: list[float],
            limit: int,
            filters: RetrievalFilters | None = None,
    ) -> list[ScoredChunk]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_points(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError
