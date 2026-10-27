import datetime
from dataclasses import dataclass, field
from enum import StrEnum


class DocumentFormat(StrEnum):
    TXT = ".txt"
    MD = ".md"
    DOCX = ".docx"
    PDF = ".pdf"

    @classmethod
    def from_suffix(cls, suffix: str) -> "DocumentFormat | None":
        try:
            return cls(suffix.lower())
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class SourceFile:
    external_id: str
    name: str
    document_format: DocumentFormat
    size_bytes: int
    modified_at: datetime.datetime | None = None
    checksum: str | None = None
    web_url: str | None = None


@dataclass(slots=True)
class DocumentBlock:
    block_type: str
    text: str = ""
    rows: list[list[str]] = field(default_factory=list)
    page: int | None = None
    style: str | None = None

    def to_text(self) -> str:
        if self.block_type == "table":
            return "\n".join(" | ".join(str(cell or "") for cell in row) for row in self.rows)
        return self.text


@dataclass(slots=True)
class DocumentQuality:
    chars: int = 0
    words: int = 0
    blocks: int = 0
    tables: int = 0
    pages: int | None = None
    replacement_chars: int = 0
    empty: bool = False
    suspiciously_short: bool = False
    ocr_needed: bool = False

    @property
    def usable(self) -> bool:
        return not self.empty and not self.ocr_needed


@dataclass(slots=True)
class ParsedDocument:
    source: str
    document_format: DocumentFormat
    parser: str
    text: str
    lang: str = "unknown"
    title: str | None = None
    source_url: str | None = None
    blocks: list[DocumentBlock] = field(default_factory=list)
    quality: DocumentQuality = field(default_factory=DocumentQuality)

    def tables(self) -> list[DocumentBlock]:
        return [block for block in self.blocks if block.block_type == "table"]
