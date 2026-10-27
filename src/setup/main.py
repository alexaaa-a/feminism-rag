import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from src.application.interfaces.services.embedder import EmbedderInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface
from src.config import Settings
from src.infrastructure.logger.setup_logging import setup_logging
from src.presentation.api.exception_handler import setup_error_handlers
from src.presentation.api.healthcheck import router as healthcheck_router
from src.presentation.api.v1.router import router as v1_router
from src.setup.ioc import create_container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    container = app.state.dishka_container
    logger = await container.get(logging.Logger)

    vector_store = await container.get(VectorStoreInterface)
    embedder = await container.get(EmbedderInterface)
    try:
        await vector_store.ensure_collection(embedder.vector_size())
    except Exception:
        logger.exception("Не удалось подготовить коллекцию векторного хранилища")

    yield

    await container.close()


def create_app() -> FastAPI:
    settings = Settings()
    setup_logging(settings)

    app = FastAPI(
        title="Feminism RAG API",
        description=(
            "Бэкенд ИИ-ассистента по феминизму и его истории: "
            "ingestion из Google Drive, гибридный поиск, генерация с цитатами."
        ),
        lifespan=lifespan,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.api_settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_error_handlers(app)
    container = create_container(settings)
    setup_dishka(container, app)

    app.include_router(v1_router, prefix="/rag/v1")
    app.include_router(healthcheck_router, prefix="/rag/health")

    Instrumentator().instrument(app).expose(app, endpoint="/rag/metrics")
    mount_frontend(app, settings)

    return app


def mount_frontend(app: FastAPI, settings: Settings) -> None:
    frontend_dir = Path(settings.api_settings.frontend_dir)
    if not frontend_dir.is_dir():
        return

    app.mount(
        "/ui",
        StaticFiles(directory=frontend_dir, html=True),
        name="frontend",
    )


app = create_app()
