import assert from "node:assert/strict";
import test from "node:test";
import { billingPeriod, parseAnalytics, quotaPolicy } from "../src/policy.js";
import { QuotaGate } from "../src/index.js";

test("monthly boundaries preserve the actual anchor time and handle month ends", () => {
  const anchor = "2026-01-31T14:30:00.500Z";
  assert.deepEqual(billingPeriod(anchor, new Date("2026-03-01T00:00:00Z")), {
    start: "2026-02-28T14:30:00.500Z", end: "2026-03-31T14:30:00.500Z",
  });
  assert.equal(billingPeriod(anchor, new Date("2026-03-31T14:30:00.499Z")).start, "2026-02-28T14:30:00.500Z");
  assert.equal(billingPeriod(anchor, new Date("2026-03-31T14:30:00.500Z")).start, "2026-03-31T14:30:00.500Z");
  assert.throws(() => billingPeriod(""));
  assert.throws(() => billingPeriod("2099-01-01T00:00:00Z"));
});

test("quota configuration never permits limits above the safety margins", () => {
  assert.equal(quotaPolicy({}).limits.b, 9500000);
  assert.throws(() => quotaPolicy({ CLASS_A_LIMIT: "1000000" }));
  assert.throws(() => quotaPolicy({ CLASS_A_WARNING: "-1" }));
  assert.throws(() => quotaPolicy({ STORAGE_LIMIT_BYTES: "NaN" }));
});

test("billing rollover preserves stored bytes, pending uploads, locks, and undelivered alerts", async () => {
  const now = new Date();
  const anchor = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1)).toISOString();
  let stored = {
    anchor, initialized: true, period: { start: anchor }, used: { a: 10, b: 20, bytes: 123 },
    pendingObjects: 1, manualLock: true,
    alerts: { pending: { delivered: false }, sent: { delivered: true } },
    checkedAt: 123, snapshot: { old: true },
  };
  const gate = new QuotaGate({ storage: {
    get: async () => structuredClone(stored),
    put: async (key, value) => { stored = structuredClone(typeof key === "object" ? key.state : value); },
  } }, { BILLING_ANCHOR_UTC: anchor, BILLING_RESET_CONFIRMED: "true" });
  const state = await gate.loadState();
  assert.deepEqual(state.used, { a: 0, b: 0, bytes: 123 });
  assert.equal(state.pendingObjects, 1);
  assert.equal(state.manualLock, true);
  assert.deepEqual(state.alerts, { pending: { delivered: false } });
  assert.equal(state.snapshot, null);
  assert.equal(state.checkedAt, 0);
});

test("analytics treats unknown operations conservatively and counts each bucket once", () => {
  const usage = parseAnalytics({ data: { viewer: { accounts: [{
    r2OperationsAdaptiveGroups: [
      { dimensions: { actionType: "PutObject" }, sum: { requests: 2 } },
      { dimensions: { actionType: "GetObject" }, sum: { requests: 3 } },
      { dimensions: { actionType: "DeleteObject" }, sum: { requests: 4 } },
      { dimensions: { actionType: "UnknownAction" }, sum: { requests: 1 } },
    ],
    r2StorageAdaptiveGroups: [
      { dimensions: { bucketName: "one" }, max: { payloadSize: 10, metadataSize: 2 } },
      { dimensions: { bucketName: "one" }, max: { payloadSize: 5, metadataSize: 1 } },
      { dimensions: { bucketName: "two" }, max: { payloadSize: 20, metadataSize: 3 } },
    ],
  }] } } });
  assert.deepEqual(usage, { a: 3, b: 4, bytes: 35 });
  assert.throws(() => parseAnalytics({ errors: [{ message: "Unavailable" }] }));
});


test("unconfirmed rollover keeps counters and cannot be manually unlocked", async () => {
  const now = new Date();
  const anchor = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1)).toISOString();
  const initial = { anchor, initialized: true, period: { start: anchor, end: now.toISOString() },
    used: { a: 12, b: 34, bytes: 567 }, pendingObjects: 1, manualLock: false,
    alerts: {}, checkedAt: Date.now(),
    snapshot: { observed: { a: 25, b: 50, bytes: 600 }, local: { a: 12, b: 34, bytes: 567 } } };
  let stored = structuredClone(initial);
  const gate = new QuotaGate({ storage: {
    get: async () => structuredClone(stored),
    put: async (key, value) => { stored = structuredClone(typeof key === "object" ? key.state : value); },
  } }, { BILLING_ANCHOR_UTC: anchor });
  const state = await gate.loadState();
  assert.deepEqual(state.used, initial.used);
  assert.deepEqual(state.snapshot, initial.snapshot);
  assert.deepEqual(state.period, initial.period);
  assert.equal(state.pendingObjects, 1);
  assert.equal(gate.blockedReason(state, quotaPolicy({})), "billing_review_required");
  const response = await gate.control(new Request("https://test/v1/control/unlock", { method: "POST" }), state, quotaPolicy({}));
  assert.equal((await response.json()).blocked, "billing_review_required");
  await gate.loadState();
  assert.equal(Object.values(stored.alerts).filter(a => a.kind === "billing_review_required").length, 1);
});
