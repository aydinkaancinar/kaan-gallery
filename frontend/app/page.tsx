import Link from "next/link";
import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";
import ArtworkCard from "@/components/ArtworkCard";
import GalleryPagination from "@/components/GalleryPagination";
import GalleryFilters from "@/components/GalleryFilters";
import type { GalleryCategory } from "@/components/GalleryControls";
import { notFound } from "next/navigation";

const BACKEND_ORIGIN = "http://127.0.0.1:8000";

type ApiArtworkImage = {
  id: number;
  image: string;
  alt_text: string;
  position: number;
};

type ApiArtwork = {
  id: number;
  name: string;
  creation_year: number | null;
  creation_month: number | null;
  cover_image: ApiArtworkImage | null;
  slug: string;
};

type ArtworkPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ApiArtwork[];
};

type DateBounds = {
  earliest: string | null;
  latest: string | null;
};

type HomeProps = {
  searchParams: Promise<{
    page?: string | string[];
    category?: string | string[];
    search?: string | string[];
    created_from?: string | string[];
    created_to?: string | string[];
  }>;
};

function readMonth(value: string | string[] | undefined) {
  if (
    typeof value === "string" &&
    /^(1999|20\d{2})-(0[1-9]|1[0-2])$/.test(value)
  ) {
    return value;
  }

  return undefined;
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const [categoriesResponse, boundsResponse] = await Promise.all([
    fetch(`${BACKEND_ORIGIN}/items/categories/`, { cache: "no-store" }),
    fetch(`${BACKEND_ORIGIN}/items/date-bounds/`, { cache: "no-store" }),
  ]);

  if (!categoriesResponse.ok || !boundsResponse.ok) {
    throw new Error("Unable to load gallery filters.");
  }

  const categories: GalleryCategory[] = await categoriesResponse.json();
  const dateBounds: DateBounds = await boundsResponse.json();

  const category =
    typeof params.category === "string" &&
    categories.some((option) => option.value === params.category)
      ? params.category
      : "all";

  const search =
    typeof params.search === "string"
      ? params.search.trim().slice(0, 200)
      : "";

  let createdFrom = readMonth(params.created_from);
  let createdTo = readMonth(params.created_to);

  if (createdFrom && createdTo && createdFrom > createdTo) {
    [createdFrom, createdTo] = [createdTo, createdFrom];
  }
  const filters = new URLSearchParams();

  if (createdFrom) {
    filters.set("created_from", createdFrom);
  }

  if (createdTo) {
    filters.set("created_to", createdTo);
  }

  if (category !== "all") {
    filters.set("category", category);
  }

  if (search) {
    filters.set("search", search);
  }
  const requestedPage =
    typeof params.page === "string" ? Number(params.page) : 1;

  const page =
    Number.isSafeInteger(requestedPage) && requestedPage > 0
      ? requestedPage
      : 1;

  const apiParams = new URLSearchParams(filters);
  apiParams.set("page", String(page));

  const response = await fetch(
    `${BACKEND_ORIGIN}/items/?${apiParams.toString()}`,
    { cache: "no-store" }
  );

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("Unable to load artworks.");
  }

  const artworkPage: ArtworkPage = await response.json();

  const galleryParams = new URLSearchParams(filters);

  if (page > 1) {
    galleryParams.set("page", String(page));
  }

  const galleryQuery = galleryParams.toString();
  const returnTo = galleryQuery ? `/?${galleryQuery}` : "/";
  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />
      <main className="gallery-main">
        <h1 className="visually-hidden">Artworks</h1>
        <GalleryFilters
          key={[
            category,
            search,
            createdFrom,
            createdTo,
            dateBounds.earliest,
            dateBounds.latest,
          ].join(":")}
          categories={categories}
          category={category}
          search={search}
          earliest={dateBounds.earliest}
          latest={dateBounds.latest}
          createdFrom={createdFrom}
          createdTo={createdTo}
        />
        <div className="gallery-results-bar">
          <p className="gallery-summary">
            Showing {artworkPage.results.length} of {artworkPage.count} artworks
          </p>
          {(category !== "all" || search || createdFrom || createdTo) && (
            <Link
              className="gallery-reset-link"
              href="/"
              prefetch={false}
              scroll={false}
            >
              Reset filters
            </Link>
          )}
        </div>
        <div className="artwork-grid">
          {artworkPage.results.map((artwork) => {
            const completionDate =
              artwork.creation_year !== null &&
              artwork.creation_month !== null
                ? `${artwork.creation_year}-${String(
                    artwork.creation_month
                  ).padStart(2, "0")}`
                : undefined;
                  const detailParams = new URLSearchParams({ from: returnTo });

                  const detailHref =
                    `/artworks/${encodeURIComponent(artwork.slug)}` +
                    `?${detailParams.toString()}`;
            return (
              <ArtworkCard
                key={artwork.id}
                title={artwork.name}
                completionDate={completionDate}
                imageUrl={
                  artwork.cover_image
                    ? new URL(artwork.cover_image.image, BACKEND_ORIGIN).href
                    : undefined
                }
                imageAlt={artwork.cover_image?.alt_text}
                href={detailHref}
              />
            );
          })}
        </div>

        {artworkPage.results.length === 0 && (
          <p className="gallery-empty">
            No artworks match these filters.
          </p>
        )}
        <GalleryPagination
          page={page}
          count={artworkPage.count}
          hasPrevious={artworkPage.previous !== null}
          hasNext={artworkPage.next !== null}
          filtersQuery={filters.toString()}
        />
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
