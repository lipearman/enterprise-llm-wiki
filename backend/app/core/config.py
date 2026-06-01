from functools import lru_cache
from typing import Tuple, Type
from pydantic_settings import (
    BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource,
    DotEnvSettingsSource, EnvSettingsSource,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @classmethod
    def settings_customise_sources(cls, settings_cls: Type[BaseSettings], **kwargs) -> Tuple[PydanticBaseSettingsSource, ...]:
        # .env file takes precedence over container environment variables
        # so that updating .env is enough to change feature flags without
        # recreating the container.
        init    = kwargs.get("init_settings")
        dotenv  = kwargs.get("dotenv_settings")
        env     = kwargs.get("env_settings")
        secrets = kwargs.get("file_secret_settings") or kwargs.get("secrets_settings")
        return tuple(s for s in [init, dotenv, env, secrets] if s is not None)

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
    # ── Chat answer generation backend ───────────────────────────────────────
    # ANSWER_LLM_USE_LOCAL=false → cloud OLLAMA_CHAT_MODEL via chat_llm
    #   (fast ~5-11s, good quality; gpt-oss:20b-cloud occasionally answers the
    #    wrong fact for formally-phrased questions, and is subject to cloud
    #    rate limits).
    # ANSWER_LLM_USE_LOCAL=true → ANSWER_LLM_MODEL via local_llm (llm-server)
    #   (follows question-type rules more reliably, no rate limits, but slower
    #    on the local GPU — qwen2.5:7b ~25-35s, 14b ~80s per answer).
    # Ingestion models (FACT/WIKI/QA below) always use the cloud.
    ANSWER_LLM_USE_LOCAL: bool = False
    ANSWER_LLM_MODEL: str = "qwen2.5:14b-instruct"
    FACT_EXTRACTION_MODEL: str = "gpt-oss:20b-cloud"
    WIKI_GENERATION_MODEL: str = "gpt-oss:20b-cloud"
    QA_GENERATION_MODEL: str = "gpt-oss:20b-cloud"
    OLLAMA_NUM_CTX: int = 32768
    OLLAMA_TIMEOUT: int = 180

    OLLAMA_EMBED_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_EMBED_API_KEY: str = ""
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768

    # =========================================
    # LOCAL LLM SERVER (for canonical QA, extraction, etc.)
    # =========================================
    LOCAL_LLM_BASE_URL: str = "http://llm-server:11434"
    CANONICAL_QA_MODEL: str = "qwen2.5:7b-instruct"
    CANONICAL_QA_MAX_CANDIDATES: int = 40   # max Q&As passed to LLM per request

    DEFAULT_COMPANY_CODE: str = "LOCKTON"
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 8    # raised from 5 → 8 so contact-page results survive reranking
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
    ENABLE_RERANKER: bool = True
    # LLM-based reranker — uses the answer_llm provider chain (Gemini) to reorder
    # candidates by relevance. Handles Thai well (unlike the English ms-marco
    # FlashRank model). Adds ~1 LLM call/query. Takes precedence over ENABLE_RERANKER.
    ENABLE_LLM_RERANK: bool = False
    LLM_RERANK_CANDIDATES: int = 20   # how many top-similarity chunks to send to the LLM
    ENABLE_QUERY_REWRITE: bool = False
    ENABLE_GROUNDING: bool = True
    ENABLE_RELATIONSHIP_SEARCH: bool = False
    GRAPHRAG_MAX_HOPS: int = 1     # Phase 5.2: BFS depth for graph traversal (1 = direct neighbours only)
    ENABLE_METADATA_SEARCH: bool = True

    # ── Phase 5: Agentic RAG ─────────────────────────────────────────────────
    # Iterative retrieve → answer → validate loop. When the answer is judged
    # insufficient, reformulate the retrieval query from the critic's feedback
    # and try again (up to AGENTIC_MAX_ITERS). Off by default — adds 1-2 LLM
    # calls per retry (latency cost), so A/B via eval before enabling.
    ENABLE_AGENTIC_ANSWER: bool = False
    AGENTIC_MAX_ITERS: int = 2
    # Query planner — when agentic is on, classify each query (simple vs complex)
    # and route simple factual lookups to fast single-pass, reserving the costly
    # agentic loop for complex/multi-part questions. Lightweight alternative to a
    # LangGraph planner that fits the existing async service architecture.
    ENABLE_QUERY_PLANNER: bool = False
    # Tool-calling agent (Phase 6) — the LLM picks retrieval tools (search KB /
    # lookup FAQ) via function-calling instead of a fixed pipeline. Takes
    # precedence over the agentic loop. Falls back to single-pass on any error.
    ENABLE_TOOL_CALLING: bool = False
    TOOL_CALLING_MAX_STEPS: int = 3
    # LangGraph agentic graph (Phase 6.3) — streams intermediate steps (searching/
    # validating/answering) to the chat UI. Used only on the streaming path.
    ENABLE_LANGGRAPH: bool = False

    # =========================================
    # CRAWLER
    # =========================================
    CRAWLER_BACKEND: str = "trafilatura"   # trafilatura | playwright | crawl4ai

    # =========================================
    # AUTH
    # =========================================
    API_KEY: str = ""                   # empty = auth disabled
    API_KEY_ENABLED: bool = True        # set False to bypass auth entirely

    ENABLE_SCHEDULER: bool = True
    DAILY_CRAWL_CRON_HOUR: int = 2
    DAILY_CRAWL_CRON_MINUTE: int = 0
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
