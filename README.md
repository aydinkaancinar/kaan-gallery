# Kaan Gallery

A personal gallery for the artwork of Aydın Kaan Çınar, developed step by step as a full-stack learning project. The Django REST Framework backend and Next.js frontend run locally, with a responsive gallery based on approved light/dark mockups.

**Status: local development, not production-ready.** Public visitors can read published artwork. API writes and draft previews require active, MFA-verified staff. Production infrastructure and remaining security work are not deployed.

## Current features

- Artwork and artist management through Django admin and protected API endpoints.
- Draft/published workflow with restricted draft metadata and image access.
- Admin-managed categories, artist relationships, and many-to-many tags.
- Name/description search, physical creation-date search, and combined filters.
- Inclusive month/year ranges and paginated lists (nine items per page).
- Optional admin-set gallery positions, followed by physical creation date newest first; stable ID tie-breakers.
- Unique artwork slugs that remain stable when titles change.
- Multiple images with alt text, display order, and automatically selected cover images.
- Image delivery through a publication-aware endpoint rather than public storage URLs.
- Upload size, actual-format, pixel-limit, and Pillow decompression-bomb validation.
- Session authentication, authenticator-app MFA, CSRF enforcement, and staff authorization.
- Responsive light/dark gallery with real images, category/search/month filters, URL-based pagination, and reset controls.
- Individual artwork pages with uncropped photos, image navigation, and a full-screen viewer.
- Loading, error/retry, and not-found screens; adaptive sun favicon and artwork-specific sharing metadata.
- Browser-aware theme defaults, persistent manual theme choices, and contact links.
- Clay Studio vessel modeling, clay estimates, undo/redo, saved designs, and shareable design links. See [model assumptions](docs/CLAY_STUDIO.md); the vessel estimate includes a provisional 25% adjustment, not a manufacturer calibration.
- Public field allowlists hide prices, inventory quantities, and management metadata; price queries require verified staff.
- **123 passing backend tests**, verified 2026-11-08; 12 frontend behavior tests, lint, and production build also pass.

## Architecture

| Component | Current / planned |
| --- | --- |
| Backend | Django 5.2 + Django REST Framework |
| Local database | SQLite |
| Local image storage | Files under ignored `media/`; delivered through Django access checks |
| Frontend | Next.js 16 + React 19 + TypeScript, implemented locally |
| Hosting | Vercel frontend, Render backend, Neon PostgreSQL; free tiers initially, planned |
| Production media | Private object storage, provider to be selected |
| Edge security | Cloudflare proxy/Access with direct-origin bypass protection, planned |

The first release is a gallery with private administration. Sales are deferred. The frontend includes light/dark themes, individual artwork pages, search, categories, a completion-date range slider, and MM/YY dates beside titles. Visitor sorting controls are not planned initially; explicit backend sorting remains available.

## Local setup

Use Python 3.12. From your checkout:

```bash
git clone https://github.com/aydinkaancinar/kaan-gallery.git
cd kaan-gallery
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements-lock.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py runserver
```

For an existing installation, run migrations and start the server. The database and artwork files are not included in Git; a fresh install starts empty.

