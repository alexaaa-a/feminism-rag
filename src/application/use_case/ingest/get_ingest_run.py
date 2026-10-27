from src.application.interfaces.db.ingest_db import IngestRunDBInterface
from src.domain.entities.ingest import IngestRun


class GetIngestRunUseCase:
    def __init__(self, ingest_db: IngestRunDBInterface) -> None:
        self._ingest_db = ingest_db

    async def __call__(self, run_id: str) -> IngestRun | None:
        return await self._ingest_db.get_run(run_id)
