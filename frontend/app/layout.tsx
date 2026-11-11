import type { Metadata } from "next";
import "./globals.css";
import { themeBootstrapScript } from "@/components/theme-store";
import {
  GALLERY_DESCRIPTION, GALLERY_PREVIEW, GALLERY_TITLE, SITE_NAME, SITE_URL,
} from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: SITE_URL,
  robots: process.env.VERCEL_ENV === "preview" ? { index: false, follow: false } : undefined,
  title: GALLERY_TITLE,
  description: GALLERY_DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: GALLERY_TITLE,
    description: GALLERY_DESCRIPTION,
    images: [GALLERY_PREVIEW],
  },
  twitter: {
    card: "summary_large_image",
    title: GALLERY_TITLE,
    description: GALLERY_DESCRIPTION,
    images: [GALLERY_PREVIEW],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
