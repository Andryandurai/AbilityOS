"""
Django settings for the AbilityOS backend.

AbilityOS — An Operating System for Human Abilities.
See docs/ARCHITECTURE.md for the system design this configuration supports.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me-for-any-real-deployment"
)

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # AbilityOS apps
    "users",
    "abilities",
    "tasks",
    "environments",
    "barriers",
    "adaptations",
    "ai_engine",
    "feedback",
    "analytics",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
#
# AbilityOS is designed for PostgreSQL (see docs/DATABASE.md). For a fast
# hackathon setup without a local Postgres server, DATABASE_URL can be left
# unset and the project falls back to SQLite automatically.
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

# ---------------------------------------------------------------------------
# REST Framework / Auth
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    # The hackathon demo intentionally allows unauthenticated access to the
    # AbilityOS reasoning endpoints so judges can drive the kiosk demo
    # without a login flow. Real deployments would tighten this per-view.
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "api.exceptions.abilityos_exception_handler",
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3434,http://127.0.0.1:3434"
    ).split(",")
    if o.strip()
]
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)

# ---------------------------------------------------------------------------
# AbilityOS AI configuration
#
# The AI Decision Engine is provider-agnostic. When no key is configured (or
# the provider call fails) the system deliberately falls back to the
# deterministic Adaptation Engine scoring formula rather than breaking the
# demo. See docs/AI_DECISION_ENGINE.md.
# ---------------------------------------------------------------------------
AI_PROVIDER = os.environ.get("AI_PROVIDER", "none").strip().lower()
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
AI_AVAILABLE = bool(AI_PROVIDER not in ("", "none") and AI_API_KEY)

# Computer-vision / OCR environment analysis (optional, P1). Guarded at the
# import site in ai_engine.services.vision_service so a missing OpenCV/OCR
# install never breaks the JSON-fixture demo path.
VISION_ENABLED = env_bool("VISION_ENABLED", False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "ai_engine": {"handlers": ["console"], "level": "INFO"},
        "barriers": {"handlers": ["console"], "level": "INFO"},
        "adaptations": {"handlers": ["console"], "level": "INFO"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
