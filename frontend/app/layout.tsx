import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: "Aydın Kaan Çınar — Art Gallery",
  description: "Ceramics, objects, and illustrations by Aydın Kaan Çınar.",
  openGraph: {
    type: "website",
    siteName: "Kaan Gallery",
    title: "Aydın Kaan Çınar — Art Gallery",
    description: "Ceramics, objects, and illustrations by Aydın Kaan Çınar.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Aydın Kaan Çınar — Art Gallery",
    description: "Ceramics, objects, and illustrations by Aydın Kaan Çınar.",
    images: [{
      url: "/opengraph-image.png",
      alt: "Red sun emblem beside the stacked name Aydın Kaan Çınar.",
    }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
