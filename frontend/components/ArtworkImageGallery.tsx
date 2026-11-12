"use client";

import { useState, type ReactNode } from "react";
import ArtworkPhotoCarousel, { type GalleryImage } from "@/components/ArtworkPhotoCarousel";
import ArtworkImageNavigation from "@/components/ArtworkImageNavigation";
import ArtworkImageViewer from "@/components/ArtworkImageViewer";

export default function ArtworkImageGallery({
  images,
  children,
}: {
  images: GalleryImage[];
  children: ReactNode;
}) {
  const [index, setIndex] = useState(0);
  const selected = images[index];

  function navigate(direction: number) {
    setIndex((current) => (current + direction + images.length) % images.length);
  }

  const previous = () => navigate(-1);
  const next = () => navigate(1);
  const navigation = (
    <ArtworkImageNavigation
      index={index}
      count={images.length}
      onPrevious={previous}
      onNext={next}
    />
  );

  return (
    <div className="artwork-detail-layout">
      <section
        className="artwork-photo-gallery"
        aria-label="Artwork images"
        tabIndex={images.length > 1 ? 0 : undefined}
        onKeyDown={(event) => {
          if (images.length < 2 || event.altKey || event.ctrlKey || event.metaKey) return;
          if (event.key === "ArrowLeft") {
            event.preventDefault();
            previous();
          } else if (event.key === "ArrowRight") {
            event.preventDefault();
            next();
          }
        }}
      >
        <ArtworkPhotoCarousel
          images={images}
          index={index}
          onNavigate={navigate}
          className={`artwork-detail-image${selected ? " has-image" : ""}`}
        />
        {navigation}
      </section>
      <div className="artwork-detail-info">
        {children}
        {selected && (
          <ArtworkImageViewer
            images={images}
            index={index}
            onNavigate={navigate}
            navigation={navigation}
            onPrevious={images.length > 1 ? previous : undefined}
            onNext={images.length > 1 ? next : undefined}
          />
        )}
      </div>
    </div>
  );
}
