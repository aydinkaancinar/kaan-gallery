# Containerized Django deployment preparation

The backend container is implemented and verified locally. **Render has not been
created or deployed, and kaancinar.com has not been changed.** Local development now runs through [Docker Compose](LOCAL_DOCKER.md), with
loopback-only HTTP settings and the same Neon/R2 storage.

## Design

- `config/settings_base.py` holds shared configuration. Local settings may load
  private local files; `config/settings_production.py` imports the shared base
  directly and reads only runtime environment variables.
- Production startup requires a strong Django secret, explicit allowed hosts,
  HTTPS CSRF origins, PostgreSQL with TLS, and a valid private R2 gateway
  connection. Missing configuration stops startup instead of selecting SQLite
  or local image storage. No credentials are embedded in the image.
- Secure session/CSRF cookies, HTTPS redirects and a one-hour HSTS policy are
  enabled. HSTS include-subdomains and preload remain deliberately disabled
  until the complete domain setup is verified. Django flags those two choices
  as deployment warnings; no checks are silenced.
- Gunicorn runs one threaded worker (four threads), binds to `$PORT`, and sends
  logs to stdout/stderr. Adjust resources from observed load after deployment.
- WhiteNoise serves compressed, hashed admin static files. Build-time collection
  uses `config.settings_build` without runtime secrets or a database connection.
- `/healthz/` is an unauthenticated GET/HEAD liveness probe with no database or R2
  access. It is exempt from HTTPS redirection for hosting probes. It does not
  assert database/storage availability; monitor those separately.

## Image and secret boundaries

`Dockerfile` uses the Python 3.12 Debian slim image and locked dependencies,
then runs as UID 10001. The Python minor version is pinned; the base tag can
receive security updates. Pin a reviewed digest for fully reproducible builds.

`.dockerignore` uses an allowlist. The build includes backend code, templates
and dependency locks, and excludes env files, local connection files, SQLite,
backups, media, frontend and Worker files. Database migrations are not run at
image build or on every Gunicorn startup. New images reuse external Neon/R2.

See [.env.example](../.env.example) for names and placeholders. Actual production
values go into Render's private environment settings. Use a new Django secret
rather than the local development key. This invalidates existing signed sessions;
the imported password hashes and MFA records remain in PostgreSQL.

`DATABASE_URL` is pooled application traffic. Keep the direct URL as
`DATABASE_URL_UNPOOLED` for an explicit release migration command. The only R2
credential Django needs is the storage token; do not give it the control,
analytics or Resend secrets. Those remain in the Worker.

## Render setup — next, not yet performed

1. Create a Docker Web Service from the repository, in a region near Neon
   N. Virginia. Set Dockerfile path to `./Dockerfile` and leave the Docker start
   command empty so the image's Gunicorn command runs. Choose a service plan
   explicitly; the Free plan can sleep, while always-on service costs money.
2. Set the required runtime variables from `.env.example`, using Render's assigned
   backend hostname in allowed hosts and the HTTPS admin origin in CSRF origins.
   Do not use wildcards or add every frontend preview domain.
3. Verify Render's TLS/forwarded-header behavior before setting
   `DJANGO_TRUST_PROXY_HEADERS=true`. Django and Gunicorn trust the proxy only
   when this flag is enabled. Do not enable it behind an untrusted proxy or on an
   ingress where clients can control the forwarded headers reaching Django.
4. Set the health-check path to `/healthz/`. The container listens on Render's
   supplied `PORT`. Confirm the health probe reaches the process successfully.
5. Run `manage.py check --deploy --settings=config.settings_production` with runtime
   configuration. Apply future migrations as a separate release step using the
   direct database URL. Where a pre-deploy command is unavailable on the chosen
   plan, run that release operation explicitly from a secure environment. Do not
   silently add database writes to the image build.
6. Verify API access, MFA admin login, CSRF, image delivery and upload boundaries
   on the backend's temporary domain. Complete Cloudflare ingress/bot protections,
   direct-origin bypass controls, monitoring, backups and a restore test before
   treating this as a public release.
7. Set the Vercel frontend's server-side `BACKEND_ORIGIN` to the deployed backend,
   preview and verify it, then plan the kaancinar.com switch. Database and Worker
   credentials never belong in `NEXT_PUBLIC_*` variables.

No Render manifest automatically provisions a paid service. Region, plan,
domain/proxy behavior and the release migration mechanism still need selection
and live verification.

## Local verification completed

- All **167 backend tests** passed: seven production/health tests cover required
  configuration, rejection of insecure settings, explicit proxy trust, and health
  behavior without database access.
- The Docker image built successfully. A filesystem inspection confirmed UID
  10001, a collected static manifest, and no local secret/data directories.
- A temporary production container connected to existing Neon and passed health,
  HTTP-to-HTTPS redirect, artwork API, WhiteNoise admin CSS and login-page checks.
  Its CSRF cookie was Secure. No migrations or application writes were performed.
- That temporary production smoke-test container and its credential file were removed afterward.
  A separate local HTTP Compose container is now running; see the local guide.
  The image remains locally as `kaan-gallery-backend:local`.
- Dependency consistency and whitespace checks passed. Django's production check
  reported only the two deferred HSTS warnings described above.

## Commands and source

```bash
docker build -t kaan-gallery-backend:local .
# Real secrets must be placed in an ignored, private file, never in this example.
docker run --rm --env-file .env.production \
  -p 127.0.0.1:18000:8000 kaan-gallery-backend:local
```

With HTTPS enforcement enabled, plain HTTP application routes redirect. A local
HTTP health probe still works. Our smoke test explicitly simulated a trusted TLS
proxy; do not weaken production settings to make an HTTP demo appear secure.

Implementation: [Dockerfile](../Dockerfile), [production settings](../config/settings_production.py),
[build settings](../config/settings_build.py), [Gunicorn](../gunicorn.conf.py),
[health view](../config/health.py), [tests](../items/tests/test_production.py).

Official references: [Render Docker](https://render.com/docs/docker),
[Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html).
