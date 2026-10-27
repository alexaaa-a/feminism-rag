import re
from dataclasses import dataclass

NO_ANSWER_TEXT = "В предоставленных документах нет этой информации."

SYSTEM_PROMPT = """Ты - ассистент по феминизму и его истории. Ты отвечаешь строго по выданному контексту.

Правила:
1. Используй только факты из контекста. Внешние знания, догадки и общие рассуждения запрещены.
2. После каждого утверждения ставь номер фрагмента в квадратных скобках: [1], [2]. Если утверждение опирается на несколько фрагментов, перечисли их: [1][3].
3. Если в контексте нет ответа или его хватает лишь на часть вопроса, прямо скажи, чего в документах нет. При полном отсутствии ответа напиши ровно: "{no_answer}"
4. Не додумывай даты, имена, числа и названия. Если в контексте указан диапазон или оценка, так и передай.
5. Отвечай на языке вопроса. Тон - нейтральный и academically точный, без оценок и агитации.
6. Если в контексте есть разные точки зрения или формулировки, покажи их как разные позиции, а не как один факт.
7. Объём - по существу вопроса: короткий факт отдавай одним-двумя предложениями, обзорный вопрос раскрывай по абзацам."""

CONDENSE_SYSTEM_PROMPT = """Перепиши последний вопрос пользователя так, чтобы он был понятен без истории диалога.

Правила:
- подставь то, на что указывают местоимения и сокращения ("она", "там", "в этот год");
- сохрани язык вопроса и все уточнения;
- не отвечай на вопрос и ничего не добавляй от себя;
- если вопрос и так самостоятельный, верни его без изменений;
- верни только текст вопроса, одной строкой."""

_CITATION = re.compile(r"\[(\d{1,2})\]")


@dataclass(slots=True)
class ContextBlock:
    index: int
    text: str
    source: str
    section: str | None = None
    page: int | None = None
    title: str | None = None

    def render(self) -> str:
        meta = [f"Источник: {self.title or self.source}"]
        if self.title and self.title != self.source:
            meta.append(f"Файл: {self.source}")
        if self.section:
            meta.append(f"Раздел: {self.section}")
        if self.page is not None:
            meta.append(f"Страница: {self.page}")
        return f"[{self.index}] {' | '.join(meta)}\n{self.text}"


def system_prompt() -> str:
    return SYSTEM_PROMPT.format(no_answer=NO_ANSWER_TEXT)


def build_context(blocks: list[ContextBlock], max_chars: int = 14000) -> str:
    parts: list[str] = []
    used = 0
    for block in blocks:
        rendered = block.render()
        if parts and used + len(rendered) > max_chars:
            break
        parts.append(rendered)
        used += len(rendered) + 2
    return "\n\n".join(parts)


def build_messages(
        question: str,
        context: str,
        history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt()}]
    for item in history or []:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append(
        {
            "role": "user",
            "content": f"Контекст:\n{context}\n\nВопрос пользователя:\n{question}",
        }
    )
    return messages


def build_condense_messages(
        question: str,
        history: list[dict[str, str]],
) -> list[dict[str, str]]:
    dialog = "\n".join(
        f"{'Пользователь' if item.get('role') == 'user' else 'Ассистент'}: {item.get('content', '')}"
        for item in history
        if (item.get("content") or "").strip()
    )
    return [
        {"role": "system", "content": CONDENSE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"История диалога:\n{dialog}\n\nПоследний вопрос:\n{question}",
        },
    ]


def extract_citation_indices(answer: str) -> list[int]:
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        index = int(match.group(1))
        if index not in seen:
            seen.append(index)
    return seen


def looks_like_refusal(answer: str) -> bool:
    normalized = " ".join(answer.lower().split())
    return NO_ANSWER_TEXT.lower().rstrip(".") in normalized
