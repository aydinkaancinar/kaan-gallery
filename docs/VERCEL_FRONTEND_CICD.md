# Frontend CI/CD

The production site at `arts.kaancinar.com` is deployed by
[`vercel-frontend.yml`](../.github/workflows/vercel-frontend.yml). Pushes to
`deploy/frontend-preview` that change `frontend/`, the Python lockfile used by
browser tests, or the workflow run it. It can also be started manually from
GitHub Actions. The workflow deploys the exact checkout it tested.

The job installs the locked Node and Python dependencies, runs lint and unit
tests, and runs Playwright's desktop and phone journeys against a disposable
local Django catalog. It then checks a production Next.js build using the
documented public origins and asks Vercel to build and deploy with
`vercel deploy --prod`. Vercel supplies its Production environment settings
to that build. A failed check stops deployment. Runs are
serialized so an older run cannot finish after a newer one.

## One-time GitHub secret

Create a Vercel access token in **Vercel → Account Settings → Tokens** with
access to the account that owns `kaan-gallery-arts`. Add it to this GitHub
repository at **Settings → Secrets and variables → Actions → New repository
secret** as `VERCEL_TOKEN`. Do not add the token to source, a local `.env`, or
the workflow file. The Vercel organization and project IDs in the workflow
identify the destination; they are not credentials. The job fails before
deploying if the secret is absent.

`BACKEND_ORIGIN` and `SITE_URL` stay in the Vercel project's Production
environment settings. Vercel marks their values sensitive, so its CLI replaces
them with placeholders when pulling them into GitHub Actions. This is why the
final build runs on Vercel. Keep the Vercel
project's Git auto-deployment disabled or disconnected, so it cannot publish a
push before these checks finish. Its custom domain remains attached to the
production project; a successful `--prod` deployment updates that domain.

To verify the first run, open **GitHub → Actions → Test and deploy Vercel
frontend**, check the tested commit and all steps, then inspect the deployment
in Vercel and load `https://arts.kaancinar.com`. The existing Render and R2
deployments are separate and are not changed by this workflow.
