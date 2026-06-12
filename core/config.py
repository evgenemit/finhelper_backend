import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BACK_DB_HOST: str
    BACK_DB_PORT: int
    BACK_DB_USER: str
    BACK_DB_PASS: str
    BACK_DB_NAME: str

    SECRET_KEY: str
    DEEPSEEK_KEY: str

    REDIS_HOST: str

    @property
    def database_url(self) -> str:
        return (
            f'postgresql+asyncpg://{self.BACK_DB_USER}:{self.BACK_DB_PASS}'
            f'@{self.BACK_DB_HOST}:{self.BACK_DB_PORT}/{self.BACK_DB_NAME}'
        )

    class Config:
        env_file = ".env" if os.path.exists(".env") else None
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
