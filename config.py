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
    PER_PROVIDER_FETCH: int = 15
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    CONTENT_DEDUPE_THRESHOLD: float = 0.75

settings = Settings()

# 对关键配置做兜底校验/限制，避免误配导致异常行为
try:
    if settings.PER_PROVIDER_FETCH is None:
        settings.PER_PROVIDER_FETCH = 15
    settings.PER_PROVIDER_FETCH = max(1, min(int(settings.PER_PROVIDER_FETCH), 100))
except Exception:
    settings.PER_PROVIDER_FETCH = 15

try:
    settings.BM25_K1 = float(settings.BM25_K1)
except Exception:
    settings.BM25_K1 = 1.5

try:
    settings.BM25_B = float(settings.BM25_B)
    settings.BM25_B = max(0.0, min(settings.BM25_B, 1.0))
except Exception:
    settings.BM25_B = 0.75

try:
    settings.CONTENT_DEDUPE_THRESHOLD = float(settings.CONTENT_DEDUPE_THRESHOLD)
    settings.CONTENT_DEDUPE_THRESHOLD = max(0.0, min(settings.CONTENT_DEDUPE_THRESHOLD, 1.0))
except Exception:
    settings.CONTENT_DEDUPE_THRESHOLD = 0.75