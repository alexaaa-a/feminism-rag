import asyncio
import datetime
import logging
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.application.interfaces.db.document_db import DocumentDBInterface
from src.application.interfaces.db.ingest_db import IngestRunDBInterface
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.application.interfaces.services.corpus_source import CorpusSourceInterface
from src.application.interfaces.services.embedder import EmbedderInterface
from src.application.interfaces.services.parser import DocumentParserInterface
from src.application.interfaces.services.vector_store import VectorPoint, VectorStoreInterface
from src.config import Settings
from src.domain.entities.chunk import Chunk, ParentChunk
from src.domain.entities.document import ParsedDocument, SourceFile
from src.domain.entities.ingest import (
    DocumentRecord,
    DocumentStatus,
    IngestRun,
    IngestStatus,
)
from src.domain.services.chunking import ChunkingService
from src.domain.services.tokenization import Bm25Encoder

MAX_REPORTED_ERRORS = 20


@dataclass(frozen=True, slots=True)
class SyncResult:
    run: IngestRun | None = None
    error: str | None = None
    message: str | None = None


class SyncCorpusUseCase:
    def __init__(
            self,
            sources: list[CorpusSourceInterface],
            parser: DocumentParserInterface,
            chunking: ChunkingService,
            embedder: EmbedderInterface,
            vector_store: VectorStoreInterface,
            document_db: DocumentDBInterface,
            parent_db: ParentChunkDBInterface,
            ingest_db: IngestRunDBInterface,
            bm25: Bm25Encoder,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._sources = sources
        self._parser = parser
        self._chunking = chunking
        self._embedder = embedder
        self._vector_store = vector_store
        self._document_db = document_db
        self._parent_db = parent_db
        self._ingest_db = ingest_db
        self._bm25 = bm25
        self._logger = logger
        self._settings = settings
        self._task: asyncio.Task | None = None

    async def start(self, origin: str | None = None, force: bool = False) -> SyncResult:
        active = await self._ingest_db.get_active_run()
        if active is not None:
            return SyncResult(
                run=active,
                error="already_running",
                message="Синхронизация уже идёт",
            )

        sources = self._pick_sources(origin)
        if not sources:
            return SyncResult(
                error="no_sources",
                message="Ни один источник документов не настроен",
            )

        run = self._new_run(origin, force)
        await self._ingest_db.save_run(run)

        self._task = asyncio.create_task(self._execute(run, sources, force))
        return SyncResult(run=run)

    async def __call__(self, origin: str | None = None, force: bool = False) -> SyncResult:
        sources = self._pick_sources(origin)
        if not sources:
            return SyncResult(
                error="no_sources",
                message="Ни один источник документов не настроен",
            )

        run = self._new_run(origin, force)
        await self._ingest_db.save_run(run)
        await self._execute(run, sources, force)
        return SyncResult(run=run)

    def _new_run(self, origin: str | None, force: bool) -> IngestRun:
        return IngestRun(
            run_id=str(uuid.uuid4()),
            status=IngestStatus.RUNNING,
            started_at=datetime.datetime.now(datetime.UTC),
            origin=origin or "all",
            force=force,
        )

    def _pick_sources(self, origin: str | None) -> list[CorpusSourceInterface]:
        return [
            source
            for source in self._sources
            if source.available() and (origin is None or source.origin() == origin)
        ]

    async def _execute(
            self,
            run: IngestRun,
            sources: list[CorpusSourceInterface],
            force: bool,
    ) -> None:
        try:
            await self._vector_store.ensure_collection(self._embedder.vector_size())
            for source in sources:
                await self._sync_source(run, source, force)
            run.status = IngestStatus.SUCCEEDED
        except Exception as error:
            self._logger.exception("Ingest run %s failed", run.run_id)
            run.status = IngestStatus.FAILED
            self._add_error(run, f"run: {error}")
        finally:
            run.finished_at = datetime.datetime.now(datetime.UTC)
            await self._ingest_db.save_run(run)
            self._logger.info(
                "Ingest run %s finished: status=%s indexed=%s skipped=%s failed=%s deleted=%s chunks=%s",
                run.run_id,
                run.status,
                run.documents_indexed,
                run.documents_skipped,
                run.documents_failed,
                run.documents_deleted,
                run.chunks_indexed,
            )

    async def _sync_source(
            self,
            run: IngestRun,
            source: CorpusSourceInterface,
            force: bool,
    ) -> None:
        origin = source.origin()
        files = await source.list_files()
        run.files_seen += len(files)
        await self._ingest_db.save_run(run)

        seen_ids: set[str] = set()
        with tempfile.TemporaryDirectory(prefix="rag-ingest-") as temp_dir:
            target_dir = Path(temp_dir)
            for source_file in files:
                document_id = f"{origin}:{source_file.external_id}"
                seen_ids.add(document_id)
                try:
                    await self._sync_file(run, source, source_file, document_id, target_dir, force)
                except Exception as error:
                    self._logger.exception("Failed to index %s", source_file.name)
                    run.documents_failed += 1
                    self._add_error(run, f"{source_file.name}: {error}")
                await self._ingest_db.save_run(run)

        await self._delete_missing(run, origin, seen_ids)

    async def _sync_file(
            self,
            run: IngestRun,
            source: CorpusSourceInterface,
            source_file: SourceFile,
            document_id: str,
            target_dir: Path,
            force: bool,
    ) -> None:
        existing = await self._document_db.get_document(document_id)
        if self._is_up_to_date(existing, source_file, force):
            run.documents_skipped += 1
            return

        path = await source.download(source_file, target_dir)
        if path is None:
            run.documents_failed += 1
            self._add_error(run, f"{source_file.name}: не удалось скачать")
            return

        try:
            parsed = self._parser.parse(path, source_file.name)
            if parsed is None:
                run.documents_failed += 1
                self._add_error(run, f"{source_file.name}: парсер не справился")
                return

            if not parsed.quality.usable:
                await self._document_db.save_document(
                    self._record(
                        document_id,
                        source_file,
                        parsed,
                        source.origin(),
                        status=DocumentStatus.SKIPPED,
                        error="нет извлекаемого текста, нужен OCR",
                    )
                )
                run.documents_skipped += 1
                self._logger.warning("Document %s has no extractable text", source_file.name)
                return

            chunks, parents = self._chunking.chunk(parsed, document_id)
            if not chunks:
                await self._document_db.save_document(
                    self._record(
                        document_id,
                        source_file,
                        parsed,
                        source.origin(),
                        status=DocumentStatus.SKIPPED,
                        error="после чанкинга не осталось содержимого",
                    )
                )
                run.documents_skipped += 1
                return

            await self._index_chunks(document_id, chunks, parents)
            await self._document_db.save_document(
                self._record(
                    document_id,
                    source_file,
                    parsed,
                    source.origin(),
                    status=DocumentStatus.INDEXED,
                    chunks_count=len(chunks),
                    parents_count=len(parents),
                )
            )
            run.documents_indexed += 1
            run.chunks_indexed += len(chunks)
        finally:
            path.unlink(missing_ok=True)

    def _is_up_to_date(
            self,
            existing: DocumentRecord | None,
            source_file: SourceFile,
            force: bool,
    ) -> bool:
        if force or existing is None:
            return False
        if existing.status is not DocumentStatus.INDEXED:
            return False
        if not existing.checksum or not source_file.checksum:
            return False
        return existing.checksum == source_file.checksum

    async def _index_chunks(
            self,
            document_id: str,
            chunks: list[Chunk],
            parents: list[ParentChunk],
    ) -> None:
        vectors = await self._embedder.embed_documents([chunk.embed_text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"эмбеддингов {len(vectors)}, а чанков {len(chunks)}"
            )

        points: list[VectorPoint] = []
        for chunk, vector in zip(chunks, vectors):
            indices, values = self._bm25.encode_document(chunk.embed_text)
            points.append(
                VectorPoint(
                    point_id=chunk.chunk_id,
                    dense=vector,
                    payload=chunk.payload(),
                    sparse_indices=indices,
                    sparse_values=values,
                )
            )

        await self._vector_store.delete_by_document(document_id)
        await self._parent_db.delete_by_document(document_id)

        if not await self._vector_store.upsert_points(points):
            raise RuntimeError("не удалось записать точки в векторное хранилище")
        if not await self._parent_db.save_parents(parents):
            raise RuntimeError("не удалось сохранить родительские окна")

    async def _delete_missing(
            self,
            run: IngestRun,
            origin: str,
            seen_ids: set[str],
    ) -> None:
        stored_ids = await self._document_db.list_document_ids(origin)
        for document_id in stored_ids:
            if document_id in seen_ids:
                continue
            self._logger.info("Document %s disappeared from %s, removing", document_id, origin)
            await self._vector_store.delete_by_document(document_id)
            await self._parent_db.delete_by_document(document_id)
            await self._document_db.delete_document(document_id)
            run.documents_deleted += 1

    def _record(
            self,
            document_id: str,
            source_file: SourceFile,
            parsed: ParsedDocument,
            origin: str,
            status: DocumentStatus,
            chunks_count: int = 0,
            parents_count: int = 0,
            error: str | None = None,
    ) -> DocumentRecord:
        return DocumentRecord(
            document_id=document_id,
            source=parsed.source,
            origin=origin,
            document_format=str(parsed.document_format),
            lang=parsed.lang,
            status=status,
            chars=parsed.quality.chars,
            words=parsed.quality.words,
            chunks_count=chunks_count,
            parents_count=parents_count,
            tables=parsed.quality.tables,
            pages=parsed.quality.pages,
            title=parsed.title,
            source_url=parsed.source_url or source_file.web_url,
            external_id=source_file.external_id,
            checksum=source_file.checksum,
            modified_at=source_file.modified_at,
            indexed_at=datetime.datetime.now(datetime.UTC),
            parser=parsed.parser,
            ocr_needed=parsed.quality.ocr_needed,
            error=error,
        )

    def _add_error(self, run: IngestRun, message: str) -> None:
        if len(run.errors) < MAX_REPORTED_ERRORS:
            run.errors.append(message)
