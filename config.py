# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    GOOGLE_API_KEY: str = "default_google_key"
    SERPAPI_API_KEYS: str = "default_serpapi_key"
    GEMINI_REVERSE_PROXY: str | None = None
    DDG_REVERSE_PROXY: str | None = None
    BING_REVERSE_PROXY: str | None = None

settings = Settings()