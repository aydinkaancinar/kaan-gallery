import { chromium } from "@playwright/test";

const url = process.argv[2] ?? "https://arts.kaancinar.com/";
const runs = Number(process.argv[3] ?? 5);
if (!Number.isSafeInteger(runs) || runs < 1) {
  throw new Error("Run count must be a positive integer.");
}

const selector = ".artwork-card .artwork-image img";
const browser = await chromium.launch();
const samples = [];

try {
  for (let run = 1; run <= runs; run++) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    try {
      const page = await context.newPage();
      const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
      if (!response?.ok()) throw new Error(`Gallery returned HTTP ${response?.status()}`);
      await page.locator(selector).first().waitFor({ state: "attached", timeout: 10_000 });

      const cards = await page.evaluate(async (cardSelector) => {
        const images = [...document.querySelectorAll(cardSelector)];
        const measure = async (image) => {
          image.loading = "eager";
          await image.decode();
          const resource = performance.getEntriesByName(image.currentSrc, "resource").at(-1);
          return {
            name: image.closest(".artwork-card")?.querySelector("h2")?.textContent?.trim(),
            url: image.currentSrc,
            resourceStart: resource?.startTime ?? null,
            requestStart: resource?.requestStart || null,
            firstByte: resource?.responseStart || null,
            downloaded: resource?.responseEnd ?? null,
            decoded: performance.now(),
            serverTiming: Object.fromEntries(resource?.serverTiming.map(({ name, duration }) => [name, duration]) ?? []),
          };
        };

        let timeout;
        try {
          return await Promise.race([
            Promise.all(images.map(measure)),
            new Promise((_, reject) => {
              timeout = setTimeout(() => reject(new Error("Card images did not decode within 30 seconds.")), 30_000);
            }),
          ]);
        } finally {
          clearTimeout(timeout);
        }
      }, selector);

      const first = Math.min(...cards.map((card) => card.decoded));
      const all = Math.max(...cards.map((card) => card.decoded));
      const single = await page.evaluate(async (imageUrl) => {
        const response = await fetch(imageUrl, {
          cache: "no-store",
          signal: AbortSignal.timeout(30_000),
        });
        if (!response.ok || !response.headers.get("content-type")?.startsWith("image/")) {
          throw new Error(`Single-image request returned HTTP ${response.status} or a non-image response.`);
        }
        await response.arrayBuffer();
        const resource = performance.getEntriesByName(imageUrl, "resource")
          .filter((entry) => entry.initiatorType === "fetch").at(-1);
        return {
          requestStart: resource?.requestStart || null,
          firstByte: resource?.responseStart || null,
          serverTiming: Object.fromEntries(resource?.serverTiming.map(({ name, duration }) => [name, duration]) ?? []),
        };
      }, cards[0].url);

      samples.push({ first, all });
      console.log(`Run ${run} · ${cards.length} images · first ${first.toFixed(0)} ms · all ${all.toFixed(0)} ms`);
      const ms = (value) => value === null ? "unavailable" : Math.round(value);
      const elapsed = (start, end) => start === null || end === null ? null : end - start;
      console.table(cards.map(({ name, url: imageUrl, resourceStart, requestStart, firstByte, downloaded, decoded, serverTiming }) => ({
        artwork: name || new URL(imageUrl).pathname,
        "fetch start (ms)": ms(resourceStart),
        "request sent (ms)": ms(requestStart),
        "pre-request (ms)": ms(elapsed(resourceStart, requestStart)),
        "TTFB (ms)": ms(elapsed(requestStart, firstByte)),
        "publication (ms)": ms(serverTiming.publication ?? null),
        "storage (ms)": ms(serverTiming.storage ?? null),
        "transfer (ms)": ms(elapsed(firstByte, downloaded)),
        "downloaded (ms)": ms(downloaded),
        "decoded (ms)": Math.round(decoded),
      })));
      console.table([
        { mode: "with other cards", ...cards[0] },
        { mode: "single request", ...single },
      ].map(({ mode, requestStart, firstByte, serverTiming }) => ({
        mode,
        "TTFB (ms)": ms(elapsed(requestStart, firstByte)),
        "publication (ms)": ms(serverTiming.publication ?? null),
        "storage (ms)": ms(serverTiming.storage ?? null),
      })));
    } catch (error) {
      console.error(`Run ${run} failed: ${error.message}`);
      process.exitCode = 1;
    } finally {
      await context.close();
    }
  }

  if (samples.length) {
    const average = (key) => Math.round(samples.reduce((sum, sample) => sum + sample[key], 0) / samples.length);
    console.log(`${samples.length}/${runs} successful · avg first ${average("first")} ms · avg all ${average("all")} ms`);
  }
} finally {
  await browser.close();
}
