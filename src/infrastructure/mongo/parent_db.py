import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.config import Settings
from src.domain.entities.chunk import ParentChunk
from src.infrastructure.mongo.mappers import parent_from_document, parent_to_document


class ParentChunkDB(ParentChunkDBInterface):
    def __init__(
            self,
            client: AsyncIOMotorClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self.db = client[settings.mongo_settings.name]["parents"]
        self.logger = logger

    async def save_parents(self, parents: list[ParentChunk]) -> bool:
        if not parents:
            return True
        try:
            operations = []
            for parent in parents:
                payload = parent_to_document(parent)
                payload.pop("_id", None)
                operations.append(
                    UpdateOne({"_id": parent.parent_id}, {"$set": payload}, upsert=True)
                )
            await self.db.bulk_write(operations, ordered=False)
            return True
        except Exception:
            self.logger.exception("Failed to save %s parent chunks", len(parents))
            return False

    async def get_parents(self, parent_ids: list[str]) -> dict[str, ParentChunk]:
        if not parent_ids:
            return {}
        try:
            docs = await self.db.find({"_id": {"$in": parent_ids}}).to_list(None)
            parents = [parent_from_document(doc) for doc in docs]
            return {parent.parent_id: parent for parent in parents}
        except Exception:
            self.logger.exception("Failed to get parent chunks")
            return {}

    async def delete_by_document(self, document_id: str) -> bool:
        try:
            await self.db.delete_many({"document_id": document_id})
            return True
        except Exception:
            self.logger.exception("Failed to delete parents for document %s", document_id)
            return False

    async def count_parents(self) -> int:
        try:
            return int(await self.db.count_documents({}))
        except Exception:
            self.logger.exception("Failed to count parent chunks")
            return 0
