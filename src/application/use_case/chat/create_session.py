import datetime
import uuid
from dataclasses import dataclass

from src.application.interfaces.db.chat_db import ChatDBInterface
from src.domain.entities.chat import ChatSession

DEFAULT_TITLE = "Новый диалог"


@dataclass(frozen=True, slots=True)
class CreateSessionResult:
    session: ChatSession | None = None
    error: str | None = None


class CreateSessionUseCase:
    def __init__(self, chat_db: ChatDBInterface) -> None:
        self._chat_db = chat_db

    async def __call__(
            self,
            title: str | None = None,
            client_id: str | None = None,
    ) -> CreateSessionResult:
        now = datetime.datetime.now(datetime.UTC)
        session = ChatSession(
            session_id=str(uuid.uuid4()),
            title=(title or DEFAULT_TITLE).strip()[:120],
            created_at=now,
            updated_at=now,
            client_id=client_id,
        )

        if not await self._chat_db.create_session(session):
            return CreateSessionResult(error="save_failed")
        return CreateSessionResult(session=session)
