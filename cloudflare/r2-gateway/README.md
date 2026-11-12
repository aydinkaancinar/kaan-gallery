# Private R2 quota gateway

Local implementation for the gallery's private `kaan-gallery-media` bucket.
Worker deployed and initialized on November 10, 2026.
Resend inbox delivery and the account analytics query were verified separately.

Django checks publication state and the Protect images checkbox, then calls
this authenticated Worker. The Worker uses one SQLite-backed Durable Object
to serialize quota reservations and object-ledger updates before R2 access.
Browser clients receive image bytes through the existing Django routes.

## Limits and warnings

| Metric | Warning | Gateway cutoff |
| --- | --- | --- |
| Class A operations | 900,000 per billing period | 950,000 |
| Class B operations | 9,000,000 per billing period | 9,500,000 |
| Stored bytes | 9,000,000,000 | 9,500,000,000 |

Each object also reserves 8 KiB for metadata. These margins are deliberately
conservative. Account analytics include all R2 buckets. A dedicated bucket
starts empty, and all writes, reads, and deletes must use this gateway.

The daily Workers Free allowance is an additional availability limit. Request
counts and R2 operation counts differ. Workers and Durable Objects also have
their own compute/storage allowances. Confirm the account uses Workers Free
before enabling traffic.

This is an application cutoff, not a Cloudflare billing guarantee. Analytics
are delayed estimates. Direct S3 credentials, presigned URLs, public bucket
domains, another Worker binding, dashboard operations, or other R2 workloads
can bypass local reservations. Stored data still contributes to storage
charges while requests are stopped. Deleting data does not cancel storage
usage already accrued.

The gateway enforces aggregate storage budgets. Public gallery image/API routes
still require bot and request-rate controls at deployment, with verified ingress
and exceptions for legitimate search and sharing crawlers.

## Safety behavior

- Requests need the Django-only storage secret. Management routes need a
  separate control secret. Anonymous requests are rejected before R2 access.
- The Worker reserves each R2 GET/PUT/list operation before making the call.
  Metadata HEAD requests use the durable ledger and make no R2 calls.
- Object keys are immutable. Conditional R2 writes detect unexpected existing
  objects. Reservation state survives Worker restarts and partial failures.
- Failed operations keep their reservations, which can stop the service early.
  Pending objects are counted in status. Deleting a known pending key can
  remove its byte reservation after R2 deletion succeeds.
- Billable access stops on stale analytics (30 minutes), failed analytics,
  manual lock, or any exhausted budget. Authorized deletes remain available
  because R2 delete operations are free.
- Every 15 minutes, Cron reconciles account analytics and retries warning
  delivery. It preserves the highest operation totals seen within the period.
  The storage snapshot uses the highest size per bucket over the last 24 hours.
  Storage-related blocking can therefore persist after deletion until the
  high-water snapshot falls. Local byte accounting also remains enforced.
- Warnings are stored durably. An HTTPS webhook receives JSON events with
  stable IDs. Acknowledged events are marked delivered. A crash after delivery
  can cause a duplicate; the recipient should deduplicate by ID. An absent or
  failing webhook leaves events pending. Verify delivery before launch.
- The billing anchor is persisted and cannot be changed on an existing ledger.
  Only with `BILLING_RESET_CONFIRMED=true` do quota counters reset on the configured billing boundary. Stored bytes,
  pending reservations, and manual locks remain. Traffic waits for a fresh
  analytics reconciliation at rollover. Undelivered warnings survive rollover.
- Responses use private/no-store caching. The bucket has no public route.

## Local verification

Use Node.js 24 and the gallery's Python environment.

```bash
cd cloudflare/r2-gateway
npm ci
npm test
```

The tests use Cloudflare's local runtime, an isolated R2 bucket and Durable
Object, and mocked analytics/webhooks. They never contact your live bucket.

From the repository root:

