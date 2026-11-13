import Link from "next/link";

export default function GalleryFooter() {
  return (
    <footer className="gallery-footer">
      <p>© Aydın Kaan Çınar. All rights reserved.</p>
      <p>
        For permission to use an artwork,{" "}
        <a href="mailto:akcinar99@gmail.com">contact me</a>.
      </p>
      <p>
        <Link href="/privacy">Privacy policy</Link>
        {" · "}
        <a href="/THIRD_PARTY_LICENSES.txt">Software licenses</a>
      </p>
      <a
        href="https://kaancinar.com/"
        target="_blank"
        rel="noopener noreferrer"
      >
        kaancinar.com
      </a>
      <p>
        <a className="gallery-project-link" href="https://github.com/aydinkaancinar/kaan-gallery">
          For more information about this project
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
            <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38l-.01-1.49c-2.23.48-2.7-1-2.7-1-.36-.92-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.22.82 1.22.82.72 1.22 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.65-.89-3.65-3.96 0-.87.31-1.58.82-2.14-.08-.2-.35-1.01.08-2.11 0 0 .67-.21 2.2.82a7.64 7.64 0 0 1 4 0c1.53-1.03 2.2-.82 2.2-.82.43 1.1.16 1.91.08 2.11.51.56.82 1.27.82 2.14 0 3.08-1.87 3.76-3.66 3.96.29.25.55.74.55 1.49l-.01 2.24c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
          </svg>
        </a>
      </p>
    </footer>
  );
}
