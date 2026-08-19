"""Django settings for the Etana ground-segment archive and API.

The database is configured from environment variables so the same code targets
Dockerized Postgres in normal operation and SQLite in tests, with no code change.
Set ETANA_DB=sqlite for a local file database (used by the test suite); otherwise
Postgres connection details are read from the environment.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load ground-segment/.env so Django reads the same credentials Docker Compose
# does. Docker Compose loads .env automatically; Django does not, so without this
# the two would drift apart. Values already set in the real environment win over
# the .env file, and a missing python-dotenv or .env file is not fatal.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parent.parent / ".env", override=False)
except ImportError:
    pass

SECRET_KEY = os.environ.get("ETANA_SECRET_KEY", "dev-insecure-key-change-in-production")
DEBUG = os.environ.get("ETANA_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ETANA_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "telemetry",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if os.environ.get("ETANA_DB", "postgres") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("ETANA_SQLITE_PATH", BASE_DIR / "etana.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "etana"),
            "USER": os.environ.get("POSTGRES_USER", "etana"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "etana"),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

USE_TZ = True
TIME_ZONE = "UTC"
