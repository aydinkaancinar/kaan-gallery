# Kaan Gallery

[![Aydın Kaan Çınar — ceramics, objects, and illustrations](docs/readme-banner.png)](https://arts.kaancinar.com)

**[Visit the live portfolio → arts.kaancinar.com](https://arts.kaancinar.com)**

This is the online home for Aydın Kaan Çınar's ceramics, objects, and illustrations. It presents the artwork clearly, gives visitors a Clay Studio to explore pottery forms, and aims to run without recurring hosting charges while traffic stays within free-tier allowances. The [design decisions](docs/DESIGN_DECISIONS.md) explain the choices and their limits.

## What is here

- **Gallery:** responsive artwork pages, categories, search, date filters, pagination, image viewer, and light/dark themes.
- **Clay Studio:** shape a vessel, estimate clay weight, undo and redo changes, save a design in the browser, or share it in a URL. The weight adjustment is provisional; see the [model notes](docs/CLAY_STUDIO.md).
- **Owner-only editing:** Django admin and API write routes are intended for Aydın Kaan Çınar alone. Sign-in requires a password, authenticator-app MFA, and an active session.
- **Sharing and discovery:** artwork-specific previews and metadata, a sitemap, robots rules, and structured data.

Visitors do not create accounts, check out, or upload artwork. [Clay Studio](https://arts.kaancinar.com/clay-studio) and the [privacy policy](https://arts.kaancinar.com/privacy) are also live.

## How it works

```mermaid
flowchart LR
    Browser[Visitor browser] --> Vercel[Vercel · Next.js]
    Vercel -->|Artwork data and image requests| Render[Render · Django API]
    Owner[Site owner] -->|Admin + MFA| Render
    Render --> Neon[(Neon · PostgreSQL)]
    Render --> Gateway[Cloudflare Worker · private image gateway]
    Gateway --> R2[(Private R2 bucket)]
    Gateway --> Ledger[(Durable Object · quota ledger)]
    Gateway -.->|Quota alerts| Resend[Resend · email]
```

Next.js renders the public pages and asks Django for artwork data. Image URLs stay under the gallery domain through a Next.js rewrite, but Django checks publication and image-protection rules before reading files from the private gateway. The browser never receives R2 credentials or a direct bucket URL.

Django stores artwork records and staff sessions in Neon. The Cloudflare Worker reserves R2 usage before reads and writes, checks account usage every 15 minutes, and can stop billable access at conservative limits. Its cutoff is an application safeguard, not a Cloudflare billing guarantee. See the [gateway design](docs/R2_QUOTA_GATEWAY.html).

Gallery cards use small WebP variants, artwork pages use larger detail variants, and sharing links use 1200 × 630 previews. Clicking **View image** loads the original for unprotected work. For work with **Protect images** checked, all public copies are watermarked and the original remains staff-only. See [image behavior](frontend/README.md#image-delivery-and-search).

The current hosting plan uses Vercel Hobby for the frontend, Render Free for Django, Neon Free for PostgreSQL, and Cloudflare/Resend free allowances for image storage and quota alerts. This keeps recurring application-hosting charges at zero **only while usage and plan terms permit**. The domain has its own renewal cost; free services can sleep, stop at limits, or change terms. The [cost and tradeoff notes](docs/DESIGN_DECISIONS.md#keeping-hosting-costs-down) explain each choice.

### Where to look

| If you are changing… | Start here |
| --- | --- |
| Gallery pages, filters, navigation, viewer | [`frontend/app/`](frontend/app/), [`frontend/components/`](frontend/components/) |
| Clay Studio and its estimates | [`frontend/app/clay-studio/`](frontend/app/clay-studio/), [`frontend/lib/clay.ts`](frontend/lib/clay.ts), [model notes](docs/CLAY_STUDIO.md) |
| Metadata, sitemap, robots, privacy page | [`frontend/app/layout.tsx`](frontend/app/layout.tsx), [`frontend/app/sitemap.ts`](frontend/app/sitemap.ts), [`frontend/app/robots.ts`](frontend/app/robots.ts), [`frontend/app/privacy/page.tsx`](frontend/app/privacy/page.tsx) |
| Artwork data and admin | [`items/models.py`](items/models.py), [`items/serializers.py`](items/serializers.py), [`items/views.py`](items/views.py), [`items/admin.py`](items/admin.py) |
| Image generation and access | [`items/image_variants.py`](items/image_variants.py), [`items/validators.py`](items/validators.py), [`items/views.py`](items/views.py), [`frontend/next.config.ts`](frontend/next.config.ts) |
| Authentication and request limits | [`config/settings_base.py`](config/settings_base.py), [`config/settings_production.py`](config/settings_production.py), [`items/permissions.py`](items/permissions.py), [`items/public_read_limit.py`](items/public_read_limit.py) |
| R2 quota and alerts | [`cloudflare/r2-gateway/`](cloudflare/r2-gateway/), [`items/storage_gateway.py`](items/storage_gateway.py) |
| Builds and releases | [`Dockerfile`](Dockerfile), [GitHub workflows](.github/workflows/), [branch workflow](docs/BRANCH_WORKFLOW.md) |

The Django app lives in `items/`, but its database app label is `tasks` for migration compatibility. Use that label if an app-specific migration command needs one.

## Run it locally

For a fresh, empty gallery, use Python 3.12 and Node.js 24. The default Django settings use local SQLite; private credentials are not needed for this path.

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements-lock.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py runserver
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open [localhost:3000](http://localhost:3000). `BACKEND_ORIGIN` defaults to `http://127.0.0.1:8000`; `SITE_URL` controls canonical and sharing URLs. A fresh database has no artwork until you add it in Django admin and publish it. Admin setup begins at [the MFA login](http://127.0.0.1:8000/account/login/).

On the project workstation, [Docker Compose](docs/LOCAL_DOCKER.md) is the usual local backend: it uses a private, ignored `.env.docker` file and connects to Neon and the R2 gateway. The [Neon setup guide](docs/NEON_SETUP.md) explains the alternative virtual-environment connection. **Check which database and storage settings are active before changing real artwork.** Never commit `.env.*`, database dumps, MFA recovery codes, or original media.

## Check a change

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py makemigrations --check --dry-run
./.venv/bin/python manage.py test

cd frontend
npm test
npm run lint
npm run build
npx playwright install chromium  # first browser-test run only
npm run test:browser

cd ../cloudflare/r2-gateway
npm ci
npm test
```

Run the checks relevant to your change. Django's default test command uses an isolated SQLite test database; the [PostgreSQL testing guide](docs/POSTGRES_TESTING.html) covers an isolated Neon branch. Browser tests exercise desktop and phone journeys against a temporary backend. Gateway tests use local Cloudflare bindings, not the live bucket.

## How changes reach the site

```mermaid
flowchart TD
    Main["main · reviewed source"] -->|Create from latest main| Feature["feature/* or fix/*"]
    Feature -->|Review and merge PR| Main
    Main -->|Fast-forward for a frontend release| FrontendBranch["deploy/frontend-preview"]
    Main -->|Fast-forward for a backend release| BackendBranch["deploy/render-backend"]
    FrontendBranch --> FrontendChecks[Frontend GitHub Actions checks]
    BackendBranch --> BackendChecks[Backend GitHub Actions checks]
    FrontendChecks --> VercelDeploy[Vercel]
    BackendChecks --> RenderDeploy[Render]
```

`main` is the source of truth. The deployment branches can lag until that part of the site is ready to release. Never merge a feature directly into either deployment branch. The [branch workflow](docs/BRANCH_WORKFLOW.md) has the exact commands.

The [frontend workflow](.github/workflows/vercel-frontend.yml) runs tests and deploys Vercel when frontend files change on its deployment branch. The [backend workflow](.github/workflows/render-backend.yml) tests and builds the Docker image before asking Render to deploy its commit. A workflow accepting a deploy is not proof that the live release is healthy; check the hosting dashboard and site. Database migrations are a separate release step, using a reviewed direct Neon connection. Secrets belong in the providers' private settings, not in Git or frontend `NEXT_PUBLIC_*` variables.

## Current operating notes

- The frontend runs on Vercel Hobby at `arts.kaancinar.com`; the Docker backend runs on Render Free in Virginia and may be slow to wake after idle time. The root `kaancinar.com` website is a separate site.
- Neon holds the production PostgreSQL database. Original artwork and variants live in a private Cloudflare R2 bucket behind the Worker. The Worker uses a conservative billing hold because the exact R2 renewal hour has not been verified; review the [gateway runbook](cloudflare/r2-gateway/README.md) before the December 10 boundary.
- Vercel Bot Protection and an image-request rate rule are enabled. Direct requests to the Render origin still need a stronger ingress plan. Backups, a restore test, monitoring, and a wider real-device/browser pass remain release work.
- A [privacy policy](frontend/app/privacy/page.tsx) is live. Owner-only login does not prevent automated login attempts or provider request logging. The current review still needs a retention routine for security records and expired sessions, a live cookie/provider-settings check, and an assessment of Vercel Hobby terms and data preferences. Keep policy claims aligned with verified behavior.

For deeper context, read the [design decisions](docs/DESIGN_DECISIONS.md), [frontend guide](frontend/README.md), [security notes](docs/SECURITY_IMPLEMENTATION.md), [Render deployment record](docs/RENDER_DEPLOYMENT.md), and [Vercel deployment record](docs/VERCEL_FRONTEND_DEPLOYMENT.md). Deployment records include historical setup steps; current code and provider settings take precedence when they differ.
