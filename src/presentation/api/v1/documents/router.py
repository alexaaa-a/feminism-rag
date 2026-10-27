from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, status

from src.application.use_case.documents.corpus_stats import CorpusStatsUseCase
from src.application.use_case.documents.delete_document import DeleteDocumentUseCase
from src.application.use_case.documents.get_document import GetDocumentUseCase
from src.application.use_case.documents.list_documents import ListDocumentsUseCase
from src.application.use_case.ingest.get_ingest_run import GetIngestRunUseCase
from src.application.use_case.ingest.list_ingest_runs import ListIngestRunsUseCase
from src.application.use_case.ingest.sync_corpus import SyncCorpusUseCase
from src.config import Settings
from src.domain.entities.ingest import DocumentRecord, IngestRun
from src.presentation.api.deps import require_admin_or_401
from src.presentation.api.v1.documents.schema import (
    CorpusStatsOut,
    DocumentOut,
    DocumentsOut,
    IngestRunOut,
    IngestRunsOut,
    SyncIn,
)

router = APIRouter(route_class=DishkaRoute)


def _document_to_response(record: DocumentRecord) -> DocumentOut:
    data = asdict(record)
    data["status"] = str(record.status)
    return DocumentOut(**data)


def _run_to_response(run: IngestRun) -> IngestRunOut:
    data = asdict(run)
    data["status"] = str(run.status)
    data["duration_sec"] = run.duration_sec
    return IngestRunOut(**data)


@router.get(
    "/documents",
    status_code=status.HTTP_200_OK,
    response_model=DocumentsOut,
    description="Реестр документов корпуса",
)
async def list_documents(
        uc: FromDishka[ListDocumentsUseCase],
        origin: str | None = None,
        lang: str | None = None,
        limit: int = 200,
        offset: int = 0,
):
    page = await uc(origin=origin, lang=lang, limit=limit, offset=offset)
    return DocumentsOut(
        documents=[_document_to_response(item) for item in page.documents],
        total=page.total,
    )


@router.get(
    "/documents/stats",
    status_code=status.HTTP_200_OK,
    response_model=CorpusStatsOut,
    description="Сводка по корпусу: документы, чанки и что реально лежит в индексе",
)
async def corpus_stats(
        uc: FromDishka[CorpusStatsUseCase],
):
    return CorpusStatsOut(**asdict(await uc()))


@router.get(
    "/documents/sync",
    status_code=status.HTTP_200_OK,
    response_model=IngestRunsOut,
    description="История прогонов синхронизации",
)
async def list_sync_runs(
        uc: FromDishka[ListIngestRunsUseCase],
        limit: int = 20,
):
    runs = await uc(limit=limit)
    return IngestRunsOut(runs=[_run_to_response(run) for run in runs])


@router.post(
    "/documents/sync",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestRunOut,
    description="Запустить синхронизацию корпуса из Google Drive и локальной папки",
)
async def start_sync(
        body: SyncIn,
        request: Request,
        settings: FromDishka[Settings],
        uc: FromDishka[SyncCorpusUseCase],
):
    require_admin_or_401(request=request, settings=settings)
    result = await uc.start(origin=body.origin, force=body.force)

    if result.error == "already_running" and result.run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{result.message}: run_id={result.run.run_id}",
        )
    if result.error or result.run is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message or "Не удалось запустить синхронизацию",
        )

    return _run_to_response(result.run)


@router.get(
    "/documents/sync/{run_id}",
    status_code=status.HTTP_200_OK,
    response_model=IngestRunOut,
    description="Статус прогона синхронизации",
)
async def get_sync_run(
        run_id: str,
        uc: FromDishka[GetIngestRunUseCase],
):
    run = await uc(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Прогон не найден",
        )
    return _run_to_response(run)


@router.get(
    "/documents/{document_id:path}",
    status_code=status.HTTP_200_OK,
    response_model=DocumentOut,
    description="Карточка одного документа",
)
async def get_document(
        document_id: str,
        uc: FromDishka[GetDocumentUseCase],
):
    record = await uc(document_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )
    return _document_to_response(record)


@router.delete(
    "/documents/{document_id:path}",
    status_code=status.HTTP_200_OK,
    description="Удалить документ из индекса и реестра",
)
async def delete_document(
        document_id: str,
        request: Request,
        settings: FromDishka[Settings],
        uc: FromDishka[DeleteDocumentUseCase],
):
    require_admin_or_401(request=request, settings=settings)
    result = await uc(document_id)

    if result.error == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )
    if result.error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Документ удалён не полностью, проверьте логи",
        )
    return {"status": "deleted"}
