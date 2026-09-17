"""
Django settings for the AbilityOS backend.

AbilityOS — An Operating System for Human Abilities.
See docs/ARCHITECTURE.md for the system design this configuration supports.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# `manage.py test` runs the whole suite in one process against Django's
# default in-memory cache — unlike the database, that cache is NOT reset
# between TestCase classes, so a real per-IP request throttle (see
# REST_FRAMEWORK below) accumulates across the entire run and can trip
# itself on nothing but normal test volume, not a real abuse pattern. Only
# the throttle *rate* is relaxed for a test run; the mechanism itself
# still runs unmodified (a dedicated test can still assert it fires with
# `@override_settings`), and production is entirely unaffected since this
# is never true outside `manage.py test`.
TESTING = "test" in sys.argv


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
    "rest_framework_simplejwt.token_blacklist",
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
    # Phase 2 (Onboarding, Consent & Questionnaire): a front door onto the
    # existing AbilityProfile, not a second profile system -- see
    # docs/QUESTIONNAIRE.md.
    "questionnaire",
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
    # Phase 8 section 28: lightweight, IP-based rate limiting on the few
    # endpoints worth protecting (auth, session creation, the AI-adjacent
    # recommend call). ScopedRateThrottle only throttles a view that opts
    # in via `throttle_scope` (see api/views.py, users/views.py) — every
    # other endpoint is unaffected by adding this globally.
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": (
        {
            "auth_login": "10000/min",
            "auth_register": "10000/min",
            "session_start": "10000/min",
            "adaptation_recommend": "10000/min",
        }
        if TESTING
        else {
            "auth_login": "10/min",
            # Phase 1 (Real User Authentication): same scoped-throttle
            # pattern as auth_login -- registration is exactly as worth
            # protecting from abuse as login is.
            "auth_register": "10/min",
            "session_start": "30/min",
            "adaptation_recommend": "30/min",
        }
    ),
}

# ---------------------------------------------------------------------------
# Phase 1 (Real User Authentication): explicit SimpleJWT configuration.
#
# Previously absent -- the library's own defaults (5 min access / 1 day
# refresh, no rotation, no blacklist) were silently in effect. Made explicit
# here, with values chosen for a hackathon demo (a judge or a person running
# through onboarding should not be logged out mid-session) rather than a
# generic production-security template:
#
# - ACCESS_TOKEN_LIFETIME: 1 day. Long enough that a full demo/judging
#   session never silently expires mid-flow -- Phase 1 deliberately does not
#   implement a silent-refresh-on-401 interceptor (see docs/AUTHENTICATION.md
#   "Known limitations"), so a short-lived access token would just mean the
#   user gets logged out while using the app, which is worse for this
#   project's actual use case than the small extra exposure window.
# - REFRESH_TOKEN_LIFETIME: 7 days, so "stay logged in" across normal
#   day-to-day demo/dev use without re-entering credentials constantly.
# - ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION: a refresh token is
#   single-use and the old one is blacklisted the moment it's rotated --
#   this only has an effect because token_blacklist is now installed
#   (above); it also means POST /api/auth/logout/ has a real blacklist
#   table to write the current refresh token into.
# - AUTH_HEADER_TYPES: kept at the library default ("Bearer",) -- this is
#   what frontend/src/services/api.js sends and is the conventional value,
#   not something worth deviating from.
# - UPDATE_LAST_LOGIN: True, since Django's User model already has a
#   last_login field doing nothing today; cheap and meaningful once /me
#   exists.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
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

# Phase 8 audit: "api" logs (api/services/orchestrator.py, api/exceptions.py)
# but wasn't listed here, so its .info()/.exception() calls were silently
# dropped at the root logger's WARNING threshold. "barriers" was listed but
# nothing in that app actually logs — left out below rather than kept as
# dead configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "api": {"handlers": ["console"], "level": "INFO"},
        "ai_engine": {"handlers": ["console"], "level": "INFO"},
        "adaptations": {"handlers": ["console"], "level": "INFO"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
