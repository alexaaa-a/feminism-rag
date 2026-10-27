import re
import zlib

import snowballstemmer

_TOKEN = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_CYRILLIC = re.compile(r"[а-яё]")

_RU_STEMMER = snowballstemmer.stemmer("russian")
_EN_STEMMER = snowballstemmer.stemmer("english")

BRIDGE_MARKER = "~"
BRIDGE_LENGTH = 5

_TRANSLITERATION = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
)

_STOP_WORDS = frozenset(
    """
    и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по
    только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если
    уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя ничего ей
    может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто чего раз
    тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом
    один почти мой тем чтобы нее сейчас были куда зачем всех никогда можно при наконец
    два об другой хоть после над больше тот через эти нас про всего них какая много
    разве три эту моя впрочем свою этой перед иногда лучше чуть том нельзя такой им
    более всегда конечно всю между каком какое какие таком
    the a an and or but if then than that this these those of in on at to for from by
    with as is are was were be been being it its his her their our your my we you they
    he she not no do does did have has had will would can could should may might must
    about into over after before between what which who whom when where why how
    """.split()
)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if len(raw) < 2 or raw in _STOP_WORDS:
            continue
        tokens.append(_stem(raw))
    return tokens


def _stem(token: str) -> str:
    if token.isdigit():
        return token
    if _CYRILLIC.search(token):
        return _RU_STEMMER.stemWord(token)
    return _EN_STEMMER.stemWord(token)


def bridge_token(token: str) -> str | None:
    if token.isdigit() or len(token) < BRIDGE_LENGTH:
        return None

    latin = token.translate(_TRANSLITERATION) if _CYRILLIC.search(token) else token
    if len(latin) < BRIDGE_LENGTH:
        return None
    return f"{BRIDGE_MARKER}{latin[:BRIDGE_LENGTH]}"


def token_id(token: str) -> int:
    return zlib.crc32(token.encode("utf-8"))


class Bm25Encoder:
    def __init__(self, k1: float = 1.2, b: float = 0.75, avg_doc_len: float = 120.0) -> None:
        self.k1 = k1
        self.b = b
        self.avg_doc_len = max(avg_doc_len, 1.0)

    def with_avg_doc_len(self, avg_doc_len: float) -> "Bm25Encoder":
        return Bm25Encoder(k1=self.k1, b=self.b, avg_doc_len=avg_doc_len)

    def encode_document(self, text: str) -> tuple[list[int], list[float]]:
        tokens = tokenize(text)
        if not tokens:
            return [], []

        counts = _count_with_bridges(tokens)
        norm = self.k1 * (1.0 - self.b + self.b * len(tokens) / self.avg_doc_len)

        indices: list[int] = []
        values: list[float] = []
        for token, count in counts.items():
            indices.append(token_id(token))
            values.append(round(count * (self.k1 + 1.0) / (count + norm), 6))
        return indices, values

    def encode_query(self, text: str) -> tuple[list[int], list[float]]:
        tokens = tokenize(text)
        if not tokens:
            return [], []

        counts = _count_with_bridges(tokens)
        return [token_id(token) for token in counts], [float(count) for count in counts.values()]


def _count_with_bridges(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    for token, count in list(counts.items()):
        bridge = bridge_token(token)
        if bridge is not None and bridge not in counts:
            counts[bridge] = count
    return counts
