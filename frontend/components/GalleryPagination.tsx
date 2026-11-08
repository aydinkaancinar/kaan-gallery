import Link from "next/link";

// Keep in sync with REST_FRAMEWORK["PAGE_SIZE"] in Django settings.
const PAGE_SIZE = 9;

function Chevron({ double = false }: { double?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {double ? (
        <>
          <path d="m10 4-8 8 8 8" />
          <path d="m22 4-8 8 8 8" />
        </>
      ) : (
        <path d="m16 4-8 8 8 8" />
      )}
    </svg>
  );
}

type GalleryPaginationProps = {
  page: number;
  count: number;
  hasPrevious: boolean;
  hasNext: boolean;
  filtersQuery: string;
};

export default function GalleryPagination({
  page,
  count,
  hasPrevious,
  hasNext,
  filtersQuery,
}: GalleryPaginationProps) {
  const lastPage = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const controls = [
    { label: "First page", page: 1, enabled: hasPrevious, double: true },
    { label: "Previous page", page: page - 1, enabled: hasPrevious, double: false },
    { label: "Next page", page: page + 1, enabled: hasNext, double: false },
    { label: "Last page", page: lastPage, enabled: hasNext, double: true },
  ];
  function pageHref(targetPage: number) {
    const params = new URLSearchParams(filtersQuery);
    params.set("page", String(targetPage));
    return `/?${params.toString()}`;
  }

  function renderControl(control: (typeof controls)[number]) {
    const icon = <Chevron double={control.double} />;
    return control.enabled ? (
      <Link
        key={control.label}
        href={pageHref(control.page)}
        prefetch={false}
        aria-label={control.label}
        className="pagination-control"
      >
        {icon}
      </Link>
    ) : (
      <span
        key={control.label}
        className="pagination-control pagination-disabled"
        role="link"
        aria-label={control.label}
        aria-disabled="true"
      >
        {icon}
      </span>
    );
  }

  return (
    <nav className="gallery-pagination" aria-label="Gallery pages">
      <div className="pagination-side">
        {controls.slice(0, 2).map(renderControl)}
      </div>
      <span aria-current="page" aria-label={`Page ${page}`}>{page}</span>
      <div className="pagination-side pagination-forward">
        {controls.slice(2).map(renderControl)}
      </div>
    </nav>
  );
}
