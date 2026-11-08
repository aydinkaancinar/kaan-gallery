import MonthRange from "@/components/MonthRange";

export type GalleryCategory = {
  value: string;
  label: string;
};

type GalleryControlsProps = {
  categories: GalleryCategory[];
  category: string;
  search: string;
  onCategoryChange: (category: string) => void;
  onSearchChange: (search: string) => void;
  earliest?: string | null;
  latest?: string | null;
  createdFrom?: string;
  createdTo?: string;
  onDateCommit?: (from: string, to: string) => void;
};

export default function GalleryControls({
  categories,
  category,
  search,
  onCategoryChange,
  onSearchChange,
  earliest,
  latest,
  createdFrom,
  createdTo,
  onDateCommit,
}: GalleryControlsProps) {
  return (
    <div className="gallery-controls">
      <div
        className="category-controls"
        role="group"
        aria-label="Artwork category"
      >
        {[{ value: "all", label: "All works" }, ...categories].map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={category === option.value}
            onClick={() => onCategoryChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

        <MonthRange
        key={`${earliest}:${latest}:${createdFrom}:${createdTo}`}
        earliest={earliest}
        latest={latest}
        createdFrom={createdFrom}
        createdTo={createdTo}
        onCommit={onDateCommit}
        />

      <label className="gallery-search">
        <span className="visually-hidden">Search artworks</span>
        <span className="search-icon" aria-hidden="true">⌕</span>
        <input
          type="search"
          name="search"
          placeholder="Search works…"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
    </div>
  );
}
