from src.application.interfaces.db.chat_db import ChatDBInterface
from src.domain.entities.chat import ChatSession


class ListSessionsUseCase:
    def __init__(self, chat_db: ChatDBInterface) -> None:
        self._chat_db = chat_db

    async def __call__(
            self,
            client_id: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> list[ChatSession]:
        return await self._chat_db.list_sessions(
            client_id=client_id,
            limit=limit,
            offset=offset,
        )