```bash
./.venv/bin/python manage.py test items.tests.test_storage_gateway
```

## Deployment sequence

1. Confirm R2 public development access is disabled and there are no bucket
   custom domains. Keep the bucket empty until initialization succeeds.
2. Keep other R2 writers disabled for this bucket. Django will use this
   gateway instead of an S3 client. Use the Worker binding for R2 access.
3. Verify `ACCOUNT_ID` and the conservative accounting start in
   `BILLING_ANCHOR_UTC`. Keep `BILLING_RESET_CONFIRMED=false` while the reset
   hour is unknown; see the conservative-hold section below. Automatic
   rollover requires a verified exact boundary and a matching persisted anchor.
4. Generate two independent random secrets of at least 32 characters and store
   them securely. For example, run `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   separately for each secret. Install Worker secrets using the CLI prompts:

   ```bash
   npx wrangler secret put STORAGE_TOKEN
   npx wrangler secret put CONTROL_TOKEN
   npx wrangler secret put ANALYTICS_TOKEN
   npx wrangler secret put ALERT_WEBHOOK_URL
   ```

   Use an account Analytics Read token for `ANALYTICS_TOKEN`. The webhook must
   accept a JSON POST and return a success response to acknowledge delivery.
   It can forward the notification to email or your chosen notification service.
   No email delivery service is configured by this repository.
5. Confirm the account's Workers plan and all bindings, then deploy using
   `npm run deploy`. Configuration includes the R2 binding, SQLite Durable
   Object migration, and 15-minute Cron trigger. Deploying can activate
   billable Cloudflare resources depending on the account's plan.
6. Use the control credential to POST `/v1/control/initialize` on the deployed
   Worker. This queries analytics and checks the bucket is empty. Initialization
   consumes one Class A list operation. Initialization cannot reset an existing
   ledger. A failed check leaves access blocked.
7. Verify `GET /v1/control/status` reports initialized, fresh analytics, no
   block, and a configured notification destination. Trigger and acknowledge
   a warning with a deliberately low test quota in a separate test deployment.
8. Set Django's `ARTWORK_GATEWAY_URL` to the Worker's HTTPS origin and
   `ARTWORK_GATEWAY_TOKEN` to the storage secret. The control and analytics
   tokens belong only in Cloudflare's secret store. Treat the webhook URL
   as a secret when it contains an authentication token.
9. Import original files into the empty bucket through
   `QuotaGatewayStorage.save()`, preserving the database's original keys.
   Run `generate_artwork_variants` against the gateway-backed configuration.
   Verify file counts/content and access restrictions before switching traffic.
   Media import and database migration are separate production-release steps.

The default local Django configuration continues using filesystem storage.
Gateway settings activate the new backend when `ARTWORK_GATEWAY_URL` is set.
Gateway failures produce a private/no-store HTTP 503 with Retry-After instead
of redirecting to storage or trying another backend.

## Management routes

Use `Authorization: Bearer <CONTROL_TOKEN>`.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/v1/control/status` | Counters, budgets, block reason, pending objects and alerts |
| POST | `/v1/control/initialize` | Initialize a new empty bucket once |
| POST | `/v1/control/reconcile` | Refresh analytics and retry alert delivery |
| POST | `/v1/control/lock` | Stop billable operations manually |
| POST | `/v1/control/unlock` | Clear the manual lock; quota and analytics checks still apply |

Storage calls use the separate `STORAGE_TOKEN` on
`/v1/objects/<base64url-encoded UTF-8 key>`. GET reads, HEAD returns metadata,
PUT creates a new immutable object, and DELETE removes an object.
Only `artworks/` and `artwork-variants/` keys are accepted. PUT requires
Content-Length and accepts at most 10 MiB. Multipart uploads, object listing,
and signed/public download URLs are not exposed.

## References

- [R2 operations and pricing](https://developers.cloudflare.com/r2/pricing/)
- [R2 account analytics](https://developers.cloudflare.com/r2/platform/metrics-analytics/)
- [Durable Objects free allowances](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [Workers free allowances](https://developers.cloudflare.com/workers/platform/pricing/)
- [KV consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/)

## Email alerts with Resend

Email is supported as an alternative to the generic webhook. When
`RESEND_API_KEY`, `ALERT_EMAIL_FROM`, and `ALERT_EMAIL_TO` are configured,
email takes priority. The configured sender is
`alerts@notify.kaancinar.com`; the recipient is `akcinar99@gmail.com`.

Create a sending-only Resend key restricted to `notify.kaancinar.com`.
Store it as the Worker secret `RESEND_API_KEY`, never in committed config
or chat. For local testing, use the ignored `.dev.vars` file instead.
Do not use `wrangler secret put` before the deployment is ready: it deploys
a new Worker version.

Email uses the same durable retry queue as webhooks. A successful API response
means Resend accepted the email, not that it arrived in the inbox. The stable
alert ID is also sent as an idempotency key; Resend's deduplication window is
finite, so delayed retries may still produce duplicates. Verify inbox delivery
before relying on notifications. No real email was sent by automated tests.

## Unconfirmed renewal hour: conservative hold

Workers Free and an R2 renewal date of December 10 were confirmed by the owner.
The dashboard does not expose the hour. Current configuration therefore uses
`2026-11-10T00:00:00.000Z` as an initial accounting lower bound (before this new
account and bucket existed), with `BILLING_RESET_CONFIRMED=false`. This is not
an assertion that billing resets at midnight.

At December 10 00:00 UTC, billable gateway access stops with
`billing_review_required`. All counters, snapshots, objects and pending alerts
remain intact, and one review alert is queued. Manual unlock does not bypass
this hold. Authorized deletes remain available. This deliberately favors
quota protection over availability, even if substantial allowance remains.

There is no automatic recovery from this hold in the unconfirmed mode. Verify
the actual allowance boundary before enabling automatic rollover; if its hour
differs from the persisted anchor, a separately reviewed state migration is
required. Changing the anchor directly is rejected. Do not delete the ledger
to reset usage. Reconciliation continues to use the retained accounting window;
if Cloudflare rejects that older window, the gateway also remains blocked.

## First deployment

- Worker: `kaan-gallery-r2-gateway`
- URL: https://kaan-gallery-r2-gateway.kaan-gallery-r2-gateway.workers.dev
- Version: `057d7dca-33b0-4100-a5f8-9d4977054e18`
- Schedule: every 15 minutes
- Four secrets uploaded with the deployment; no secret values are documented.
- Live initialization and account analytics reconciliation succeeded. Anonymous
  callers and storage credentials receive 403 on control routes. Authenticated
  requests for missing images return 404. The ledger reports no block.
- Artwork import is complete; the local Django app is now configured to use the gateway.

### Live storage verification

A temporary one-pixel PNG was uploaded through the authenticated gateway,
read back byte-for-byte, checked with HEAD, and deleted. An overwrite attempt
returned 409; reading after deletion returned 404. Stored-byte accounting
returned to zero, with no pending uploads or active block. This test consumed
one Class A write and one Class B read, in addition to initialization and
account activity. Artwork import was subsequently completed; local Django activation was subsequently completed.

## Copy existing local media

From the repository root, inventory the originals referenced by `ArtworkImage`
and each image's current card/detail/share variants:

```bash
./.venv/bin/python manage.py import_artwork_storage --report /tmp/kaan-media-inventory.json
```

Missing, unsafe or oversized files stop the entire preflight before any remote
request. Only DB-referenced originals and the currently selected protected or
unprotected variants are copied; orphan files and obsolete variants are excluded.
The optional report includes paths, sizes and SHA-256 hashes, never secrets.

```bash
./.venv/bin/python manage.py import_artwork_storage --upload \
  --gateway-url https://kaan-gallery-r2-gateway.kaan-gallery-r2-gateway.workers.dev \
  --token-file cloudflare/r2-gateway/.dev.vars \
  --report /tmp/kaan-media-inventory.json
```

The token file must have private permissions (`chmod 600`). Uploads preserve
exact keys and never use automatic filename replacement. Existing remote files
are downloaded and compared by SHA-256. A mismatch stops the import without
overwriting it. Failed runs can be resumed with the same command: already
matching files are verified and skipped. Every verification consumes a read;
a retry may consume additional operation reservations. Run while media edits
are paused; do not switch storage until the final inventory is verified.
Neither local files nor database rows are modified. This command does not
activate gateway storage in Django.

### Completed import — November 10, 2026

All 124 referenced files (79,113,408 bytes; 80,129,216 bytes with metadata
reservations) were uploaded and verified by SHA-256. The local inventory report
is `/tmp/kaan-media-inventory.json` and the run log is `/tmp/kaan-media-import.log`;
these temporary files are not durable backups. Original local media and DB keys
are unchanged. All 160 backend tests passed.

An isolated Django process selected the gateway and passed eight live endpoint
checks: card/detail/share images for protected and unprotected published works,
public access to an unprotected original, and 404 for a protected original.
That initial verification did not change the running app's storage selection; local activation was completed afterward. Initial live import also
revealed Cloudflare error 1010 for Python's default client identifier; the
adapter now identifies itself as `KaanGallery-Storage/1.0`.

## Local Django activation

The root `.artwork-storage.json` now selects gateway storage for this workstation.
It contains only `url` and the storage `token`, is Git-ignored, and has mode 600.
No control, analytics or Resend key is copied into this file. Environment
`ARTWORK_GATEWAY_URL` takes precedence over the local file; deployments should
set both `ARTWORK_GATEWAY_URL` and `ARTWORK_GATEWAY_TOKEN` as server-side settings.
Nothing goes into frontend variables. Other checkouts without either configuration
continue to use filesystem storage.

The local runserver reloaded, and real HTTP requests for card/detail/share images
returned 200 with matching bytes. All 160 backend tests passed with this local
configuration present; test storage remains isolated.

For a local rollback, stop Django, move `.artwork-storage.json` outside the
repository (keep it private), unset both gateway environment variables if set,
and restart. This restores access to the retained local snapshot only. New or
changed images uploaded after gateway activation must be copied back before a
filesystem rollback; local media is not automatically synchronized from R2.
The website currently live at kaancinar.com was not redeployed or changed.

## Authenticated card cache experiment

Wrangler declares `media.kaancinar.com` as a custom domain and keeps the
existing `workers.dev` endpoint available. Before deploying, verify the
hostname is available in the Worker's Cloudflare zone. Run `npm test` from
this directory, then `npm run deploy` when ready to attach the domain.

Caching is disabled by default. For a baseline on the new hostname, deploy
with `CARD_CACHE_ENABLED=false`, point Render's `ARTWORK_GATEWAY_URL` at
`https://media.kaancinar.com`, and run the gallery benchmark. Then set
`CARD_CACHE_ENABLED=true` in Wrangler and redeploy the Worker. Repeat the
benchmark with the same Gunicorn configuration. Inspect `X-Artwork-Cache`
on authenticated gateway responses for `BYPASS`, `MISS`, and `HIT`.
The browser-facing Django response does not forward this header.

Only authenticated card GETs on the configured hostname use this cache.
A ledger HEAD checks object existence and gateway state before cache lookup.
Hits avoid R2 reads but still visit the shared quota object. The cached copy
expires after five minutes, while the response to Django stays `no-store`.
A replacement gets a new ledger generation even if it reuses the object
key. To start with an empty cache, bump `CARD_CACHE_VERSION`. To bypass it,
set `CARD_CACHE_ENABLED=false` and redeploy.
