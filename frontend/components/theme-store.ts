type Theme = "light" | "dark";

let fallbackTheme: Theme = "light";

export function getTheme(): Theme {
  try {
    const saved = localStorage.getItem("gallery-theme");

    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch {
    // Use the in-memory preference if storage is unavailable.
  }

  return fallbackTheme;
}

export function getServerTheme(): Theme {
  return "light";
}

export function subscribeToTheme(onChange: () => void) {
  window.addEventListener("gallery-theme-change", onChange);
  window.addEventListener("storage", onChange);

  return () => {
    window.removeEventListener("gallery-theme-change", onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function saveTheme(theme: Theme) {
  fallbackTheme = theme;

  try {
    localStorage.setItem("gallery-theme", theme);
  } catch {
    // The in-memory preference still works.
  }

  window.dispatchEvent(new Event("gallery-theme-change"));
}
