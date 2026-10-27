import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from src.application.answering import (
    align_citations,
    build_citations,
    build_diagnostics,
    history_to_messages,
    refusal_answer,
)
from src.application.dialog import DialogService
from src.application.dto.chat import AskRequest
from src.application.dto.search import SearchRequest
from src.application.interfaces.db.chat_db import ChatDBInterface
from src.application.interfaces.services.llm import LlmInterface
from src.application.retrieval.pipeline import RetrievalPipeline
from src.config import Settings
from src.domain.entities.chat import ChatSession, RagAnswer
from src.domain.services.prompting import build_messages, looks_like_refusal


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event: str
    text: str = ""
    answer: RagAnswer | None = None
    error: str | None = None
    message: str | None = None


class StreamAnswerUseCase:
    def __init__(
            self,
            pipeline: RetrievalPipeline,
            llm: LlmInterface,
            chat_db: ChatDBInterface,
            dialog: DialogService,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._pipeline = pipeline
        self._llm = llm
        self._chat_db = chat_db
        self._dialog = dialog
        self._logger = logger
        self._llm_settings = settings.llm_settings
        self._jev_settings = settings.jev_settings
        self._api_settings = settings.api_settings

    async def __call__(self, request: AskRequest) -> AsyncIterator[StreamEvent]:
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        task = asyncio.create_task(self._produce(request, queue))
        task.add_done_callback(self._log_failure)

        while True:
            event = await queue.get()
            if event is None:
                return
            yield event

    async def _produce(
            self,
            request: AskRequest,
            queue: asyncio.Queue[StreamEvent | None],
    ) -> None:
        try:
            await self._run(request, queue)
        finally:
            await queue.put(None)

    def _log_failure(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            self._logger.error("Streaming answer failed", exc_info=error)

    async def _run(
            self,
            request: AskRequest,
            queue: asyncio.Queue[StreamEvent | None],
    ) -> None:
        question = request.question.strip()
        if not question:
            await queue.put(StreamEvent(
                event="error",
                error="empty_question",
                message="Вопрос не может быть пустым",
            ))
            return
        if len(question) > self._api_settings.max_question_chars:
            await queue.put(StreamEvent(
                event="error",
                error="question_too_long",
                message="Вопрос слишком длинный",
            ))
            return

        session: ChatSession | None = None
        history: list[dict[str, str]] = []
        if request.session_id:
            session = await self._chat_db.get_session(request.session_id)
            if session is None:
                await queue.put(StreamEvent(
                    event="error",
                    error="session_not_found",
                    message="Диалог не найден",
                ))
                return
            if request.use_history:
                stored = await self._chat_db.get_messages(session.session_id)
                history = history_to_messages(stored, self._llm_settings.history_messages)

        started = time.perf_counter()
        await self._dialog.save_question(session, question)
        search_query = await self._dialog.condense_query(question, history)
        retrieval = await self._pipeline.retrieve(
            SearchRequest(
                question=search_query,
                top_k=request.top_k,
                filters=request.filters,
            )
        )
        retrieval.query = question
        retrieval.search_query = search_query

        gate_closed = (
            retrieval.answerable is not None
            and retrieval.answerable < self._jev_settings.answerable_threshold
        )
        if not retrieval.found or gate_closed:
            answer = refusal_answer(question, retrieval, self._elapsed_ms(started))
            await queue.put(StreamEvent(event="meta", answer=answer))
            await queue.put(StreamEvent(event="delta", text=answer.answer))
            await self._dialog.save_answer(session, answer)
            await queue.put(StreamEvent(event="done", answer=answer))
            return

        meta = RagAnswer(
            question=question,
            answer="",
            citations=build_citations(retrieval),
            diagnostics=build_diagnostics(
                retrieval,
                llm_model=self._llm.model_name(),
            ),
        )
        await queue.put(StreamEvent(event="meta", answer=meta))
        retrieved_ms = self._elapsed_ms(started)

        pieces: list[str] = []
        first_token_ms: int | None = None
        async for piece in self._llm.stream(
            build_messages(question, retrieval.context, history)
        ):
            if first_token_ms is None:
                first_token_ms = self._elapsed_ms(started)
            pieces.append(piece)
            await queue.put(StreamEvent(event="delta", text=piece))

        text = "".join(pieces).strip()
        if not text:
            await queue.put(StreamEvent(
                event="error",
                error="generation_failed",
                message="Модель не вернула ответ",
            ))
            return

        text, citations = align_citations(text, build_citations(retrieval))
        answer = RagAnswer(
            question=question,
            answer=text,
            citations=citations,
            refused=looks_like_refusal(text),
            diagnostics=build_diagnostics(
                retrieval,
                llm_model=self._llm.model_name(),
                latency_ms=self._elapsed_ms(started),
            ),
        )
        await self._dialog.save_answer(session, answer)
        self._logger.info(
            "Answer ready: поиск %d мс, первый токен %s мс, всего %d мс",
            retrieved_ms,
            first_token_ms,
            self._elapsed_ms(started),
        )
        await queue.put(StreamEvent(event="done", answer=answer))

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
