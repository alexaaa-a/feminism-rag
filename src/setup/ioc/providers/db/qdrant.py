from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from qdrant_client import AsyncQdrantClient

from src.application.interfaces.services.vector_store import VectorStoreInterface
from src.config import Settings
from src.infrastructure.qdrant.vector_store import QdrantVectorStore


class QdrantProvider(Provider):
    @provide(scope=Scope.APP)
    async def client(self, settings: Settings) -> AsyncIterable[AsyncQdrantClient]:
        qdrant_settings = settings.qdrant_settings
        if qdrant_settings.url:
            client = AsyncQdrantClient(
                url=qdrant_settings.url,
                api_key=qdrant_settings.api_key or None,
                timeout=int(qdrant_settings.timeout_sec),
            )
        else:
            client = AsyncQdrantClient(path=qdrant_settings.path)

        try:
            yield client
        finally:
            await client.close()


class QdrantVectorStoreProvider(Provider):
    vector_store = provide(
        QdrantVectorStore,
        provides=VectorStoreInterface,
        scope=Scope.APP,
    )
