from .mongo import MongoClientProvider, MongoDBProvider
from .qdrant import QdrantProvider, QdrantVectorStoreProvider
from .redis import RedisCacheProvider, RedisProvider


db_provider = [
    MongoClientProvider(),
    MongoDBProvider(),
    RedisProvider(),
    RedisCacheProvider(),
    QdrantProvider(),
    QdrantVectorStoreProvider(),
]
