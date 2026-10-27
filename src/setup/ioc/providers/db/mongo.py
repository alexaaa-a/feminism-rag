from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from motor.motor_asyncio import AsyncIOMotorClient

from src.application.interfaces.db.chat_db import ChatDBInterface
from src.application.interfaces.db.document_db import DocumentDBInterface
from src.application.interfaces.db.eval_db import EvaluationDBInterface
from src.application.interfaces.db.ingest_db import IngestRunDBInterface
from src.application.interfaces.db.mongodb import MongoDBInterface
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.config import Settings
from src.infrastructure.mongo.chat_db import ChatDB
from src.infrastructure.mongo.document_db import DocumentDB
from src.infrastructure.mongo.eval_db import EvaluationDB
from src.infrastructure.mongo.gateway import MongoGateway
from src.infrastructure.mongo.ingest_db import IngestRunDB
from src.infrastructure.mongo.parent_db import ParentChunkDB


class MongoClientProvider(Provider):
    @provide(scope=Scope.APP)
    async def mongo_client(self, settings: Settings) -> AsyncIterable[AsyncIOMotorClient]:
        client = AsyncIOMotorClient(
            str(settings.mongo_settings.connection_string),
            serverSelectionTimeoutMS=settings.mongo_settings.server_selection_timeout_ms,
        )
        try:
            yield client
        finally:
            client.close()


class MongoDBProvider(Provider):
    mongo_db = provide(MongoGateway, provides=MongoDBInterface, scope=Scope.APP)
    document_db = provide(DocumentDB, provides=DocumentDBInterface, scope=Scope.APP)
    parent_db = provide(ParentChunkDB, provides=ParentChunkDBInterface, scope=Scope.APP)
    chat_db = provide(ChatDB, provides=ChatDBInterface, scope=Scope.APP)
    ingest_db = provide(IngestRunDB, provides=IngestRunDBInterface, scope=Scope.APP)
    evaluation_db = provide(EvaluationDB, provides=EvaluationDBInterface, scope=Scope.APP)
