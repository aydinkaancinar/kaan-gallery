import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { convertV4MiniflareOptions, Miniflare } from "miniflare";
import { METADATA_RESERVE_BYTES } from "../src/policy.js";

const STORAGE_TOKEN = "storage-test-secret-".padEnd(40, "s");
const CONTROL_TOKEN = "control-test-secret-".padEnd(40, "c");

async function gateway(t, overrides = {}) {
  const now = new Date();
  const anchor = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)).toISOString();
  const remote = { a: 0, b: 0, bytes: 0, fail: false, alertFail: false, alerts: [] };
  const options = {
    name: "gateway",
    modules: [
      { type: "ESModule", path: fileURLToPath(new URL("../src/index.js", import.meta.url)) },
      { type: "ESModule", path: fileURLToPath(new URL("../src/policy.js", import.meta.url)) },
    ],
    compatibilityDate: "2026-11-09",
    compatibilityFlags: ["nodejs_compat"],
    cf: false,
    r2Buckets: ["BUCKET"],
    durableObjects: { QUOTA: { className: "QuotaGate", useSQLite: true } },
    bindings: {
      STORAGE_TOKEN, CONTROL_TOKEN, ANALYTICS_TOKEN: "test-analytics-token",
      ACCOUNT_ID: "a".repeat(32), BILLING_ANCHOR_UTC: anchor,
      CLASS_A_LIMIT: "100", CLASS_B_LIMIT: "100",
      CLASS_A_WARNING: "90", CLASS_B_WARNING: "90",
      STORAGE_LIMIT_BYTES: "1000000", STORAGE_WARNING_BYTES: "900000",
      ALERT_WEBHOOK_URL: "https://alerts.example.test/quota",
      ...overrides,
    },
    outboundService: async (request) => {
      const host = new URL(request.url).hostname;
      if (host === "api.resend.com") {
        remote.emailHeaders = Object.fromEntries(request.headers);
        remote.emails ??= [];
        remote.emails.push(await request.json());
        return remote.alertFail ? new Response(null, { status: 503 }) : Response.json({ id: "test-email" });
      }
      if (host === "alerts.example.test") {
        if (remote.alertFail) return new Response(null, { status: 503 });
        remote.alerts.push(await request.json());
        return new Response(null, { status: 204 });
      }
      assert.equal(host, "api.cloudflare.com", "Tests must never access external services.");
      if (remote.fail) return new Response(null, { status: 503 });
      return Response.json({ data: { viewer: { accounts: [{
        r2OperationsAdaptiveGroups: [
          { sum: { requests: remote.a }, dimensions: { actionType: "PutObject" } },
          { sum: { requests: remote.b }, dimensions: { actionType: "GetObject" } },
        ],
        r2StorageAdaptiveGroups: [{ max: { payloadSize: remote.bytes, metadataSize: 0 },
          dimensions: { bucketName: "test", datetime: new Date().toISOString() } }],
      }] } } });
    },
  };
  const mf = new Miniflare(convertV4MiniflareOptions(options));
  t.after(() => mf.dispose());
  await mf.ready;
  const request = (path, method = "GET", body, token = STORAGE_TOKEN) => mf.dispatchFetch(
    `https://gateway.example.test${path}`,
    { method, body, headers: { Authorization: `Bearer ${token}`,
      ...(body !== undefined ? { "Content-Length": String(Buffer.byteLength(body)), "Content-Type": "image/png" } : {}) } },
  );
  const control = (action, method = "POST") => request(`/v1/control/${action}`, method, undefined, CONTROL_TOKEN);
  const path = (key = "artworks/test.png") => `/v1/objects/${Buffer.from(key).toString("base64url")}`;
  const status = async () => (await control("status", "GET")).json();
  const initialize = async () => {
    const response = await control("initialize");
    assert.equal(response.status, 200, await response.text());
  };
  const setBindings = (bindings) => mf.setOptions(convertV4MiniflareOptions({
    ...options, bindings: { ...options.bindings, ...bindings },
  }));
  return { mf, remote, request, control, path, status, initialize, setBindings };
}

test("unauthenticated calls and storage credentials cannot access controls", async (t) => {
  const g = await gateway(t);
  assert.equal((await g.request(g.path(), "GET", undefined, "wrong")).status, 403);
  assert.equal((await g.request("/v1/control/initialize", "POST")).status, 403);
  assert.equal((await g.status()).usage.a, 0);
  assert.equal((await g.request(g.path())).status, 503);
});

test("initialization rejects a nonempty bucket and cannot reset counters", async (t) => {
  const g = await gateway(t);
  const bucket = await g.mf.getR2Bucket("BUCKET");
  await bucket.put("artworks/external.png", "external");
  assert.equal((await g.control("initialize")).status, 409);
  assert.equal((await g.status()).initialized, false);
  await bucket.delete("artworks/external.png");
  await g.initialize();
  const before = (await g.status()).usage.a;
  assert.equal((await g.control("initialize")).status, 409);
  assert.equal((await g.status()).usage.a, before);
});

