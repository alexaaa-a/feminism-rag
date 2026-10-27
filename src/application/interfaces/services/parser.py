from abc import abstractmethod
from pathlib import Path
from typing import Protocol

from src.domain.entities.document import ParsedDocument


class DocumentParserInterface(Protocol):
    @abstractmethod
    def parse(self, path: Path, source_name: str) -> ParsedDocument | None:
        raise NotImplementedError
