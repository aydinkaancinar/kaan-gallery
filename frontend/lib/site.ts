export const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
export const SITE_URL = new URL(
  process.env.SITE_URL ??
    (process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000"),
);
export const SITE_NAME = "Kaan Gallery";
export const GALLERY_TITLE = "Aydın Kaan Çınar — Art Portfolio";
export const GALLERY_DESCRIPTION =
  "Explore the ceramics, objects, and illustrations of artist Aydın Kaan Çınar, and design your own pottery forms in Clay Studio.";
export const GALLERY_PREVIEW = {
  url: "/opengraph-image.png",
  alt: "Red sun emblem beside the stacked name Aydın Kaan Çınar.",
  width: 1200,
  height: 630,
  type: "image/png",
};

export function artworkImagePath(apiPath: string) {
  return apiPath.replace(/\/$/, "");
}
