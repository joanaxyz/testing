import os
from datetime import timedelta
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_database_url(url: str) -> str:
    """Django expects postgresql://, not JDBC-style jdbc:postgresql:// URLs."""
    if url.startswith("jdbc:"):
        return url.removeprefix("jdbc:")
    return url


def _clean_env_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _deployment_version(explicit_version: str, render_commit: str) -> str:
    """Prefer an explicit release ID, then Render's runtime commit SHA."""
    return explicit_version.strip() or render_commit.strip() or "development"


env = environ.Env(
    # Safer default. Your local .env should explicitly set DJANGO_DEBUG=True.
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOW_CREDENTIALS=(bool, True),
    PERFORMANCE_TIMING_ENABLED=(bool, False),
    ALLOW_DESTRUCTIVE_SEED_RESET=(bool, False),
    DJANGO_TRUST_PROXY_HEADERS=(bool, False),
    DJANGO_TRUSTED_PROXY_IPS=(list, []),
    AUTH_LOGIN_MAX_ATTEMPTS=(int, 5),
    AUTH_LOGIN_LOCKOUT_SECONDS=(int, 300),
    EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(bool, True),
    DEFAULT_FROM_EMAIL=(str, "GIT it! <no-reply@example.com>"),
    PASSWORD_RESET_TIMEOUT=(int, 3600),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 15),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    JWT_COOKIE_NAME=(str, "git_it_refresh"),
    JWT_COOKIE_PATH=(str, "/api/auth/"),
    JWT_COOKIE_DOMAIN=(str, ""),
    JWT_COOKIE_SAMESITE=(str, "Strict"),
    JWT_COOKIE_SECURE=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
    SECURE_CONTENT_TYPE_NOSNIFF=(bool, True),
    SECURE_REFERRER_POLICY=(str, "same-origin"),
    API_VERSION=(str, "0.1.0"),
    AI_CHAT_ENABLED=(bool, False),
    GROQ_API_KEY=(str, ""),
    GROQ_MODEL=(str, "openai/gpt-oss-20b"),
    GROQ_TIMEOUT_SECONDS=(float, 12.0),
    AI_CHAT_MAX_OUTPUT_TOKENS=(int, 700),
)

_os_database_url_before_read_env = os.environ.get("DATABASE_URL")
env.read_env(BASE_DIR / ".env")
# A system-level JDBC URL (common when copied from desktop DB tools) overrides
# backend/.env and often points at the wrong pooler/port. Prefer project .env.
if (_os_database_url_before_read_env or "").startswith("jdbc:"):
    env.read_env(BASE_DIR / ".env", overwrite=True)

DEBUG = env("DJANGO_DEBUG")

DEV_SECRET_KEY = "dev-local-change-before-production"

if DEBUG:
    SECRET_KEY = env("DJANGO_SECRET_KEY", default=DEV_SECRET_KEY)
else:
    SECRET_KEY = env("DJANGO_SECRET_KEY", default="").strip()

    if not SECRET_KEY or SECRET_KEY == DEV_SECRET_KEY:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set to a unique secret when DJANGO_DEBUG=False."
        )

PERFORMANCE_TIMING_ENABLED = env("PERFORMANCE_TIMING_ENABLED", default=DEBUG)

ALLOWED_HOSTS = _clean_env_list(env("DJANGO_ALLOWED_HOSTS"))

if DEBUG:
    # Allow development access through LAN addresses and custom hostnames.
    ALLOWED_HOSTS = ["*"]

if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be explicit when DJANGO_DEBUG=False.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "players",
    "authoring",
    "shop",
    "curriculum",
    "adventures.apps.AdventuresConfig",
    "challenges",
    "practice",
    "simulator",
    "evaluation",
    "progress",
    "common",
    "adminconsole",
    "ai_support.apps.AISupportConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.RequestContextMiddleware",
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

