import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";
import ArtworkImageGallery from "@/components/ArtworkImageGallery";

const BACKEND_ORIGIN = "http://127.0.0.1:8000";

type ArtworkPhoto = {
  id: number;
  image: string;
  alt_text: string;
  position: number;
};

type ArtworkDetail = {
  name: string;
  description: string;
  category: string;
  creation_year: number | null;
  creation_month: number | null;
  artist_details: {
    id: number;
    name: string;
    surname: string;
  } | null;
  images: ArtworkPhoto[];
  cover_image: ArtworkPhoto | null;
};

type ArtworkPageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ from?: string | string[] }>;
};

async function getArtwork(slug: string): Promise<ArtworkDetail> {
  const response = await fetch(
    `${BACKEND_ORIGIN}/artworks/${encodeURIComponent(slug)}/`,
    { cache: "no-store" }
  );

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("Unable to load artwork.");
  }

  return response.json();
}

export async function generateMetadata({
  params,
}: ArtworkPageProps): Promise<Metadata> {
  const { slug } = await params;
  const artwork = await getArtwork(slug);

  const title = `${artwork.name} — Aydın Kaan Çınar`;

  const description =
    artwork.description.trim().replace(/\s+/g, " ").slice(0, 160) ||
    `${artwork.name}, from the art gallery of Aydın Kaan Çınar.`;

  const artworkPath = `/artworks/${encodeURIComponent(slug)}`;

  const previewImage = artwork.cover_image
    ? {
        url: new URL(
            artwork.cover_image.image,
            BACKEND_ORIGIN
        ).href,
        alt: artwork.cover_image.alt_text || artwork.name,
        }
    : {
        url: "/opengraph-image.png",
        alt: "Red sun emblem beside the stacked name Aydın Kaan Çınar.",
        };

  return {
    title,
    description,
    alternates: {
      canonical: artworkPath,
    },
    openGraph: {
      type: "website",
      siteName: "Kaan Gallery",
      title,
      description,
      url: artworkPath,
      images: [previewImage],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [previewImage],
    },
  };
}

export default async function ArtworkPage({
  params,
  searchParams,
}: ArtworkPageProps) {
  const { slug } = await params;
  const query = await searchParams;

  const returnTo =
    typeof query.from === "string" &&
    (query.from === "/" || query.from.startsWith("/?"))
      ? query.from
      : "/";

  const artwork = await getArtwork(slug);

  const completionDate =
    artwork.creation_year !== null &&
    artwork.creation_month !== null
      ? `${artwork.creation_year}-${String(
          artwork.creation_month
        ).padStart(2, "0")}`
      : undefined;

  const displayDate = completionDate
    ? `${completionDate.slice(5, 7)}/${completionDate.slice(2, 4)}`
    : undefined;

  const photos = artwork.images.length
    ? artwork.images
    : artwork.cover_image ? [artwork.cover_image] : [];
  const images = photos.map((photo) => ({
    id: photo.id,
    src: new URL(photo.image, BACKEND_ORIGIN).href,
    alt: photo.alt_text || artwork.name,
  }));
  const categoryLabel = artwork.category.replace(/_/g, " ");

  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />

      <main className="artwork-detail">
        <Link
          className="artwork-back"
          href={returnTo}
          prefetch={false}
        >
          ← Back to artworks
        </Link>

        <ArtworkImageGallery key={slug} images={images}>
            <div className="artwork-eyebrow">Artwork</div>
            <h1>
              {artwork.name}
              {completionDate && (
                <time dateTime={completionDate}>
                  <span aria-hidden="true">· </span>
                  {displayDate}
                </time>
              )}
            </h1>

            {artwork.description && (
              <p className="artwork-description">
                {artwork.description}
              </p>
            )}

            <dl className="artwork-facts">
              <div>
                <dt>Category</dt>
                <dd className="artwork-category">{categoryLabel}</dd>
              </div>
              {artwork.artist_details && (
                <div>
                  <dt>Artist</dt>
                  <dd>
                    {artwork.artist_details.name}{" "}
                    {artwork.artist_details.surname}
                  </dd>
                </div>
              )}
            </dl>

        </ArtworkImageGallery>
      </main>

      <footer className="gallery-footer">
        <a
          href="https://kaancinar.com/"
          target="_blank"
          rel="noopener noreferrer"
        >
          kaancinar.com
        </a>
      </footer>
    </div>
  );
}
