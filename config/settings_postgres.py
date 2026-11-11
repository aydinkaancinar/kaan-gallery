"""Opt-in Neon database settings for development and migration verification.

This inherits local DEBUG/security settings; production settings are still needed.
Run with --settings=config.settings_postgres. The default local app stays on SQLite.
"""
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .settings import *  # noqa: F403

# Never replace credentials supplied by the hosting environment.
load_dotenv(BASE_DIR / ".env.local", override=False)  # noqa: F405
_database_url = os.environ.get("DATABASE_URL")
if not _database_url:
    raise ImproperlyConfigured("DATABASE_URL is required for PostgreSQL settings.")
try:
    _database = dj_database_url.parse(_database_url, conn_max_age=0, conn_health_checks=True)
except (ValueError, TypeError):
    raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL connection URL.") from None
if _database["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("PostgreSQL settings require a PostgreSQL connection URL.")
if _database.get("OPTIONS", {}).get("sslmode") not in ("require", "verify-ca", "verify-full"):
    raise ImproperlyConfigured("DATABASE_URL must require TLS (sslmode=require or stricter).")
# Neon transaction pooling cannot keep a server-side cursor on one connection.
_database["DISABLE_SERVER_SIDE_CURSORS"] = True
DATABASES = {"default": _database}
