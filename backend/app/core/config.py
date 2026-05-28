from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Enterprise LLM Wiki"
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    ALLOW_ORIGINS: str = "*"

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_SCHEMA: str = "public"

    OLLAMA_BASE_URL: str = "https://ollama.com"
    OLLAMA_API_KEY: str = ""
    OLLAMA_CHAT_MODEL: str = "gpt-oss:20b-cloud"
    FACT_EXTRACTION_MODEL: str = "gpt-oss:20b-cloud"
    WIKI_GENERATION_MODEL: str = "gpt-oss:20b-cloud"
    QA_GENERATION_MODEL: str = "gpt-oss:20b-cloud"
    OLLAMA_NUM_CTX: int = 32768
    OLLAMA_TIMEOUT: int = 180

    OLLAMA_EMBED_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_EMBED_API_KEY: str = ""
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768

    DEFAULT_COMPANY_CODE: str = "LOCKTON"
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    CANONICAL_THRESHOLD: float = 0.90
    ANSWER_CACHE_THRESHOLD: float = 0.96
    SIMILARITY_THRESHOLD: float = 0.35

    TEMPERATURE: float = 0
    TOP_P: float = 0.1
    TOP_K: int = 1
    SEED: int = 42

    ENABLE_CANONICAL_QA: bool = True
    ENABLE_ANSWER_CACHE: bool = True
    ENABLE_WIKI_SEARCH: bool = True
    ENABLE_CHUNK_SEARCH: bool = True
    ENABLE_RERANKER: bool = False
    ENABLE_QUERY_REWRITE: bool = False
    ENABLE_GROUNDING: bool = True
    ENABLE_RELATIONSHIP_SEARCH: bool = False
    ENABLE_METADATA_SEARCH: bool = True

    ENABLE_SCHEDULER: bool = True
    DAILY_CRAWL_CRON_HOUR: int = 2
    DAILY_CRAWL_CRON_MINUTE: int = 0
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
