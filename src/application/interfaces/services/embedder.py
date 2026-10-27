from abc import abstractmethod
from typing import Protocol


class EmbedderInterface(Protocol):
    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def vector_size(self) -> int:
        raise NotImplementedError
