from abc import abstractmethod
from typing import Protocol

from src.domain.entities.ingest import DocumentRecord


class DocumentDBInterface(Protocol):
    @abstractmethod
    async def save_document(self, document: DocumentRecord) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_document(self, document_id: str) -> DocumentRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(
            self,
            origin: str | None = None,
            lang: str | None = None,
            limit: int = 200,
            offset: int = 0,
    ) -> list[DocumentRecord]:
        raise NotImplementedError

    @abstractmethod
    async def count_documents(self, origin: str | None = None) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_document_ids(self, origin: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def corpus_stats(self) -> dict:
        raise NotImplementedError