test("normal upload, metadata, read, and delete use the durable ledger", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  assert.equal((await g.request(g.path(), "PUT", "image")).status, 201);
  assert.equal((await g.request(g.path(), "PUT", "replacement")).status, 409);
  const metadata = await g.request(g.path(), "HEAD");
  assert.equal(metadata.status, 200);
  assert.equal(metadata.headers.get("Content-Length"), "5");
  assert.equal((await g.status()).usage.b, 0);
  const image = await g.request(g.path());
  assert.equal(await image.text(), "image");
  assert.match(image.headers.get("Cache-Control"), /no-store/);
  assert.equal((await g.status()).usage.b, 1);
  assert.equal((await g.request(g.path(), "DELETE")).status, 204);
  assert.equal((await g.status()).usage.bytes, 0);
  assert.equal((await g.request(g.path())).status, 404);
});

test("concurrent reads reserve before touching R2 and cannot exceed the limit", async (t) => {
  const g = await gateway(t, { CLASS_B_LIMIT: "2", CLASS_B_WARNING: "1" });
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  const responses = await Promise.all(Array.from({ length: 12 }, () => g.request(g.path())));
  assert.equal(responses.filter((response) => response.status === 200).length, 2);
  assert.equal(responses.filter((response) => response.status === 429).length, 10);
  assert.equal((await g.status()).usage.b, 2);
  assert.equal((await g.request(g.path(), "DELETE")).status, 204);
});

test("concurrent writes stop at the Class A budget", async (t) => {
  const g = await gateway(t, { CLASS_A_LIMIT: "3", CLASS_A_WARNING: "2" });
  await g.initialize(); // Initialization itself reserves one Class A list operation.
  const responses = await Promise.all(Array.from({ length: 10 }, (_, i) =>
    g.request(g.path(`artworks/${i}.png`), "PUT", "image")));
  assert.equal(responses.filter((response) => response.status === 201).length, 2);
  assert.equal((await g.status()).usage.a, 3);
});

test("storage reservation includes metadata and rejects over-budget writes", async (t) => {
  const capacity = METADATA_RESERVE_BYTES + 5;
  const g = await gateway(t, {
    STORAGE_LIMIT_BYTES: String(capacity), STORAGE_WARNING_BYTES: String(capacity - 1),
  });
  await g.initialize();
  assert.equal((await g.request(g.path(), "PUT", "image")).status, 201);
  assert.equal((await g.request(g.path("artworks/second.png"), "PUT", "image")).status, 429);
  assert.equal((await g.status()).usage.bytes, capacity);
  await g.request(g.path(), "DELETE");
  assert.equal((await g.request(g.path("artworks/second.png"), "PUT", "image")).status, 201);
});

test("analytics failure stops billable operations and recovery resumes them", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  const before = await g.status();
  g.remote.fail = true;
  assert.equal((await g.control("reconcile")).status, 503);
  assert.equal((await g.request(g.path())).status, 503);
  assert.equal((await g.status()).usage.b, before.usage.b);
  g.remote.fail = false;
  assert.equal((await g.control("reconcile")).status, 200);
  assert.equal((await g.request(g.path())).status, 200);
});

test("account analytics include usage outside the gateway", async (t) => {
  const g = await gateway(t, { CLASS_B_LIMIT: "3", CLASS_B_WARNING: "2" });
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  g.remote.b = 3;
  await g.control("reconcile");
  assert.equal((await g.request(g.path())).status, 429);
  assert.equal((await g.status()).usage.b, 3);
});

test("delayed analytics cannot reduce consumed operation budgets", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  g.remote.b = 3;
  await g.control("reconcile");
  await g.request(g.path());
  assert.equal((await g.status()).usage.b, 4);
  g.remote.b = 0;
  await g.control("reconcile");
  assert.equal((await g.status()).usage.b, 4);
});

test("operation reservations survive Durable Object eviction", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  await (await g.request(g.path())).text();
  const before = await g.status();
  await g.mf.unsafeEvictDurableObject("gateway", "QuotaGate", { name: "account-r2-quota-v1" });
  assert.deepEqual((await g.status()).usage, before.usage);
});

test("changing the billing anchor cannot reset an existing ledger", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  const now = new Date();
  const differentAnchor = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 1)).toISOString();
  await g.setBindings({ BILLING_ANCHOR_UTC: differentAnchor });
  assert.equal((await g.control("status", "GET")).status, 503);
});

test("an unexpected existing object keeps its reservation and locks the gateway", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  const bucket = await g.mf.getR2Bucket("BUCKET");
  await bucket.put("artworks/test.png", "external");
  assert.equal((await g.request(g.path(), "PUT", "image")).status, 503);
  const state = await g.status();
  assert.equal(state.blocked, "manual_lock");
  assert.equal(state.pendingObjects, 1);
  assert.equal(state.usage.a, 2);
  assert.equal(state.usage.bytes, 5 + METADATA_RESERVE_BYTES);
  assert.equal(await (await bucket.get("artworks/test.png")).text(), "external");
  assert.equal((await g.request(g.path(), "DELETE")).status, 204);
  await g.control("unlock");
  assert.equal((await g.status()).pendingObjects, 0);
  assert.equal((await g.status()).usage.bytes, 0);
});

