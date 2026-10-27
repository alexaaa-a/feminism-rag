import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING

from src.application.interfaces.db.eval_db import EvaluationDBInterface
from src.config import Settings
from src.domain.entities.evaluation import EvalReport
from src.infrastructure.mongo.mappers import eval_report_from_document, eval_report_to_document


class EvaluationDB(EvaluationDBInterface):
    def __init__(
            self,
            client: AsyncIOMotorClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self.db = client[settings.mongo_settings.name]["eval_runs"]
        self.logger = logger

    async def save_report(self, report: EvalReport) -> bool:
        try:
            payload = eval_report_to_document(report)
            payload.pop("_id", None)
            await self.db.update_one({"_id": report.run_id}, {"$set": payload}, upsert=True)
            return True
        except Exception:
            self.logger.exception("Failed to save eval report %s", report.run_id)
            return False

    async def get_report(self, run_id: str) -> EvalReport | None:
        try:
            doc = await self.db.find_one({"_id": run_id})
            if not doc:
                return None
            return eval_report_from_document(doc)
        except Exception:
            self.logger.exception("Failed to get eval report %s", run_id)
            return None

    async def list_reports(self, limit: int = 20) -> list[EvalReport]:
        try:
            docs = await (
                self.db.find({}).sort("started_at", DESCENDING).limit(max(limit, 1))
            ).to_list(None)
            return [eval_report_from_document(doc) for doc in docs]
        except Exception:
            self.logger.exception("Failed to list eval reports")
            return []
