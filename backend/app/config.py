import os

from dotenv import load_dotenv

load_dotenv()
load_dotenv("../.env")


class Settings:
    serpapi_key: str = os.getenv("SERPAPI_API_KEY", "")
    gemini_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    # Tried in order when the primary model is overloaded (503/429) or retired (404).
    gemini_fallbacks: list = [m.strip() for m in os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.5-flash-lite,gemini-flash-latest").split(",") if m.strip()]
    mock: bool = os.getenv("MOCK_MODE", "0") == "1"
    cache_path: str = os.getenv("CACHE_PATH", "./data/cache.sqlite")
    cors: list = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]


settings = Settings()
