from pathlib import Path

from docx import Document
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph

from src.domain.entities.document import DocumentBlock, DocumentFormat, ParsedDocument
from src.domain.services.language import detect_language
from src.domain.services.quality import assess_quality


class DocxParser:
    def parse(self, path: Path, source_name: str) -> ParsedDocument:
        document = Document(str(path))
        blocks = self._blocks(document)

        parts: list[str] = []
        title: str | None = None
        for block in blocks:
            if block.block_type == "heading" and title is None:
                title = block.text
            parts.append(block.to_text())

        text = "\n\n".join(part for part in parts if part.strip())

        return ParsedDocument(
            source=source_name,
            document_format=DocumentFormat.DOCX,
            parser="python-docx",
            text=text,
            lang=detect_language(source_name, text),
            title=title,
            blocks=blocks,
            quality=assess_quality(text, blocks),
        )

    def _blocks(self, document: Document) -> list[DocumentBlock]:
        blocks: list[DocumentBlock] = []
        for item in self._iter_content(document):
            if isinstance(item, Paragraph):
                text = item.text.strip()
                if not text:
                    continue
                style = item.style.name if item.style else None
                block_type = (
                    "heading"
                    if style and str(style).lower().startswith("heading")
                    else "paragraph"
                )
                blocks.append(DocumentBlock(block_type=block_type, text=text, style=style))
            elif isinstance(item, DocxTable):
                rows = [[cell.text.strip() for cell in row.cells] for row in item.rows]
                blocks.append(DocumentBlock(block_type="table", rows=rows))
        return blocks

    def _iter_content(self, document: Document):
        try:
            return list(document.iter_inner_content())
        except AttributeError:
            items = []
            for element in document.element.body:
                tag = element.tag.split("}")[-1]
                if tag == "p":
                    items.append(Paragraph(element, document))
                elif tag == "tbl":
                    items.append(DocxTable(element, document))
            return items
