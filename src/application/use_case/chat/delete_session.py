from src.application.interfaces.db.chat_db import ChatDBInterface


class DeleteSessionUseCase:
    def __init__(self, chat_db: ChatDBInterface) -> None:
        self._chat_db = chat_db

    async def __call__(self, session_id: str) -> bool:
        return await self._chat_db.delete_session(session_id)
