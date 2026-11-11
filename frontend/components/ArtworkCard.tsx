import Image from "next/image";
import Link from "next/link";

type ArtworkCardProps = {
  title: string;
  completionDate?: string;
  imageUrl?: string;
  imageAlt?: string;
  href?: string;
  priority?: boolean;
};

export default function ArtworkCard({
  title,
  completionDate,
  imageUrl,
  imageAlt,
  href,
  priority,
}: ArtworkCardProps) {
  const displayDate = completionDate
    ? `${completionDate.slice(5, 7)}/${completionDate.slice(2, 4)}`
    : null;

  const content = (
    <>
        <div className="artwork-image">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={imageAlt || title}
            fill
            unoptimized
            loading={priority ? "eager" : "lazy"}
            fetchPriority={priority ? "high" : undefined}
          />
        ) : (
          <span className="visually-hidden">Image unavailable</span>
        )}
      </div>
      <h2>
        {title}
        {completionDate && (
          <time dateTime={completionDate}>{displayDate}</time>
        )}
      </h2>
    </>
    );

  return (
  <article className="artwork-card">
    {href ? (
      <Link className="artwork-card-link" href={href} prefetch={false}>
        {content}
      </Link>
    ) : (
      content
    )}
  </article>
);
}
