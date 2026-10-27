from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
