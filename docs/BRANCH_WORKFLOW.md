# Branch and release workflow

`main` is the complete, reviewed source of truth. `deploy/render-backend` and
`deploy/frontend-preview` are release pointers. They should contain only
commits already on `main`; they may intentionally lag behind it. The first
reconciliation merged the formerly separate deployment histories into `main`,
so both deployment branches can now be fast-forwarded from it.

## Make a change

```sh
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/short-description
# Edit and test the change, then commit it.
git push -u origin feature/short-description
```

Open a pull request from the feature branch to `main`, review the diff and
checks, and merge it there. Keep deployment commits out of feature branches.
If `main` moves while work is in progress, update the feature branch from
`main` and rerun relevant checks before merging.

## Release a tested main commit

First update local `main`. Then advance only the destination you intend to
release:

```sh
git fetch origin
git switch main
git pull --ff-only origin main
git switch deploy/frontend-preview  # or deploy/render-backend
git pull --ff-only origin deploy/frontend-preview
git merge --ff-only main
git push origin deploy/frontend-preview
```

Use the backend branch name in both commands for a backend release. The
fast-forward fails if the branch has diverged, which is a signal to stop and
investigate rather than force-push. GitHub Actions checks that the pushed
deployment commit is already in `main`, then runs tests and deploys. Watch the
workflow and the hosting dashboard for the final result. A frontend push
without changes under `frontend/` or its workflow does not start Vercel CI;
use **Run workflow** in GitHub Actions if a redeploy is needed.

For a rollback, make a revert commit on a feature branch, merge that branch
into `main`, and fast-forward the affected deployment branch. This preserves
history and keeps the release branch related to `main`.
