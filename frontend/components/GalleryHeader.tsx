import Image from "next/image";
import Link from "next/link";

export default function GalleryHeader({ currentPage }: { currentPage?: "home" | "clay-studio" }) {
  return (
    <>
      <header className="gallery-header">
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
      </header>
      <nav className="gallery-navigation" aria-label="Gallery navigation">
        <Link href="/" aria-current={currentPage === "home" ? "page" : undefined}>
          Home
        </Link>
        <Link href="/clay-studio" aria-current={currentPage === "clay-studio" ? "page" : undefined}>
          Clay Studio
        </Link>
      </nav>
    </>
  );
}
