from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./storage/threatgraph.db"
    redis_url: str = "redis://localhost:6379/0"
    model_dir: Path = Path("models")
    storage_dir: Path = Path("storage")
    privacy_mode: bool = True
    enable_external_reputation: bool = False
    urlhaus_auth_key: str = ""
    phishtank_api_key: str = ""
    max_upload_mb: int = 250
    retention_hours: int = 24
    max_depth: int = 3
    max_nodes: int = 40
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"
    task_always_eager: bool = False
    demo_data: bool = False
    clamav_host: str = ""
    auth_required: bool = False
    secure_cookies: bool = False
    enable_browser_inspection: bool = False
    browser_channel: str = 'msedge'


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
