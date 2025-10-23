# config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # 配置
    GOOGLE_API_KEY: str = "default_google_key"
    SERPAPI_API_KEYS: str = "default_serpapi_key"
    GEMINI_REVERSE_PROXY: str | None = None
    DDG_REVERSE_PROXY: str | None = None
    BING_REVERSE_PROXY: str | None = None
    BAIDU_REVERSE_PROXY: str | None = None
    PIXIV_REVERSE_PROXY: str | None = None
    PIXIV_IMG_REVERSE_PROXY: str | None = None
    YANDEX_REVERSE_PROXY: str | None = None
    DOMAIN_BLACKLIST: str = "smartapps.baidu.com"
    PER_PROVIDER_FETCH_TEXT: int = Field(15, ge=1, le=100)
    PER_PROVIDER_FETCH_IMAGE: int = Field(50, ge=1, le=200)
    BM25_K1: float = 1.5
    BM25_B: float = Field(0.75, ge=0.0, le=1.0)
    CONTENT_DEDUPE_THRESHOLD: float = Field(0.75, ge=0.0, le=1.0)
    TITLE_PENALTY_KEYWORDS: str = ""
    TITLE_PENALTY_VALUE: float = 2.0
settings = Settings()
