"use client";

import { useState } from "react";
import ArtworkCard from "@/components/ArtworkCard";
import GalleryControls, { type GalleryCategory } from "@/components/GalleryControls";

type Artwork = {
  id: number;
  title: string;
  category: string;
  completionDate?: string;
};

type GalleryProps = {
  artworks: Artwork[];
  categories: GalleryCategory[];
};

export default function Gallery({ artworks, categories }: GalleryProps) {
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");

  const query = search.trim().toLowerCase();

  const visibleArtworks = artworks.filter((artwork) => {
    const matchesCategory =
      category === "all" || artwork.category === category;

    const matchesSearch = artwork.title.toLowerCase().includes(query);

    return matchesCategory && matchesSearch;
  });

  return (
    <>
      <GalleryControls
        categories={categories}
        category={category}
        search={search}
        onCategoryChange={setCategory}
        onSearchChange={setSearch}
      />

      <p className="visually-hidden" role="status">
        {visibleArtworks.length} artworks found.
      </p>

      <div className="artwork-grid">
        {visibleArtworks.map((artwork) => (
          <ArtworkCard
            key={artwork.id}
            title={artwork.title}
            completionDate={artwork.completionDate}
          />
        ))}
      </div>

      {visibleArtworks.length === 0 && (
        <p className="gallery-empty">
          No works match your search. Try another name or category.
        </p>
      )}
    </>
  );
}
