# Design decisions

Kaan Gallery is built to give Aydın Kaan Çınar's artwork a clear, searchable home and let visitors experiment with pottery forms in Clay Studio. The site has no checkout or public accounts. The infrastructure aims for **no recurring hosting charge at current usage**, while keeping artwork originals and editing access private.

## Why the system is split up

| Choice | Reason and tradeoff |
| --- | --- |
| [Next.js frontend](../frontend/app/) on Vercel | Renders artwork pages with search metadata, sharing previews and interactive gallery controls. It asks Django for data, so an idle backend can slow the first page load. |
| [Django API and admin](../items/views.py) on Render | Keeps publishing rules, uploads, image authorization and owner editing in one place. Render Free can sleep after inactivity. |
| [Neon PostgreSQL](../config/settings_production.py) | Keeps artwork and admin records outside Render's disposable container. Production requires a TLS database connection; local SQLite remains useful for isolated tests. |
| [Private R2 gateway](../cloudflare/r2-gateway/) | Stores originals and generated images without a public bucket URL. Django decides who may see an image; the Worker manages storage access and quota reservations. An extra network hop adds latency. |
| [Clay Studio in the browser](../frontend/app/clay-studio/studio.tsx) | Visitors can design without accounts or a new database table. Saved designs stay in browser storage; a share link contains the design and can appear in request logs. |

The [runtime diagram](../README.md#how-it-works) shows the request path. [Small card and detail variants](../items/image_variants.py) reduce everyday image transfers, while [artwork-specific sharing previews](../frontend/app/artworks/) and a [sitemap](../frontend/app/sitemap.ts) support discovery. Image protection is an owner-controlled checkbox: public copies are watermarked only when it is enabled, and protected originals require the owner's verified session.

## Keeping hosting costs down

| Layer | Current approach | Limit to watch |
| --- | --- | --- |
| Frontend | [Vercel Hobby](https://vercel.com/docs/plans/hobby) | Free usage limits and the personal/non-commercial terms; confirm this portfolio's intended use qualifies. |
| Backend | [Render Free web service](https://render.com/docs/free) | It sleeps when idle and can be suspended at limits. Render describes Free as unsuitable for production reliability. |
| Database | [Neon Free allowance](https://neon.com/pricing) | Storage, compute, transfer and restore window. The live data is external to Render. |
| Images and gateway | [R2 Standard free allowance](https://developers.cloudflare.com/r2/pricing/), [Workers Free](https://developers.cloudflare.com/workers/platform/pricing/), [SQLite Durable Objects](https://developers.cloudflare.com/durable-objects/platform/pricing/) | Storage, read/write operations, Worker requests and Durable Object usage have separate limits. |
| Quota email | [Resend Free](https://resend.com/pricing) | Alert delivery remains inside its email allowance. |

The custom domain has a separate renewal cost. These service tiers can change, and exceeding a provider allowance may stop service or create charges. The [R2 quota Worker](R2_QUOTA_GATEWAY.html) warns at 90% and blocks gallery storage calls before configured safety margins, but direct provider activity and delayed usage reports mean it cannot guarantee a zero bill. Until the exact R2 renewal hour is confirmed, its current configuration deliberately holds billable access at the December 10 boundary for review. The zero-cost goal is a budget constraint, not a promise of uninterrupted service.

## Access and privacy

The [admin](../items/admin.py) and write routes are intended for the site owner only. Password, authenticator-app MFA, permissions, CSRF protection and session expiry protect editing. The code can support staff accounts, but there is no visitor sign-up. Owner-only access still leaves public request logs and possible unauthorized login attempts; it does not remove the need for the [privacy policy](../frontend/app/privacy/page.tsx) or an operating retention practice. The owner has deferred login-record cleanup for now.

Published artwork is public. Draft metadata and images, private originals for protected artwork, and upload operations require verified staff access. The browser has no Neon or R2 credential. See the [security notes](SECURITY_IMPLEMENTATION.md) for the exact boundaries.

## Why releases have three branches

Every change starts on `feature/*` or `fix/*` from the latest `main` and reaches `main` through a reviewed pull request. `main` holds the complete project. The Vercel and Render deployment branches move forward from `main` only when that side is ready to release, so one side can stay on an older reviewed commit. [GitHub Actions](../.github/workflows/) tests the selected deployment commit before asking its host to deploy. Database migrations remain a separate release step. See the [deployment diagram](../README.md#how-changes-reach-the-site) and [branch commands](BRANCH_WORKFLOW.md).

## Decisions still under review

- Protect direct requests to the Render origin, and measure page speed with the Free backend's cold starts.
- Verify backups by restoring them; add monitoring and broader browser/device checks.
- Confirm Vercel Hobby suitability and account data preferences, review live cookies/provider settings, and settle retention practices before treating the privacy review as complete.
- Refine Clay Studio's provisional clay-weight adjustment when more real measurements are available.

Update this page when a deployment, data flow or cost assumption changes.
