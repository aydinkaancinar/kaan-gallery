import GalleryFooter from "@/components/GalleryFooter";
import Link from "next/link";
import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";
import ArtworkCard from "@/components/ArtworkCard";
import GalleryPagination from "@/components/GalleryPagination";
import GalleryFilters from "@/components/GalleryFilters";
import type { GalleryCategory } from "@/components/GalleryControls";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { artworkImagePath, BACKEND_ORIGIN } from "@/lib/site";

type ApiArtworkImage = {
  id: number;
  card_image: string;
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

function readPage(value: string | string[] | undefined) {
  const page = typeof value === "string" ? Number(value) : 1;
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

export async function generateMetadata({ searchParams }: HomeProps): Promise<Metadata> {
  const { page, category, search, created_from, created_to } = await searchParams;
  const filtered = Boolean((category && category !== "all") || search || created_from || created_to);
  const pageNumber = readPage(page);
  return {
    alternates: { canonical: !filtered && pageNumber > 1 ? `/?page=${pageNumber}` : "/" },
    robots: filtered ? { index: false, follow: true } : undefined,
  };
}

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
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

  if (search) {
    filters.set("search", search);
  }
  const page = readPage(params.page);
  const categoriesPromise: Promise<GalleryCategory[]> = fetch(
    `${BACKEND_ORIGIN}/items/categories/`, { cache: "no-store" },
  ).then((response) => {
    if (!response.ok) throw new Error("Unable to load gallery categories.");
    return response.json();
  });
  const boundsPromise: Promise<DateBounds> = fetch(
    `${BACKEND_ORIGIN}/items/date-bounds/`, { cache: "no-store" },
  ).then((response) => {
    if (!response.ok) throw new Error("Unable to load gallery date bounds.");
    return response.json();
  });
  const categoryPromise = typeof params.category === "string" && params.category !== "all"
    ? categoriesPromise.then((categories) =>
        categories.find((option) => option.value === params.category)?.value ?? "all",
      )
    : Promise.resolve("all");
  const artworkResponse = categoryPromise.then((category) => {
    if (category !== "all") filters.set("category", category);
    const apiParams = new URLSearchParams(filters);
    apiParams.set("page", String(page));
    return fetch(`${BACKEND_ORIGIN}/items/?${apiParams}`, { cache: "no-store" });
  });
  const [categories, dateBounds, category, response] = await Promise.all([
    categoriesPromise, boundsPromise, categoryPromise, artworkResponse,
  ]);

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
        <h1 className="visually-hidden">Art portfolio of Aydın Kaan Çınar</h1>
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
          {artworkPage.results.map((artwork, index) => {
            const completionDate =
              artwork.creation_year !== null &&
              artwork.creation_month !== null
                ? `${artwork.creation_year}-${String(
                    artwork.creation_month
                  ).padStart(2, "0")}`
                : undefined;
            const detailPath = `/artworks/${encodeURIComponent(artwork.slug)}`;
            const detailHref = returnTo === "/" ? detailPath
              : `${detailPath}?${new URLSearchParams({ from: returnTo })}`;
            return (
              <ArtworkCard
                key={artwork.id}
                title={artwork.name}
                completionDate={completionDate}
                imageUrl={
                  artwork.cover_image
                    ? artworkImagePath(artwork.cover_image.card_image)
                    : undefined
                }
                imageAlt={artwork.cover_image?.alt_text}
                priority={index === 0}
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
      <GalleryFooter />
    </div>
  );
}
