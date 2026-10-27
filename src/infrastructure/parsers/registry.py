import logging
from pathlib import Path

from src.application.interfaces.services.parser import DocumentParserInterface
from src.config import Settings
from src.domain.entities.document import DocumentFormat, ParsedDocument
from src.infrastructure.parsers.docx_parser import DocxParser
from src.infrastructure.parsers.pdf_parser import PdfParser
from src.infrastructure.parsers.text_parsers import MarkdownParser, TxtParser


class DocumentParserRegistry(DocumentParserInterface):
    def __init__(self, logger: logging.Logger, settings: Settings) -> None:
        self._logger = logger
        self._parsers = {
            DocumentFormat.TXT: TxtParser(),
            DocumentFormat.MD: MarkdownParser(),
            DocumentFormat.DOCX: DocxParser(),
            DocumentFormat.PDF: PdfParser(
                logger=logger,
                max_table_pages=settings.chunking_settings.max_table_pages,
            ),
        }

    def parse(self, path: Path, source_name: str) -> ParsedDocument | None:
        document_format = DocumentFormat.from_suffix(path.suffix)
        if document_format is None:
            self._logger.warning("Unsupported format for %s", source_name)
            return None

        parser = self._parsers.get(document_format)
        if parser is None:
            self._logger.warning("No parser registered for %s", document_format)
            return None

        try:
            return parser.parse(path, source_name)
        except Exception:
            self._logger.exception("Failed to parse %s", source_name)
            return None
