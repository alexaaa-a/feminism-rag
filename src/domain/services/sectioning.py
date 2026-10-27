import re

_HEADING_MD = re.compile(r"^#{1,6}\s+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WIKI_META_PREFIXES = ("Источник:", "Лицензия:", "Заголовок:", "Source:", "License:", "Title:")


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def split_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_SPLIT.split(normalize_whitespace(text))
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def split_markdown_sections(text: str) -> list[dict]:
    sections: list[dict] = []
    heading: str | None = None
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip()
        if body or heading:
            sections.append({"heading": heading, "text": body})

    for line in text.splitlines():
        stripped = line.strip()
        if _HEADING_MD.match(stripped):
            flush()
            heading = _HEADING_MD.sub("", stripped).strip()
            lines = []
        else:
            lines.append(line)

    flush()
    return [section for section in sections if section["text"]]


def split_wiki_sections(text: str) -> list[dict]:
    sections: list[dict] = []
    heading: str | None = None
    paragraphs: list[str] = []

    def flush() -> None:
        if paragraphs:
            sections.append({"heading": heading, "text": "\n\n".join(paragraphs)})

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(_WIKI_META_PREFIXES):
            continue

        words = line.split()
        looks_like_heading = (
            len(line) < 120
            and len(words) <= 9
            and not line.endswith((".", ",", ":", ";", "!", "?"))
        )
        if looks_like_heading:
            flush()
            heading = line
            paragraphs = []
        else:
            paragraphs.append(line)

    flush()
    return sections


def extract_wiki_header(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in text.splitlines()[:8]:
        if line.startswith(("Источник:", "Source:")):
            meta["source_url"] = line.split(":", 1)[1].strip()
        elif line.startswith(("Заголовок:", "Title:")):
            meta["title"] = line.split(":", 1)[1].strip()
        elif line.startswith(("Лицензия:", "License:")):
            meta["license"] = line.split(":", 1)[1].strip()
    return meta
