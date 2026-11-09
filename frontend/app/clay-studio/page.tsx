import type { Metadata } from "next";
import { inflateSync } from "node:zlib";
import { readSharedDesign } from "@/lib/clay-design-link";
import ClayStudio from "./studio";
export const metadata: Metadata = {
  title: "Clay studio — Kaan Gallery",
  description: "Shape a vessel and estimate its wet clay weight.",
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
    />
  );
}
