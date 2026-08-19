import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


def _database_uri() -> str:
    configured = os.getenv('DATABASE_URL', '').strip()
    if not configured:
        return f"sqlite:///{(BASE_DIR / 'instance' / 'runtime.db').as_posix()}"

    # Flask-SQLAlchemy resolves relative SQLite paths against the Flask
    # instance directory. Normalize relative sqlite URLs to an absolute
    # filesystem path so `sqlite:///instance/runtime.db` does not become
    # `<project>/instance/instance/runtime.db`.
    if configured.startswith('sqlite:///') and not configured.startswith('sqlite:////'):
        relative = configured[len('sqlite:///'):]
        if relative and not os.path.isabs(relative):
            absolute = (BASE_DIR / relative).resolve()
            absolute.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:////{absolute.as_posix().lstrip('/')}"

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
