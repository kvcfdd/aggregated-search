# config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # API配置
    GOOGLE_API_KEY: str = "default_google_key"
    SERPAPI_API_KEYS: str = "default_serpapi_key"

    # 反向代理配置
    GEMINI_REVERSE_PROXY: str | None = None
    DDG_REVERSE_PROXY: str | None = None
    BING_REVERSE_PROXY: str | None = None
    BAIDU_REVERSE_PROXY: str | None = None
    PIXIV_REVERSE_PROXY: str | None = None
    PIXIV_IMG_REVERSE_PROXY: str | None = None
    YANDEX_REVERSE_PROXY: str | None = None
    DIMTOWN_REVERSE_PROXY: str | None = None
    ACG66_REVERSE_PROXY: str | None = None

    # 搜索行为配置
    DOMAIN_BLACKLIST: str = ""
    TITLE_BLACKLIST: str = ""
    PER_PROVIDER_FETCH_TEXT: int = Field(15, ge=1, le=100)
    PER_PROVIDER_FETCH_IMAGE: int = Field(50, ge=1, le=200)

settings = Settings()