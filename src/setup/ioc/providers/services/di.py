import logging
from collections.abc import AsyncIterable

import httpx
from dishka import Provider, Scope, provide
from openai import AsyncOpenAI

from src.application.dialog import DialogService
from src.application.interfaces.db.cache import CacheInterface
from src.application.interfaces.db.chat_db import ChatDBInterface
from src.application.interfaces.db.parent_db import ParentChunkDBInterface
from src.application.interfaces.services.corpus_source import CorpusSourceInterface
from src.application.interfaces.services.decider import (
    AnswerJudgeInterface,
    QueryRouterInterface,
    RerankerInterface,
)
from src.application.interfaces.services.embedder import EmbedderInterface
from src.application.interfaces.services.llm import LlmInterface
from src.application.interfaces.services.parser import DocumentParserInterface
from src.application.interfaces.services.vector_store import VectorStoreInterface
from src.application.retrieval.pipeline import RetrievalPipeline
from src.config import Settings
from src.domain.services.chunking import ChunkingService
from src.domain.services.tokenization import Bm25Encoder
from src.infrastructure.openrouter.embedder import OpenRouterEmbedder
from src.infrastructure.openrouter.llm import OpenRouterLlm
from src.infrastructure.parsers.registry import DocumentParserRegistry
from src.infrastructure.sources.google_drive import GoogleDriveSource
from src.infrastructure.sources.local_folder import LocalFolderSource
from src.infrastructure.typesafe.jev import JevDecider


class ServiceProvider(Provider):
    scope = Scope.APP

    @provide
    async def http_client(self, settings: Settings) -> AsyncIterable[httpx.AsyncClient]:
        timeout = httpx.Timeout(
            max(
                settings.drive_settings.timeout_sec,
                settings.jev_settings.timeout_sec,
            )
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            yield client

    @provide
    async def openai_client(self, settings: Settings) -> AsyncIterable[AsyncOpenAI]:
        openrouter = settings.openrouter_settings
        client = AsyncOpenAI(
            api_key=openrouter.api_key or "missing-key",
            base_url=openrouter.base_url,
            timeout=openrouter.timeout_sec,
            max_retries=openrouter.max_retries,
            default_headers={
                "HTTP-Referer": openrouter.app_url,
                "X-Title": openrouter.app_title,
            },
        )
        try:
            yield client
        finally:
            await client.close()

    @provide
    def embedder(
            self,
            client: AsyncOpenAI,
            cache: CacheInterface,
            logger: logging.Logger,
            settings: Settings,
    ) -> EmbedderInterface:
        return OpenRouterEmbedder(client, cache, logger, settings)

    @provide
    def llm(
            self,
            client: AsyncOpenAI,
            logger: logging.Logger,
            settings: Settings,
    ) -> LlmInterface:
        return OpenRouterLlm(client, logger, settings)

    @provide
    def jev(
            self,
            client: httpx.AsyncClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> JevDecider:
        return JevDecider(client, logger, settings)

    @provide
    def query_router(self, jev: JevDecider) -> QueryRouterInterface:
        return jev

    @provide
    def reranker(self, jev: JevDecider) -> RerankerInterface:
        return jev

    @provide
    def answer_judge(self, jev: JevDecider) -> AnswerJudgeInterface:
        return jev

    @provide
    def chunking(self, settings: Settings) -> ChunkingService:
        chunking_settings = settings.chunking_settings
        return ChunkingService(
            chunk_size_words=chunking_settings.chunk_size_words,
            chunk_overlap_words=chunking_settings.chunk_overlap_words,
            parent_group_size=chunking_settings.parent_group_size,
            min_chunk_words=chunking_settings.min_chunk_words,
        )

    @provide
    def bm25(self) -> Bm25Encoder:
        return Bm25Encoder()

    @provide
    def parser(
            self,
            logger: logging.Logger,
            settings: Settings,
    ) -> DocumentParserInterface:
        return DocumentParserRegistry(logger, settings)

    @provide
    def drive_source(
            self,
            client: httpx.AsyncClient,
            logger: logging.Logger,
            settings: Settings,
    ) -> GoogleDriveSource:
        return GoogleDriveSource(client, logger, settings)

    @provide
    def local_source(
            self,
            logger: logging.Logger,
            settings: Settings,
    ) -> LocalFolderSource:
        return LocalFolderSource(logger, settings)

    @provide
    def corpus_sources(
            self,
            drive: GoogleDriveSource,
            local: LocalFolderSource,
            logger: logging.Logger,
    ) -> list[CorpusSourceInterface]:
        sources: list[CorpusSourceInterface] = [drive, local]
        available = [source.origin() for source in sources if source.available()]
        if len(available) > 1:
            logger.warning(
                "Активны оба источника %s: один и тот же файл попадёт в индекс дважды. "
                "Обычно локальную папку выключают через RAG_LOCAL_ENABLED=false",
                available,
            )
        return sources

    @provide
    def dialog(
            self,
            llm: LlmInterface,
            chat_db: ChatDBInterface,
            logger: logging.Logger,
            settings: Settings,
    ) -> DialogService:
        return DialogService(llm, chat_db, logger, settings)

    @provide
    def retrieval_pipeline(
            self,
            embedder: EmbedderInterface,
            vector_store: VectorStoreInterface,
            parent_db: ParentChunkDBInterface,
            query_router: QueryRouterInterface,
            reranker: RerankerInterface,
            answer_judge: AnswerJudgeInterface,
            bm25: Bm25Encoder,
            logger: logging.Logger,
            settings: Settings,
    ) -> RetrievalPipeline:
        return RetrievalPipeline(
            embedder=embedder,
            vector_store=vector_store,
            parent_db=parent_db,
            query_router=query_router,
            reranker=reranker,
            answer_judge=answer_judge,
            bm25=bm25,
            logger=logger,
            settings=settings,
        )
