from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    document_id: str
    source: str
    origin: str
    document_format: str
    lang: str
    status: str
    chars: int = 0
    words: int = 0
    chunks_count: int = 0
    parents_count: int = 0
    tables: int = 0
    pages: int | None = None
    title: str | None = None
    source_url: str | None = None
    checksum: str | None = None
    modified_at: datetime | None = None
    indexed_at: datetime | None = None
    parser: str | None = None
    ocr_needed: bool = False
    error: str | None = None


class DocumentsOut(BaseModel):
    documents: list[DocumentOut] = Field(default_factory=list)
    total: int = 0


class SyncIn(BaseModel):
    origin: str | None = Field(
        default=None,
        description="google_drive или local; пусто - все настроенные источники",
    )
    force: bool = Field(
        default=False,
        description="Переиндексировать документы, даже если checksum не изменился",
    )


class IngestRunOut(BaseModel):
    run_id: str
    status: str
    origin: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_sec: float | None = None
    files_seen: int = 0
    documents_indexed: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    documents_deleted: int = 0
    chunks_indexed: int = 0
    force: bool = False
    errors: list[str] = Field(default_factory=list)


class IngestRunsOut(BaseModel):
    runs: list[IngestRunOut] = Field(default_factory=list)


class CorpusStatsOut(BaseModel):
    documents: int = 0
    chunks: int = 0
    parents: int = 0
    points_in_index: int = 0
    chars: int = 0
    words: int = 0
    tables: int = 0
    by_lang: dict[str, int] = Field(default_factory=dict)
    by_format: dict[str, int] = Field(default_factory=dict)
    by_origin: dict[str, int] = Field(default_factory=dict)
