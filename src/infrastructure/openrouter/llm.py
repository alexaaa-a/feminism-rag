import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from src.application.interfaces.services.llm import LlmCompletion, LlmInterface
from src.config import Settings


class OpenRouterLlm(LlmInterface):
    def __init__(
            self,
            client: AsyncOpenAI,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._client = client
        self._logger = logger
        self._settings = settings.llm_settings

    def model_name(self) -> str:
        return self._settings.model

    async def complete(
            self,
            messages: list[dict[str, str]],
            max_tokens: int | None = None,
            temperature: float | None = None,
    ) -> LlmCompletion | None:
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
                max_tokens=max_tokens or self._settings.max_tokens,
                temperature=self._settings.temperature if temperature is None else temperature,
            )
        except Exception:
            self._logger.exception("LLM call failed model=%s", self._settings.model)
            return None

        if not response.choices:
            self._logger.warning("LLM returned no choices model=%s", self._settings.model)
            return None

        usage = response.usage
        return LlmCompletion(
            text=(response.choices[0].message.content or "").strip(),
            model=response.model or self._settings.model,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )

    async def stream(
            self,
            messages: list[dict[str, str]],
            max_tokens: int | None = None,
            temperature: float | None = None,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
                max_tokens=max_tokens or self._settings.max_tokens,
                temperature=self._settings.temperature if temperature is None else temperature,
                stream=True,
            )
        except Exception:
            self._logger.exception("LLM stream failed model=%s", self._settings.model)
            return

        try:
            async for part in stream:
                if not part.choices:
                    continue
                delta = part.choices[0].delta
                piece = getattr(delta, "content", None)
                if piece:
                    yield piece
        except Exception:
            self._logger.exception("LLM stream interrupted model=%s", self._settings.model)
