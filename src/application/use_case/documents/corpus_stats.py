from dataclasses import dataclass, field

from src.application.interfaces.db.document_db import DocumentDBInterface
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface


@dataclass(frozen=True, slots=True)
class CorpusStats:
    documents: int = 0
    chunks: int = 0
    parents: int = 0
    points_in_index: int = 0
    chars: int = 0
    words: int = 0
    tables: int = 0
    by_lang: dict[str, int] = field(default_factory=dict)
    by_format: dict[str, int] = field(default_factory=dict)
    by_origin: dict[str, int] = field(default_factory=dict)


class CorpusStatsUseCase:
    def __init__(
            self,
            document_db: DocumentDBInterface,
            parent_db: ParentChunkDBInterface,
            vector_store: VectorStoreInterface,
    ) -> None:
        self._document_db = document_db
        self._parent_db = parent_db
        self._vector_store = vector_store

    async def __call__(self) -> CorpusStats:
        stats = await self._document_db.corpus_stats()
        return CorpusStats(
            documents=int(stats.get("documents") or 0),
            chunks=int(stats.get("chunks") or 0),
            parents=await self._parent_db.count_parents(),
            points_in_index=await self._vector_store.count_points(),
            chars=int(stats.get("chars") or 0),
            words=int(stats.get("words") or 0),
            tables=int(stats.get("tables") or 0),
            by_lang=stats.get("by_lang") or {},
            by_format=stats.get("by_format") or {},
            by_origin=stats.get("by_origin") or {},
        )
