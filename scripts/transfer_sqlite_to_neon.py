#!/usr/bin/env python3
"""Copy a private SQLite snapshot into an empty Neon database; verify before commit."""
import argparse
from datetime import datetime, date, time
from collections import Counter
from io import StringIO
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--env-file', required=True, type=Path)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    from dotenv import dotenv_values
    env = dotenv_values(args.env_file)
    if env.get('NEON_BRANCH') != args.branch:
        raise SystemExit('Environment file does not select the expected branch.')
    url = env.get('DATABASE_URL_UNPOOLED')
    if not url:
        raise SystemExit('A direct database connection is required.')
    snapshot = args.snapshot.resolve()
    if not snapshot.is_file() or snapshot.stat().st_mode & 0o077:
        raise SystemExit('Snapshot must exist and have private permissions (600).')
    os.environ['DATABASE_URL'] = url
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_postgres'
    import django
    django.setup()
    from django.apps import apps
    from django.core import serializers
    from django.core.serializers.json import DjangoJSONEncoder
    from django.core.management import call_command
    from django.db import connections, transaction
    from django.db.migrations.executor import MigrationExecutor
    connections.databases['snapshot'] = {
        'ENGINE': 'django.db.backends.sqlite3', 'NAME': f'file:{snapshot}?mode=ro',
        'OPTIONS': {'uri': True}, 'AUTOCOMMIT': True, 'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'TIME_ZONE': None,
        'TEST': {'NAME': None},
    }
    # Generated permissions/content types already exist from migrate. Sessions
    # deliberately stay local; login on the destination requires MFA again.
    excluded = {'contenttypes.contenttype', 'auth.permission', 'sessions.session'}
    models = serializers.sort_dependencies([
        (app, [m for m in app.get_models() if m._meta.label_lower not in excluded])
        for app in apps.get_app_configs()
    ])

    class FullPrecisionEncoder(DjangoJSONEncoder):
        def default(self, value):
            if isinstance(value, (datetime, date, time)):
                return value.isoformat()
            return super().default(value)

    def rows(alias):
        objects = (obj for model in models for obj in model._default_manager.using(alias).order_by('pk'))
        # Django's JSON encoder trims datetime microseconds to milliseconds.
        # Use the Python serializer and preserve full precision for migration.
        data = serializers.serialize('python', objects, use_natural_foreign_keys=True)
        return json.loads(json.dumps(data, cls=FullPrecisionEncoder))

    def canonical(data):
        # Relation membership is unordered; PostgreSQL may return M2M rows in
        # a different order from SQLite even when the relationships are equal.
        normalized = json.loads(json.dumps(data))
        for row in normalized:
            model = apps.get_model(row['model'])
            for field in model._meta.many_to_many:
                if field.name in row['fields']:
                    row['fields'][field.name].sort(key=lambda value: json.dumps(value, sort_keys=True))
        return json.dumps(normalized, sort_keys=True, separators=(',', ':'))

    connection = connections['default']
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        if not connection.connection.pgconn.ssl_in_use:
            raise SystemExit('TLS is required.')
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise SystemExit('Apply schema migrations before importing.')
    source = rows('snapshot')
    current = rows('default')
    counts = Counter(row['model'] for row in source)
    print('Snapshot record counts:', json.dumps(dict(counts), sort_keys=True))
    if canonical(source) == canonical(current):
        print('Destination already matches the snapshot; nothing changed.')
        return
    if any(row['model'] != 'tasks.category' for row in current):
        raise SystemExit('Destination contains application data; refusing to overwrite it.')
    source_categories = {row['pk']: row['fields']['slug'] for row in source if row['model'] == 'tasks.category'}
    if any(source_categories.get(row['pk']) != row['fields']['slug'] for row in current):
        raise SystemExit('Seed category identities differ; review mapping before import.')
    if not args.apply:
        print('Preflight passed. No records written. Add --apply to import.')
        return
    fixture = snapshot.with_suffix('.fixture.json')
    fd = os.open(fixture, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as file:
        json.dump(source, file)
    os.chmod(fixture, 0o600)
    # loaddata preserves PKs, resolves natural foreign keys, skips model save()
    # side effects, checks constraints and resets identity sequences.
    with transaction.atomic():
        call_command('loaddata', str(fixture), verbosity=0, stdout=StringIO())
        destination = rows('default')
        if canonical(destination) != canonical(source):
            actual = {(row['model'], row['pk']): row for row in destination}
            for row in source:
                other = actual.get((row['model'], row['pk']))
                if other and canonical([row]) != canonical([other]):
                    fields = [key for key in row['fields'] if row['fields'][key] != other['fields'].get(key)]
                    print('Mismatch model/field names only:', row['model'], ', '.join(fields))
            raise ValueError('Verification failed; imported records were rolled back.')
    print('Import committed: every serialized field, ID and relationship matches the snapshot.')
    print('Password hashes and MFA records preserved. Sessions not copied; sign in again.')
    print('Source database, local images and R2 objects were not changed.')


if __name__ == '__main__':
    main()
