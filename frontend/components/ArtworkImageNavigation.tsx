type ArtworkImageNavigationProps = {
  index: number;
  count: number;
  onPrevious: () => void;
  onNext: () => void;
};

export default function ArtworkImageNavigation({
  index,
  count,
  onPrevious,
  onNext,
}: ArtworkImageNavigationProps) {
  if (count < 2) return null;

  return (
    <div className="artwork-image-navigation" role="group" aria-label="Artwork photos">
      <button type="button" onClick={onPrevious} aria-label="Previous image">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d="m16 4-8 8 8 8" />
        </svg>
      </button>
      <span role="status" aria-live="polite" aria-atomic="true">
        <span className="visually-hidden">Image </span>
        {index + 1} / {count}
      </span>
      <button type="button" onClick={onNext} aria-label="Next image">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d="m8 4 8 8-8 8" />
        </svg>
      </button>
    </div>
  );
}
