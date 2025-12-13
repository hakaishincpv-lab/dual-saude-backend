from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dual Saúde"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",          # permite usar variáveis de ambiente
        env_file_encoding="utf-8"
    )


settings = Settings()
