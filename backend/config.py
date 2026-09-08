import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Base configuration with shared enterprise defaults."""

    SECRET_KEY = os.getenv("SECRET_KEY", "assignment-portal-insecure-dev-secret-key-999")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/assignment_portal_db")
    # Handle Heroku/Render postgres:// vs postgresql:// dialect prefix
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # Redis Cache Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_DEFAULT_TIMEOUT = int(os.getenv("REDIS_DEFAULT_TIMEOUT", "300"))  # 5 minutes

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.getenv("PERMANENT_SESSION_LIFETIME", "86400"))
    )

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Application Settings
    APP_NAME = "Assignment Group Portal"
    ITEMS_PER_PAGE = 10
    ALLOWED_GROUP_SIZES = [1, 2, 3, 4, 5]


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = False


class TestingConfig(BaseConfig):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    REDIS_URL = "redis://localhost:6379/1"


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
