"use client";

import Image from "next/image";
import { useState, type ReactNode } from "react";
import ArtworkImageNavigation from "@/components/ArtworkImageNavigation";
import ArtworkImageViewer from "@/components/ArtworkImageViewer";

type GalleryImage = {
  id: number;
  src: string;
  viewerSrc: string;
  alt: string;
};

export default function ArtworkImageGallery({
  images,
  children,
}: {
  images: GalleryImage[];
  children: ReactNode;
}) {
  const [index, setIndex] = useState(0);
  const selected = images[index];
  const previous = () => setIndex((current) => (current - 1 + images.length) % images.length);
  const next = () => setIndex((current) => (current + 1) % images.length);
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
        <div className={`artwork-detail-image${selected ? " has-image" : ""}`}>
          {selected ? (
            <Image
              src={selected.src}
              alt={selected.alt}
              fill
              unoptimized
              loading="eager"
              fetchPriority="high"
            />
          ) : (
            <span>Image unavailable</span>
          )}
        </div>
        {navigation}
      </section>
      <div className="artwork-detail-info">
        {children}
        {selected && (
          <ArtworkImageViewer
            src={selected.viewerSrc}
            alt={selected.alt}
            navigation={navigation}
            onPrevious={images.length > 1 ? previous : undefined}
            onNext={images.length > 1 ? next : undefined}
          />
        )}
      </div>
    </div>
  );
}
