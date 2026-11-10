"use client";

import Image from "next/image";
import { useRef, useState, type ReactNode } from "react";

export default function ArtworkImageViewer({
  src,
  alt,
  navigation,
  onPrevious,
  onNext,
}: {
  src: string;
  alt: string;
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
        <div className="artwork-viewer-image">
          {isOpen && <Image src={src} alt={alt} fill unoptimized loading="eager" />}
        </div>
        <div className="artwork-viewer-navigation">{navigation}</div>
      </dialog>
    </>
  );
}