_database_url = _normalize_database_url(
    env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
)
DATABASES = {
    "default": env.db_url_config(_database_url),
}
_IS_SQLITE = "sqlite3" in DATABASES["default"].get("ENGINE", "")
_SQLITE_TIMEOUT_SECONDS = env.float("SQLITE_TIMEOUT_SECONDS", default=20.0)
# Persist DB connections for 60s by default so each command submit doesn't pay a
# fresh connect/handshake (notably costly against a remote Postgres pooler).
# SQLite is file-locked and much happier in local dev with request-scoped
# connections; Postgres keeps the previous persistent-connection default.
# Override explicitly with DATABASE_CONN_MAX_AGE when you need different behavior.
DATABASES["default"]["CONN_MAX_AGE"] = env.int(
    "DATABASE_CONN_MAX_AGE", default=0 if _IS_SQLITE else 60
)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env.bool(
    "DATABASE_CONN_HEALTH_CHECKS", default=not _IS_SQLITE
)
_DATABASE_SSLMODE = env("DATABASE_SSLMODE", default="").strip().lower()
if _DATABASE_SSLMODE:
    valid_sslmodes = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
    if _DATABASE_SSLMODE not in valid_sslmodes:
        raise RuntimeError(
            "DATABASE_SSLMODE must be disable, allow, prefer, require, verify-ca, or verify-full."
        )
    if _IS_SQLITE:
        raise RuntimeError("DATABASE_SSLMODE cannot be used with SQLite.")
    DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = _DATABASE_SSLMODE
if _IS_SQLITE:
    from django.db.backends.signals import connection_created

    DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = _SQLITE_TIMEOUT_SECONDS

    def _enable_sqlite_wal(sender, connection, **kwargs):
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute(f"PRAGMA busy_timeout={int(_SQLITE_TIMEOUT_SECONDS * 1000)};")
                cursor.execute("PRAGMA journal_mode=WAL;")

    connection_created.connect(_enable_sqlite_wal, dispatch_uid="git_it.sqlite_wal")
if "postgresql" in DATABASES["default"].get("ENGINE", ""):
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env.bool(
        "DATABASE_DISABLE_SERVER_SIDE_CURSORS",
        default=True,
    )
    if env.bool("DATABASE_DISABLE_PREPARED_STATEMENTS", default=True):
        DATABASES["default"].setdefault("OPTIONS", {})["prepare_threshold"] = None
    DATABASES["default"].setdefault("OPTIONS", {})["options"] = (
        # idle_in_transaction_session_timeout reclaims a connection whose
        # transaction was left open (crash/disconnect) so it stops pinning row
        # locks. lock_timeout makes a statement that cannot acquire a row lock
        # fail in seconds instead of blocking until the far longer server-side
        # statement_timeout - one contended command-submit row otherwise wedged
        # a request for ~2 minutes before erroring out.
        "-c idle_in_transaction_session_timeout=5000 "
        f"-c lock_timeout={env.int('DATABASE_LOCK_TIMEOUT_MS', default=10000)} "
        f"-c statement_timeout={env.int('DATABASE_STATEMENT_TIMEOUT_MS', default=30000)}"
    )

REDIS_URL = env("REDIS_URL", default="").strip()
# Refresh-token revocation is stored in the configured Django cache. The
# process-local fallback is useful for development, but production needs a
# shared cache so logout and rotated-token revocation apply across workers.
if not DEBUG and not REDIS_URL:
    raise RuntimeError("REDIS_URL is required in production for shared token revocation cache.")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": env.float("REDIS_SOCKET_CONNECT_TIMEOUT", default=0.5),
                "SOCKET_TIMEOUT": env.float("REDIS_SOCKET_TIMEOUT", default=0.5),
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "git-it-dev-cache",
        }
    }

