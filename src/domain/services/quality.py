from src.domain.entities.document import DocumentBlock, DocumentQuality

MIN_USEFUL_CHARS = 200


def assess_quality(
        text: str,
        blocks: list[DocumentBlock],
        pages: int | None = None,
) -> DocumentQuality:
    stripped = text.strip()
    tables = sum(1 for block in blocks if block.block_type == "table")

    return DocumentQuality(
        chars=len(text),
        words=len(text.split()),
        blocks=len(blocks),
        tables=tables,
        pages=pages,
        replacement_chars=text.count("�"),
        empty=not stripped,
        suspiciously_short=0 < len(stripped) < MIN_USEFUL_CHARS,
        ocr_needed=not stripped and (pages or 0) > 0,
    )
