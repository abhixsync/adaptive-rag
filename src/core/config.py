"""
Core configuration and environment settings.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    CODE_COLLECTION = os.getenv("QDRANT_CODE_COLLECTION", "codebase")
    DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "guidelines")
    USER_DOCS_COLLECTION = os.getenv("QDRANT_USER_DOCS_COLLECTION", "user_documents")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


settings = Settings()

# Set env variables for LangChain integrations
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
