from abc import abstractmethod
from typing import Protocol

from src.domain.entities.chat import ChatMessage, ChatSession


class ChatDBInterface(Protocol):
    @abstractmethod
    async def create_session(self, session: ChatSession) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_session(self, session_id: str) -> ChatSession | None:
        raise NotImplementedError

    @abstractmethod
    async def list_sessions(
            self,
            client_id: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> list[ChatSession]:
        raise NotImplementedError

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_message(self, message: ChatMessage) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_messages(
            self,
            session_id: str,
            limit: int = 50,
    ) -> list[ChatMessage]:
        raise NotImplementedError

    @abstractmethod
    async def update_session_meta(
            self,
            session_id: str,
            title: str | None = None,
            messages_added: int = 0,
    ) -> bool:
        raise NotImplementedError
