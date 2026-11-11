import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  testMatch: "**/*.spec.ts",
  workers: 2,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3113",
    colorScheme: "light",
    channel: process.env.PLAYWRIGHT_CHANNEL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "../.venv/bin/python tests/browser/server.py",
      url: "http://127.0.0.1:8114/items/categories/",
      name: "Django test catalog",
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGINT", timeout: 5000 },
    },
    {
      command: "npm run build && npm run start -- --hostname 127.0.0.1 --port 3113",
      url: "http://127.0.0.1:3113/robots.txt",
      name: "Frontend test build",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        GALLERY_BROWSER_TEST: "1",
        BACKEND_ORIGIN: "http://127.0.0.1:8114",
        SITE_URL: "http://127.0.0.1:3113",
      },
      gracefulShutdown: { signal: "SIGTERM", timeout: 5000 },
    },
  ],
});
