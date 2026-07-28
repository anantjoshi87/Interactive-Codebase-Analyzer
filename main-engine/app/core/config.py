import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Application configuration loaded from .env
    """

    # AI APIs
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_LLM_MODEL = os.getenv("LLM_MODEL", "mistral-large-latest")
    MISTRAL_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mistral-embed")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # Web Search
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # Database
    REDIS_URL = os.getenv("REDIS_URL")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    NEON_URL = os.getenv("NEON_URL")


settings = Settings()