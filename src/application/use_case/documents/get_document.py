from src.application.interfaces.db.document_db import DocumentDBInterface
from src.domain.entities.ingest import DocumentRecord


class GetDocumentUseCase:
    def __init__(self, document_db: DocumentDBInterface) -> None:
        self._document_db = document_db

    async def __call__(self, document_id: str) -> DocumentRecord | None:
        return await self._document_db.get_document(document_id)
