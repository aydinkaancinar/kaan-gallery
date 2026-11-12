"use client";

import ArtworkPhotoCarousel, { type GalleryImage } from "@/components/ArtworkPhotoCarousel";
import { useRef, useState, type ReactNode } from "react";

export default function ArtworkImageViewer({
  images,
  index,
  onNavigate,
  navigation,
  onPrevious,
  onNext,
}: {
  images: GalleryImage[];
  index: number;
  onNavigate: (direction: number) => void;
  navigation?: ReactNode;
  onPrevious?: () => void;
  onNext?: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        className="artwork-view"
        type="button"
        aria-haspopup="dialog"
        onClick={() => {
          setIsOpen(true);
          dialog.current?.showModal();
        }}
      >
        View image <span aria-hidden="true">↗</span>
      </button>
      <dialog
        ref={dialog}
        className="artwork-viewer"
        aria-label="Full artwork image"
        onClose={() => setIsOpen(false)}
        onKeyDown={(event) => {
          if (event.altKey || event.ctrlKey || event.metaKey) return;
          if (event.key === "ArrowLeft" && onPrevious) {
            event.preventDefault();
            onPrevious();
          } else if (event.key === "ArrowRight" && onNext) {
            event.preventDefault();
            onNext();
          }
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
      >
        <button
          className="artwork-viewer-close"
          type="button"
          onClick={() => dialog.current?.close()}
        >
          Close <span aria-hidden="true">×</span>
        </button>
        {isOpen && (
          <ArtworkPhotoCarousel
            images={images}
            index={index}
            onNavigate={onNavigate}
            className="artwork-viewer-image"
            fullSize
          />
        )}
        <div className="artwork-viewer-navigation">{navigation}</div>
      </dialog>
    </>
  );
}
