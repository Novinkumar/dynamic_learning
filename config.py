import os


DEMO_ACCOUNT_EMAIL = "demo@example.com"
UNSAFE_SECRET_KEYS = {
    "dev-change-this-secret", "replace-with-a-long-random-value", "test-only-secret",
    "secret", "changeme", "change-me", "your-secret-key", "replace-me",
}


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


class TestingConfig(Config):
    TESTING = True
    APP_ENV = "testing"
    SECRET_KEY = "test-only-secret"
    DEMO_ACCOUNT_ENABLED = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
