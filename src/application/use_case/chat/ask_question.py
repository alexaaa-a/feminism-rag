import logging
import time
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
from src.application.interfaces.services.decider import AnswerJudgeInterface
from src.application.interfaces.services.llm import LlmInterface
from src.application.retrieval.pipeline import RetrievalPipeline
from src.config import Settings
from src.domain.entities.chat import ChatSession, RagAnswer
from src.domain.entities.retrieval import RetrievalResult
from src.domain.services.prompting import build_messages, looks_like_refusal


@dataclass(frozen=True, slots=True)
class AskResult:
    answer: RagAnswer | None = None
    session_id: str | None = None
    error: str | None = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.answer is not None and self.error is None


class AskQuestionUseCase:
    def __init__(
            self,
            pipeline: RetrievalPipeline,
            llm: LlmInterface,
            answer_judge: AnswerJudgeInterface,
            chat_db: ChatDBInterface,
            dialog: DialogService,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._pipeline = pipeline
        self._llm = llm
        self._answer_judge = answer_judge
        self._chat_db = chat_db
        self._dialog = dialog
        self._logger = logger
        self._llm_settings = settings.llm_settings
        self._jev_settings = settings.jev_settings
        self._api_settings = settings.api_settings

    async def __call__(self, request: AskRequest) -> AskResult:
        question = request.question.strip()
        if not question:
            return AskResult(error="empty_question", message="Вопрос не может быть пустым")
        if len(question) > self._api_settings.max_question_chars:
            return AskResult(error="question_too_long", message="Вопрос слишком длинный")

        session: ChatSession | None = None
        history: list[dict[str, str]] = []
        if request.session_id:
            session = await self._chat_db.get_session(request.session_id)
            if session is None:
                return AskResult(error="session_not_found", message="Диалог не найден")
            if request.use_history:
                stored = await self._chat_db.get_messages(session.session_id)
                history = history_to_messages(stored, self._llm_settings.history_messages)

        started = time.perf_counter()
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

        answer = await self._answer(question, history, retrieval, started)
        await self._dialog.save_exchange(session, question, answer)
        return AskResult(
            answer=answer,
            session_id=session.session_id if session else None,
        )

    async def _answer(
            self,
            question: str,
            history: list[dict[str, str]],
            retrieval: RetrievalResult,
            started: float,
    ) -> RagAnswer:
        if not retrieval.found:
            return refusal_answer(question, retrieval, self._elapsed_ms(started))

        if (
            retrieval.answerable is not None
            and retrieval.answerable < self._jev_settings.answerable_threshold
        ):
            self._logger.info(
                "Jev closed the gate: answerable=%s threshold=%s",
                retrieval.answerable,
                self._jev_settings.answerable_threshold,
            )
            return refusal_answer(question, retrieval, self._elapsed_ms(started))

        completion = await self._llm.complete(
            build_messages(question, retrieval.context, history)
        )
        if completion is None:
            return RagAnswer(
                question=question,
                answer="Не удалось получить ответ модели. Попробуйте ещё раз.",
                citations=build_citations(retrieval),
                refused=True,
                diagnostics=build_diagnostics(
                    retrieval,
                    llm_model=self._llm.model_name(),
                    latency_ms=self._elapsed_ms(started),
                ),
            )

        groundedness = await self._answer_judge.is_grounded(
            question,
            retrieval.context,
            completion.text,
        )
        if (
            groundedness is not None
            and groundedness < self._jev_settings.grounded_threshold
        ):
            self._logger.warning(
                "Answer dropped as ungrounded: groundedness=%s",
                groundedness,
            )
            return refusal_answer(
                question,
                retrieval,
                self._elapsed_ms(started),
                groundedness=groundedness,
            )

        text, citations = align_citations(completion.text, build_citations(retrieval))
        return RagAnswer(
            question=question,
            answer=text,
            citations=citations,
            refused=looks_like_refusal(text),
            diagnostics=build_diagnostics(
                retrieval,
                llm_model=completion.model,
                latency_ms=self._elapsed_ms(started),
                groundedness=groundedness,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
            ),
        )

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
