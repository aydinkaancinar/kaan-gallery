# Render backend — first live verification deployment

Deployed November 10, 2026. This is the backend verification deployment; the
existing kaancinar.com website has not been changed and the new Vercel frontend
has not been deployed.

| Setting | Value |
| --- | --- |
| Workspace | Kaan Gallery |
| Service | kaan-gallery-backend |
| Service ID | srv-dbpphf56e07s73b316k0 |
| Region / plan | Virginia / Free |
| Runtime | Docker, non-root Gunicorn |
| Source branch | deploy/render-backend |
| Verified code commit | 2960db96ec32df6b15136c3e2cf4fbaacc68a785 |
| Live deploy | dep-dbpphm74j4sc738qoh50 |
| Health path | /healthz/ |
| Auto-deploy | Disabled; manual deploys during verification |

[Open backend](https://kaan-gallery-backend.onrender.com/items/) ·
[Open admin](https://kaan-gallery-backend.onrender.com/admin/) ·
[Render dashboard](https://dashboard.render.com/web/srv-dbpphf56e07s73b316k0)

## Runtime configuration

The Docker image uses `config.settings_production`. Runtime secrets were
uploaded through Render's environment API, using the authorized CLI credential
in memory. No secret values were passed as command arguments, logged or committed.
A private, ignored `.env.render` retains the selected runtime configuration locally.
The production Django secret differs from the local Docker secret.

Configured keys: `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
`DJANGO_TRUST_PROXY_HEADERS`, `DATABASE_URL`, `ARTWORK_GATEWAY_URL`,
`ARTWORK_GATEWAY_TOKEN`. Render supplies the listening port. Neon main and the
existing private R2 quota gateway are reused; no Render database was created.
No database migration or data import ran during deployment.

The initial automatic deploy began before runtime secrets were configured and
failed closed on missing `DJANGO_SECRET_KEY`. The subsequent explicitly triggered
deploy used the configured environment and became live. The earlier failed
entry remains in deployment history; it is not the current deployment.

## Live verification passed

- HTTPS health, artwork API, admin CSS and MFA login form returned 200.
- Session/CSRF HTTPS configuration includes a Secure CSRF cookie and HSTS.
- Requests made over HTTPS with a spoofed HTTP protocol header still succeeded;
  HTTP requests with a spoofed HTTPS header still redirected to HTTPS. This
  verified the ingress behavior required by the explicit proxy-trust setting.
- A login POST without CSRF returned 403.
- Six card/detail/share image responses matched retained local bytes. Public
  originals returned 200; protected originals returned 404 anonymously.
- A human password/MFA login and an authorized disposable upload still need
  manual verification. Automated checks did not submit account credentials.

The Free service sleeps after idle periods, so the next request may need to wake
it. Database and artwork remain external in Neon and R2. Monitor included usage;
Free hosting is being used for initial verification, not as an always-on promise.

## Next steps

1. Sign in at the Render admin URL with password and MFA. The new origin/secret
   means a new session is needed. Confirm gallery data and a disposable upload.
2. Complete the planned Cloudflare bot/rate controls and verified ingress/direct
   origin protections before announcing the new public site.
3. Verify production backups, restore procedure and monitoring. The retained
   local SQLite snapshot is not a current backup of future PostgreSQL edits.
4. Deploy the new Vercel frontend using this backend origin on a preview first.
   Keep database and Worker credentials out of frontend variables. Switch the
   public domain only after end-to-end verification.

To deploy a reviewed commit later, use the Render Dashboard or:

```bash
render deploys create srv-dbpphf56e07s73b316k0 --wait --confirm --output json
```

Confirm the workspace and intended branch/commit first. This deploy command does
not apply database migrations; future schema changes require an explicit release
step using a direct Neon connection. On Free, paid pre-deploy commands are not
available. Rollback of a Render image does not roll back database changes.

The official Render plugin was installed, but its tools were not exposed in the
session. Deployment used the official Render CLI 2.35.0 and documented API instead.
