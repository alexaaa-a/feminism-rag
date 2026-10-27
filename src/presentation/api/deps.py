from fastapi import HTTPException, status
from starlette.requests import Request

from src.config import Settings

API_KEY_HEADER = "X-API-Key"
CLIENT_ID_HEADER = "X-Client-Id"


def require_admin_or_401(request: Request, settings: Settings) -> None:
    admin_key = settings.api_settings.admin_key.strip()
    if not admin_key:
        return

    provided = (request.headers.get(API_KEY_HEADER) or "").strip()
    if provided != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужен административный ключ",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )


def client_id_from(request: Request) -> str | None:
    client_id = (request.headers.get(CLIENT_ID_HEADER) or "").strip()
    return client_id or None
