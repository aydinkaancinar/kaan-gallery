import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]


class ProductionSettingsTests(SimpleTestCase):
    def environment(self):
        return {
            'PATH': os.environ.get('PATH', ''),
            'DJANGO_SECRET_KEY': 'production-test-secret-with-many-distinct-characters-' * 2,
            'DJANGO_ALLOWED_HOSTS': 'api.example.test',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://api.example.test',
            'DATABASE_URL': 'postgresql://user:dummy@database.example.test/gallery?sslmode=require',
            'ARTWORK_GATEWAY_URL': 'https://storage.example.test',
            'ARTWORK_GATEWAY_TOKEN': 'gateway-test-secret-' * 3,
        }

    def load(self, env, code='import config.settings_production'):
        return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                              capture_output=True, text=True)

    def test_every_runtime_dependency_is_required_without_local_file_fallback(self):
        for name in ['DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_CSRF_TRUSTED_ORIGINS',
                     'DATABASE_URL', 'ARTWORK_GATEWAY_URL', 'ARTWORK_GATEWAY_TOKEN']:
            with self.subTest(name=name):
                env = self.environment()
                env.pop(name)
                self.assertNotEqual(self.load(env).returncode, 0)

    def test_insecure_database_hosts_secrets_and_storage_are_rejected(self):
        for name, value in [
            ('DATABASE_URL', 'sqlite:///local.db'),
            ('DATABASE_URL', 'postgresql://user:dummy@db/gallery'),
            ('DJANGO_SECRET_KEY', 'short'),
            ('DJANGO_ALLOWED_HOSTS', '*'),
            ('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://api.example.test'),
            ('ARTWORK_GATEWAY_URL', 'http://storage.example.test'),
            ('ARTWORK_GATEWAY_TOKEN', 'short'),
        ]:
            with self.subTest(name=name, value=value):
                env = self.environment()
                env[name] = value
                self.assertNotEqual(self.load(env).returncode, 0)

    def test_production_enforces_https_and_does_not_implicitly_trust_proxy(self):
        result = self.load(self.environment(), '''
import json
import config.settings_production as s
print(json.dumps([s.DEBUG, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE,
                  s.SECURE_SSL_REDIRECT, getattr(s, 'SECURE_PROXY_SSL_HEADER', None),
                  s.DATABASES['default']['ENGINE'], s.STORAGES['default']['BACKEND']]))
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [False, True, True, True, None,
            'django.db.backends.postgresql', 'items.storage_gateway.QuotaGatewayStorage'])

    def test_proxy_trust_is_explicit(self):
        env = self.environment()
        env['DJANGO_TRUST_PROXY_HEADERS'] = 'true'
        result = self.load(env, 'import config.settings_production as s; print(s.SECURE_PROXY_SSL_HEADER[0])')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'HTTP_X_FORWARDED_PROTO')

    def test_local_container_allows_http_without_changing_production(self):
        result = self.load(self.environment(), '''
import json
import config.settings_container_local as local
import config.settings_production as production
print(json.dumps([local.DEBUG, local.SECURE_SSL_REDIRECT,
    local.SESSION_COOKIE_SECURE, local.CSRF_COOKIE_SECURE,
    local.SECURE_PROXY_SSL_HEADER, production.SECURE_SSL_REDIRECT,
    production.SESSION_COOKIE_SECURE, production.CSRF_COOKIE_SECURE]))
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         [False, False, False, False, None, True, True, True])


class HealthTests(SimpleTestCase):
    def test_health_is_public_and_uses_no_database(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.head('/healthz/').status_code, 200)

    def test_health_rejects_writes(self):
        self.assertEqual(self.client.post('/healthz/').status_code, 405)
