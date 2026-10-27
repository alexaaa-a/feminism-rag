from collections.abc import Callable

DEFAULT_SEPARATORS = ("\n\n", "\n", ". ", "; ", ", ", " ", "")


def count_words(text: str) -> int:
    return len(text.split())


def recursive_split(
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separators: tuple[str, ...] = DEFAULT_SEPARATORS,
        length_function: Callable[[str], int] = count_words,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть больше нуля")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap должен быть меньше chunk_size")

    text = text.strip()
    if not text:
        return []
    if length_function(text) <= chunk_size:
        return [text]

    pieces = _split_to_pieces(text, chunk_size, separators, length_function)
    return _merge_pieces(pieces, chunk_size, chunk_overlap, length_function)


def _split_to_pieces(
        text: str,
        chunk_size: int,
        separators: tuple[str, ...],
        length_function: Callable[[str], int],
) -> list[str]:
    separator = separators[-1]
    rest = separators
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = ""
            rest = separators[index:]
            break
        if candidate in text:
            separator = candidate
            rest = separators[index + 1:]
            break

    if separator == "":
        return [text]

    pieces: list[str] = []
    for part in text.split(separator):
        part = part.strip()
        if not part:
            continue
        if length_function(part) <= chunk_size or not rest:
            pieces.append(part)
        else:
            pieces.extend(_split_to_pieces(part, chunk_size, rest, length_function))
    return pieces


def _merge_pieces(
        pieces: list[str],
        chunk_size: int,
        chunk_overlap: int,
        length_function: Callable[[str], int],
) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for piece in pieces:
        piece_length = length_function(piece)
        if current and current_length + piece_length > chunk_size:
            chunks.append(" ".join(current))
            current, current_length = _carry_overlap(current, chunk_overlap, length_function)
        current.append(piece)
        current_length += piece_length

    if current:
        chunks.append(" ".join(current))

    return [chunk for chunk in (item.strip() for item in chunks) if chunk]


def _carry_overlap(
        current: list[str],
        chunk_overlap: int,
        length_function: Callable[[str], int],
) -> tuple[list[str], int]:
    if chunk_overlap <= 0:
        return [], 0

    tail: list[str] = []
    tail_length = 0
    for piece in reversed(current):
        piece_length = length_function(piece)
        if tail_length + piece_length > chunk_overlap and tail:
            break
        tail.insert(0, piece)
        tail_length += piece_length
    return tail, tail_length
