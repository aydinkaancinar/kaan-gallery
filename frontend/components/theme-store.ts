export type Theme = "light" | "dark";

const STORAGE_KEY = "gallery-theme";
const CHANGE_EVENT = "gallery-theme-change";
let memoryPreference: Theme | null = null;

function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

function savedPreference(): Theme | null {
  if (memoryPreference) return memoryPreference;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isTheme(saved)) return saved;
  } catch {
    // Storage may be blocked; explicit choices still work for this visit.
  }
  return memoryPreference;
}

function systemTheme(): Theme {
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  } catch {
    return "light";
  }
}

export function getTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const applied = document.documentElement.dataset.theme;
  return isTheme(applied) ? applied : savedPreference() ?? systemTheme();
}

export function getServerTheme(): null {
  // Keep theme buttons pending until their browser event handlers are ready.
  return null;
}

export function subscribeToTheme(onChange: () => void) {
  function sync() {
    document.documentElement.dataset.theme = savedPreference() ?? systemTheme();
    onChange();
  }

  function onStorage(event: StorageEvent) {
    if (event.key === STORAGE_KEY || event.key === null) {
      memoryPreference = null;
      sync();
    }
  }

  let media: MediaQueryList | undefined;
  try {
    media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", sync);
  } catch {
    // Basic theme controls still work without media-query event support.
  }

  window.addEventListener(CHANGE_EVENT, sync);
  window.addEventListener("storage", onStorage);
  sync();

  return () => {
    media?.removeEventListener("change", sync);
    window.removeEventListener(CHANGE_EVENT, sync);
    window.removeEventListener("storage", onStorage);
  };
}

export function saveTheme(theme: Theme) {
  memoryPreference = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Keep the in-memory preference if persistence is unavailable.
  }
  document.documentElement.dataset.theme = theme;
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

// Run in <head>, before body content is painted. Only fixed code is injected.
export const themeBootstrapScript = `(() => {
  let saved;
  try { saved = localStorage.getItem("gallery-theme"); } catch {}
  let theme = saved === "light" || saved === "dark" ? saved : null;
  if (!theme) {
    try {
      theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } catch { theme = "light"; }
  }
  document.documentElement.dataset.theme = theme;
})();`;
