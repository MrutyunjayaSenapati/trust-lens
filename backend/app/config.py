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
    # Optional, local only: Gemini via Vertex AI with your gcloud login (`gcloud auth application-default login`).
    # Tried before the API key when set; its quota is your Cloud project's, not the free API key's.
    vertex_project: str = os.getenv("GEMINI_VERTEX_PROJECT", "")
    vertex_location: str = os.getenv("GEMINI_VERTEX_LOCATION", "global")
    adc_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    mock: bool = os.getenv("MOCK_MODE", "0") == "1"
    cache_path: str = os.getenv("CACHE_PATH", "./data/cache.sqlite")
    cors: list = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]


settings = Settings()
