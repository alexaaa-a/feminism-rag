from pathlib import Path

from src.domain.entities.document import DocumentBlock, DocumentFormat, ParsedDocument
from src.domain.services.language import detect_language
from src.domain.services.quality import assess_quality
from src.domain.services.sectioning import extract_wiki_header


class TxtParser:
    def parse(self, path: Path, source_name: str) -> ParsedDocument:
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta = extract_wiki_header(text)

        return ParsedDocument(
            source=source_name,
            document_format=DocumentFormat.TXT,
            parser="pathlib",
            text=text,
            lang=detect_language(source_name, text),
            title=meta.get("title"),
            source_url=meta.get("source_url"),
            blocks=[],
            quality=assess_quality(text, []),
        )


class MarkdownParser:
    def parse(self, path: Path, source_name: str) -> ParsedDocument:
        text = path.read_text(encoding="utf-8", errors="ignore")
        blocks: list[DocumentBlock] = []
        title: str | None = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                if title is None:
                    title = heading
                blocks.append(DocumentBlock(block_type="heading", text=heading))
            elif line.startswith("|") and set(line.replace("|", "").strip()) != {"-"}:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                blocks.append(DocumentBlock(block_type="table_row", rows=[cells], text=line))
            else:
                blocks.append(DocumentBlock(block_type="paragraph", text=line))

        return ParsedDocument(
            source=source_name,
            document_format=DocumentFormat.MD,
            parser="pathlib",
            text=text,
            lang=detect_language(source_name, text),
            title=title,
            blocks=blocks,
            quality=assess_quality(text, blocks),
        )
