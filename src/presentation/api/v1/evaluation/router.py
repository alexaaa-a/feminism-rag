from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, status

from src.application.dto.evaluation import EvaluationRequest
from src.application.use_case.evaluation.get_evaluation import GetEvaluationUseCase
from src.application.use_case.evaluation.list_evaluations import ListEvaluationsUseCase
from src.application.use_case.evaluation.run_evaluation import RunEvaluationUseCase
from src.config import Settings
from src.domain.entities.evaluation import EvalReport
from src.presentation.api.deps import require_admin_or_401
from src.presentation.api.v1.evaluation.schema import (
    EvalReportOut,
    EvalReportsOut,
    EvaluationIn,
)

router = APIRouter(route_class=DishkaRoute)


def _report_to_response(report: EvalReport) -> EvalReportOut:
    return EvalReportOut(**asdict(report))


@router.post(
    "/evaluation/runs",
    status_code=status.HTTP_200_OK,
    response_model=EvalReportOut,
    description="Прогнать eval-набор по живому пайплайну и посчитать Hit@k",
)
async def run_evaluation(
        body: EvaluationIn,
        request: Request,
        settings: FromDishka[Settings],
        uc: FromDishka[RunEvaluationUseCase],
):
    require_admin_or_401(request=request, settings=settings)
    result = await uc(
        EvaluationRequest(
            cases=[case.to_entity() for case in body.cases],
            top_k=body.top_k,
            hit_at_k=body.hit_at_k,
        )
    )

    if result.error or result.report is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message or "Не удалось прогнать eval",
        )
    return _report_to_response(result.report)


@router.get(
    "/evaluation/runs",
    status_code=status.HTTP_200_OK,
    response_model=EvalReportsOut,
    description="История прогонов eval",
)
async def list_evaluations(
        uc: FromDishka[ListEvaluationsUseCase],
        limit: int = 20,
):
    reports = await uc(limit=limit)
    return EvalReportsOut(runs=[_report_to_response(report) for report in reports])


@router.get(
    "/evaluation/runs/{run_id}",
    status_code=status.HTTP_200_OK,
    response_model=EvalReportOut,
    description="Отчёт одного прогона",
)
async def get_evaluation(
        run_id: str,
        uc: FromDishka[GetEvaluationUseCase],
):
    report = await uc(run_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Прогон не найден",
        )
    return _report_to_response(report)
