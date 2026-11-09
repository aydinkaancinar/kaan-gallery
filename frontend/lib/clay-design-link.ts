import { templates, type Design, type Section } from "./clay";

export const CYLINDER_DOT_LIMIT = 10;
export const DOT_SPACING = 0.025;

function inRange(value: unknown, min: number, max: number): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= min &&
    value <= max
  );
}

function isSection(value: unknown): value is Section {
  if (!value || typeof value !== "object") return false;
  const section = value as Partial<Section>;
  return (
    typeof section.name === "string" &&
    section.name.length > 0 &&
    section.name.length <= 48 &&
    inRange(section.y, 0, 1) &&
    inRange(section.r, Number.MIN_VALUE, 300) &&
    inRange(section.curve, -360, 360)
  );
}

export function isClayDesign(value: unknown): value is Design {
  if (!value || typeof value !== "object") return false;
  const design = value as Partial<Design>;
  const { template, sections } = design;
  return (
    typeof template === "string" &&
    Object.hasOwn(templates, template) &&
    inRange(design.height, 5, 60) &&
    inRange(design.wall, 2, 15) &&
    inRange(design.base, 3, 25) &&
    inRange(design.density, 1, 2.5) &&
    inRange(design.allowance, 0, 40) &&
    Array.isArray(sections) &&
    sections.length >= 2 &&
    sections.length <= 12 &&
    sections.every(
      (section, index) =>
        isSection(section) &&
        (index === 0 || section.y > sections[index - 1].y),
    ) &&
    sections[0].y === 0 &&
    sections[sections.length - 1].y === 1
  );
}

export function readSharedDesign(
  encoded: string | undefined,
): Design | undefined {
  if (!encoded?.startsWith("1:") || encoded.length > 4000) return undefined;
  try {
    const design: unknown = JSON.parse(encoded.slice(2));
    return isClayDesign(design) ? design : undefined;
  } catch {
    return undefined;
  }
}

export async function makeDesignLink(
  currentUrl: string,
  design: Design,
  imperial: boolean,
  showHand: boolean,
) {
  const url = new URL(currentUrl);
  const payload = JSON.stringify(design);
  let encoded = `1:${payload}`;
  try {
    const compressed = new Blob([payload])
      .stream()
      .pipeThrough(new CompressionStream("deflate"));
    const bytes = new Uint8Array(await new Response(compressed).arrayBuffer());
    const token = btoa(String.fromCharCode(...bytes))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replace(/=+$/, "");
    encoded = `2.${token}`;
  } catch {
    // Older browsers can still create links using the original format.
  }
  url.searchParams.set("design", encoded);
  if (imperial) url.searchParams.set("units", "imperial");
  else url.searchParams.delete("units");
  if (!showHand) url.searchParams.set("hand", "off");
  else url.searchParams.delete("hand");
  return url.toString();
}
