"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import GalleryControls, { type GalleryCategory } from "@/components/GalleryControls";

type GalleryFiltersProps = {
  categories: GalleryCategory[];
  category: string;
  search: string;
  earliest: string | null;
  latest: string | null;
  createdFrom?: string;
  createdTo?: string;
};

export default function GalleryFilters({
  categories,
  category,
  search,
  earliest,
  latest,
  createdFrom,
  createdTo,
}: GalleryFiltersProps) {
  const router = useRouter();
  const [draftSearch, setDraftSearch] = useState(search);
  const [isPending, startTransition] = useTransition();

    function applyFilters(
    nextCategory: string,
    from = createdFrom,
    to = createdTo
    ) {
  const params = new URLSearchParams();

    if (nextCategory !== "all") {
      params.set("category", nextCategory);
    }

    const query = draftSearch.trim();

    if (query) {
      params.set("search", query);
    }
    if (from) {
      params.set("created_from", from);
    }
    if (to) {
      params.set("created_to", to);
    }
    const queryString = params.toString();
    startTransition(() => {
    router.push(queryString ? `/?${queryString}` : "/", {
        scroll: false,
    });
    });
  }
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        applyFilters(category);
      }}
    >
      <GalleryControls
        categories={categories}
        category={category}
        search={draftSearch}
        onCategoryChange={applyFilters}
        onSearchChange={setDraftSearch}
        earliest={earliest}
        latest={latest}
        createdFrom={createdFrom}
        createdTo={createdTo}
        onDateCommit={(from, to) => {
        applyFilters(category, from, to);
        }}
      />
        <p className="gallery-filter-status" role="status">
        {isPending ? "Updating artworks…" : ""}
        </p>
    </form>
  );
}
