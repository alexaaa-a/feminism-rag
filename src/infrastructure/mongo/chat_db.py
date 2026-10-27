import datetime
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from src.application.interfaces.db.chat_db import ChatDBInterface
from src.config import Settings
from src.domain.entities.chat import ChatMessage, ChatSession
from src.infrastructure.mongo.mappers import (
    message_from_document,
    message_to_document,
    session_from_document,
    session_to_document,
)


class ChatDB(ChatDBInterface):
    def __init__(
            self,
            client: AsyncIOMotorClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        database = client[settings.mongo_settings.name]
        self.sessions = database["chat_sessions"]
        self.messages = database["chat_messages"]
        self.logger = logger

    async def create_session(self, session: ChatSession) -> bool:
        try:
            await self.sessions.insert_one(session_to_document(session))
            return True
        except Exception:
            self.logger.exception("Failed to create chat session %s", session.session_id)
            return False

    async def get_session(self, session_id: str) -> ChatSession | None:
        try:
            doc = await self.sessions.find_one({"_id": session_id})
            if not doc:
                return None
            return session_from_document(doc)
        except Exception:
            self.logger.exception("Failed to get chat session %s", session_id)
            return None

    async def list_sessions(
            self,
            client_id: str | None = None,
            limit: int = 50,
            offset: int = 0,
    ) -> list[ChatSession]:
        try:
            query = {"client_id": client_id} if client_id else {}
            cursor = (
                self.sessions.find(query)
                .sort("updated_at", DESCENDING)
                .skip(max(offset, 0))
                .limit(max(limit, 1))
            )
            docs = await cursor.to_list(None)
            return [session_from_document(doc) for doc in docs]
        except Exception:
            self.logger.exception("Failed to list chat sessions")
            return []

    async def delete_session(self, session_id: str) -> bool:
        try:
            result = await self.sessions.delete_one({"_id": session_id})
            await self.messages.delete_many({"session_id": session_id})
            return bool(getattr(result, "deleted_count", 0))
        except Exception:
            self.logger.exception("Failed to delete chat session %s", session_id)
            return False

    async def add_message(self, message: ChatMessage) -> bool:
        try:
            await self.messages.insert_one(message_to_document(message))
            return True
        except Exception:
            self.logger.exception("Failed to add message to session %s", message.session_id)
            return False

    async def get_messages(
            self,
            session_id: str,
            limit: int = 50,
    ) -> list[ChatMessage]:
        try:
            cursor = (
                self.messages.find({"session_id": session_id})
                .sort("created_at", ASCENDING)
                .limit(max(limit, 1))
            )
            docs = await cursor.to_list(None)
            return [message_from_document(doc) for doc in docs]
        except Exception:
            self.logger.exception("Failed to get messages for session %s", session_id)
            return []

    async def update_session_meta(
            self,
            session_id: str,
            title: str | None = None,
            messages_added: int = 0,
    ) -> bool:
        try:
            update: dict[str, Any] = {"$set": {"updated_at": datetime.datetime.now(datetime.UTC)}}
            if title:
                update["$set"]["title"] = title
            if messages_added:
                update["$inc"] = {"messages_count": messages_added}
            result = await self.sessions.update_one({"_id": session_id}, update)
            return bool(getattr(result, "matched_count", 0))
        except Exception:
            self.logger.exception("Failed to update chat session %s", session_id)
            return False
