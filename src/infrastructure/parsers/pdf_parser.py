import logging
from pathlib import Path

import pymupdf

from src.domain.entities.document import DocumentBlock, DocumentFormat, ParsedDocument
from src.domain.services.language import detect_language
from src.domain.services.quality import assess_quality

OCR_DPI = 150
OCR_LANGUAGES = "rus+eng"


class PdfParser:
    def __init__(self, logger: logging.Logger, max_table_pages: int = 20) -> None:
        self._logger = logger
        self._max_table_pages = max_table_pages

    def parse(self, path: Path, source_name: str) -> ParsedDocument:
        document = pymupdf.open(str(path))
        pages: list[str] = []
        blocks: list[DocumentBlock] = []

        try:
            for page_number, page in enumerate(document, start=1):
                pages.append(page.get_text("text", sort=True).strip())

                for block in page.get_text("blocks", sort=True):
                    block_text = str(block[4] or "").strip()
                    if block_text:
                        blocks.append(
                            DocumentBlock(
                                block_type="text",
                                text=block_text,
                                page=page_number,
                            )
                        )

                if page_number <= self._max_table_pages:
                    blocks.extend(self._tables(page, page_number))

            text = "\n\n".join(page_text for page_text in pages if page_text)
            parser = "pymupdf"

            if not text.strip():
                ocr_text = self._ocr(document)
                if ocr_text.strip():
                    text = ocr_text
                    parser = "pymupdf+ocr"

            quality = assess_quality(text, blocks, pages=document.page_count)
            return ParsedDocument(
                source=source_name,
                document_format=DocumentFormat.PDF,
                parser=parser,
                text=text,
                lang=detect_language(source_name, text),
                blocks=blocks,
                quality=quality,
            )
        finally:
            document.close()

    def _tables(self, page, page_number: int) -> list[DocumentBlock]:
        try:
            found = page.find_tables()
        except Exception:
            self._logger.debug("Table detection failed on page %s", page_number)
            return []

        tables: list[DocumentBlock] = []
        for table in getattr(found, "tables", []):
            try:
                rows = [[str(cell or "") for cell in row] for row in table.extract()]
            except Exception:
                continue
            if rows:
                tables.append(
                    DocumentBlock(block_type="table", rows=rows, page=page_number)
                )
        return tables

    def _ocr(self, document) -> str:
        parts: list[str] = []
        try:
            for page in document:
                textpage = page.get_textpage_ocr(language=OCR_LANGUAGES, dpi=OCR_DPI)
                parts.append(page.get_text(textpage=textpage).strip())
        except Exception:
            self._logger.warning("OCR unavailable, scanned PDF stays unparsed")
            return ""
        return "\n\n".join(part for part in parts if part)
