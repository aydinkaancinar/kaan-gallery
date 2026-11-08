"use client";

import { useState } from "react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

    function changeTheme(nextTheme: "light" | "dark") {
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;

    try {
        localStorage.setItem("gallery-theme", nextTheme);
    } catch {
        // Theme switching still works if browser storage is unavailable.
    }
    }

  return (
    <div className="theme-toggle" role="group" aria-label="Color theme">
      <button
        type="button"
        aria-pressed={theme === "light"}
        onClick={() => changeTheme("light")}
      >
        Light
      </button>

      <button
        type="button"
        aria-pressed={theme === "dark"}
        onClick={() => changeTheme("dark")}
      >
        Dark
      </button>
    </div>
  );
}
