from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from src.application.dto.llm import LlmCompletion


class LlmInterface(Protocol):
    @abstractmethod
    async def complete(
            self,
            messages: list[dict[str, str]],
            max_tokens: int | None = None,
            temperature: float | None = None,
    ) -> LlmCompletion | None:
        raise NotImplementedError

    @abstractmethod
    def stream(
            self,
            messages: list[dict[str, str]],
            max_tokens: int | None = None,
            temperature: float | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError
