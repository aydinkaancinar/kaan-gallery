# Local backend in Docker

The backend now runs in Docker with Gunicorn at http://127.0.0.1:8000.
It connects to Neon main and private R2. Docker Desktop must be running; the
host Python virtual environment is not needed to start this container.
The Next.js frontend still runs separately and uses the same backend address.

From the repository root:

```bash
docker compose up -d --build backend   # build and start after code changes
docker compose ps                     # check health
docker compose logs -f backend        # watch logs; Ctrl-C exits log viewing
docker compose stop backend           # stop without deleting configuration
docker compose down                   # remove container and Compose network
```

The image has no source bind mount or development auto-reload. Rebuild with
`docker compose up -d --build backend` after editing backend code. Stopping or
removing this container does not delete the external Neon database or R2 images.
`restart: unless-stopped` permits restart when Docker restarts unless you stopped
it explicitly.

## Local HTTP versus production HTTPS

Compose explicitly selects `config.settings_container_local`. It retains
production dependency validation, DEBUG=False, Gunicorn, PostgreSQL/R2 and
WhiteNoise, but disables HTTPS redirect, secure-only cookies and HSTS for local
HTTP. It trusts no forwarded scheme headers. The published port is bound only
to host loopback (`127.0.0.1:8000`). Do not expose this configuration publicly.
The image still defaults to strict `config.settings_production` when deployed
without these Compose overrides.

The private, Git-ignored `.env.docker` contains a dedicated local Django secret,
allowed hosts and existing database/storage credentials. It has mode 600 and
is passed at runtime, never copied into the image. Compose uses raw env-file
parsing to avoid expanding dollar signs in credential values (Compose 2.30+
required). No control, analytics, Resend or database administration key is added.
Avoid commands that expand and print the fully resolved Compose environment.

The local Django secret differs from the prior development server, so sign in
again at http://127.0.0.1:8000/admin/ using your password and MFA. A human login
confirmation is still needed; automated checks confirmed the login form and
HTTP-compatible CSRF cookie, not password/MFA submission.

## Switching back to the virtual environment

Stop Docker first, then start the alternative backend; both cannot bind 8000:

```bash
docker compose stop backend
./.venv/bin/python scripts/run_backend.py
```

This also uses Neon and R2; it is not a database rollback. SQLite remains an old
snapshot. Continue using only one active backend configuration for admin edits.

## Verified

The Compose container is healthy and non-root. Its selected database is
PostgreSQL and selected file storage is the private quota gateway. Health,
artwork API, login form and admin CSS return 200 over local HTTP; R2
card/detail/share bytes match retained local files. All 167 backend tests pass,
including a check that local HTTP settings do not weaken production settings.
No Render service or live website was changed.
