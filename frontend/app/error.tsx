"use client";

import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";

type GalleryErrorProps = {
  retry: () => void;
};

export default function GalleryError({ retry }: GalleryErrorProps) {
  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />

      <main className="gallery-state">
        <h1>The gallery couldn’t load</h1>
        <p>Please try again in a moment.</p>

        <button
          className="gallery-retry"
          type="button"
          onClick={() => retry()}
        >
          Try again
        </button>
      </main>
    </div>
  );
}
