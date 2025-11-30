from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Enterprise RAG Platform"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://rag_user:rag_pass@db:5432/rag_db"
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_dimension: int = 384

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()
