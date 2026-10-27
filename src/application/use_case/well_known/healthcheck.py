from src.application.interfaces.db.cache import CacheInterface
from src.application.interfaces.db.mongodb import MongoDBInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface


class HealthCheckUseCase:
    def __init__(
            self,
            mongo_db: MongoDBInterface,
            cache: CacheInterface,
            vector_store: VectorStoreInterface,
    ) -> None:
        self.mongo_db = mongo_db
        self.cache = cache
        self.vector_store = vector_store

    async def __call__(self) -> None:
        mongo_ok = await self.mongo_db.health()
        cache_ok = await self.cache.health()
        vector_ok = await self.vector_store.health()

        if not (mongo_ok and cache_ok and vector_ok):
            raise RuntimeError("Not all storages are ready")
