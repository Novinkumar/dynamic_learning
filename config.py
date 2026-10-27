import os


DEMO_ACCOUNT_EMAIL = "demo@example.com"
UNSAFE_SECRET_KEYS = {
    "dev-change-this-secret", "replace-with-a-long-random-value", "test-only-secret",
    "secret", "changeme", "change-me", "your-secret-key", "replace-me",
}


def _env_int(name, default, minimum, maximum):
    """Read a bounded integer setting without making startup brittle."""
    try:
        return max(minimum, min(maximum, int(os.environ.get(name, default))))
    except (TypeError, ValueError):
        return default


class Config:
    """Runtime defaults that keep a fresh local checkout easy to run.

    The fallback secret is intentionally retained for the documented local
    demo. Deployments must provide their own long, random ``SECRET_KEY`` and
    must not rely on the seeded demo account or its published password.
    """

    # Keep the zero-configuration development flow, but make the deployment
    # requirement explicit for anyone copying this file into production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-this-secret")
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    DEMO_ACCOUNT_ENABLED = APP_ENV != "production" and os.environ.get("ENABLE_DEMO_ACCOUNT", "1") == "1"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dynamic_learning.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = 3600
    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = APP_ENV == "production" or os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # Optional live AI quiz generation. The application remains fully usable
    # without a key: it falls back to a local, validated question generator.
    # Any OpenAI-compatible Chat Completions endpoint can be configured.
    AI_API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    AI_API_BASE = os.environ.get("AI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
    AI_TIMEOUT = _env_int("AI_TIMEOUT", 25, 5, 90)
    AI_QUIZ_DEFAULT_LENGTH = _env_int("AI_QUIZ_DEFAULT_LENGTH", 10, 5, 20)
    AI_QUIZ_MAX_LENGTH = max(AI_QUIZ_DEFAULT_LENGTH, _env_int("AI_QUIZ_MAX_LENGTH", 20, 8, 20))


class TestingConfig(Config):
    TESTING = True
    APP_ENV = "testing"
    SECRET_KEY = "test-only-secret"
    DEMO_ACCOUNT_ENABLED = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Tests never contact a live provider unless they explicitly opt in.
    AI_API_KEY = ""
    AI_QUIZ_DEFAULT_LENGTH = 10
    AI_QUIZ_MAX_LENGTH = 20
