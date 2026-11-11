import type { NextConfig } from "next";
import { BACKEND_ORIGIN } from "./lib/site";

const nextConfig: NextConfig = {
  distDir: process.env.GALLERY_BROWSER_TEST === "1" ? ".next-browser-tests" : ".next",
  typescript: {
    tsconfigPath: process.env.GALLERY_BROWSER_TEST === "1"
      ? "tsconfig.browser.json" : "tsconfig.json",
  },
  async rewrites() {
    return [
      {
        source: "/artwork-images/:id(\\d+)/:variant(card|detail|share)",
        destination: new URL("/artwork-images/:id/:variant/", BACKEND_ORIGIN).href,
      },
      {
        source: "/artwork-images/:id(\\d+)",
        destination: new URL("/artwork-images/:id/", BACKEND_ORIGIN).href,
      },
    ];
  },
};

export default nextConfig;
