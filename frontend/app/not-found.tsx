import GalleryHeader from "@/components/GalleryHeader";
import ThemeToggle from "@/components/ThemeToggle";

export default function NotFound() {
  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader />

      <main className="gallery-state">
        <h1>Page not found</h1>
        <p>There is nothing here ... yet.</p>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- Reload to clear the same-path 404 boundary. */}
        <a href="/">Return to all artworks</a>
      </main>
    </div>
  );
}
