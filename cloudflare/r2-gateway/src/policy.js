export const MAX_OBJECT_BYTES = 10 * 1024 * 1024;
export const METADATA_RESERVE_BYTES = 8192;
export const MAX_METRICS_AGE_MS = 30 * 60 * 1000;

function positiveInteger(value, fallback, ceiling) {
  const number = Number(value ?? fallback);
  if (!Number.isSafeInteger(number) || number < 1 || number > ceiling) {
    throw new Error("Invalid quota configuration.");
  }
  return number;
}

export function quotaPolicy(env) {
  const limits = {
    a: positiveInteger(env.CLASS_A_LIMIT, 950000, 950000),
    b: positiveInteger(env.CLASS_B_LIMIT, 9500000, 9500000),
    bytes: positiveInteger(env.STORAGE_LIMIT_BYTES, 9500000000, 9500000000),
  };
  const warnings = {
    a: positiveInteger(env.CLASS_A_WARNING, 900000, limits.a),
    b: positiveInteger(env.CLASS_B_WARNING, 9000000, limits.b),
    bytes: positiveInteger(env.STORAGE_WARNING_BYTES, 9000000000, limits.bytes),
  };
  return { limits, warnings };
}

export function billingPeriod(anchorString, now = new Date()) {
  const anchor = new Date(anchorString);
  if (!anchorString || !Number.isFinite(anchor.getTime()) || anchor > now) {
    throw new Error("Set BILLING_ANCHOR_UTC to the actual R2 billing-period start.");
  }
  const occurrence = (monthOffset) => {
    const month = anchor.getUTCMonth() + monthOffset;
    const date = new Date(Date.UTC(anchor.getUTCFullYear(), month, 1));
    const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    date.setUTCDate(Math.min(anchor.getUTCDate(), lastDay));
    date.setUTCHours(
      anchor.getUTCHours(), anchor.getUTCMinutes(), anchor.getUTCSeconds(), anchor.getUTCMilliseconds(),
    );
    return date;
  };
  let offset = (now.getUTCFullYear() - anchor.getUTCFullYear()) * 12
    + now.getUTCMonth() - anchor.getUTCMonth();
  if (occurrence(offset) > now) offset -= 1;
  return { start: occurrence(offset).toISOString(), end: occurrence(offset + 1).toISOString() };
}

export function objectKey(pathname) {
  const prefix = "/v1/objects/";
  if (!pathname.startsWith(prefix)) throw new Error("Invalid object route.");
  const encoded = pathname.slice(prefix.length);
  if (!/^[A-Za-z0-9_-]+$/.test(encoded)) throw new Error("Invalid object key.");
  const bytes = Uint8Array.from(atob(encoded.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  const key = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  if (
    bytes.length > 1024 || !/^(artworks|artwork-variants)\//.test(key)
    || /[\x00-\x1f\\]/.test(key)
    || key.split("/").some((part) => !part || part === "." || part === "..")
  ) throw new Error("Invalid object key.");
  return key;
}

const CLASS_A = new Set([
  "PutObject", "CopyObject", "ListObjects", "ListObjectsV2", "ListBuckets",
  "ListMultipartUploads", "CreateMultipartUpload", "UploadPart", "UploadPartCopy",
  "CompleteMultipartUpload", "ListParts",
]);
const CLASS_B = new Set([
  "GetObject", "HeadObject", "HeadBucket", "UsageSummary", "GetBucketEncryption",
  "GetBucketLocation", "GetBucketCors", "GetBucketLifecycleConfiguration",
]);
const FREE = new Set(["DeleteObject", "DeleteObjects", "AbortMultipartUpload"]);

function usageNumber(number) {
  if (!Number.isSafeInteger(number) || number < 0) throw new Error("Invalid analytics data.");
  return number;
}

export function parseAnalytics(body) {
  if (body.errors?.length || body.data?.viewer?.accounts?.length !== 1) {
    throw new Error("Analytics unavailable.");
  }
  const account = body.data.viewer.accounts[0];
  const operations = account.r2OperationsAdaptiveGroups;
  const storage = account.r2StorageAdaptiveGroups;
  if (!Array.isArray(operations) || !Array.isArray(storage) || operations.length >= 256 || storage.length >= 256) {
    throw new Error("Incomplete analytics data.");
  }
  const totals = { a: 0, b: 0, bytes: 0 };
  for (const operation of operations) {
    const count = usageNumber(operation.sum?.requests);
    const action = operation.dimensions?.actionType;
    if (FREE.has(action)) continue;
    // Unknown operation types count against both budgets until reviewed.
    if (CLASS_A.has(action) || !CLASS_B.has(action)) totals.a += count;
    if (CLASS_B.has(action) || !CLASS_A.has(action)) totals.b += count;
  }
  const buckets = new Map();
  for (const row of storage) {
    const bucket = row.dimensions?.bucketName;
    if (typeof bucket !== "string") throw new Error("Invalid storage analytics.");
    const bytes = usageNumber(row.max?.payloadSize) + usageNumber(row.max?.metadataSize);
    buckets.set(bucket, Math.max(buckets.get(bucket) ?? 0, bytes));
  }
  totals.bytes = [...buckets.values()].reduce((sum, bytes) => sum + bytes, 0);
  return totals;
}
