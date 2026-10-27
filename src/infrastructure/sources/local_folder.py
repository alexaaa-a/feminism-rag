import datetime
import hashlib
import logging
import shutil
from pathlib import Path

from src.application.interfaces.services.corpus_source import CorpusSourceInterface
from src.config import Settings
from src.domain.entities.document import DocumentFormat, SourceFile

ORIGIN = "local"
_CHECKSUM_CHUNK = 1024 * 1024


class LocalFolderSource(CorpusSourceInterface):
    def __init__(self, logger: logging.Logger, settings: Settings) -> None:
        self._logger = logger
        self._settings = settings.local_corpus_settings
        self._root = Path(self._settings.path)

    def origin(self) -> str:
        return ORIGIN

    def available(self) -> bool:
        return self._settings.enabled and self._root.is_dir()

    async def list_files(self) -> list[SourceFile]:
        if not self.available():
            self._logger.info("Local corpus folder %s is not available", self._root)
            return []

        files: list[SourceFile] = []
        for path in sorted(self._root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue

            document_format = DocumentFormat.from_suffix(path.suffix)
            if document_format is None:
                continue

            stat = path.stat()
            files.append(
                SourceFile(
                    external_id=str(path.relative_to(self._root)),
                    name=path.name,
                    document_format=document_format,
                    size_bytes=stat.st_size,
                    modified_at=datetime.datetime.fromtimestamp(
                        stat.st_mtime, tz=datetime.UTC
                    ),
                    checksum=self._checksum(path),
                    web_url=path.as_uri(),
                )
            )
        return files

    async def download(self, source_file: SourceFile, target_dir: Path) -> Path | None:
        source_path = self._root / source_file.external_id
        if not source_path.is_file():
            self._logger.warning("Local file disappeared: %s", source_file.external_id)
            return None

        target_path = target_dir / source_file.name
        try:
            shutil.copyfile(source_path, target_path)
            return target_path
        except Exception:
            self._logger.exception("Failed to copy local file %s", source_file.name)
            return None

    def _checksum(self, path: Path) -> str:
        digest = hashlib.md5()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(_CHECKSUM_CHUNK), b""):
                digest.update(block)
        return digest.hexdigest()
