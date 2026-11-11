# Render public-read limits

The Vercel firewall protects `arts.kaancinar.com`, but the Render backend also
has its own public `onrender.com` address. Django now applies a small limit
before serving anonymous catalog data or opening an image through R2. See
[the middleware](../items/public_read_limit.py) and
[production settings](../config/settings_production.py).

| Route | Per client | Total, per app process |
| --- | ---: | ---: |
| `/artwork-images/…` | 240/minute | 1,200/minute |
| `/items/…`, `/artworks/…`, `/artists/…` | 120/minute | 600/minute |

The limits count GET and HEAD, including requests for nonexistent resources.
Excess requests return HTTP 429 with `Retry-After` and `Cache-Control: no-store`.
Health checks, admin/login paths, and staff with a verified MFA session are
outside these public-read limits. Axes still handles failed password attempts.

Render documents that its proxy supplies the client address first in
`X-Forwarded-For`; production uses that address after validation. Local settings
use the socket address instead. Render's own edge handles large network floods,
while these limits reduce application and R2 work from repeated reads.

These counters use Django's in-process memory cache. The current Free service
runs one Gunicorn worker, but counters reset on restart and do not share across
future service instances. Move them to a shared, atomic store before scaling.
Vercel's outbound requests may share a source address at Render, so watch for
429s during normal browsing and tune with observed traffic. These limits do
not make the Render address private, and distributed clients can still consume
the aggregate allowance. The private R2 quota gateway remains the final cutoff.

The focused tests are in [test_public_read_limit.py](../items/tests/test_public_read_limit.py).
After deployment, verify the gallery and image viewer on the public domain,
then inspect Render logs for 429s and the R2 quota alerts. Avoid sending a
large burst to production merely to demonstrate the limit.
