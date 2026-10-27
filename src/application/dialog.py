import datetime
import logging
import uuid

from src.application.interfaces.db.chat_db import ChatDBInterface
from src.application.interfaces.services.llm import LlmInterface
from src.config import Settings
from src.domain.entities.chat import ChatMessage, ChatSession, MessageRole, RagAnswer
from src.domain.services.prompting import build_condense_messages

SESSION_TITLE_CHARS = 60


class DialogService:
    def __init__(
            self,
            llm: LlmInterface,
            chat_db: ChatDBInterface,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._llm = llm
        self._chat_db = chat_db
        self._logger = logger
        self._llm_settings = settings.llm_settings
        self._max_question_chars = settings.api_settings.max_question_chars

    async def condense_query(self, question: str, history: list[dict[str, str]]) -> str:
        if not history:
            return question

        completion = await self._llm.complete(
            build_condense_messages(question, history),
            max_tokens=self._llm_settings.condense_max_tokens,
            temperature=0.0,
        )
        if completion is None or not completion.text:
            return question

        rewritten = completion.text.splitlines()[0].strip().strip('"«»')
        if not rewritten or len(rewritten) > self._max_question_chars:
            return question
        return rewritten

    async def save_question(
            self,
            session: ChatSession | None,
            question: str,
    ) -> None:
        if session is None:
            return

        await self._chat_db.add_message(
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role=MessageRole.USER,
                content=question,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        title = question[:SESSION_TITLE_CHARS] if session.messages_count == 0 else None
        await self._chat_db.update_session_meta(
            session.session_id,
            title=title,
            messages_added=1,
        )

    async def save_answer(
            self,
            session: ChatSession | None,
            answer: RagAnswer,
    ) -> None:
        if session is None:
            return

        await self._chat_db.add_message(
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role=MessageRole.ASSISTANT,
                content=answer.answer,
                created_at=datetime.datetime.now(datetime.UTC),
                citations=answer.citations,
                refused=answer.refused,
                diagnostics=answer.diagnostics,
            )
        )
        await self._chat_db.update_session_meta(
            session.session_id,
            messages_added=1,
        )

    async def save_exchange(
            self,
            session: ChatSession | None,
            question: str,
            answer: RagAnswer,
    ) -> None:
        await self.save_question(session, question)
        await self.save_answer(session, answer)
