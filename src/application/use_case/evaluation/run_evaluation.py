import datetime
import logging
import uuid
from dataclasses import dataclass

from src.application.dto.evaluation import EvaluationRequest
from src.application.dto.search import SearchRequest
from src.application.interfaces.db.eval_db import EvaluationDBInterface
from src.application.retrieval.pipeline import RetrievalPipeline
from src.application.use_case.evaluation.default_cases import DEFAULT_EVAL_CASES
from src.config import Settings
from src.domain.entities.evaluation import EvalCase, EvalCaseResult, EvalReport
from src.domain.entities.retrieval import RetrievalResult


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    report: EvalReport | None = None
    error: str | None = None
    message: str | None = None


class RunEvaluationUseCase:
    def __init__(
            self,
            pipeline: RetrievalPipeline,
            evaluation_db: EvaluationDBInterface,
            logger: logging.Logger,
            settings: Settings,
    ) -> None:
        self._pipeline = pipeline
        self._evaluation_db = evaluation_db
        self._logger = logger
        self._settings = settings

    async def __call__(self, request: EvaluationRequest) -> EvaluationResult:
        cases = request.cases or DEFAULT_EVAL_CASES
        if not cases:
            return EvaluationResult(error="no_cases", message="Нет вопросов для прогона")

        hit_at_k = sorted({k for k in request.hit_at_k if k > 0}) or [1, 3, 5, 10]
        top_k = max(request.top_k, max(hit_at_k))

        report = EvalReport(
            run_id=str(uuid.uuid4()),
            started_at=datetime.datetime.now(datetime.UTC),
            mode=self._pipeline_mode(),
            top_k=top_k,
            cases=len(cases),
        )

        for case in cases:
            retrieval = await self._pipeline.retrieve(
                SearchRequest(question=case.question, top_k=top_k)
            )
            report.results.append(self._evaluate_case(case, retrieval))

        self._fill_metrics(report, hit_at_k)
        report.finished_at = datetime.datetime.now(datetime.UTC)
        await self._evaluation_db.save_report(report)
        return EvaluationResult(report=report)

    def _pipeline_mode(self) -> str:
        return "hybrid" if self._settings.retrieval_settings.hybrid else "dense"

    def _evaluate_case(self, case: EvalCase, retrieval: RetrievalResult) -> EvalCaseResult:
        gold = {source.lower() for source in case.gold_sources}
        evidence = (case.evidence or "").lower()

        rank_gold: int | None = None
        rank_evidence: int | None = None
        for rank, chunk in enumerate(retrieval.chunks, start=1):
            if rank_gold is None and chunk.source.lower() in gold:
                rank_gold = rank
            if rank_evidence is None and evidence and evidence in chunk.text.lower():
                rank_evidence = rank

        refused = self._is_refused(retrieval)
        correct = (
            rank_gold is not None
            if case.has_answer
            else refused
        )

        top_chunk = retrieval.chunks[0] if retrieval.chunks else None
        return EvalCaseResult(
            question=case.question,
            has_answer=case.has_answer,
            rank_gold_source=rank_gold,
            rank_evidence=rank_evidence,
            top1_source=top_chunk.source if top_chunk else None,
            top1_score=top_chunk.score if top_chunk else None,
            best_dense_score=retrieval.best_dense_score,
            answerable=retrieval.answerable,
            refused=refused,
            correct=correct,
        )

    def _is_refused(self, retrieval: RetrievalResult) -> bool:
        if not retrieval.found:
            return True
        if retrieval.answerable is None:
            return False
        return retrieval.answerable < self._settings.jev_settings.answerable_threshold

    def _fill_metrics(self, report: EvalReport, hit_at_k: list[int]) -> None:
        answerable = [item for item in report.results if item.has_answer]
        no_answer = [item for item in report.results if not item.has_answer]

        for k in hit_at_k:
            report.hit_at[k] = _share(
                answerable,
                lambda item, limit=k: item.rank_gold_source is not None
                and item.rank_gold_source <= limit,
            )
            report.evidence_hit_at[k] = _share(
                answerable,
                lambda item, limit=k: item.rank_evidence is not None
                and item.rank_evidence <= limit,
            )

        report.answered_when_no_answer = sum(1 for item in no_answer if not item.refused)
        report.refused_when_answerable = sum(1 for item in answerable if item.refused)


def _share(items: list[EvalCaseResult], predicate) -> float:
    if not items:
        return 0.0
    return round(sum(1 for item in items if predicate(item)) / len(items), 3)
