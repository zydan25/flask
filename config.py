import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


def _database_uri() -> str:
    """Return a stable database URL independent of the process working directory."""
    configured = os.getenv('DATABASE_URL', '').strip()
    if not configured:
        db_path = BASE_DIR / 'instance' / 'runtime.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"

    if configured.startswith('sqlite:///') and not configured.startswith('sqlite:////'):
        raw_path = configured[len('sqlite:///'):]
        path = Path(raw_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"

    return configured


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv('SESSION_DAYS', '7')))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(32 * 1024 * 1024)))
    DEFAULT_APP_SLUG = os.getenv('DEFAULT_APP_SLUG', 'flutter-app')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@local')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change-me')
    ALLOWED_API_HOSTS = [x.strip().lower() for x in os.getenv('ALLOWED_API_HOSTS', '').split(',') if x.strip()]
    RUNTIME_SCHEMA_VERSION = int(os.getenv('RUNTIME_SCHEMA_VERSION', '1'))