1. Open [MFA login](http://127.0.0.1:8000/account/login/).
2. After password authentication, open [authenticator setup](http://127.0.0.1:8000/account/two_factor/setup/) and complete enrollment.
3. Use [Django admin](http://127.0.0.1:8000/admin/) to create artists, artwork, tags, and image records.
4. Publish an artwork to make it visible to anonymous gallery requests. New artwork defaults to draft.

Admin access requires MFA verification. Keep authenticator secrets and recovery material private. Test fixtures use simulated sessions in selected tests; those helpers are not a production login mechanism.

## Frontend setup

Use Node.js 24 (verified with 24.22.2). Keep Django running on
`http://127.0.0.1:8000` and start Next.js in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend currently uses
the local Django address directly; deployment-specific API configuration remains
planned. `SITE_URL` controls absolute sharing URLs and defaults to localhost;
set it to the real public frontend origin before deployment.

```bash
npm run lint
npm run build
npm start
```

The production build passes, but that is not a production security or hosting
approval. See [frontend notes](frontend/README.md) for current limitations.

Dependency audit on 2026-11-08: `npm audit --omit=dev` reports zero findings.
The full audit reports eight moderate development-tool findings through
`minimatch` and TypeScript ESLint. They remain unresolved; no forced major
upgrades or dependency overrides were applied.

## API

Use trailing slashes. Public item reads are restricted to published artwork; active MFA-verified staff can preview drafts.

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/items/` | GET, POST | Paginated artwork list; protected creation |
| `/items/categories/` | GET | Category values/labels used by published artworks |
| `/items/date-bounds/` | GET | Earliest/latest known published completion months |
| `/items/<id>/` | GET, PATCH, DELETE | Read, update, or delete by ID |
| `/artworks/<slug>/` | GET | Read artwork by stable slug |
| `/artwork-images/<id>/` | GET | Stream an image subject to current publication and session checks |
| `/artists/` | GET, POST | Artists linked to published work; protected creation |
| `/artists/<id>/` | GET, PATCH, DELETE | Read, update, or delete an artist |

POST, PATCH, and DELETE require staff/MFA session authorization and CSRF protection. Image uploads currently use private admin forms; there is no public image-upload API. Item PATCH returns 200 without a response body; successful deletion returns 204.

### Search and filtering

```bash
# Published artwork
curl 'http://127.0.0.1:8000/items/'

# Free-text search combined with category
curl 'http://127.0.0.1:8000/items/?search=moon&category=vase'

# Inclusive physical creation month/year range
curl 'http://127.0.0.1:8000/items/?created_from=2024-06&created_to=2026-05'

# Exact creation month and year
curl 'http://127.0.0.1:8000/items/?creation_year=2026&creation_month=5'

# Match either tag, without duplicate artwork
curl 'http://127.0.0.1:8000/items/?tag=ceramic&tag=handmade'

# Explicit backend sort, retained for future UI use
curl 'http://127.0.0.1:8000/items/?order_by=-creation_date'
```

Other public filters include `name` and `artist`. `min_price`, `max_price`, and `order_by=price` require an active, MFA-verified staff session; public price queries return 403. Valid `YYYY`/`YYYY-MM` search terms search physical dates rather than textual occurrences. Dates are optional year/month pairs; current year bounds are 1999–2099. The database record's `created` timestamp is separate from physical creation dates.

Public artwork responses explicitly omit price, quantity, database creation timestamp, status, gallery position, and the duplicate artist foreign key. Verified staff retain management fields. Public artist list/detail access requires at least one published artwork.

Successful list responses contain `count`, `next`, `previous`, and `results`. Follow `next` to traverse the collection. Date filters and sorting use full year/month values; MM/YY is a frontend presentation decision.

The default sequence puts assigned gallery positions first, lowest number first; equal positions and unpositioned groups use newest physical date first, then ID. Unknown dates are last within their position group. Position zero is valid; blank means unpositioned. Explicit `order_by` overrides the curated default.

## Images and access

Artwork responses include ordered `images` and `cover_image` (the first image by position, then ID; null if there are none). Image URLs point to `/artwork-images/<id>/`.

Published images are public. Draft images require an active, MFA-verified staff session. Unpublishing an artwork denies subsequent anonymous requests to the same image endpoint. Previously downloaded copies cannot be recalled. Successful image responses use private/no-store caching; error-response and production edge-cache policy still need completion.

Uploads allow JPEG, PNG, and WebP, up to 10 MiB and 25 million pixels. Validation inspects contents; a `.jpeg` filename alone is not sufficient (for example, multi-picture MPO files are not in the allowlist). These checks are not a claim that every upload threat is solved.

## Managing categories

Use **Admin → Categories → Add category** to create a category, then select it on an artwork (or use the + button beside its category field). Names and positions can be edited; lower positions appear first in gallery filters. A category appears publicly once it has a published artwork. Existing categories and artwork assignments are preserved by migration 0022. Category slugs stay fixed after creation to preserve links, and categories in use cannot be deleted. Keep Miscellaneous available as the default for new artworks.

## Tests and development checks

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py test
./.venv/bin/python manage.py makemigrations --check --dry-run
./.venv/bin/python -m pip check

# Focused modules
./.venv/bin/python manage.py test items.tests.test_session_security
./.venv/bin/python manage.py test items.tests.test_creation_dates
./.venv/bin/python manage.py test items.tests.test_gallery_ordering
```

Tests use a separate database. File-delivery tests use temporary media storage; some serializer tests use placeholder paths without writing images. Shared helpers and fixtures live under `items/tests/`.

After model changes, generate migrations with `makemigrations` and apply them with `migrate`. The Python app is `items`, but its internal app label remains `tasks` to preserve migration/table compatibility; app-specific migration commands therefore use `tasks`.

## Repository map

```text
config/                  Django settings, routes, WSGI entry point
items/
  models.py              Artwork, artist, tag, image models
  serializers.py         API representations and input validation
  views.py               API operations and authorized image streaming
  permissions.py         Shared verified-staff policy
  validators.py          Image size/content/dimension checks
  admin.py               Private administration forms and lists
  migrations/            Versioned schema and data changes
  tests/                 Topic-specific tests and helpers
frontend/                Next.js App Router gallery, components, and styles
logo/                    Light/dark identity source assets
templates/two_factor/    Account-page presentation
scripts/                 Documentation page generator
docs/                    Security notes and behavior specifications
```

Local databases, media originals, environment files, the virtual environment, and the personal project checklist are ignored. The approved visual design is implemented in the frontend; the temporary standalone prototype remains outside this repository.

## Security and remaining work

Do not deploy the local configuration unchanged: it uses DEBUG, a development-only key, and SQLite. Production work includes environment-managed secrets, HTTPS/secure cookies, login rate limiting, MFA recovery and bypass tests, private storage, origin lockdown, backups/restoration, monitoring, and remaining upload/access coverage.

Sessions currently expire eight hours after their last save; ordinary requests do not refresh them. Browser-close expiry is enabled, but closing the browser does not revoke a copied session on the server. See the security notes for the distinction between session expiry, MFA state, and CSRF tokens.

Public source is intentional. Credentials, session cookies, MFA secrets, recovery codes, private artwork, and database dumps must never be committed. Passing tests are evidence for specified scenarios, not a security guarantee. See the documented limitations before deployment.

## Documentation

- [Security implementation and learning notes](docs/SECURITY_IMPLEMENTATION.md)
- [Security notes as standalone HTML](docs/SECURITY_IMPLEMENTATION.html) — open locally in a browser; GitHub displays HTML source rather than hosting the page.
- [Physical creation-date contract](docs/CREATION_DATE_SPEC.md)
- [Curated gallery ordering](docs/GALLERY_ORDERING.md)

After updating security Markdown, regenerate its HTML version:

```bash
python3 scripts/build_security_page.py
```
