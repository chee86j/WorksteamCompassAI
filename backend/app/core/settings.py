from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration derived from environment variables."""

    app_name: str = Field(default='WorkStream Compass AI')
    environment: str = Field(default='local')
    api_version: str = Field(default='0.1.0')

    openai_api_key: str | None = Field(default=None, env='OPENAI_API_KEY')
    openai_chat_model: str = Field(default='gpt-4.1-mini')
    openai_embed_model: str = Field(default='text-embedding-3-large')

    qdrant_url: str = Field(default='http://localhost:6333')
    qdrant_api_key: str | None = Field(default=None)
    qdrant_collection: str = Field(default='helpdesk_chunks')

    redis_url: str = Field(default='redis://localhost:6379/0')

    notes_dir: str = Field(default='../notes')
    allowed_exts: str = Field(default='.pdf,.docx,.xlsx,.csv,.md,.txt,.log')

    chunk_size: int = Field(default=700)
    chunk_overlap: int = Field(default=80)

    cache_rewrite_ttl_sec: int = Field(default=86400)
    cache_retrieval_ttl_sec: int = Field(default=3600)
    cache_compress_ttl_sec: int = Field(default=1800)
    cache_answer_ttl_sec: int = Field(default=900)

    class Config:
        env_file = 'backend/.env'
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance for dependency injection."""
    return Settings()
