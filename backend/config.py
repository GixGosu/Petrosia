from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://petrosia:petrosia123@db:5432/petrosia"
    DATABASE_URL_SYNC: str = "postgresql://petrosia:petrosia123@db:5432/petrosia"

    # LLM Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = "http://localhost:11434"

    # Default LLM Provider
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_LLM_MODEL: str = "qwen2.5:3b"

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384

    # RAG Settings
    MAX_CONTEXT_ARTICLES: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    RAG_SIMILARITY_THRESHOLD: float = 0.3

    # Auth
    REQUIRE_API_KEY: bool = False

    # Rate Limiting
    RATE_LIMIT_READS: str = "60/minute"
    RATE_LIMIT_WRITES: str = "10/minute"

    # Server
    CORS_ORIGINS: list = ["http://localhost:8000", "http://localhost:3000"]
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
