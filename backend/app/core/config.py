from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARESES_")

    database_url: str = "sqlite+aiosqlite:///./data/areses.db"
    local_mode: bool = True
    base_url: str = "http://localhost:8000"
    secret_key: str | None = None
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        dev_defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
        extra = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return dev_defaults + extra


settings = Settings()