test("manual lock is immediate and cannot be bypassed with unlock when quota is exhausted", async (t) => {
  const g = await gateway(t, { CLASS_B_LIMIT: "1", CLASS_B_WARNING: "1" });
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  await g.control("lock");
  assert.equal((await g.request(g.path())).status, 503);
  await g.control("unlock");
  assert.equal((await g.request(g.path())).status, 200);
  await g.control("unlock");
  assert.equal((await g.request(g.path())).status, 429);
});

test("warning delivery retries failures and records each event once", async (t) => {
  const g = await gateway(t, { CLASS_B_LIMIT: "3", CLASS_B_WARNING: "1" });
  await g.initialize();
  await g.request(g.path(), "PUT", "image");
  await g.request(g.path());
  assert.equal((await g.status()).pendingAlerts, 1);
  g.remote.alertFail = true;
  await g.control("reconcile");
  assert.equal((await g.status()).pendingAlerts, 1);
  g.remote.alertFail = false;
  await g.control("reconcile");
  assert.equal(g.remote.alerts.length, 1);
  assert.equal((await g.status()).pendingAlerts, 0);
  await g.control("reconcile");
  assert.equal(g.remote.alerts.length, 1);
});

test("invalid keys are rejected before any R2 operation", async (t) => {
  const g = await gateway(t);
  await g.initialize();
  const before = await g.status();
  assert.equal((await g.request(g.path("artworks/../private.png"), "PUT", "image")).status, 400);
  assert.equal((await g.request(g.path("other/test.png"), "PUT", "image")).status, 400);
  assert.deepEqual((await g.status()).usage, before.usage);
});


test("Resend email alerts retry failures and preserve an idempotency key", async (t) => {
  const g = await gateway(t, { RESEND_API_KEY: "test-resend-secret",
    ALERT_EMAIL_FROM: "alerts@notify.kaancinar.com", ALERT_EMAIL_TO: "akcinar99@gmail.com" });
  await g.initialize();
  g.remote.b = 91;
  g.remote.alertFail = true;
  await g.control("reconcile");
  assert.ok((await g.status()).pendingAlerts > 0);
  const key = g.remote.emailHeaders["idempotency-key"];
  assert.equal(g.remote.emailHeaders.authorization, "Bearer test-resend-secret");
  assert.equal(g.remote.emails[0].from, "alerts@notify.kaancinar.com");
  assert.deepEqual(g.remote.emails[0].to, ["akcinar99@gmail.com"]);
  assert.match(g.remote.emails[0].text, /kaan-gallery-media/);
  g.remote.alertFail = false;
  await g.control("reconcile");
  assert.equal(g.remote.emailHeaders["idempotency-key"], key);
  assert.equal((await g.status()).pendingAlerts, 0);
  assert.equal((await g.status()).emailConfigured, true);
  assert.equal(g.remote.alerts.length, 0);
});

test("authenticated card cache skips R2 and respects deletion and replacement", async (t) => {
  const g = await gateway(t, {
    CARD_CACHE_ENABLED: "true", CARD_CACHE_HOST: "gateway.example.test",
  });
  await g.initialize();
  const path = g.path(`artwork-variants/v1/${"a".repeat(64)}/card.webp`);
  assert.equal((await g.request(path, "PUT", "old")).status, 201);

  const miss = await g.request(path);
  assert.equal(miss.headers.get("X-Artwork-Cache"), "MISS");
  assert.equal(await miss.text(), "old");
  await g.mf.getCaches().then(async (caches) => {
    const cache = caches.default;
    const url = `https://gateway.example.test/__card-cache/v1/${encodeURIComponent(`artwork-variants/v1/${"a".repeat(64)}/card.webp`)}/${encodeURIComponent(miss.headers.get("ETag"))}`;
    for (let attempt = 0; attempt < 50; attempt++) {
      if (await cache.match(url)) return;
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
    assert.fail("Card was not written to cache");
  });

  assert.equal((await g.request(path, "GET", undefined, "wrong")).status, 403);
  const hit = await g.request(path);
  assert.equal(hit.headers.get("X-Artwork-Cache"), "HIT");
  assert.equal(hit.headers.get("Cache-Control"), "private, no-store");
  assert.equal(await hit.text(), "old");
  assert.equal((await g.status()).usage.b, 1);

  assert.equal((await g.request(path, "DELETE")).status, 204);
  assert.equal((await g.request(path)).status, 404);
  assert.equal((await g.request(path, "PUT", "new")).status, 201);
  const replacement = await g.request(path);
  assert.equal(replacement.headers.get("X-Artwork-Cache"), "MISS");
  assert.equal(await replacement.text(), "new");

  await g.setBindings({ CARD_CACHE_ENABLED: "false" });
  const bypass = await g.request(path);
  assert.equal(bypass.headers.get("X-Artwork-Cache"), "BYPASS");
  assert.equal(await bypass.text(), "new");
  assert.equal((await g.status()).usage.b, 3);
});
