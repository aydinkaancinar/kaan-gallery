import Link from "next/link";

export default function GalleryFooter() {
  return (
    <footer className="gallery-footer">
      <p>© Aydın Kaan Çınar. All rights reserved.</p>
      <p>
        For permission to use an artwork,{" "}
        <a href="mailto:akcinar99@gmail.com">contact me</a>.
      </p>
      <p><Link href="/privacy">Privacy policy</Link></p>
      <a
        href="https://kaancinar.com/"
        target="_blank"
        rel="noopener noreferrer"
      >
        kaancinar.com
      </a>
    </footer>
  );
}
