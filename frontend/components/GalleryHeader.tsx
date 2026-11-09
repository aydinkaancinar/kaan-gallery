import Image from "next/image";
import Link from "next/link";

export default function GalleryHeader({ backToGallery = false }: { backToGallery?: boolean }) {
  return (
    <header className="gallery-header" style={{ flexWrap: "wrap" }}>
      <Link className="gallery-identity" href="/" aria-label="Aydın Kaan Çınar — Home">
        <Image
          unoptimized
          src="/images/red-sun.jpeg"
          alt=""
          width={126}
          height={138}
          className="gallery-logo logo-light"
        />
        <Image
          unoptimized
          src="/images/black-sun.jpeg"
          alt=""
          width={126}
          height={138}
          className="gallery-logo logo-dark"
        />

        <span className="identity-divider" aria-hidden="true" />

        <span className="gallery-name" aria-hidden="true">
          {["AYDIN", "KAAN", "ÇINAR"].map((name) => (
            <span className="name-line" key={name}>
              {Array.from(name).map((letter, index) => (
                <span key={index}>{letter}</span>
              ))}
            </span>
          ))}
        </span>
      </Link>
      <nav aria-label="Gallery navigation" style={{ width: "100%", textAlign: "center", marginTop: 22 }}>
        <Link href={backToGallery ? "/" : "/clay-studio"} style={{ color: "var(--accent)", fontSize: 12, textUnderlineOffset: 4 }}>{backToGallery ? "Back to the gallery" : "Clay studio — design a pot"}</Link>
      </nav>
    </header>
  );
}
