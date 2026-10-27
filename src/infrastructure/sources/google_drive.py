import datetime
import json
import logging
import time
from pathlib import Path

import httpx
import jwt

from src.application.interfaces.services.corpus_source import CorpusSourceInterface
from src.config import Settings
from src.domain.entities.document import DocumentFormat, SourceFile

ORIGIN = "google_drive"
TOKEN_URL = "https://oauth2.googleapis.com/token"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TOKEN_LIFETIME_SEC = 3600
TOKEN_REFRESH_MARGIN_SEC = 120
MAX_FOLDER_DEPTH = 5

_MIME_TO_FORMAT = {
    "text/plain": DocumentFormat.TXT,
    "text/markdown": DocumentFormat.MD,
    "text/x-markdown": DocumentFormat.MD,
    "application/pdf": DocumentFormat.PDF,
    DOCX_MIME: DocumentFormat.DOCX,
    GOOGLE_DOC_MIME: DocumentFormat.DOCX,
}

_FILE_FIELDS = "nextPageToken, files(id, name, mimeType, size, modifiedTime, md5Checksum, webViewLink)"


class GoogleDriveSource(CorpusSourceInterface):
    def __init__(
            self,
            client: httpx.AsyncClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._client = client
        self._logger = logger
        self._settings = settings.drive_settings
        self._credentials = self._load_credentials()
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def origin(self) -> str:
        return ORIGIN

    def available(self) -> bool:
        if not self._settings.enabled or not self._settings.folder_id:
            return False
        return bool(self._credentials or self._settings.api_key)

    def _load_credentials(self) -> dict | None:
        raw = self._settings.service_account_json.strip()
        if not raw and self._settings.service_account_file:
            path = Path(self._settings.service_account_file)
            if not path.is_file():
                self._logger.warning("Service account file not found: %s", path)
                return None
            raw = path.read_text(encoding="utf-8")

        if not raw:
            return None

        try:
            credentials = json.loads(raw)
        except Exception:
            self._logger.exception("Service account json is not valid json")
            return None

        if not credentials.get("client_email") or not credentials.get("private_key"):
            self._logger.warning("Service account json has no client_email or private_key")
            return None
        return credentials

    async def list_files(self) -> list[SourceFile]:
        if not self.available():
            self._logger.info("Google Drive source is not configured")
            return []

        files: list[SourceFile] = []
        pending: list[tuple[str, int]] = [(self._settings.folder_id, 0)]

        while pending:
            folder_id, depth = pending.pop(0)
            entries = await self._list_folder(folder_id)
            for entry in entries:
                if entry.get("mimeType") == FOLDER_MIME:
                    if depth < MAX_FOLDER_DEPTH:
                        pending.append((str(entry["id"]), depth + 1))
                    continue

                source_file = self._to_source_file(entry)
                if source_file is not None:
                    files.append(source_file)

        self._logger.info("Google Drive folder gave %s supported files", len(files))
        return sorted(files, key=lambda item: item.name)

    async def _list_folder(self, folder_id: str) -> list[dict]:
        entries: list[dict] = []
        page_token: str | None = None

        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": _FILE_FIELDS,
                "pageSize": self._settings.page_size,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token

            payload = await self._request_json("GET", FILES_URL, params=params)
            if payload is None:
                break

            entries.extend(payload.get("files") or [])
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return entries

    def _to_source_file(self, entry: dict) -> SourceFile | None:
        name = str(entry.get("name") or "")
        mime_type = str(entry.get("mimeType") or "")

        document_format = _MIME_TO_FORMAT.get(mime_type)
        if document_format is None:
            document_format = DocumentFormat.from_suffix(Path(name).suffix)
        if document_format is None:
            self._logger.debug("Skipping unsupported file %s (%s)", name, mime_type)
            return None

        return SourceFile(
            external_id=str(entry.get("id") or ""),
            name=self._target_name(name, mime_type, document_format),
            document_format=document_format,
            size_bytes=int(entry.get("size") or 0),
            modified_at=_parse_timestamp(entry.get("modifiedTime")),
            checksum=entry.get("md5Checksum") or str(entry.get("modifiedTime") or ""),
            web_url=entry.get("webViewLink"),
        )

    def _target_name(
            self,
            name: str,
            mime_type: str,
            document_format: DocumentFormat,
    ) -> str:
        if mime_type == GOOGLE_DOC_MIME and not name.lower().endswith(".docx"):
            return f"{name}.docx"
        if Path(name).suffix.lower() == str(document_format):
            return name
        return f"{name}{document_format}"

    async def download(self, source_file: SourceFile, target_dir: Path) -> Path | None:
        if not source_file.external_id:
            return None

        is_google_doc = source_file.name.endswith(".docx") and await self._is_google_doc(
            source_file.external_id
        )
        if is_google_doc:
            url = f"{FILES_URL}/{source_file.external_id}/export"
            params: dict[str, str] = {"mimeType": DOCX_MIME}
        else:
            url = f"{FILES_URL}/{source_file.external_id}"
            params = {"alt": "media", "supportsAllDrives": "true"}

        content = await self._request_bytes(url, params)
        if content is None:
            return None

        target_path = target_dir / source_file.name
        try:
            target_path.write_bytes(content)
            return target_path
        except Exception:
            self._logger.exception("Failed to save downloaded file %s", source_file.name)
            return None

    async def _is_google_doc(self, file_id: str) -> bool:
        payload = await self._request_json(
            "GET",
            f"{FILES_URL}/{file_id}",
            params={"fields": "mimeType", "supportsAllDrives": "true"},
        )
        if payload is None:
            return False
        return str(payload.get("mimeType") or "") == GOOGLE_DOC_MIME

    async def _request_json(
            self,
            method: str,
            url: str,
            params: dict | None = None,
    ) -> dict | None:
        response = await self._request(method, url, params)
        if response is None:
            return None
        try:
            payload = response.json()
        except Exception:
            self._logger.exception("Drive returned invalid json for %s", url)
            return None
        return payload if isinstance(payload, dict) else None

    async def _request_bytes(self, url: str, params: dict) -> bytes | None:
        response = await self._request("GET", url, params)
        if response is None:
            return None
        return response.content

    async def _request(
            self,
            method: str,
            url: str,
            params: dict | None = None,
    ) -> httpx.Response | None:
        request_params = dict(params or {})
        headers: dict[str, str] = {}

        token = await self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self._settings.api_key:
            request_params["key"] = self._settings.api_key
        else:
            self._logger.warning("No Drive credentials available")
            return None

        try:
            response = await self._client.request(
                method,
                url,
                params=request_params,
                headers=headers,
                timeout=self._settings.timeout_sec,
                follow_redirects=True,
            )
        except Exception:
            self._logger.exception("Drive request failed url=%s", url)
            return None

        if response.status_code != 200:
            self._logger.warning(
                "Drive status=%s url=%s body=%s",
                response.status_code,
                url,
                response.text[:300],
            )
            return None
        return response

    async def _access_token(self) -> str | None:
        if self._credentials is None:
            return None
        if self._token and time.time() < self._token_expires_at:
            return self._token

        issued_at = int(time.time())
        assertion_payload = {
            "iss": self._credentials["client_email"],
            "scope": DRIVE_SCOPE,
            "aud": TOKEN_URL,
            "iat": issued_at,
            "exp": issued_at + TOKEN_LIFETIME_SEC,
        }
        subject = self._credentials.get("subject")
        if subject:
            assertion_payload["sub"] = subject

        try:
            assertion = jwt.encode(
                assertion_payload,
                self._credentials["private_key"],
                algorithm="RS256",
            )
            response = await self._client.post(
                TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                timeout=self._settings.timeout_sec,
            )
        except Exception:
            self._logger.exception("Failed to get Drive access token")
            return None

        if response.status_code != 200:
            self._logger.warning("Drive token status=%s", response.status_code)
            return None

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            self._logger.warning("Drive token response has no access_token")
            return None

        expires_in = int(payload.get("expires_in") or TOKEN_LIFETIME_SEC)
        self._token = str(token)
        self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_MARGIN_SEC
        return self._token


def _parse_timestamp(value: object) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
