import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from src.application.interfaces.db.document_db import DocumentDBInterface
from src.config import Settings
from src.domain.entities.ingest import DocumentRecord
from src.infrastructure.mongo.mappers import (
    document_record_from_document,
    document_record_to_document,
)


class DocumentDB(DocumentDBInterface):
    def __init__(
            self,
            client: AsyncIOMotorClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self.db = client[settings.mongo_settings.name]["documents"]
        self.logger = logger

    async def save_document(self, document: DocumentRecord) -> bool:
        try:
            payload = document_record_to_document(document)
            payload.pop("_id", None)
            await self.db.update_one(
                {"_id": document.document_id},
                {"$set": payload},
                upsert=True,
            )
            return True
        except Exception:
            self.logger.exception("Failed to save document record %s", document.document_id)
            return False

    async def get_document(self, document_id: str) -> DocumentRecord | None:
        try:
            doc = await self.db.find_one({"_id": document_id})
            if not doc:
                return None
            return document_record_from_document(doc)
        except Exception:
            self.logger.exception("Failed to get document record %s", document_id)
            return None

    async def list_documents(
            self,
            origin: str | None = None,
            lang: str | None = None,
            limit: int = 200,
            offset: int = 0,
    ) -> list[DocumentRecord]:
        try:
            query: dict[str, Any] = {}
            if origin:
                query["origin"] = origin
            if lang:
                query["lang"] = lang
            cursor = (
                self.db.find(query)
                .sort("source", ASCENDING)
                .skip(max(offset, 0))
                .limit(max(limit, 1))
            )
            docs = await cursor.to_list(None)
            return [document_record_from_document(doc) for doc in docs]
        except Exception:
            self.logger.exception("Failed to list document records")
            return []

    async def count_documents(self, origin: str | None = None) -> int:
        try:
            query = {"origin": origin} if origin else {}
            return int(await self.db.count_documents(query))
        except Exception:
            self.logger.exception("Failed to count document records")
            return 0

    async def delete_document(self, document_id: str) -> bool:
        try:
            result = await self.db.delete_one({"_id": document_id})
            return bool(getattr(result, "deleted_count", 0))
        except Exception:
            self.logger.exception("Failed to delete document record %s", document_id)
            return False

    async def list_document_ids(self, origin: str) -> list[str]:
        try:
            docs = await self.db.find({"origin": origin}, {"_id": 1}).to_list(None)
            return [str(doc["_id"]) for doc in docs]
        except Exception:
            self.logger.exception("Failed to list document ids for origin=%s", origin)
            return []

    async def corpus_stats(self) -> dict:
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "documents": {"$sum": 1},
                        "chunks": {"$sum": "$chunks_count"},
                        "parents": {"$sum": "$parents_count"},
                        "chars": {"$sum": "$chars"},
                        "words": {"$sum": "$words"},
                        "tables": {"$sum": "$tables"},
                    }
                }
            ]
            totals = await self.db.aggregate(pipeline).to_list(1)
            by_lang = await self.db.aggregate(
                [{"$group": {"_id": "$lang", "count": {"$sum": 1}}}, {"$sort": {"count": DESCENDING}}]
            ).to_list(None)
            by_format = await self.db.aggregate(
                [{"$group": {"_id": "$format", "count": {"$sum": 1}}}, {"$sort": {"count": DESCENDING}}]
            ).to_list(None)
            by_origin = await self.db.aggregate(
                [{"$group": {"_id": "$origin", "count": {"$sum": 1}}}]
            ).to_list(None)

            summary = totals[0] if totals else {}
            summary.pop("_id", None)
            return {
                **{key: int(value or 0) for key, value in summary.items()},
                "by_lang": {str(item["_id"]): item["count"] for item in by_lang},
                "by_format": {str(item["_id"]): item["count"] for item in by_format},
                "by_origin": {str(item["_id"]): item["count"] for item in by_origin},
            }
        except Exception:
            self.logger.exception("Failed to build corpus stats")
            return {}
