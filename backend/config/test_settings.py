# ruff: noqa: F403, F405, I001

import os

os.environ.setdefault("DJANGO_DEBUG", "True")

from .settings import *  # noqa: F403


DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = False

# Tests run the real committed migration graph. CI separately proves a clean
# database can migrate from zero and that models have no uncommitted changes.

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "git-it-test-cache",
    }
}

# Throttle counters live in the shared locmem cache and user/IP keys repeat
# across tests, so real rates would trip mid-suite. Throttle tests override
# these locally.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "10000/hour",
        "auth_refresh": "10000/hour",
        "auth_password_reset": "10000/hour",
        "auth_password_reset_confirm": "10000/hour",
        "command_submit": "10000/min",
        "ai_chat": "10000/min",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
