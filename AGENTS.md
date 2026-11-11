# Repository working rules

- Read `README.md` at the start of a task for the current architecture, code map, local setup, deployment flow, and known gaps. Read `docs/DESIGN_DECISIONS.md` for architecture, hosting, cost, or data-flow work. Then read the relevant linked guide and verify behavior against the code or live settings before changing it. Keep both documents in sync when their assumptions or release procedures change.
- Start every code or documentation change on a new `feature/*` (or `fix/*`) branch created from the latest `origin/main`.
- Never commit, cherry-pick, or merge a feature branch directly into `deploy/render-backend` or `deploy/frontend-preview`.
- Review and test the feature branch, then merge it into `main` first. Keep `main` as the source of truth for both deployments.
- Deploy only by fast-forwarding the selected deployment branch to a commit already on `main`, then pushing that branch. Do not rewrite deployment branch history.
- Syncing the backend branch triggers its Render workflow. Syncing the frontend branch triggers its Vercel workflow when frontend files or its workflow change. Choose which branch to advance based on what should be released.
- If a hotfix is needed, create it from `main`, merge it into `main`, and fast-forward the affected deployment branch. Rollbacks also go through a new commit on `main`.
- Follow `docs/BRANCH_WORKFLOW.md` for commands and verification. Existing nested `AGENTS.md` files add instructions for their directories.
