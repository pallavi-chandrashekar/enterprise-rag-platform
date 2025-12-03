import os

from pydantic import BaseSettings, Field


def _default_db_url() -> str:
    # Use env if provided; fall back to a local dev password placeholder.
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    return os.getenv("DATABASE_URL", f"postgresql+psycopg://rag_user:{password}@db:5432/rag_db")


class Settings(BaseSettings):
    app_name: str = "Enterprise RAG Platform"
    environment: str = "local"
    database_url: str = Field(default_factory=_default_db_url)
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_dimension: int = 384
    normalize_embeddings: bool = True
    llm_provider: str = "stub"
    llm_model: str = "stub-v1"
    llm_api_key: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()
