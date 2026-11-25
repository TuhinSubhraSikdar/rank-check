import secrets

from .base import *  # noqa: F403

DEBUG = True
# A temporary key makes first-run local setup safe; set a persistent .env key for sessions.
SECRET_KEY = SECRET_KEY or secrets.token_urlsafe(50)  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
