from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int

    @property
    def DB_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    YANDEX_API_KEY: str
    YANDEX_API_KEY_ID: str
    YANDEX_API_MODEL_URI: str
    YANDEX_CLOUD_CATALOG_ID: str

    UPLOAD_DIR: Path = BASE_DIR / 'storage' / 'uploads'
    VECTOR_DB_DIR: Path = BASE_DIR / 'storage' / 'vector_db'
    
    @property
    def YANDEX_API_URL(self) -> str:
        return 'https://llm.api.cloud.yandex.net/v1'

    @property
    def YANDEX_GPT_MODEL_URI(self) -> str:
        return f'gpt://{self.YANDEX_CLOUD_CATALOG_ID}/yandexgpt/rc'

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        extra='ignore',
    )

settings = Settings()