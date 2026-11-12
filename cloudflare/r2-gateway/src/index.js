import { timingSafeEqual } from "node:crypto";
import {
  billingPeriod, MAX_METRICS_AGE_MS, MAX_OBJECT_BYTES, METADATA_RESERVE_BYTES,
  objectKey, parseAnalytics, quotaPolicy,
} from "./policy.js";

const encoder = new TextEncoder();
const GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql";
const ANALYTICS_QUERY = `
query GalleryQuota($account: string!, $start: Time!, $end: Time!, $storageStart: Time!) {
  viewer { accounts(filter: {accountTag: $account}) {
    r2OperationsAdaptiveGroups(limit: 256, filter: {datetime_geq: $start, datetime_leq: $end}) {
      sum { requests } dimensions { actionType }
    }
    r2StorageAdaptiveGroups(limit: 256, filter: {datetime_geq: $storageStart, datetime_leq: $end}) {
      max { payloadSize metadataSize } dimensions { bucketName }
    }
  }}
}`;

function reply(status, body, headers = {}) {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff", ...headers },
  });
}

function authorized(request, secret) {
  if (typeof secret !== "string" || secret.length < 32) return false;
  const supplied = encoder.encode(request.headers.get("Authorization") ?? "");
  const expected = encoder.encode(`Bearer ${secret}`);
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

function quotaStub(env) {
  return env.QUOTA.get(env.QUOTA.idFromName("account-r2-quota-v1"));
}

async function readCard(request, env, ctx, quota) {
  const url = new URL(request.url);
  let key;
  try { key = objectKey(url.pathname); }
  catch { return quota.fetch(request); }

  if (!/^artwork-variants\/[^/]+\/[a-f0-9]{64}\/card\.webp$/.test(key)) {
    return quota.fetch(request);
  }
  if (env.CARD_CACHE_ENABLED !== "true" || url.hostname !== env.CARD_CACHE_HOST) {
    const upstream = await quota.fetch(request);
    const response = new Response(upstream.body, upstream);
    response.headers.set("X-Artwork-Cache", "BYPASS");
    return response;
  }

  // HEAD checks the ledger and gateway state without an R2 operation.
  const metadata = await quota.fetch(new Request(request.url, { method: "HEAD" }));
  if (!metadata.ok) return metadata;

  const generation = metadata.headers.get("ETag");
  const cacheUrl = new URL(request.url);
  cacheUrl.pathname = `/__card-cache/${encodeURIComponent(env.CARD_CACHE_VERSION || "v1")}/${encodeURIComponent(key)}/${encodeURIComponent(generation)}`;
  cacheUrl.search = "";
  const cacheKey = new Request(cacheUrl);
  const cache = caches.default;
  const hit = await cache.match(cacheKey).catch(() => undefined);
  if (hit) {
    const response = new Response(hit.body, { headers: metadata.headers });
    response.headers.set("X-Artwork-Cache", "HIT");
    return response;
  }

  const upstream = await quota.fetch(request);
  const response = new Response(upstream.body, upstream);
  if (response.ok && generation && response.headers.get("ETag") === generation) {
    const copy = new Response(response.clone().body, response);
    copy.headers.set("Cache-Control", "public, max-age=300");
    ctx.waitUntil(cache.put(cacheKey, copy).catch(() => {}));
  }
  response.headers.set("X-Artwork-Cache", "MISS");
  return response;
}

export default {
  async fetch(request, env, ctx) {
    const path = new URL(request.url).pathname;
    const control = path.startsWith("/v1/control/");
    if (!authorized(request, control ? env.CONTROL_TOKEN : env.STORAGE_TOKEN)) {
      return reply(403, { error: "Forbidden" });
    }
    if (!control && !path.startsWith("/v1/objects/")) return reply(404, { error: "Not found" });
    if (!env.STORAGE_TOKEN || env.STORAGE_TOKEN === env.CONTROL_TOKEN) {
      return reply(503, { error: "Separate storage and control secrets are required." });
    }
    try {
      const quota = quotaStub(env);
      if (!control && request.method === "GET") return await readCard(request, env, ctx, quota);
      return await quota.fetch(request);
    } catch {
      return reply(503, { error: "Storage gateway unavailable." }, { "Retry-After": "900" });
    }
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(quotaStub(env).fetch(new Request("https://quota.internal/tick", { method: "POST" })));
  },
};

export class QuotaGate {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
  }

  async fetch(request) {
    // Serialize reservation, R2 operation, and ledger update across all callers.
    return this.ctx.blockConcurrencyWhile(async () => {
      try {
        const policy = quotaPolicy(this.env);
        const state = await this.loadState();
        const path = new URL(request.url).pathname;
        if (path === "/tick" || path === "/v1/control/reconcile") {
          if (request.method !== "POST") return reply(405, { error: "Method not allowed" });
          await this.reconcile(state, policy);
          await this.deliverAlerts(state);
          return reply(state.analyticsError ? 503 : 200, this.status(state, policy));
        }
        if (path.startsWith("/v1/control/")) return await this.control(request, state, policy);
        return await this.object(request, state, policy);
      } catch {
        return reply(503, { error: "Storage operation unavailable." }, { "Retry-After": "900" });
      }
    });
  }

  async loadState() {
    const period = billingPeriod(this.env.BILLING_ANCHOR_UTC);
    const anchor = new Date(this.env.BILLING_ANCHOR_UTC).toISOString();
    let state = await this.ctx.storage.get("state");
    if (!state) {
      state = { initialized: false, anchor, period, used: { a: 0, b: 0, bytes: 0 },
        pendingObjects: 0, manualLock: false, alerts: {}, checkedAt: 0 };
    }
    if (state.anchor !== anchor) throw new Error("The persisted billing anchor cannot be changed.");
    if (state.period.start !== period.start && this.env.BILLING_RESET_CONFIRMED !== "true") {
      // Preserve the original analytics window and every reservation when the
      // billing date is only an estimate. Never replenish quota automatically.
      if (!state.billingReviewRequired) {
        state.billingReviewRequired = true;
        this.addAlert(state, "billing_review_required", "account");
        await this.ctx.storage.put("state", state);
      }
      return state;
    }
    if (state.period.start !== period.start) {
      state = { ...state, period, used: { a: 0, b: 0, bytes: state.used.bytes },
        alerts: Object.fromEntries(Object.entries(state.alerts).filter(([, alert]) => !alert.delivered)),
        checkedAt: 0, snapshot: null, analyticsError: null, billingReviewRequired: false };
      await this.ctx.storage.put("state", state);
    }
    return state;
  }

  effective(state) {
    const usage = { ...state.used };
    if (state.snapshot) {
      for (const metric of ["a", "b", "bytes"]) {
        const sinceSnapshot = Math.max(0, state.used[metric] - state.snapshot.local[metric]);
        usage[metric] = Math.max(usage[metric], state.snapshot.observed[metric] + sinceSnapshot);
      }
    }
    return usage;
  }

  blockedReason(state, policy) {
    if (!state.initialized) return "not_initialized";
    if (state.billingReviewRequired) return "billing_review_required";
    if (state.manualLock) return "manual_lock";
    if (state.analyticsError || Date.now() - state.checkedAt > MAX_METRICS_AGE_MS) {
      return "analytics_unavailable";
    }
    const used = this.effective(state);
    return ["a", "b", "bytes"].find((metric) => used[metric] >= policy.limits[metric]) ?? null;
  }

  status(state, policy) {
    return { initialized: state.initialized, period: state.period,
      usage: this.effective(state), limits: policy.limits, warnings: policy.warnings,
      blocked: this.blockedReason(state, policy), checkedAt: state.checkedAt,
      pendingObjects: state.pendingObjects,
      billingResetConfirmed: this.env.BILLING_RESET_CONFIRMED === "true",
      billingReviewRequired: Boolean(state.billingReviewRequired),
      pendingAlerts: Object.values(state.alerts).filter((alert) => !alert.delivered).length,
      webhookConfigured: Boolean(this.env.ALERT_WEBHOOK_URL),
      emailConfigured: Boolean(this.env.RESEND_API_KEY && this.env.ALERT_EMAIL_FROM && this.env.ALERT_EMAIL_TO) };
  }

  addAlert(state, kind, metric) {
    const id = `${state.period.start}:${kind}:${metric}`;
    state.alerts[id] ??= { id, kind, metric, period: state.period,
      usage: this.effective(state), createdAt: new Date().toISOString(), delivered: false };
  }

  async save(state, policy, entries = {}) {
    const usage = this.effective(state);
    for (const metric of ["a", "b", "bytes"]) {
      if (usage[metric] >= policy.warnings[metric]) this.addAlert(state, "quota_warning", metric);
      if (usage[metric] >= policy.limits[metric]) this.addAlert(state, "quota_blocked", metric);
    }
    await this.ctx.storage.put({ state, ...entries });
  }

  deny(state, policy) {
    const reason = this.blockedReason(state, policy);
    if (!reason) return null;
    const status = ["a", "b", "bytes"].includes(reason) ? 429 : 503;
    const wait = Math.min(86400, Math.max(1, Math.ceil((Date.parse(state.period.end) - Date.now()) / 1000)));
    return reply(status, { error: "Storage temporarily unavailable.", reason }, {
      "Retry-After": status === 429 ? String(wait) : "900",
    });
  }

  async reconcile(state, policy) {
    try {
      if (!/^[a-f0-9]{32}$/.test(this.env.ACCOUNT_ID ?? "") || !this.env.ANALYTICS_TOKEN) {
        throw new Error("Analytics configuration required.");
      }
      const now = new Date();
      const response = await fetch(GRAPHQL_URL, {
        method: "POST",
        headers: { Authorization: `Bearer ${this.env.ANALYTICS_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({ query: ANALYTICS_QUERY, variables: {
          account: this.env.ACCOUNT_ID, start: state.period.start, end: now.toISOString(),
          storageStart: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString(),
        } }),
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("Analytics request failed.");
      const observed = parseAnalytics(await response.json());
      const previous = this.effective(state);
      // Delayed or revised analytics must never refund operation reservations.
      observed.a = Math.max(observed.a, previous.a);
      observed.b = Math.max(observed.b, previous.b);
      state.snapshot = { observed, local: { ...state.used } };
      state.checkedAt = Date.now();
      state.analyticsError = null;
    } catch {
      state.analyticsError = true;
      this.addAlert(state, "analytics_unavailable", "account");
    }
    await this.save(state, policy);
  }

  async deliverAlerts(state) {
    const pending = Object.values(state.alerts).filter((alert) => !alert.delivered).slice(0, 3);
    if (!pending.length) return;
    const email = Boolean(this.env.RESEND_API_KEY && this.env.ALERT_EMAIL_FROM && this.env.ALERT_EMAIL_TO);
    const destination = email ? "https://api.resend.com/emails" : this.env.ALERT_WEBHOOK_URL;
    if (!destination || !destination.startsWith("https://")) {
      console.warn("Quota alerts pending; configure email or an HTTPS webhook and verify delivery.");
      return;
    }
    for (const alert of pending) {
      try {
        const response = await fetch(destination, {
          method: "POST", headers: { "Content-Type": "application/json",
            ...(email ? { Authorization: `Bearer ${this.env.RESEND_API_KEY}`,
              "Idempotency-Key": `r2-quota/${alert.id}` } : {}) },
          body: JSON.stringify(email ? {
            from: this.env.ALERT_EMAIL_FROM, to: [this.env.ALERT_EMAIL_TO],
            subject: `Kaan Gallery: ${["quota_blocked", "billing_review_required"].includes(alert.kind) ? "storage access stopped" : "storage quota warning"} (${alert.metric})`,
            text: `R2 quota notification for kaan-gallery-media.\n\n${JSON.stringify(alert, null, 2)}\n\nReview gateway status before changing limits or unlocking access.`,
          } : alert), signal: AbortSignal.timeout(3000),
          redirect: "manual",
        });
        if (response.ok) {
          alert.delivered = true;
          await this.ctx.storage.put("state", state);
        }
      } catch {
        console.warn("Quota alert delivery failed; retained for retry.");
      }
    }
  }

  async control(request, state, policy) {
    const path = new URL(request.url).pathname;
    if (path === "/v1/control/status" && request.method === "GET") {
      return reply(200, this.status(state, policy));
    }
    if (request.method !== "POST") return reply(405, { error: "Method not allowed" });
    if (path === "/v1/control/lock" || path === "/v1/control/unlock") {
      state.manualLock = path.endsWith("/lock");
      await this.save(state, policy);
      return reply(200, this.status(state, policy));
    }
    if (path !== "/v1/control/initialize") return reply(404, { error: "Not found" });
    if (state.initialized) return reply(409, { error: "Already initialized; counters cannot be reset." });
    await this.reconcile(state, policy);
    if (state.analyticsError) return reply(503, { error: "Analytics configuration or availability failed." });
    const used = this.effective(state);
    if (used.a + 1 > policy.limits.a || used.b >= policy.limits.b || used.bytes >= policy.limits.bytes) {
      return reply(429, { error: "Account quota already reached." });
    }
    state.used.a += 1;
    await this.save(state, policy);
    const listing = await this.env.BUCKET.list({ limit: 1 });
    if (listing.objects.length || listing.truncated) {
      return reply(409, { error: "Initialization requires an empty bucket." });
    }
    state.initialized = true;
    await this.save(state, policy);
    return reply(200, this.status(state, policy));
  }

  async object(request, state, policy) {
    let key;
    try { key = objectKey(new URL(request.url).pathname); }
    catch { return reply(400, { error: "Invalid object key." }); }
    if (!["GET", "HEAD", "PUT", "DELETE"].includes(request.method)) {
      return reply(405, { error: "Method not allowed" });
    }
    const ledgerKey = `object:${key}`;
    const entry = await this.ctx.storage.get(ledgerKey);
    if (request.method === "DELETE" && state.initialized) {
      if (!entry) return reply(204, null);
      // R2 deletes are free; allow cleanup even when billable operations are stopped.
      await this.env.BUCKET.delete(key);
      state.used.bytes -= entry.chargedBytes;
      if (entry.pending) state.pendingObjects -= 1;
      await this.ctx.storage.transaction(async (transaction) => {
        await transaction.delete(ledgerKey);
        await transaction.put("state", state);
      });
      return reply(204, null);
    }
    const denied = this.deny(state, policy);
    if (denied) return denied;
    if (request.method === "PUT") return this.putObject(request, key, ledgerKey, entry, state, policy);
    if (!entry) return reply(404, { error: "Not found" });
    if (entry.pending) return reply(503, { error: "Incomplete upload; cleanup required." });
    const headers = { "Content-Type": entry.contentType, "Content-Length": String(entry.size),
      "Last-Modified": entry.uploaded, "Cache-Control": "private, no-store",
      ETag: `"${entry.generation ?? Date.parse(entry.uploaded)}"`,
      "X-Content-Type-Options": "nosniff" };
    // Metadata comes from the durable ledger, avoiding a billable R2 HEAD operation.
    if (request.method === "HEAD") return new Response(null, { headers });
    if (this.effective(state).b + 1 > policy.limits.b) return reply(429, { error: "Read quota reached." });
    state.used.b += 1;
    await this.save(state, policy);
    const object = await this.env.BUCKET.get(key);
    if (!object) return reply(404, { error: "Not found" });
    return new Response(object.body, { headers });
  }

  async putObject(request, key, ledgerKey, entry, state, policy) {
    if (entry) return reply(409, { error: "Object keys are immutable." });
    const declared = Number(request.headers.get("Content-Length"));
    if (!request.headers.has("Content-Length") || !Number.isSafeInteger(declared) || declared < 0) {
      return reply(411, { error: "Content-Length required." });
    }
    if (declared > MAX_OBJECT_BYTES) return reply(413, { error: "Object too large." });
    const body = await request.arrayBuffer();
    if (body.byteLength !== declared || body.byteLength > MAX_OBJECT_BYTES) {
      return reply(413, { error: "Invalid object size." });
    }
    const chargedBytes = body.byteLength + METADATA_RESERVE_BYTES;
    const used = this.effective(state);
    if (used.a + 1 > policy.limits.a || used.bytes + chargedBytes > policy.limits.bytes) {
      return reply(429, { error: "Write or storage quota reached." });
    }
    const suppliedType = request.headers.get("Content-Type");
    const contentType = ["image/jpeg", "image/png", "image/webp"].includes(suppliedType)
      ? suppliedType : "application/octet-stream";
    const reserved = { size: body.byteLength, chargedBytes, contentType,
      uploaded: new Date().toUTCString(), generation: crypto.randomUUID(), pending: true };
    state.used.a += 1;
    state.used.bytes += chargedBytes;
    state.pendingObjects += 1;
    // Keep reservations after failures so retries or crashes cannot undercount usage.
    await this.save(state, policy, { [ledgerKey]: reserved });
    const object = await this.env.BUCKET.put(key, body, {
      onlyIf: { etagDoesNotMatch: "*" }, httpMetadata: { contentType },
    });
    if (!object) {
      state.manualLock = true;
      await this.save(state, policy);
      return reply(503, { error: "Untracked object found; gateway locked." });
    }
    reserved.pending = false;
    state.pendingObjects -= 1;
    await this.save(state, policy, { [ledgerKey]: reserved });
    return reply(201, { key, size: body.byteLength });
  }
}
