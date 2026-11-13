# Gallery image delivery investigation

The goal is to make gallery cards appear sooner and reduce repeat R2 reads within the existing free hosting setup. Render keepalive is already configured, so the comparison focuses on the normal image delivery path.

## Current request path

The gallery data contains an image path such as `/artwork-images/6/card`. Once that path is available to the browser, it requests the image separately. Next.js rewrites the request to Django on Render. Django checks publication, chooses the clean or protected card variant, and requests it from the authenticated Cloudflare Worker. The Worker applies the quota ledger before reading R2. Django buffers the full object before returning it through Vercel.

Relevant code lives in the [Next.js rewrites](../frontend/next.config.ts), [Django image view](../items/views.py), [storage adapter](../items/storage_gateway.py), and [Worker](../cloudflare/r2-gateway/src/index.js).

## Options and decision

| Option | Expected effect | Tradeoff |
| --- | --- | --- |
| Cache card bytes in the authenticated Worker | Cache hits skip the R2 read and its quota charge. Django still performs the publication check. | Django still buffers and relays the image. Cache entries are local to each Cloudflare data center. |
| Serve public cards directly from the Worker | Removes Render and Vercel from the image request and lets the Worker stream the object to the browser. The browser still downloads the same image bytes and needs the URL before requesting it. | The Worker needs its own public access checks and traffic controls. Staff previews and originals can keep using Django. |

The proposed order is to record a baseline, test authenticated Worker caching, then use the measurements to decide whether to introduce direct delivery. No change has been deployed as part of this investigation.

For authenticated caching, validate the storage token and current object ledger entry before looking up cached bytes. Cache successful card responses under immutable object keys, use a new key when bytes change, and keep the downstream response private and uncached. Route misses through the existing quota-checked R2 read and expose a cache hit or miss header for verification.

The Render image endpoint already accepts anonymous requests for published cards. Vercel's bot protection covers its own entry point. A public Worker route would move traffic to Cloudflare, where requests still consume Worker capacity even when cache hits save R2 reads. Keep the R2 bucket and the existing storage token private.

## Proposed direct delivery

