import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";

export default function Loading() {
  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />

      <main className="gallery-main">
        <h1 className="visually-hidden">Artworks</h1>
        <p className="gallery-summary" role="status">
          Loading artworks…
        </p>

        <div className="artwork-grid" aria-hidden="true">
          {Array.from({ length: 9 }, (_, index) => (
            <div key={index}>
              <div className="artwork-image" />
              <div className="loading-caption" />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
