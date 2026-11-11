import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import GalleryHeader from "@/components/GalleryHeader";
import GalleryFooter from "@/components/GalleryFooter";
import ThemeToggle from "@/components/ThemeToggle";
import ArtworkImageGallery from "@/components/ArtworkImageGallery";
import StructuredData from "@/components/StructuredData";
import { artworkImagePath, BACKEND_ORIGIN, GALLERY_PREVIEW, SITE_NAME, SITE_URL } from "@/lib/site";

type ArtworkPhoto = {
  id: number;
  image: string;
  detail_image: string;
  share_image: string;
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
        url: artworkImagePath(artwork.cover_image.share_image),
        alt: artwork.cover_image.alt_text || artwork.name,
        width: 1200,
        height: 630,
        type: "image/jpeg",
      }
    : GALLERY_PREVIEW;

  return {
    title,
    description,
    alternates: {
      canonical: artworkPath,
    },
    robots: { googleBot: { "max-image-preview": "large" } },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
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
    src: artworkImagePath(photo.detail_image),
    viewerSrc: artworkImagePath(photo.image),
    alt: photo.alt_text || artwork.name,
  }));
  const categoryLabel = artwork.category.replace(/[-_]/g, " ");
  const artist = artwork.artist_details;
  const artworkUrl = new URL(`/artworks/${encodeURIComponent(slug)}`, SITE_URL).href;

  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />

      <main className="artwork-detail">
        <StructuredData data={{
          "@context": "https://schema.org",
          "@type": "VisualArtwork",
          name: artwork.name,
          url: artworkUrl,
          description: artwork.description || undefined,
          image: images.length ? images.map(({ src }) => new URL(src, SITE_URL).href) : undefined,
          artform: categoryLabel,
          dateCreated: completionDate,
          creator: artist ? { "@type": "Person", name: `${artist.name} ${artist.surname}`.trim() } : undefined,
        }} />
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

      <GalleryFooter />
    </div>
  );
}
