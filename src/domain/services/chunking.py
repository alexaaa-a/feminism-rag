from dataclasses import dataclass

from src.domain.entities.chunk import Chunk, ParentChunk
from src.domain.entities.document import DocumentBlock, DocumentFormat, ParsedDocument
from src.domain.services.sectioning import split_markdown_sections, split_wiki_sections
from src.domain.services.splitting import count_words, recursive_split

MAX_TABLE_ROWS = 300
_TEXT_BLOCK_TYPES = frozenset({"text", "paragraph"})


@dataclass(slots=True)
class _Piece:
    text: str
    method: str
    block_type: str = "text"
    section: str | None = None
    page: int | None = None
    standalone: bool = False


class ChunkingService:
    def __init__(
            self,
            chunk_size_words: int = 220,
            chunk_overlap_words: int = 45,
            parent_group_size: int = 3,
            min_chunk_words: int = 12,
    ) -> None:
        self._chunk_size = chunk_size_words
        self._chunk_overlap = chunk_overlap_words
        self._parent_group_size = max(parent_group_size, 1)
        self._min_words = min_chunk_words

    def chunk(
            self,
            document: ParsedDocument,
            document_id: str,
    ) -> tuple[list[Chunk], list[ParentChunk]]:
        pieces = self._build_pieces(document)
        chunks = self._pieces_to_chunks(pieces, document, document_id)
        parents = self._build_parents(chunks, document, document_id)
        return chunks, parents

    def _build_pieces(self, document: ParsedDocument) -> list[_Piece]:
        if document.document_format is DocumentFormat.DOCX:
            return self._docx_pieces(document)
        if document.document_format is DocumentFormat.MD:
            return self._markdown_pieces(document)
        if document.document_format is DocumentFormat.TXT:
            return self._wiki_pieces(document)
        if document.document_format is DocumentFormat.PDF:
            return self._pdf_pieces(document)
        return self._plain_pieces(document.text, "recursive")

    def _docx_pieces(self, document: ParsedDocument) -> list[_Piece]:
        pieces: list[_Piece] = []
        section: str | None = None

        for block in document.blocks:
            if block.block_type == "heading":
                section = block.text or section
                continue
            if block.block_type == "table":
                pieces.extend(self._table_pieces(block, section, "docx_table"))
                continue
            for text in self._split(block.text):
                pieces.append(_Piece(text=text, method="docx_paragraph", section=section))

        if not pieces:
            pieces = self._plain_pieces(document.text, "docx_plain")
        return pieces

    def _markdown_pieces(self, document: ParsedDocument) -> list[_Piece]:
        pieces: list[_Piece] = []
        for section in split_markdown_sections(document.text):
            for text in self._split(section["text"]):
                pieces.append(
                    _Piece(text=text, method="md_section", section=section["heading"])
                )
        if not pieces:
            pieces = self._plain_pieces(document.text, "md_plain")
        return pieces

    def _wiki_pieces(self, document: ParsedDocument) -> list[_Piece]:
        pieces: list[_Piece] = []
        for section in split_wiki_sections(document.text):
            for text in self._split(section["text"]):
                pieces.append(
                    _Piece(text=text, method="wiki_section", section=section["heading"])
                )
        if not pieces:
            pieces = self._plain_pieces(document.text, "txt_plain")
        return pieces

    def _pdf_pieces(self, document: ParsedDocument) -> list[_Piece]:
        pieces: list[_Piece] = []
        for block in document.tables():
            pieces.extend(self._table_pieces(block, None, "pdf_table"))
        for text in self._split(document.text):
            pieces.append(_Piece(text=text, method="pdf_recursive"))
        return pieces

    def _plain_pieces(self, text: str, method: str) -> list[_Piece]:
        return [_Piece(text=piece, method=method) for piece in self._split(text)]

    def _table_pieces(
            self,
            block: DocumentBlock,
            section: str | None,
            method: str,
    ) -> list[_Piece]:
        rows = [[str(cell or "").strip() for cell in row] for row in block.rows]
        rows = [row for row in rows if any(row)]
        if not rows:
            return []

        table_text = "\n".join(" | ".join(row) for row in rows)
        pieces = [
            _Piece(
                text=table_text,
                method=f"{method}_whole",
                block_type="table",
                section=section,
                page=block.page,
                standalone=True,
            )
        ]

        header = rows[0]
        if len(rows) < 2 or not any(header):
            return pieces

        for row in rows[1 : MAX_TABLE_ROWS + 1]:
            fields = [
                f"{column}: {value}"
                for column, value in zip(header, row)
                if value
            ]
            if not fields:
                continue
            pieces.append(
                _Piece(
                    text=" | ".join(fields),
                    method=f"{method}_row",
                    block_type="table_row",
                    section=section,
                    page=block.page,
                    standalone=True,
                )
            )
        return pieces

    def _split(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        return recursive_split(
            text,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )

    def _pieces_to_chunks(
            self,
            pieces: list[_Piece],
            document: ParsedDocument,
            document_id: str,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        for piece in pieces:
            words = count_words(piece.text)
            if words < self._min_words and piece.block_type in _TEXT_BLOCK_TYPES:
                continue

            position = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}::{position:04d}",
                    document_id=document_id,
                    text=piece.text,
                    embed_text=self._embed_text(piece, document),
                    source=document.source,
                    document_format=str(document.document_format),
                    lang=document.lang,
                    method=piece.method,
                    block_type=piece.block_type,
                    section=piece.section,
                    page=piece.page,
                    title=document.title,
                    source_url=document.source_url,
                    position=position,
                    words=words,
                )
            )
        return chunks

    def _embed_text(self, piece: _Piece, document: ParsedDocument) -> str:
        header: list[str] = []
        title = document.title or document.source
        if title:
            header.append(f"Документ: {title}")
        if piece.section:
            header.append(f"Раздел: {piece.section}")
        if piece.block_type in {"table", "table_row"}:
            header.append("Тип: таблица")
        if not header:
            return piece.text
        return "\n".join(header) + "\n" + piece.text

    def _build_parents(
            self,
            chunks: list[Chunk],
            document: ParsedDocument,
            document_id: str,
    ) -> list[ParentChunk]:
        parents: list[ParentChunk] = []
        group: list[Chunk] = []
        group_key: tuple[str | None, str] | None = None

        def flush() -> None:
            if not group:
                return
            parent = self._make_parent(group, document, document_id, len(parents))
            parents.append(parent)
            for chunk in group:
                chunk.parent_id = parent.parent_id
            group.clear()

        for chunk in chunks:
            if chunk.block_type in {"table", "table_row"}:
                flush()
                group_key = None
                group.append(chunk)
                flush()
                continue

            key = (chunk.section, chunk.block_type)
            if group_key != key or len(group) >= self._parent_group_size:
                flush()
                group_key = key
            group.append(chunk)

        flush()
        return parents

    def _make_parent(
            self,
            group: list[Chunk],
            document: ParsedDocument,
            document_id: str,
            index: int,
    ) -> ParentChunk:
        texts: list[str] = []
        for chunk in group:
            if texts and chunk.text in texts[-1]:
                continue
            texts.append(chunk.text)

        return ParentChunk(
            parent_id=f"{document_id}::p{index:03d}",
            document_id=document_id,
            source=document.source,
            text="\n\n".join(texts),
            section=group[0].section,
            page=group[0].page,
            title=document.title,
            source_url=document.source_url,
            child_ids=[chunk.chunk_id for chunk in group],
        )
