"use client";

import { useSyncExternalStore } from "react";
import {
  getTheme,
  getServerTheme,
  subscribeToTheme,
  saveTheme,
} from "@/components/theme-store";

export default function ThemeToggle() {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    getTheme,
    getServerTheme
  );

  return (
    <div className="gallery-topbar">
      <div className="gallery-contact-links">
        <a
          className="personal-site-link"
          href="https://kaancinar.com/"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Kaan’s personal website (opens in a new tab)"
          title="Personal website (opens in a new tab)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M3 6v12M10 6l-7 6 7 6" />
            <path d="M21 7.5c-1.2-1.7-4.2-1.9-5.9-.3-2.6 2.4-2.6 7.2 0 9.6 1.7 1.6 4.7 1.4 5.9-.3" />
          </svg>
        </a>
        <button
          className="personal-site-link theme-switch"
          type="button"
          role="switch"
          aria-label="Dark theme"
          aria-checked={theme === "dark"}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          disabled={theme === null}
          onClick={() => saveTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? (
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <circle cx="12" cy="12" r="3.5" />
              <path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </svg>
          )}
        </button>
      </div>
      <div className="gallery-contact-links">
        <a
          className="personal-site-link"
          href="mailto:akcinar99@gmail.com"
          aria-label="Email Kaan at akcinar99@gmail.com"
          title="Email akcinar99@gmail.com"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="3" y="5" width="18" height="14" rx="1.5" />
            <path d="m3 6 9 7 9-7" />
          </svg>
        </a>
        <a
          className="personal-site-link"
          href="https://www.instagram.com/ceramitect/"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Ceramitect on Instagram (opens in a new tab)"
          title="Ceramitect on Instagram (opens in a new tab)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="3" y="3" width="18" height="18" rx="5" />
            <circle cx="12" cy="12" r="4" />
            <circle cx="17.5" cy="6.5" r="0.75" fill="currentColor" stroke="none" />
          </svg>
        </a>
      </div>
    </div>
  );
}
