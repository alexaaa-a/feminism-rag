import hashlib
import json
import logging

from openai import AsyncOpenAI

from src.application.interfaces.db.cache import CacheInterface
from src.application.interfaces.services.embedder import EmbedderInterface
from src.config import Settings
from src.infrastructure.redis.cache_keys import QUERY_EMBEDDING


class OpenRouterEmbedder(EmbedderInterface):
    def __init__(
            self,
            client: AsyncOpenAI,
            cache: CacheInterface,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._client = client
        self._cache = cache
        self._logger = logger
        self._settings = settings.embedding_settings
        self._redis_settings = settings.redis_settings
        self._supports_dimensions = True

    def vector_size(self) -> int:
        return self._settings.dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        batch_size = max(self._settings.batch_size, 1)
        prefix = self._settings.document_prefix

        for start in range(0, len(texts), batch_size):
            batch = [prefix + text for text in texts[start: start + batch_size]]
            embedded = await self._embed(batch)
            if embedded is None:
                raise RuntimeError("Не удалось получить эмбеддинги документов")
            vectors.extend(embedded)

        return vectors

    async def embed_query(self, text: str) -> list[float]:
        cache_key = QUERY_EMBEDDING.format(
            model=self._settings.model,
            digest=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        cached = await self._cache.get(cache_key)
        if cached:
            try:
                return [float(value) for value in json.loads(cached)]
            except Exception:
                self._logger.warning("Broken cached embedding for key=%s", cache_key)

        embedded = await self._embed([self._settings.query_prefix + text])
        if not embedded:
            raise RuntimeError("Не удалось получить эмбеддинг запроса")

        vector = embedded[0]
        await self._cache.set(
            cache_key,
            json.dumps(vector),
            ttl_sec=self._redis_settings.embedding_ttl_sec,
        )
        return vector

    async def _embed(self, inputs: list[str]) -> list[list[float]] | None:
        payload: dict = {"model": self._settings.model, "input": inputs}
        if self._supports_dimensions and self._settings.dimensions:
            payload["dimensions"] = self._settings.dimensions

        try:
            response = await self._client.embeddings.create(**payload)
        except Exception:
            if "dimensions" in payload:
                self._logger.warning("Embeddings call rejected dimensions, retrying without it")
                self._supports_dimensions = False
                return await self._embed(inputs)
            self._logger.exception("Embeddings call failed for %s inputs", len(inputs))
            return None

        ordered = sorted(response.data, key=lambda item: item.index)
        return [[float(value) for value in item.embedding] for item in ordered]
