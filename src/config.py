from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    gemini_api_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_timeout: int = 10
    collection_name: str = "campus_connect"
    corpus_path: Path = Path("./corpus/campus-connect")
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    api_key: str = "dev-key-change-me"
    rate_limit: str = "20/minute"
    # Gemini generation models. The first is preferred; the rest are fallbacks
    # used only when the preferred model is rate-limited or unavailable.
    gemini_model: str = "gemini-3.6-flash"
    gemini_fallback_models: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    # CORS: comma-separated origins allowed to call the API from a browser.
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    # MCP Streamable HTTP: hosts permitted by DNS-rebinding protection.
    mcp_allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    # Langfuse observability (leave empty to disable)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    # GitHub webhook (HMAC-SHA256 secret for push event validation)
    github_webhook_secret: str = ""
    log_level: str = "INFO"

    @property
    def generation_models(self) -> list[str]:
        """Preferred model followed by its fallbacks, without duplicates."""
        ordered = [self.gemini_model, *self.gemini_fallback_models]
        seen: set[str] = set()
        return [m for m in ordered if m and not (m in seen or seen.add(m))]

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key) and self.gemini_api_key != "your_gemini_api_key_here"


settings = Settings()
