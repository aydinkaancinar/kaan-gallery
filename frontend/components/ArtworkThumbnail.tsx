"use client";

import Image from "next/image";

function markPending(image: HTMLImageElement | null) {
  // Keep thumbnails that loaded before hydration visible.
  if (image && !image.complete) image.dataset.loading = "";
}

export default function ArtworkThumbnail({
  src,
  alt,
  priority,
  eager = priority,
  draggable,
}: {
  src: string;
  alt: string;
  priority?: boolean;
  eager?: boolean;
  draggable?: boolean;
}) {
  return (
    <Image
      ref={markPending}
      className="artwork-fade-image"
      src={src}
      alt={alt}
      fill
      unoptimized
      draggable={draggable}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : undefined}
      onLoad={(event) => delete event.currentTarget.dataset.loading}
      onError={(event) => delete event.currentTarget.dataset.loading}
    />
  );
}
