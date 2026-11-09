import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(new URL("../components/theme-store.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

function browser({ dark = false, saved, blocked = false, writeBlocked = false, mediaUnavailable = false } = {}) {
  const values = new Map(saved === undefined ? [] : [["gallery-theme", saved]]);
  const media = new EventTarget();
  media.matches = dark;
  const window = new EventTarget();
  window.matchMedia = () => {
    if (mediaUnavailable) throw new Error("Media queries unavailable");
    return media;
  };
  const document = { documentElement: { dataset: {} } };
  const localStorage = {
    getItem(key) {
      if (blocked) throw new Error("Storage blocked");
      return values.get(key) ?? null;
    },
    setItem(key, value) {
      if (blocked || writeBlocked) throw new Error("Storage blocked");
      values.set(key, value);
    },
  };
  const context = vm.createContext({ exports: {}, window, document, localStorage, Event });
  vm.runInContext(compiled, context);
  const store = context.exports;
  return {
    store,
    values,
    document,
    bootstrap() { vm.runInContext(store.themeBootstrapScript, context); },
    system(dark) { media.matches = dark; media.dispatchEvent(new Event("change")); },
    storage(value) {
      if (value === null) values.delete("gallery-theme");
      else values.set("gallery-theme", value);
      const event = new Event("storage");
      Object.defineProperty(event, "key", { value: "gallery-theme" });
      window.dispatchEvent(event);
    },
  };
}

test("first visit follows browser preference before React starts", () => {
  for (const dark of [false, true]) {
    const env = browser({ dark });
    env.bootstrap();
    assert.equal(env.document.documentElement.dataset.theme, dark ? "dark" : "light");
    assert.equal(env.values.has("gallery-theme"), false);
  }
});

test("saved explicit choice overrides browser preference on reload", () => {
  const env = browser({ dark: true, saved: "light" });
  env.bootstrap();
  assert.equal(env.store.getTheme(), "light");
  env.store.saveTheme("dark");
  const reloaded = browser({ dark: false, saved: env.values.get("gallery-theme") });
  reloaded.bootstrap();
  assert.equal(reloaded.store.getTheme(), "dark");
});

test("invalid saved values fall back to browser preference", () => {
  const env = browser({ dark: true, saved: "invalid" });
  env.bootstrap();
  assert.equal(env.store.getTheme(), "dark");
});

test("browser preference changes apply until user chooses explicitly", () => {
  const env = browser();
  env.bootstrap();
  let notifications = 0;
  env.store.subscribeToTheme(() => notifications++);
  env.system(true);
  assert.equal(env.store.getTheme(), "dark");
  env.store.saveTheme("light");
  env.system(false);
  env.system(true);
  assert.equal(env.store.getTheme(), "light");
  assert.ok(notifications > 0);
});

test("cross-tab changes and preference removal synchronize", () => {
  const env = browser({ dark: true, saved: "dark" });
  env.bootstrap();
  env.store.subscribeToTheme(() => {});
  env.store.saveTheme("dark");
  env.storage("light");
  assert.equal(env.store.getTheme(), "light");
  env.storage(null);
  assert.equal(env.store.getTheme(), "dark");
});

test("blocked storage still permits browser default and manual switching", () => {
  const env = browser({ dark: true, blocked: true });
  env.bootstrap();
  env.store.subscribeToTheme(() => {});
  assert.equal(env.store.getTheme(), "dark");
  env.store.saveTheme("light");
  env.system(false);
  env.system(true);
  assert.equal(env.store.getTheme(), "light");
});

test("failed storage writes do not restore an old saved choice", () => {
  const env = browser({ saved: "light", writeBlocked: true });
  env.bootstrap();
  env.store.subscribeToTheme(() => {});
  env.store.saveTheme("dark");
  assert.equal(env.store.getTheme(), "dark");
});

test("subscription cleanup removes browser listeners", () => {
  const env = browser();
  env.bootstrap();
  let notifications = 0;
  const cleanup = env.store.subscribeToTheme(() => notifications++);
  const before = notifications;
  cleanup();
  env.system(true);
  env.storage("dark");
  assert.equal(notifications, before);
});

test("missing browser media support has a safe light fallback", () => {
  const env = browser({ mediaUnavailable: true });
  env.bootstrap();
  env.store.subscribeToTheme(() => {});
  assert.equal(env.store.getTheme(), "light");
  assert.equal(env.store.getServerTheme(), "light");
});
