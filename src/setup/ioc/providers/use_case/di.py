from dishka import Provider, Scope, provide, provide_all

from src.application.use_case.chat.ask_question import AskQuestionUseCase
from src.application.use_case.chat.create_session import CreateSessionUseCase
from src.application.use_case.chat.delete_session import DeleteSessionUseCase
from src.application.use_case.chat.get_session import GetSessionUseCase
from src.application.use_case.chat.list_sessions import ListSessionsUseCase
from src.application.use_case.chat.stream_answer import StreamAnswerUseCase
from src.application.use_case.documents.corpus_stats import CorpusStatsUseCase
from src.application.use_case.documents.delete_document import DeleteDocumentUseCase
from src.application.use_case.documents.get_document import GetDocumentUseCase
from src.application.use_case.documents.list_documents import ListDocumentsUseCase
from src.application.use_case.evaluation.get_evaluation import GetEvaluationUseCase
from src.application.use_case.evaluation.list_evaluations import ListEvaluationsUseCase
from src.application.use_case.evaluation.run_evaluation import RunEvaluationUseCase
from src.application.use_case.ingest.get_ingest_run import GetIngestRunUseCase
from src.application.use_case.ingest.list_ingest_runs import ListIngestRunsUseCase
from src.application.use_case.ingest.sync_corpus import SyncCorpusUseCase
from src.application.use_case.search.search_chunks import SearchChunksUseCase
from src.application.use_case.well_known.healthcheck import HealthCheckUseCase


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    interactors = provide_all(
        AskQuestionUseCase,
        StreamAnswerUseCase,
        CreateSessionUseCase,
        GetSessionUseCase,
        ListSessionsUseCase,
        DeleteSessionUseCase,
        SearchChunksUseCase,
        ListDocumentsUseCase,
        GetDocumentUseCase,
        DeleteDocumentUseCase,
        CorpusStatsUseCase,
        GetIngestRunUseCase,
        ListIngestRunsUseCase,
        RunEvaluationUseCase,
        GetEvaluationUseCase,
        ListEvaluationsUseCase,
        HealthCheckUseCase,
    )

    sync_corpus = provide(SyncCorpusUseCase, scope=Scope.APP)