This is planned work. The [roadmap diagram](../README.md#serve-public-artwork-images-from-cloudflare) shows the proposed request path, starting with public gallery cards.

- **Signed URLs and access checks.** Django would issue one-hour HMAC-signed URLs scoped to an immutable public variant. Before serving either cached or freshly fetched bytes, the Worker would verify the signature, expiry, and current public variant mapping. Staff previews, protected originals, and uploads would keep their authenticated path.
- **Revocation.** Unpublishing or deleting artwork, deleting or replacing an image, or changing image protection must revoke or update the previous public variant mapping. Test previously issued URLs after each change. Cache purge can remove obsolete bytes, while the mapping check prevents stale cached content from granting access. [Cloudflare cache deletion and purge behavior](https://developers.cloudflare.com/workers/reference/how-the-cache-works/)
- **Latency and resource use.** Direct delivery would remove the image relay through Render in Virginia and through Vercel. Edge cache hits could also avoid an R2 read. Offloading would reduce Render bandwidth and Gunicorn work. Render's free instance-hour allowance measures service uptime, so keeping the backend warm would still consume the same instance hours. [Render Free instance hours](https://render.com/docs/free#free-instance-hours)
- **Backend outages.** Already-issued URLs could keep working during a Render restart or Neon outage while valid and while Cloudflare can verify access and serve the image. Fresh gallery metadata and URL issuance would still depend on Django and Neon.
- **Verification.** Compare card time to first byte, time until cards appear, Render bandwidth, and R2 reads across warm and cold edge caches. Test revocation with previously issued URLs, retain quota reservations on cache misses, and apply rate limits to the public Worker route. Use the benchmarks below to compare results.

## Repeatable benchmark

Run this from the same machine and network before and after each change. This makes 10 sequential requests per URL and averages successful image responses.

```sh
for url in \
  'https://arts.kaancinar.com/artwork-images/6/card' \
  'https://kaan-gallery-backend.onrender.com/artwork-images/6/card/'
do
  printf '\n%s\n' "$url"
  for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -LsS --max-time 15 -o /dev/null \
      -w '%{http_code} %{content_type} %{time_starttransfer} %{time_total} %{size_download}\n' \
      "$url"
  done | awk '
    $1 == 200 && $2 ~ /^image\// {
      n++; first += $3; total += $4; bytes += $5
    }
    END {
      if (n) printf "%d/10 successful | avg TTFB %.0f ms | avg full download %.0f ms | avg %.1f KiB\n",
        n, 1000*first/n, 1000*total/n, bytes/n/1024
      else print "No successful image responses"
    }'
done
```

The gallery URL measures the public image path. The Render URL bypasses Vercel and still includes Django and storage. Each curl invocation opens its own connection. Record the date, network, cache state, and response size alongside the averages. When testing Worker caching, record misses and hits separately.

For the visitor experience, open Chrome DevTools → **Network**, disable browser caching, reload, and inspect the same above-the-fold card. Record when the image request starts, its TTFB, and when the download ends. Use a **Performance** recording with screenshots to see when the image first appears. If TTFB dominates, Django's database lookup and storage read can be measured separately with `Server-Timing`.

Single-image curl baseline pending. The initial terminal run failed DNS resolution. The page-one browser baseline is recorded below.

## Page-one browser benchmark

From the repository root, install the frontend dependencies and Playwright Chromium if needed, then run:

```sh
cd frontend
npm ci
npx playwright install chromium
node scripts/measure-gallery-images.mjs https://arts.kaancinar.com/ 5
```

Each run uses a fresh browser context at 1440 × 900. The script starts from navigation and reports the first decoded card, the last decoded card, and each image's download completion when browser resource timing is available. It switches lazy card images to eager loading once it finds them so it can measure the entire page without introducing scroll timing. These numbers measure readiness to display. Use a DevTools filmstrip to measure actual paint or the normal lazy-loading experience. Repeat with the same browser, viewport, network, and gallery page when comparing delivery changes.


### Production baseline · November 11, 2026

Five successful Chromium runs against the live gallery homepage before the proposed delivery changes. Each run measured nine card images using the eager-loading benchmark above. Times are milliseconds from navigation.

| Run | First image decoded | All images decoded |
| --- | ---: | ---: |
| 1 | 2,138 | 4,879 |
| 2 | 2,209 | 4,792 |
| 3 | 2,296 | 4,413 |
| 4 | 2,241 | 4,341 |
| 5 | 2,560 | 4,876 |
| **Mean** | **2,289** | **4,660** |

Per-card results below show **download complete / decode complete**, both measured from navigation.

| Artwork | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Eclipse Vase | 2133 / 2138 | 2479 / 2484 | 2286 / 2296 | 2235 / 2241 | 2617 / 2622 |
| Hanuman Jug | 4862 / 4879 | 2271 / 2285 | 4402 / 4413 | 2265 / 2269 | 2552 / 2560 |
| Delusion Vase | 3663 / 3673 | 2474 / 2478 | 4400 / 4408 | 3774 / 3782 | 4495 / 4500 |
| Snake Pit Vase | 2403 / 2410 | 4402 / 4407 | 2596 / 2605 | 4208 / 4215 | 4864 / 4876 |
| Turtle Dragon | 4380 / 4390 | 2185 / 2209 | 2625 / 2632 | 2257 / 2260 | 4466 / 4471 |
| Mermaid Jug | 2501 / 2508 | 4393 / 4398 | 2947 / 2957 | 3182 / 3186 | 2552 / 2565 |
| Christmas Card | 4034 / 4039 | 4782 / 4792 | 4285 / 4290 | 4331 / 4341 | 2550 / 2560 |
| Crocodile Postcard | 4499 / 4510 | 3660 / 3671 | 4131 / 4142 | 2372 / 2378 | 4396 / 4402 |
| Two Faced | 2134 / 2141 | 4469 / 4472 | 2584 / 2593 | 4071 / 4079 | 4397 / 4406 |

The final image was ready 2.37 seconds after the first on average. Across the 45 observations, decode completion followed download completion by 3–24 ms. The slowest card varied across runs. The elapsed time before download completion includes URL discovery, request scheduling, server response time, and transfer. Capture request start and TTFB in the next run to see which part accounts for the delay, then repeat this benchmark after adding Worker caching.


### Reading the request timings

The benchmark now reports the following phases for each image. Fetch start, request sent, downloaded, and decoded are timestamps relative to navigation. The other columns are durations.

| Column | What it measures |
| --- | --- |
| Fetch start | When the browser starts fetching the image. A late start can reflect URL discovery, lazy loading, or browser scheduling before the fetch begins. |
| Request sent | The browser's Resource Timing `requestStart` timestamp. |
| Pre-request | Fetch start to request start. This can include browser scheduling, DNS, and connection setup. |
| TTFB | Request start to first response byte. Includes network latency and the upstream image delivery path. |
| Transfer | First response byte to download completion. |

If fetch starts late, compare the image request with the document and gallery data in the DevTools waterfall. If TTFB dominates, use server-side timings to break down the Django and Worker hops. Cross-origin responses may hide detailed timings unless the image origin sends a matching `Timing-Allow-Origin` header.


### Production follow-up with request timings

The same live homepage benchmark completed five runs of nine images. The first card was ready in **2,014 ms** on average and all cards were ready in **4,512 ms** on average. These runs are another baseline for the existing delivery path.

| Run | First decoded (ms) | All decoded (ms) |
| --- | ---: | ---: |
| 1 | 2,184 | 4,421 |
| 2 | 2,415 | 4,636 |
| 3 | 1,420 | 4,163 |
| 4 | 2,226 | 4,443 |
| 5 | 1,825 | 4,900 |

Requests started 390–717 ms after navigation. The measured pre-request interval was 0–4 ms, TTFB was 1,011–4,196 ms, and transfer after the first byte was 0–49 ms. In run 3, Eclipse Vase and Turtle Dragon started just 17 ms apart, but their TTFBs were 1,011 and 3,714 ms. Most of the gap accumulated while waiting for the first byte.

Django buffers the complete upstream image before sending its response, so some image transfer already occurs during browser-observed TTFB. The browser timings cannot attribute that wait to Vercel, Django, the Worker, or R2. Add server timings for Django's publication lookup and storage read, then compare individual requests with the nine-card run to see whether concurrent requests amplify the delay.

All times are in milliseconds. Fetch start, request sent, downloaded, and decoded are measured from navigation.

| Run | Artwork | Fetch start | Request sent | Pre-request | TTFB | Transfer | Downloaded | Decoded |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Eclipse Vase | 462 | 462 | 1 | 2493 | 49 | 3004 | 3008 |
| 1 | Hanuman Jug | 503 | 503 | 1 | 1667 | 1 | 2172 | 2184 |
| 1 | Delusion Vase | 503 | 503 | 1 | 1946 | 2 | 2451 | 2461 |
| 1 | Snake Pit Vase | 503 | 503 | 1 | 3900 | 8 | 4411 | 4421 |
| 1 | Turtle Dragon | 503 | 504 | 1 | 1848 | 6 | 2357 | 2365 |
| 1 | Mermaid Jug | 503 | 504 | 1 | 3510 | 10 | 4024 | 4030 |
| 1 | Christmas Card | 503 | 504 | 1 | 3509 | 11 | 4024 | 4039 |
| 1 | Crocodile Postcard | 503 | 504 | 1 | 3816 | 10 | 4330 | 4341 |
| 1 | Two Faced | 503 | 504 | 1 | 1843 | 1 | 2348 | 2356 |
| 2 | Eclipse Vase | 390 | 390 | 0 | 2020 | 1 | 2412 | 2431 |
| 2 | Hanuman Jug | 405 | 405 | 0 | 1998 | 1 | 2404 | 2415 |
| 2 | Delusion Vase | 405 | 405 | 0 | 4196 | 24 | 4625 | 4636 |
| 2 | Snake Pit Vase | 405 | 406 | 0 | 2067 | 11 | 2484 | 2501 |
| 2 | Turtle Dragon | 405 | 406 | 1 | 3923 | 1 | 4330 | 4350 |
| 2 | Mermaid Jug | 405 | 406 | 1 | 1999 | 6 | 2410 | 2423 |
| 2 | Christmas Card | 405 | 406 | 1 | 3842 | 8 | 4256 | 4267 |
| 2 | Crocodile Postcard | 405 | 406 | 1 | 3865 | 12 | 4282 | 4290 |
| 2 | Two Faced | 405 | 406 | 1 | 3066 | 3 | 3475 | 3479 |
| 3 | Eclipse Vase | 396 | 396 | 0 | 1011 | 7 | 1415 | 1420 |
| 3 | Hanuman Jug | 412 | 413 | 1 | 1631 | 2 | 2046 | 2054 |
| 3 | Delusion Vase | 412 | 413 | 1 | 3473 | 29 | 3915 | 3921 |
| 3 | Snake Pit Vase | 412 | 413 | 1 | 1839 | 30 | 2282 | 2304 |
| 3 | Turtle Dragon | 412 | 413 | 1 | 3714 | 26 | 4154 | 4163 |
| 3 | Mermaid Jug | 412 | 413 | 1 | 1774 | 20 | 2207 | 2217 |
| 3 | Christmas Card | 412 | 414 | 1 | 2728 | 9 | 3150 | 3161 |
| 3 | Crocodile Postcard | 412 | 414 | 1 | 3369 | 8 | 3791 | 3796 |
| 3 | Two Faced | 412 | 414 | 2 | 3577 | 0 | 3991 | 3995 |
| 4 | Eclipse Vase | 397 | 397 | 1 | 1811 | 6 | 2214 | 2226 |
| 4 | Hanuman Jug | 425 | 426 | 1 | 3646 | 1 | 4073 | 4083 |
| 4 | Delusion Vase | 426 | 426 | 1 | 3655 | 1 | 4082 | 4091 |
| 4 | Snake Pit Vase | 426 | 427 | 1 | 4003 | 4 | 4433 | 4443 |
| 4 | Turtle Dragon | 426 | 427 | 1 | 3248 | 2 | 3677 | 3686 |
| 4 | Mermaid Jug | 426 | 427 | 1 | 1899 | 1 | 2327 | 2336 |
| 4 | Christmas Card | 426 | 427 | 1 | 2042 | 8 | 2477 | 2487 |
| 4 | Crocodile Postcard | 426 | 427 | 1 | 1788 | 1 | 2216 | 2236 |
| 4 | Two Faced | 426 | 427 | 1 | 3111 | 1 | 3540 | 3548 |
| 5 | Eclipse Vase | 684 | 686 | 1 | 1123 | 6 | 1815 | 1825 |
| 5 | Hanuman Jug | 713 | 715 | 2 | 4168 | 1 | 4883 | 4900 |
| 5 | Delusion Vase | 714 | 715 | 2 | 3858 | 1 | 4574 | 4584 |
| 5 | Snake Pit Vase | 714 | 716 | 2 | 2363 | 3 | 3082 | 3094 |
| 5 | Turtle Dragon | 714 | 716 | 3 | 2157 | 5 | 2878 | 2887 |
| 5 | Mermaid Jug | 714 | 717 | 3 | 2262 | 1 | 2980 | 2988 |
| 5 | Christmas Card | 714 | 717 | 3 | 4161 | 4 | 4882 | 4900 |
| 5 | Crocodile Postcard | 714 | 717 | 4 | 4159 | 2 | 4878 | 4889 |
| 5 | Two Faced | 714 | 717 | 4 | 3035 | 1 | 3753 | 3762 |

### Comparing an isolated image with the page load

After deploying the Django instrumentation to the backend serving the target URL, rerun the page-one benchmark above. Successful card GETs return two durations in `Server-Timing`: `publication` covers the Django lookup and publication filter, and `storage` covers opening the selected variant, including the full upstream read when using the R2 gateway.

Each run prints the per-card timings and compares the first card's URL during the page load with a single uncached browser fetch of that same URL after all cards decode. The single fetch reuses the same browser context and may benefit from warm connections or upstream state, so treat the difference as a diagnostic signal. If the timing columns show “unavailable,” verify that the card response includes the header in DevTools, first on Render and then through Vercel.

### Production comparison before Django timings were available

All five runs succeeded. The first card image decoded in 2,106 ms on average across the page runs, and all nine decoded in 4,705 ms on average.

| Run | First card's TTFB with other cards (ms) | Same card's TTFB in isolation (ms) |
| --- | ---: | ---: |
| 1 | 1,885 | 571 |
| 2 | 991 | 649 |
| 3 | 2,167 | 500 |
| 4 | 1,935 | 694 |
| 5 | 1,375 | 595 |
| **Mean** | **1,671** | **602** |

The isolated request was faster in every run. It always ran after the batch, so the test also allows for warm connections or upstream state. Publication and storage timings were unavailable in every run. Verify the `Server-Timing` header on the deployed Render and Vercel card responses before repeating this comparison.

### Load card images in groups

One proposal is to return three artwork records per backend page and fetch three backend pages sequentially for each nine-card gallery page. This can make the first three records available earlier if the metadata response itself is slow. It also adds two catalog requests, can delay later cards, and needs careful handling of filters, ordering, totals, and partial failures. The image requests can still overlap unless each group explicitly waits before starting the next.

Start by keeping the existing nine-card metadata page and controlling image loading independently. Prioritize the first three visible images, then let the remaining six load as they approach the viewport. If we want to test whether overlapping image requests amplify TTFB, compare the existing eager nine-image benchmark with a variant that allows at most three image requests at a time. Start another image as soon as a slot frees up so one slow card doesn't hold back an entire group.

Compare time to first card, time until the first three cards are ready, and time until all nine are ready. Staging can improve the first row while making the full page slower. The existing browser measurements put image request start at 390–717 ms after navigation and TTFB at 1,011–4,196 ms, so the first experiment should target image scheduling. The previous isolated request ran after the batch, so its lower TTFB alone does not establish that concurrency caused the gap. Revisit this experiment after identifying the source of the production 429.

### Research findings and experiment order

The repository has two places where concurrent requests can wait. The baseline Gunicorn configuration used one threaded worker with four threads, so a burst of nine image requests can exceed its available request slots. The gateway routes callers through a single quota Durable Object. Its request handler holds `blockConcurrencyWhile()` while it loads quota state, reserves usage, and awaits the R2 lookup. It also holds the block during reconciliation and alert delivery. Cloudflare recommends keeping external I/O outside that block and using a storage transaction for atomic read-modify-write operations. These are plausible sources of queueing. The browser measurements cannot tell us how much each contributed. [Cloudflare Durable Object concurrency guidance](https://developers.cloudflare.com/durable-objects/best-practices/rules-of-durable-objects/)

1. **Measure before changing the path.** Resolve the 429 and verify Django's `Server-Timing` header. Compare the same image under isolated and concurrent load with the order varied across runs. If storage time rises with concurrency, instrument the gateway to separate time waiting to enter its handler from quota accounting and the R2 lookup. Django's timings begin after the request reaches the view, so they exclude Gunicorn queueing. [MDN Resource Timing](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceResourceTiming/requestStart)
2. **Keep the likely LCP image eager and discoverable in the HTML.** The gallery already prioritizes the first card. Verify the actual LCP element on desktop and mobile and let offscreen images lazy-load. Compare normal page load and LCP separately from the benchmark that forces all nine images to load. Try a three-request limit as a controlled comparison with the same metadata page. [web.dev LCP optimization](https://web.dev/articles/optimize-lcp)
3. **Test authenticated edge caching with separate hit and miss results.** Use the Cache API on a Worker custom domain or route. Keep access checks ahead of cache hits and preserve the R2 quota reservation on misses. If the hit path still enters the shared Durable Object, measure its wait too. [Cloudflare R2 Cache API example](https://developers.cloudflare.com/r2/examples/cache-api/)
4. **Shorten the quota critical section if it accounts for the delay.** Preserve atomic reservation before any billable read and verify concurrent requests cannot overspend. Test interactions with reconciliation and failures before moving the R2 lookup outside the serialized section. Direct Worker delivery removes Django and Vercel from the image path, but requests will still queue if the same Durable Object serializes their R2 lookups.

### Source of the Gunicorn concurrency limit

The [backend Dockerfile](../Dockerfile#L17) starts Gunicorn with [gunicorn.conf.py](../gunicorn.conf.py#L4), which set one `gthread` worker and four threads for the baseline. The experiment below changes the thread count to nine. Verify the deployed revision and any start-command override before attributing live behavior to these settings. If nine requests reach this process while four threads are occupied, the remaining requests must wait for a slot. Django's publication and storage timers start inside the view, after dispatch. The browser data does not quantify that queue.

### Render caching options

[Render edge caching](https://render.com/docs/web-service-caching) is available for paid web services and [included at no additional feature charge](https://render.com/changelog/edge-caching-for-web-services-is-now-generally-available). The gallery's current image view uses `never_cache`, so enabling edge caching alone would leave these responses uncached. [Render Key Value](https://render.com/pricing) has a free 25 MB tier and paid tiers from $10/month. It is an application datastore. Using it for image bytes would require Django changes and would retain the Gunicorn request path.


### Nine-thread Gunicorn experiment

The experimental configuration uses one worker with nine threads so Gunicorn can service up to nine requests concurrently when the threads are free. The quota Durable Object can still serialize upstream reads. This experiment changes only the Gunicorn concurrency setting. Worker caching remains disabled.

After deploying the backend, run the same five-run browser benchmark from the same network and compare first-image time, all-nine time, and the TTFB for the same card. If available, compare Django storage timing and Render memory and error rates. If the page shows little improvement or resource usage increases materially, restore four threads. Production results are pending.
