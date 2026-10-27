from dataclasses import dataclass, field


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    embed_text: str
    source: str
    document_format: str
    lang: str
    method: str
    block_type: str = "text"
    section: str | None = None
    page: int | None = None
    title: str | None = None
    source_url: str | None = None
    parent_id: str | None = None
    position: int = 0
    words: int = 0

    def payload(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "source": self.source,
            "format": self.document_format,
            "lang": self.lang,
            "method": self.method,
            "block_type": self.block_type,
            "section": self.section,
            "page": self.page,
            "title": self.title,
            "source_url": self.source_url,
            "parent_id": self.parent_id,
            "position": self.position,
            "words": self.words,
        }


@dataclass(slots=True)
class ParentChunk:
    parent_id: str
    document_id: str
    source: str
    text: str
    section: str | None = None
    page: int | None = None
    title: str | None = None
    source_url: str | None = None
    child_ids: list[str] = field(default_factory=list)
