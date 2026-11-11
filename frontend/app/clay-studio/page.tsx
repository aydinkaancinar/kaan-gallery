import type { Metadata } from "next";
import { inflateSync } from "node:zlib";
import { readSharedDesign } from "@/lib/clay-design-link";
import StructuredData from "@/components/StructuredData";
import { GALLERY_PREVIEW, SITE_NAME, SITE_URL } from "@/lib/site";
import ClayStudio from "./studio";

const studioPath = "/clay-studio";
const title = "Clay Studio — Pottery Design and Clay Weight Calculator";
const description =
  "Design a pottery vessel, adjust its proportions and wall thickness, and estimate how much wet clay to prepare.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: studioPath },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title,
    description,
    url: studioPath,
    images: [GALLERY_PREVIEW],
  },
  twitter: { card: "summary_large_image", title, description, images: [GALLERY_PREVIEW] },
};
function decodeDesignParameter(encoded: string | undefined) {
  if (!encoded?.startsWith("2.")) return encoded;
  if (encoded.length > 4000 || !/^2\.[A-Za-z0-9_-]+$/.test(encoded))
    return undefined;

  try {
    const compressed = Buffer.from(encoded.slice(2), "base64url");
    const json = inflateSync(compressed, { maxOutputLength: 3998 }).toString(
      "utf8",
    );
    return `1:${json}`;
  } catch {
    return undefined;
  }
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{
    design?: string | string[];
    units?: string;
    hand?: string;
  }>;
}) {
  const params = await searchParams;
  const encoded = typeof params.design === "string" ? params.design : undefined;
  const design = readSharedDesign(decodeDesignParameter(encoded));
  return (
    <>
      <StructuredData data={{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Clay Studio",
        url: new URL(studioPath, SITE_URL).href,
        description,
      }} />
      <ClayStudio
        key={JSON.stringify([
          design,
          params.units,
          params.hand,
          params.design !== undefined,
        ])}
        initialDesign={design}
        initialImperial={params.units === "imperial"}
        initialShowHand={params.hand !== "off"}
        invalidLink={params.design !== undefined && !design}
        websiteHost={process.env.SITE_URL ? SITE_URL.hostname : "kaancinar.com"}
      />
    </>
  );
}
