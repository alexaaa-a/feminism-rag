from src.application.interfaces.db.ingest_db import IngestRunDBInterface
from src.domain.entities.ingest import IngestRun


class ListIngestRunsUseCase:
    def __init__(self, ingest_db: IngestRunDBInterface) -> None:
        self._ingest_db = ingest_db

    async def __call__(self, limit: int = 20) -> list[IngestRun]:
        return await self._ingest_db.list_runs(limit=limit)
