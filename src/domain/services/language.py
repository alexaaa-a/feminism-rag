import re

_FILENAME_LANG = re.compile(r"^\d+_(ru|en)_")
_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_LATIN = re.compile(r"[a-zA-Z]")


def detect_language(file_name: str, text: str = "") -> str:
    match = _FILENAME_LANG.match(file_name)
    if match:
        return match.group(1)

    sample = text[:4000]
    cyrillic = len(_CYRILLIC.findall(sample))
    latin = len(_LATIN.findall(sample))
    if cyrillic == 0 and latin == 0:
        return "unknown"
    if cyrillic >= latin:
        return "ru"
    return "en"
