from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseSettings):
    host: str
    port: int
    username: str
    password: str
    name: str
    server_selection_timeout_ms: int = 5000

    model_config = SettingsConfigDict(env_prefix="RAG_MONGO_")

    @property
    def connection_string(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="mongodb",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
        )


class RedisSettings(BaseSettings):
    host: str
    port: int
    db: int
    password: str
    cache_ttl_sec: int = 3600
    embedding_ttl_sec: int = 604800

    model_config = SettingsConfigDict(env_prefix="RAG_REDIS_")


class QdrantSettings(BaseSettings):
    url: str = ""
    api_key: str = ""
    path: str = "./qdrant_storage"
    collection: str = "feminism_chunks"
    timeout_sec: float = 30.0
    upsert_batch_size: int = 128

    model_config = SettingsConfigDict(env_prefix="RAG_QDRANT_")


class OpenRouterSettings(BaseSettings):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    app_title: str = "Feminism RAG"
    app_url: str = "https://github.com/feminism-rag"
    timeout_sec: float = 90.0
    max_retries: int = 3

    model_config = SettingsConfigDict(env_prefix="RAG_OPENROUTER_")


class LlmSettings(BaseSettings):
    model: str = "openai/gpt-6-luna"
    temperature: float = 0.2
    max_tokens: int = 1200
    condense_max_tokens: int = 160
    history_messages: int = 6

    model_config = SettingsConfigDict(env_prefix="RAG_LLM_")


class EmbeddingSettings(BaseSettings):
    model: str = "openai/text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 64
    query_prefix: str = ""
    document_prefix: str = ""

    model_config = SettingsConfigDict(env_prefix="RAG_EMBEDDING_")


class JevSettings(BaseSettings):
    enabled: bool = True
    base_url: str = ""
    api_key: str = ""
    model: str = "typesafe/jev-1.13"
    timeout_sec: float = 20.0
    route_queries: bool = True
    rerank: bool = True
    answerability_gate: bool = True
    check_groundedness: bool = False
    rerank_candidates: int = 20
    rerank_chars_per_candidate: int = 700
    rerank_weight: float = 0.7
    relevant_threshold: float = 0.45
    answerable_threshold: float = 0.5
    in_domain_threshold: float = 0.35
    grounded_threshold: float = 0.5

    model_config = SettingsConfigDict(env_prefix="RAG_JEV_")


class ChunkingSettings(BaseSettings):
    chunk_size_words: int = 220
    chunk_overlap_words: int = 45
    parent_group_size: int = 3
    min_chunk_words: int = 12
    max_table_pages: int = 20

    model_config = SettingsConfigDict(env_prefix="RAG_CHUNKING_")


class RetrievalSettings(BaseSettings):
    top_k: int = 5
    candidates_dense: int = 30
    candidates_sparse: int = 30
    rrf_k: int = 60
    dense_weight: float = 1.0
    sparse_weight: float = 0.7
    dense_score_threshold: float = 0.30
    hybrid: bool = True
    expand_to_parents: bool = True
    max_context_chars: int = 14000
    mmr_lambda: float = 0.7
    use_mmr: bool = True

    model_config = SettingsConfigDict(env_prefix="RAG_RETRIEVAL_")


class GoogleDriveSettings(BaseSettings):
    enabled: bool = True
    folder_id: str = ""
    service_account_file: str = ""
    service_account_json: str = ""
    api_key: str = ""
    timeout_sec: float = 120.0
    page_size: int = 200

    model_config = SettingsConfigDict(env_prefix="RAG_DRIVE_")


class LocalCorpusSettings(BaseSettings):
    enabled: bool = True
    path: str = "./documents"

    model_config = SettingsConfigDict(env_prefix="RAG_LOCAL_")


class ApiSettings(BaseSettings):
    admin_key: str = ""
    cors_origins: str = "*"
    max_question_chars: int = 2000
    frontend_dir: str = "./frontend"

    model_config = SettingsConfigDict(env_prefix="RAG_API_")


class LoggingSettings(BaseSettings):
    level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="RAG_LOGGING_")


class Settings(BaseSettings):
    mongo_settings: MongoSettings = MongoSettings()
    redis_settings: RedisSettings = RedisSettings()
    qdrant_settings: QdrantSettings = QdrantSettings()
    openrouter_settings: OpenRouterSettings = OpenRouterSettings()
    llm_settings: LlmSettings = LlmSettings()
    embedding_settings: EmbeddingSettings = EmbeddingSettings()
    jev_settings: JevSettings = JevSettings()
    chunking_settings: ChunkingSettings = ChunkingSettings()
    retrieval_settings: RetrievalSettings = RetrievalSettings()
    drive_settings: GoogleDriveSettings = GoogleDriveSettings()
    local_corpus_settings: LocalCorpusSettings = LocalCorpusSettings()
    api_settings: ApiSettings = ApiSettings()
    logging_settings: LoggingSettings = LoggingSettings()
