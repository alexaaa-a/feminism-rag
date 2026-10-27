from dataclasses import dataclass, field

from src.application.interfaces.db.chat_db import ChatDBInterface
from src.domain.entities.chat import ChatMessage, ChatSession


@dataclass(frozen=True, slots=True)
class SessionWithMessages:
    session: ChatSession
    messages: list[ChatMessage] = field(default_factory=list)


class GetSessionUseCase:
    def __init__(self, chat_db: ChatDBInterface) -> None:
        self._chat_db = chat_db

    async def __call__(self, session_id: str) -> SessionWithMessages | None:
        session = await self._chat_db.get_session(session_id)
        if session is None:
            return None

        messages = await self._chat_db.get_messages(session_id)
        return SessionWithMessages(session=session, messages=messages)
