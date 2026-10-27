import logging

import httpx

from src.application.interfaces.services.decider import (
    AnswerJudgeInterface,
    QueryRouterInterface,
    RerankerInterface,
)
from src.config import Settings
from src.domain.entities.retrieval import QueryRoute
from src.domain.services import decisions

SYSTEM_ONE_PATH = "/systemone"
_ALLOWED_LANGS = frozenset({"ru", "en"})


class JevDecider(QueryRouterInterface, RerankerInterface, AnswerJudgeInterface):
    def __init__(
            self,
            client: httpx.AsyncClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._client = client
        self._logger = logger
        self._settings = settings.jev_settings
        self._base_url = (
            self._settings.base_url or settings.openrouter_settings.base_url
        ).rstrip("/")
        self._api_key = self._settings.api_key or settings.openrouter_settings.api_key

    @property
    def enabled(self) -> bool:
        return self._settings.enabled and bool(self._api_key)

    async def route(self, question: str) -> QueryRoute | None:
        if not self.enabled or not self._settings.route_queries:
            return None

        answers = await self._ask(question, decisions.route_questions())
        if not answers:
            return None

        lang_answer = answers.get(decisions.ROUTE_LANG) or {}
        lang_choice = str(lang_answer.get("choice") or "")
        intent_answer = answers.get(decisions.ROUTE_INTENT) or {}

        return QueryRoute(
            in_domain=_noul(answers, decisions.ROUTE_IN_DOMAIN, default=1.0),
            needs_table=_noul(answers, decisions.ROUTE_NEEDS_TABLE, default=0.0),
            lang_preference=lang_choice if lang_choice in _ALLOWED_LANGS else None,
            intent=str(intent_answer.get("choice") or "factual"),
            confidence=float(intent_answer.get("confidence") or 0.0),
            used=True,
        )

    async def score_candidates(
            self,
            question: str,
            candidates: list[str],
    ) -> list[float] | None:
        if not self.enabled or not self._settings.rerank or not candidates:
            return None

        limit = self._settings.rerank_chars_per_candidate
        trimmed = [candidate[:limit] for candidate in candidates]
        answers = await self._ask(
            decisions.rerank_state(question, trimmed),
            decisions.rerank_questions(len(trimmed)),
        )
        if not answers:
            return None

        scores: list[float] = []
        for index in range(1, len(trimmed) + 1):
            scores.append(_noul(answers, f"{decisions.RERANK_PREFIX}{index}", default=0.0))
        return scores

    async def is_answerable(self, question: str, context: str) -> float | None:
        if not self.enabled or not self._settings.answerability_gate:
            return None

        answers = await self._ask(
            decisions.answerability_state(question, context),
            decisions.answerability_questions(),
        )
        if not answers or decisions.ANSWERABLE not in answers:
            return None
        return _noul(answers, decisions.ANSWERABLE, default=0.0)

    async def is_grounded(
            self,
            question: str,
            context: str,
            answer: str,
    ) -> float | None:
        if not self.enabled or not self._settings.check_groundedness:
            return None

        answers = await self._ask(
            decisions.groundedness_state(question, context, answer),
            decisions.groundedness_questions(),
        )
        if not answers or decisions.GROUNDED not in answers:
            return None
        return _noul(answers, decisions.GROUNDED, default=0.0)

    async def _ask(self, state: str, questions: dict[str, dict]) -> dict[str, dict] | None:
        url = f"{self._base_url}{SYSTEM_ONE_PATH}"
        body = {
            "model": self._settings.model,
            "state": state,
            "questions": questions,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._client.post(
                url,
                json=body,
                headers=headers,
                timeout=self._settings.timeout_sec,
            )
        except Exception:
            self._logger.exception("Jev call failed questions=%s", list(questions))
            return None

        if response.status_code != 200:
            self._logger.warning(
                "Jev status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            return None

        try:
            payload = response.json()
        except Exception:
            self._logger.exception("Jev returned invalid payload")
            return None

        answers = payload.get("answers") if isinstance(payload, dict) else None
        if not isinstance(answers, dict):
            self._logger.warning("Jev payload has no answers")
            return None
        return answers


def _noul(answers: dict[str, dict], key: str, default: float) -> float:
    answer = answers.get(key)
    if not isinstance(answer, dict):
        return default
    value = answer.get("noul")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
