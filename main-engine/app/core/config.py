from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from .env"""

    # Database
    DATABASE_URL: str | None = None

    # Neo4j
    NEO4J_URI: str | None = None
    NEO4J_USERNAME: str | None = None
    NEO4J_PASSWORD: str | None = None

    # AI APIs
    MISTRAL_API_KEY: str | None = None
    MISTRAL_LLM_MODEL: str = "mistral-small-latest"
    MISTRAL_EMBEDDING_MODEL: str = "mistral-embed"

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Web Search
    TAVILY_API_KEY: str | None = None

    # Embeddings / Reranking
    JINA_API_KEY: str | None = None

    # Other Services
    REDIS_URL: str | None = None
    PINECONE_API_KEY: str | None = None
    NEON_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
