import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING

from src.application.interfaces.db.ingest_db import IngestRunDBInterface
from src.config import Settings
from src.domain.entities.ingest import IngestRun, IngestStatus
from src.infrastructure.mongo.mappers import ingest_run_from_document, ingest_run_to_document


class IngestRunDB(IngestRunDBInterface):
    def __init__(
            self,
            client: AsyncIOMotorClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self.db = client[settings.mongo_settings.name]["ingest_runs"]
        self.logger = logger

    async def save_run(self, run: IngestRun) -> bool:
        try:
            payload = ingest_run_to_document(run)
            payload.pop("_id", None)
            await self.db.update_one({"_id": run.run_id}, {"$set": payload}, upsert=True)
            return True
        except Exception:
            self.logger.exception("Failed to save ingest run %s", run.run_id)
            return False

    async def get_run(self, run_id: str) -> IngestRun | None:
        try:
            doc = await self.db.find_one({"_id": run_id})
            if not doc:
                return None
            return ingest_run_from_document(doc)
        except Exception:
            self.logger.exception("Failed to get ingest run %s", run_id)
            return None

    async def list_runs(self, limit: int = 20) -> list[IngestRun]:
        try:
            docs = await (
                self.db.find({}).sort("started_at", DESCENDING).limit(max(limit, 1))
            ).to_list(None)
            return [ingest_run_from_document(doc) for doc in docs]
        except Exception:
            self.logger.exception("Failed to list ingest runs")
            return []

    async def get_active_run(self) -> IngestRun | None:
        try:
            doc = await self.db.find_one({"status": str(IngestStatus.RUNNING)})
            if not doc:
                return None
            return ingest_run_from_document(doc)
        except Exception:
            self.logger.exception("Failed to get active ingest run")
            return None
