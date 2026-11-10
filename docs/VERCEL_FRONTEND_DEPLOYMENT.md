# Gallery frontend on Vercel

The gallery is live at [arts.kaancinar.com](https://arts.kaancinar.com). It is a
separate Vercel project from the existing site at `kaancinar.com`.

| Setting | Value |
| --- | --- |
| Vercel project | `kaancinar/kaan-gallery-arts` (Hobby) |
| Frontend source | `frontend/` on `deploy/frontend-preview`, commit `db17dad` |
| Framework | Next.js, Node 24 |
| Production domain | `arts.kaancinar.com` |
| Backend | `https://kaan-gallery-backend.onrender.com` |

The first CLI deployment became the project's production deployment, as Vercel
does for a new project. Vercel verified the subdomain using the existing Vercel
DNS configuration. The root domain remains on its original project. Vercel
authentication remains on generated `vercel.app` URLs; custom domains are
public. A temporary automation bypass used for verification was revoked.

`BACKEND_ORIGIN` is set for Preview and Production. `SITE_URL` is set to
`https://arts.kaancinar.com` for Production. Both are server-side URL settings,
not API keys. The frontend server fetches artwork data from Django and proxies
image requests through its image routes. Render holds the Neon and R2 secrets.

The site exposes artwork-specific canonical and sharing URLs, a sitemap, and a
`robots.txt` that points to the production sitemap. Preview builds disallow
indexing. See [site configuration](../frontend/lib/site.ts),
[robots](../frontend/app/robots.ts), and [sitemap](../frontend/app/sitemap.ts).

## Verified on 10 November 2026

- Lint, 12 frontend tests, eight Chromium journeys, and a production build passed.
- Before firewall activation, public HTTPS returned 200 for `/`, `/clay-studio`, an artwork page,
  `/sitemap.xml`, `/robots.txt`, and a WebP card image.
- The public pages emitted canonical URLs on `arts.kaancinar.com`.

## Updating the frontend

This project was deployed with the Vercel CLI from `frontend/`. Its Git
integration and automatic deployments have not been configured. A push alone
does not release a new version. After testing a reviewed change, deploy from
`frontend/` with the Vercel CLI, using `vercel deploy --prod` for production.
Configure Git deployment only after selecting the correct production branch
and `frontend` root directory, so an unrelated branch cannot replace the site.

The Render backend is on the Free plan and can sleep when idle, causing a slow
first gallery load. Future database migrations must be applied separately;
neither the frontend nor Render's image build runs them. Before relying on this
as a complete public release, finish monitoring, backups/restore verification,
backend request controls, and cross-browser checks.

## Vercel firewall

The `kaan-gallery-arts` project has Bot Protection in **Challenge** mode. A
custom rule named **Limit gallery image bursts** matches paths beginning with
`/artwork-images/` and allows up to 120 requests per 60-second fixed window per
IP; excess requests receive a rate-limit response. Both changes were published
on 10 November 2026 after approval. Vercel reported no remaining draft changes.

Automated HTTP probes now receive Vercel's challenge response, so those probes
cannot confirm the visitor experience. Check the site in a regular browser and
watch Firewall activity for false positives. The Vercel firewall applies to
the frontend project; direct requests to the Render backend need separate
protection.
