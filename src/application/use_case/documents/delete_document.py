import logging
from dataclasses import dataclass

from src.application.interfaces.db.document_db import DocumentDBInterface
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface


@dataclass(frozen=True, slots=True)
class DeleteDocumentResult:
    deleted: bool = False
    error: str | None = None


class DeleteDocumentUseCase:
    def __init__(
            self,
            document_db: DocumentDBInterface,
            parent_db: ParentChunkDBInterface,
            vector_store: VectorStoreInterface,
            logger: logging.Logger,
    ) -> None:
        self._document_db = document_db
        self._parent_db = parent_db
        self._vector_store = vector_store
        self._logger = logger

    async def __call__(self, document_id: str) -> DeleteDocumentResult:
        record = await self._document_db.get_document(document_id)
        if record is None:
            return DeleteDocumentResult(error="not_found")

        vectors_deleted = await self._vector_store.delete_by_document(document_id)
        parents_deleted = await self._parent_db.delete_by_document(document_id)
        record_deleted = await self._document_db.delete_document(document_id)

        if not (vectors_deleted and parents_deleted and record_deleted):
            self._logger.warning(
                "Partial delete for document %s: vectors=%s parents=%s record=%s",
                document_id,
                vectors_deleted,
                parents_deleted,
                record_deleted,
            )
            return DeleteDocumentResult(error="partial_delete")

        return DeleteDocumentResult(deleted=True)
