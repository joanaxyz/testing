# ruff: noqa: F403, F405, I001

import os

os.environ.setdefault("DJANGO_DEBUG", "True")

from .settings import *  # noqa: F403

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
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
