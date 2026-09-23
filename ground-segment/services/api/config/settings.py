"""Django settings for the Etana ground-segment archive and API.

The database is configured from environment variables so the same code targets
Dockerized Postgres in normal operation and SQLite in tests, with no code change.
Set ETANA_DB=sqlite for a local file database (used by the test suite); otherwise
Postgres connection details are read from the environment.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

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

# Default OFF. Fail-open here (defaulting DEBUG on) would mean a deploy that
# forgets to set ETANA_DEBUG silently serves stack traces and settings in
# error pages. Local dev opts in explicitly via ETANA_DEBUG=1 in .env.
DEBUG = os.environ.get("ETANA_DEBUG", "0") == "1"

if not DEBUG and SECRET_KEY == "dev-insecure-key-change-in-production":
    raise ImproperlyConfigured(
        "ETANA_SECRET_KEY must be set to a real secret when ETANA_DEBUG is "
        "off (production). Refusing to start with the public default key."
    )

ALLOWED_HOSTS = os.environ.get("ETANA_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "telemetry",
]

# Origins allowed to make cross-origin requests to the API (the deployed
# dashboard's origin). Comma-separated, e.g. "https://dashboard.example.com".
# Empty by default: local dev doesn't need this, since Vite proxies /api to
# this server itself (see ground-segment/frontend/vite.config.ts), so the
# browser never makes a cross-origin request in the first place.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ETANA_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# CompressedManifestStaticFilesStorage requires collectstatic to have run (it
# reads staticfiles.json for cache-busted filenames), which local `runserver`
# dev flows don't do. Use it only when DEBUG is off, i.e. in production.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MIDDLEWARE = [
    # Must precede CommonMiddleware/WhiteNoiseMiddleware: corsheaders needs to
    # add its headers to responses those middlewares can generate directly.
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
