from abc import abstractmethod
from typing import Protocol

from src.domain.entities.ingest import IngestRun


class IngestRunDBInterface(Protocol):
    @abstractmethod
    async def save_run(self, run: IngestRun) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_run(self, run_id: str) -> IngestRun | None:
        raise NotImplementedError

    @abstractmethod
    async def list_runs(self, limit: int = 20) -> list[IngestRun]:
        raise NotImplementedError

    @abstractmethod
    async def get_active_run(self) -> IngestRun | None:
        raise NotImplementedError
