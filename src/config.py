from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    gemini_api_key:str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    collection_name: str = "campus_connect"
    corpus_path:Path = Path("./corpus/campus-connect")
    embedding_model:str = "BAAI/bge-small-en-v1.5"
    embedding_dim:int = 384
    api_key:str = "dev-key-change-me"
    rate_limit:str = "20/minute"
    # Langfuse observability (leave empty to disable)
    langfuse_public_key:str = ""
    langfuse_secret_key:str = ""
    langfuse_host:str = "https://cloud.langfuse.com"
    # GitHub webhook (HMAC-SHA256 secret for push event validation)
    github_webhook_secret:str = ""

settings = Settings()
