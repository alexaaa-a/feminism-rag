import datetime
from dataclasses import dataclass, field
from enum import StrEnum


class IngestStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DocumentStatus(StrEnum):
    INDEXED = "indexed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    source: str
    origin: str
    document_format: str
    lang: str
    status: DocumentStatus
    chars: int = 0
    words: int = 0
    chunks_count: int = 0
    parents_count: int = 0
    tables: int = 0
    pages: int | None = None
    title: str | None = None
    source_url: str | None = None
    external_id: str | None = None
    checksum: str | None = None
    modified_at: datetime.datetime | None = None
    indexed_at: datetime.datetime | None = None
    parser: str | None = None
    ocr_needed: bool = False
    error: str | None = None


@dataclass(slots=True)
class IngestRun:
    run_id: str
    status: IngestStatus
    started_at: datetime.datetime
    origin: str = "all"
    finished_at: datetime.datetime | None = None
    files_seen: int = 0
    documents_indexed: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    documents_deleted: int = 0
    chunks_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    force: bool = False

    @property
    def duration_sec(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()
