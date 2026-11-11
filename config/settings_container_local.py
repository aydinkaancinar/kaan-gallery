"""Local Docker over loopback HTTP; never use for public hosting.

Keep production dependency validation, Gunicorn, DEBUG=False and static storage.
Only browser HTTPS settings are relaxed for a container published on 127.0.0.1.
"""
from .settings_production import *  # noqa: F403

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_PROXY_SSL_HEADER = None
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']
