# Kaan Gallery frontend

Next.js App Router, React, TypeScript, and plain CSS. Run with Node.js 24
(verified with 24.22.2).

## Local development

Start Django from the repository root:

```bash
./.venv/bin/python manage.py generate_artwork_variants
./.venv/bin/python manage.py runserver
```

In a second terminal, from this directory:

```bash
npm ci
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000). Published artwork metadata
comes from Django on port 8000; images use its authorization-aware delivery
URLs. Private artwork originals are not frontend assets and must not be copied
into `public/` or committed.

## Features

- Responsive gallery, light/dark controls, categories, search, inclusive month
  ranges, nine-item pagination, and reset controls with filters stored in URLs.
- Slug-based artwork detail pages, ordered image navigation, and full-screen
  viewing, with a return link preserving gallery filters and page.
- Loading skeletons, filter-pending feedback, retry and not-found screens.
- Adaptive sun favicon, artwork-specific metadata, and branded fallback sharing image.
- Persistent light/dark themes, KC personal-site link, and email contact.
- Clay Studio vessel modeling, weight estimates, undo/redo, saved designs, and shareable design URLs. See [model notes](../docs/CLAY_STUDIO.md).

## Checks

```bash
npm test
npm run lint
npm run build
npm start
```

### How to test the frontend

`npm test` runs the 12 fast checks for theme logic and clay calculations.
`npm run test:browser` opens a real browser and exercises the frontend against
the Django API.

Install the browser once after `npm ci`, then run the journeys:

```bash
npx playwright install chromium
npm run test:browser
```

Playwright starts Django on port 8114 with a temporary database and generated
sample images, then builds and serves the frontend on port 3113. Its frontend
output goes in `.next-browser-tests`. Stop any previous browser test run before
starting another. Django dependencies must already be installed in the root
`.venv`.

Four journeys run at desktop and phone sizes. They check filters and search
through Back, Forward, and reload, theme persistence, opening and closing the
viewer with keyboard photo navigation, and protected drawings using their
limited preview while original requests are rejected.

To watch the first journey, run:

```bash
npm run test:browser -- --project=desktop --headed --workers=1 --grep "filters survive"
```

Read `tests/browser/gallery.spec.ts` alongside it. Each `test` describes a
visitor journey. `getByRole` finds a visible control by its accessible name,
`click` performs the action, and `expect` checks the result while allowing
time for it to appear. Add a regression to the relevant journey when fixing a
navigation or interaction bug.

Failed checks save a screenshot and trace under `test-results`. For a step by
step debugging session, use:

```bash
npm run test:browser -- --project=desktop --debug --grep "filters survive"
```

For a manual image check, open Chrome DevTools → Network, disable cache, and
filter by `artwork-images`. Gallery cards request `/card`, detail pages request
`/detail`, and unprotected originals first load after clicking **View image**.
Protected drawings use `/detail` in the viewer too.

The phone project emulates a phone in Chromium. Real device touch testing,
Firefox and Safari, broader keyboard and accessibility checks, pagination,
date filtering, error states, and Clay Studio journeys remain for later passes.

## Configuration and remaining work

`BACKEND_ORIGIN` defaults to `http://127.0.0.1:8000`. Next.js uses this
origin for Django requests and proxies only the artwork image routes. Set it
and `SITE_URL` before building and running the deployed app. Set `SITE_URL`
to the public frontend origin for the indexable deployment. With `SITE_URL`
unset, `robots.txt` asks crawlers to stay out.

### Image delivery and search

New admin uploads generate a cropped WebP card up to 720 × 900, a WebP detail
image with a longest edge up to 1440, and a 1200 × 630 JPEG sharing preview
that fits the whole artwork. Files stay in Django's artwork storage.
`generate_artwork_variants` fills missing variants for older uploads and reports
their sizes. Run it after importing media and before serving the frontend.
Use artwork storage that allocates a new key when a file is replaced so each
original has its own variants. The viewer requests the original for unprotected
artworks. For protected drawings, all public images have an embedded watermark,
and the viewer uses a copy with a longest edge up to 1200 pixels. Published
protected originals require verified staff authentication. Enable **Protect
images** in admin for each artwork you want protected. The checkbox controls
protection for every category.
Image delivery checks publication state and uses private, no-store responses.

The nine covers on the first local gallery page total 320 KB as card variants,
down from 21.9 MB as originals. This compares image payloads, before lazy loading
and without measuring page load time.

Artwork pages have canonical URLs, artwork-specific social previews, and
structured data. The sitemap lists published artwork pages and their detail
images, along with the portfolio and Clay Studio. After deployment, check a
live preview, inspect both landing pages in Search Console, and submit
`/sitemap.xml`. Use the live site for page speed and indexing measurements.

The first visit follows the browser's light/dark preference. Explicit Light/Dark
choices persist in localStorage and override the browser preference on later
visits. Without an explicit choice, browser theme changes are followed. Blocked
storage falls back to a preference for the current visit only. A small head
script applies the initial theme before the page content is painted.

Run the theme behavior checks with `node --test tests/theme.test.mjs`.

Dependencies are locked in `package-lock.json`. Audit results are documented in
the root README; do not apply forced dependency upgrades or unsupported major
version overrides without review.

### Third-party software notices

The footer's **Software licenses** link serves
`public/THIRD_PARTY_LICENSES.txt` at `/THIRD_PARTY_LICENSES.txt`. The `prebuild`
script regenerates it from the installed upstream license files, so both
local production builds and Vercel's npm build include the notices. CI checks
that the committed copy matches the installed packages before building.

```bash
npm run licenses:generate
npm run licenses:check
```

The inventory covers Next.js, React/React DOM, Scheduler, SWC helpers, the
browser-facing components bundled inside Next, and its core-js legacy-browser
polyfill. It conservatively includes both React Server Components transports
and browser fallback helpers. Full upstream copyright and license texts are
preserved. The core-js 3.38.1 notice is retained separately in `licenses/`
because Next only includes the minified polyfill and its upstream license URL.
These notices do not license the gallery's original code or visual assets;
see the root [LICENSE](../LICENSE).

When adding browser dependencies or updating Next.js, review the inventory in
`scripts/generate-license-notices.mjs`, regenerate the notices, and commit both
the dependency and notice changes. Next version and core-js version guards
require that review on upgrades. To inspect browser dependencies with the
installed Next.js CLI:

```bash
npx next analyze --output --snapshot licenses
npx next analyze export --snapshot licenses > /tmp/kaan-gallery-license-graph.jsonl
```

Review `module` records referenced by `output` records whose filenames start
with `[client-fs]`, plus the separately copied legacy polyfill. The notice
generator is a reviewed inventory, not an automatic license scanner. Backend
and development tools retain their own package licenses; redistribution of
those packages or container images needs a separate review.

The `software license notices` browser test follows the footer link from a
production build and checks the served text against the generated file and
the installed React/SWC licenses. Run it with:

```bash
npm run test:browser -- --grep "software license notices"
```

The frontend is live at [arts.kaancinar.com](https://arts.kaancinar.com). See
[the Vercel deployment record](../docs/VERCEL_FRONTEND_DEPLOYMENT.md). Monitoring,
backups, bot protection, and remaining security checks still need work.
