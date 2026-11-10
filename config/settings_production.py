"""Production configuration: required environment only, never local secret files."""
import os
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .settings_base import *  # noqa: F403


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} is required in production.')
    return value


def csv_setting(name):
    return [part.strip() for part in required(name).split(',') if part.strip()]


DEBUG = False
SECRET_KEY = required('DJANGO_SECRET_KEY')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-') or SECRET_KEY == 'local-practice-only-do-not-use-in-production':
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be a strong production secret.')
ALLOWED_HOSTS = csv_setting('DJANGO_ALLOWED_HOSTS')
if not ALLOWED_HOSTS or any('*' in host or '/' in host or ':' in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must contain explicit hostnames without ports.')
CSRF_TRUSTED_ORIGINS = csv_setting('DJANGO_CSRF_TRUSTED_ORIGINS')
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('At least one CSRF trusted origin is required.')
for origin in CSRF_TRUSTED_ORIGINS:
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or '*' in origin or parsed.path or parsed.query or parsed.fragment:
        raise ImproperlyConfigured('CSRF origins must be explicit HTTPS origins without trailing slashes.')
try:
    _database = dj_database_url.parse(required('DATABASE_URL'), conn_max_age=0, conn_health_checks=True)
except (ValueError, TypeError):
    raise ImproperlyConfigured('DATABASE_URL must be a valid PostgreSQL URL.') from None
if _database['ENGINE'] != 'django.db.backends.postgresql' or _database.get('OPTIONS', {}).get('sslmode') not in ('require', 'verify-ca', 'verify-full'):
    raise ImproperlyConfigured('Production requires PostgreSQL with TLS.')
_database['DISABLE_SERVER_SIDE_CURSORS'] = True
DATABASES = {'default': _database}
_gateway_url = required('ARTWORK_GATEWAY_URL')
_gateway_token = required('ARTWORK_GATEWAY_TOKEN')
from items.storage_gateway import QuotaGatewayStorage
QuotaGatewayStorage(_gateway_url, _gateway_token)  # Validate before accepting traffic.
STORAGES = {
    'default': {'BACKEND': 'items.storage_gateway.QuotaGatewayStorage',
                'OPTIONS': {'base_url': _gateway_url, 'token': _gateway_token}},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MIDDLEWARE = [MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *MIDDLEWARE[1:]]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = True
# Render terminates TLS. Enable only after verifying the ingress sanitizes this header.
if os.environ.get('DJANGO_TRUST_PROXY_HEADERS') == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = 'DENY'
# Render probes the process over HTTP; this route returns no application data.
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
