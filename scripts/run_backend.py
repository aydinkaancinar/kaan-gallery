#!/usr/bin/env python3
"""Start local Django using the selected Neon PostgreSQL connection.

Credentials are loaded by config.settings_postgres from the private .env.local.
This is a development server, not a production entry point.
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_postgres'

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', *sys.argv[1:]])