# JSON console logging with request correlation IDs. Container platforms can
# ship stdout directly to their log collector without parsing human text.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {"()": "common.logging.RequestContextFilter"},
    },
    "formatters": {
        "json": {"()": "common.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.db.backends": {"level": "WARNING"},
        "git_it.performance": {"level": "INFO"},
        "git_it.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = _clean_env_list(env("DJANGO_CORS_ALLOWED_ORIGINS"))

if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

CORS_ALLOW_CREDENTIALS = env("CORS_ALLOW_CREDENTIALS")
CORS_ALLOW_HEADERS = (*default_headers, "x-git-it-client")

CSRF_TRUSTED_ORIGINS = _clean_env_list(env("DJANGO_CSRF_TRUSTED_ORIGINS")) or CORS_ALLOWED_ORIGINS

SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", default=env("JWT_COOKIE_SECURE"))
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE", default=env("JWT_COOKIE_SECURE"))
SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")
SECURE_CONTENT_TYPE_NOSNIFF = env("SECURE_CONTENT_TYPE_NOSNIFF")
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY")

DJANGO_TRUST_PROXY_HEADERS = env("DJANGO_TRUST_PROXY_HEADERS")
DJANGO_TRUSTED_PROXY_IPS = _clean_env_list(env("DJANGO_TRUSTED_PROXY_IPS"))
if DJANGO_TRUST_PROXY_HEADERS:
    if not DJANGO_TRUSTED_PROXY_IPS:
        raise RuntimeError(
            "DJANGO_TRUSTED_PROXY_IPS must be explicit when proxy headers are trusted."
        )
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

ALLOW_DESTRUCTIVE_SEED_RESET = env("ALLOW_DESTRUCTIVE_SEED_RESET")
DEPLOYMENT_VERSION = _deployment_version(
    env("DEPLOYMENT_VERSION", default=""),
    env("RENDER_GIT_COMMIT", default=""),
)

if not DEBUG and SECURE_HSTS_SECONDS <= 0:
    raise RuntimeError("SECURE_HSTS_SECONDS must be set when DJANGO_DEBUG=False.")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("accounts.authentication.VersionedJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "common.api.api_exception_handler",
    # ScopedRateThrottle only limits views that declare a `throttle_scope`.
    # Anonymous scopes (register/refresh) key on client IP - classrooms share a
    # NAT IP, so those rates carry headroom for ~30 students behind one address.
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": env("THROTTLE_AUTH_REGISTER", default="60/hour"),
        "auth_refresh": env("THROTTLE_AUTH_REFRESH", default="600/hour"),
        "auth_password_reset": env("THROTTLE_AUTH_PASSWORD_RESET", default="20/hour"),
        "auth_password_reset_confirm": env(
            "THROTTLE_AUTH_PASSWORD_RESET_CONFIRM", default="60/hour"
        ),
        "command_submit": env("THROTTLE_COMMAND_SUBMIT", default="120/min"),
        "ai_chat": env("THROTTLE_AI_CHAT", default="5/min"),
    },
}

AI_CHAT_ENABLED = env("AI_CHAT_ENABLED")
GROQ_API_KEY = env("GROQ_API_KEY").strip()
GROQ_MODEL = env("GROQ_MODEL").strip()
GROQ_TIMEOUT_SECONDS = env("GROQ_TIMEOUT_SECONDS")
AI_CHAT_MAX_OUTPUT_TOKENS = env("AI_CHAT_MAX_OUTPUT_TOKENS")

if GROQ_TIMEOUT_SECONDS <= 0:
    raise RuntimeError("GROQ_TIMEOUT_SECONDS must be greater than 0.")
if AI_CHAT_MAX_OUTPUT_TOKENS <= 0:
    raise RuntimeError("AI_CHAT_MAX_OUTPUT_TOKENS must be greater than 0.")
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")
JWT_REFRESH_TOKEN_LIFETIME_DAYS = env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")

if JWT_ACCESS_TOKEN_LIFETIME_MINUTES <= 0:
    raise RuntimeError("JWT_ACCESS_TOKEN_LIFETIME_MINUTES must be greater than 0.")

if JWT_REFRESH_TOKEN_LIFETIME_DAYS <= 0:
    raise RuntimeError("JWT_REFRESH_TOKEN_LIFETIME_DAYS must be greater than 0.")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=JWT_REFRESH_TOKEN_LIFETIME_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

GIT_IT_REFRESH_COOKIE = env("JWT_COOKIE_NAME")
GIT_IT_REFRESH_COOKIE_SECURE = env("JWT_COOKIE_SECURE")
GIT_IT_REFRESH_COOKIE_PATH = env("JWT_COOKIE_PATH").strip() or "/api/auth/"
GIT_IT_REFRESH_COOKIE_DOMAIN = env("JWT_COOKIE_DOMAIN", default="").strip() or None
GIT_IT_REFRESH_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE").strip().capitalize()

if GIT_IT_REFRESH_COOKIE_SAMESITE not in {"Strict", "Lax", "None"}:
    raise RuntimeError("JWT_COOKIE_SAMESITE must be Strict, Lax, or None.")

if GIT_IT_REFRESH_COOKIE_SAMESITE == "None" and not GIT_IT_REFRESH_COOKIE_SECURE:
    raise RuntimeError("JWT_COOKIE_SAMESITE=None requires JWT_COOKIE_SECURE=True.")

if not DEBUG and not GIT_IT_REFRESH_COOKIE_SECURE:
    raise RuntimeError("JWT_COOKIE_SECURE must be True when DJANGO_DEBUG=False.")

SPECTACULAR_SETTINGS = {
    "TITLE": "GIT it! API",
    "DESCRIPTION": "Student-facing Git scenario level API.",
    "VERSION": env("API_VERSION"),
}

EMAIL_BACKEND = env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
PASSWORD_RESET_TIMEOUT = env("PASSWORD_RESET_TIMEOUT")

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173").rstrip("/")

if not DEBUG:
    if not FRONTEND_BASE_URL.startswith("https://"):
        raise RuntimeError("FRONTEND_BASE_URL must be an HTTPS origin when DJANGO_DEBUG=False.")
