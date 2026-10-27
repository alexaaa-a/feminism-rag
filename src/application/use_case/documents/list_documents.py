from dataclasses import dataclass, field

from src.application.interfaces.db.document_db import DocumentDBInterface
from src.domain.entities.ingest import DocumentRecord


@dataclass(frozen=True, slots=True)
class DocumentsPage:
    documents: list[DocumentRecord] = field(default_factory=list)
    total: int = 0


class ListDocumentsUseCase:
    def __init__(self, document_db: DocumentDBInterface) -> None:
        self._document_db = document_db

    async def __call__(
            self,
            origin: str | None = None,
            lang: str | None = None,
            limit: int = 200,
            offset: int = 0,
    ) -> DocumentsPage:
        documents = await self._document_db.list_documents(
            origin=origin,
            lang=lang,
            limit=limit,
            offset=offset,
        )
        total = await self._document_db.count_documents(origin=origin)
        return DocumentsPage(documents=documents, total=total)
