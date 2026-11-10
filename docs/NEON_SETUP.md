# Neon PostgreSQL setup

Project **kaan-gallery** (`shiny-smoke-23111194`) was created in organization
`org-square-moon-41477749`, in AWS US East (N. Virginia), on November 10, 2026.

[Open the Neon project](https://console.neon.tech/app/projects/shiny-smoke-23111194/).

## Connection configuration

Neon's CLI wrote the pooled `DATABASE_URL` and direct `DATABASE_URL_UNPOOLED`
into root `.env.local`. That file is Git-ignored and restricted to the local
user (mode 600). `.neon` contains the project link and is also ignored. Never
paste either connection string into chat, documentation, frontend configuration
or Git. Neon agent tooling was installed through the official Codex plugin;
restart Codex to load its tools.

Django's normal `config.settings` still uses the existing SQLite database.
The separate [PostgreSQL settings](../config/settings_postgres.py) read
`.env.local` without replacing environment values supplied by hosting.
They require a PostgreSQL URL with TLS, disable server-side cursors for
transaction pooling, and avoid persistent Django connections.

```bash
./.venv/bin/python manage.py check --settings=config.settings_postgres
./.venv/bin/python manage.py migrate --settings=config.settings_postgres
```

These settings inherit local DEBUG and security defaults. **They are not
production settings.** A future production module will require the database,
Django secret key, allowed hosts, HTTPS protections and R2 settings explicitly.
Render will receive database credentials as private environment settings rather
than relying on a file in the repository. Use the direct connection for
administrative tools that require session-level behavior.

## Verified and still pending

- A live Django connection and client TLS were verified.
- All existing Django schema migrations were applied to the new database.
- Artwork, users, MFA, admin history and Axes records were imported and verified
  against a private SQLite snapshot. Sessions were intentionally not copied.
- The local server now uses Neon and private R2, started with
  `./.venv/bin/python scripts/run_backend.py`. Plain `manage.py runserver`
  still selects SQLite. No Render service was created or deployed.
- All 160 backend tests now pass on `dev-postgres-tests` using a temporary
  PostgreSQL test database; all 160 also pass on SQLite. Image response cleanup
  in the tests was corrected to avoid closing the active test transaction.

The isolated PostgreSQL tests and record transfer are complete. See
[transfer details](DATABASE_TRANSFER.md). The running server was switched after rechecking SQLite and Neon against the
verified snapshot. Future admin edits on that server now go to PostgreSQL.
SQLite is a retained snapshot and will no longer stay synchronized. Production
settings and Docker remain pending.
