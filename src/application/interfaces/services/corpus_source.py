from abc import abstractmethod
from pathlib import Path
from typing import Protocol

from src.domain.entities.document import SourceFile


class CorpusSourceInterface(Protocol):
    @abstractmethod
    def origin(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_files(self) -> list[SourceFile]:
        raise NotImplementedError

    @abstractmethod
    async def download(self, source_file: SourceFile, target_dir: Path) -> Path | None:
        raise NotImplementedError
