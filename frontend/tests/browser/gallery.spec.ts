import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

test("software license notices are accessible from the production footer", async ({ page }) => {
  await page.goto("/privacy");
  const link = page.getByRole("link", { name: "Software licenses", exact: true });
  await expect(link).toBeVisible();
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/THIRD_PARTY_LICENSES.txt",
  );
  await link.click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("text/plain");
  const served = await response.text();
  expect(served).toBe(await readFile(resolve(__dirname, "../../public/THIRD_PARTY_LICENSES.txt"), "utf8"));
  for (const path of ["react/LICENSE", "@swc/helpers/LICENSE"]) {
    const upstream = await readFile(resolve(__dirname, `../../node_modules/${path}`), "utf8");
    expect(served).toContain(upstream.trim());
  }
  await expect(page).toHaveURL("/THIRD_PARTY_LICENSES.txt");
});

test("privacy policy is linked from the gallery and readable", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Privacy policy" }).click();
  await expect(page).toHaveURL("/privacy");
  await expect(page.getByRole("heading", { name: "Privacy policy" })).toBeVisible();
  await expect(page.getByText("Toronto, Ontario", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: "akcinar99@gmail.com", exact: true })).toBeVisible();
});

test("filters survive artwork navigation, Back, Forward, and reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("article")).toHaveCount(3);
  await page.getByRole("button", { name: "Print", exact: true }).click();
  await expect(page).toHaveURL("/?category=print");
  await expect(page.getByRole("article")).toHaveCount(1);

  await page.getByRole("link", { name: /Browser test drawing/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Browser test drawing");
  await page.goBack();
  await expect(page.getByRole("button", { name: "Print", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.goForward();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Browser test drawing");
  await page.getByRole("link", { name: /Back to artworks/ }).click();
  await expect(page).toHaveURL("/?category=print");

  const search = page.getByRole("searchbox", { name: "Search artworks" });
  await search.fill("drawing");
  await search.press("Enter");
  await expect(page).toHaveURL("/?category=print&search=drawing");
  await page.reload();
  await expect(search).toHaveValue("drawing");
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.getByRole("link", { name: "Reset filters" }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("article")).toHaveCount(3);
});

test("an explicit theme survives navigation and reload", async ({ page }) => {
  let resumeJavaScript = () => {};
  const scriptsReady = new Promise<void>((resolve) => { resumeJavaScript = resolve; });
  await page.route(/\.js(?:\?|$)/, async (route) => {
    await scriptsReady;
    await route.continue();
  });
  await page.goto("/", { waitUntil: "commit" });
  const dark = page.getByRole("button", { name: "Dark theme" });
  try {
    await expect(dark).toBeVisible();
    await expect(dark).toBeDisabled();
  } finally {
    resumeJavaScript();
  }
  await dark.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("link", { name: /Browser test vase/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.getByRole("button", { name: "Dark theme" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("originals load after opening the viewer and keyboard navigation changes photos", async ({ page }) => {
  const originals: string[] = [];
  page.on("request", (request) => {
    if (/\/artwork-images\/\d+$/.test(new URL(request.url()).pathname)) {
      originals.push(request.url());
    }
  });
  await page.goto("/artworks/browser-vase");
  const photo = page.locator(".artwork-detail-image img");
  await expect(photo).toHaveJSProperty("complete", true);
  await expect(photo).toHaveJSProperty("naturalWidth", 1440);
  expect(originals).toHaveLength(0);

  const open = page.getByRole("button", { name: "View image" });
  await open.click();
  const dialog = page.getByRole("dialog", { name: "Full artwork image" });
  const viewer = dialog.getByRole("img");
  await expect(dialog).toBeVisible();
  await expect(viewer).toHaveJSProperty("naturalWidth", 1600);
  expect(originals).toHaveLength(1);
  await page.keyboard.press("ArrowRight");
  await expect(viewer).toHaveAttribute("alt", "Browser test vase, view 2");
  await expect(viewer).toHaveJSProperty("naturalWidth", 1600);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(open).toBeFocused();
});

test("protected drawings use their limited preview in the viewer", async ({ page, request }) => {
  await page.goto("/artworks/browser-drawing");
  const photo = page.locator(".artwork-detail-image img");
  await expect(photo).toHaveJSProperty("naturalWidth", 1200);
  const preview = await photo.getAttribute("src");
  expect(preview).toMatch(/\/detail$/);
  await page.getByRole("button", { name: "View image" }).click();
  const viewer = page.getByRole("dialog").getByRole("img");
  await expect(viewer).toHaveAttribute("src", preview!);
  await expect(viewer).toHaveJSProperty("naturalWidth", 1200);
  const original = preview!.replace(/\/detail$/, "");
  expect((await request.get(original)).status()).toBe(404);
});
