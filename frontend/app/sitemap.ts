import type { MetadataRoute } from "next";
import { artworkImagePath, BACKEND_ORIGIN, SITE_URL } from "@/lib/site";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const response = await fetch(new URL("/items/artwork-index/", BACKEND_ORIGIN), {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Unable to load the artwork sitemap.");

  const artworks: { slug: string; images: string[] }[] = await response.json();
  const absolute = (path: string) => new URL(path, SITE_URL).href;
  return [
    { url: absolute("/") },
    { url: absolute("/clay-studio") },
    { url: absolute("/privacy") },
    ...artworks.map(({ slug, images }) => ({
      url: absolute(`/artworks/${encodeURIComponent(slug)}`),
      images: images.map((path) => absolute(artworkImagePath(path))),
    })),
  ];
}
