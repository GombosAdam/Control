from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://invoice_user:invoice_pass_2024@localhost:5432/invoice_manager"
    DATABASE_URL_SYNC: str = "postgresql://invoice_user:invoice_pass_2024@localhost:5432/invoice_manager"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"

    # JWT
    JWT_SECRET: str = "invoice-manager-jwt-secret-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480

    # Ollama (Unity server)
    OLLAMA_URL: str = "http://192.168.0.120:11434"
    LLM_MODEL: str = "qwen3:14b"
    LLM_TEMPERATURE: float = 0.0
    VLM_MODEL: str = "qwen2.5vl:7b"

    # Text-to-SQL pipeline
    SQL_MODEL: str = "qwen3:14b"
    ANSWER_MODEL: str = "qwen3:14b"
    SQL_MAX_RETRIES: int = 3

    # RAG & Vector Store
    QDRANT_COLLECTION: str = "text2sql_examples"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # AI Enrichment thresholds
    PARTNER_MATCH_THRESHOLD: float = 0.85
    DUPLICATE_THRESHOLD: float = 0.92
    RAG_MIN_SCORE: float = 0.7
    RAG_DEDUP_THRESHOLD: float = 0.95

    # Agent
    ANTHROPIC_API_KEY: str = ""
    AGENT_MODEL: str = "claude-sonnet-4-20250514"
    FINANCE_SERVICE_URL: str = "http://finance-service:8003"
    INVOICE_PIPELINE_URL: str = "http://invoice-pipeline:8002"
    AGENT_MAX_TOOL_CALLS: int = 10
    PULSE_CACHE_TTL: int = 300  # 5 perc

    # App
    APP_NAME: str = "Financial Planning and Controls"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://192.168.0.120:3000"
    UPLOAD_DIR: str = "./data/pdfs"
    INBOX_DIR: str = "./data/inbox"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
