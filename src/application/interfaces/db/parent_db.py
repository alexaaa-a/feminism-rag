from abc import abstractmethod
from typing import Protocol

from src.domain.entities.chunk import ParentChunk


class ParentChunkDBInterface(Protocol):
    @abstractmethod
    async def save_parents(self, parents: list[ParentChunk]) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_parents(self, parent_ids: list[str]) -> dict[str, ParentChunk]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_parents(self) -> int:
        raise NotImplementedError
