# Kaan Gallery frontend

Next.js App Router, React, TypeScript, and plain CSS. Run with Node.js 24
(verified with 24.22.2).

## Local development

Start Django from the repository root:

```bash
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
- Adaptive sun favicon and a branded Open Graph/Twitter sharing image.

## Checks

```bash
npm run lint
npm run build
npm start
```

Both lint and the production build passed on 2026-11-08. Interactive browser,
keyboard, responsive, and assistive-technology checks are not yet complete.

## Configuration and remaining work

`SITE_URL` controls absolute social-sharing URLs and defaults to
`http://localhost:3000`. Set it to the public frontend origin before deployment.
The backend origin is still local and hardcoded in the gallery and detail pages;
production backend configuration remains outstanding.

Theme restoration after reload and artwork-specific metadata/sharing previews
remain unfinished. Gallery photos currently download original files without
Next.js image optimization; smaller responsive variants and measured performance
work are planned. Do not add caching without preserving publication visibility
and unpublish behavior.

Dependencies are locked in `package-lock.json`. Audit results are documented in
the root README; do not apply forced dependency upgrades or unsupported major
version overrides without review.

Nothing is deployed. Production settings, persistent private storage, backups,
rate limiting, and the remaining security checks are required before launch.
