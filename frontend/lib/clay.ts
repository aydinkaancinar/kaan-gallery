export type Section = { name: string; y: number; r: number; curve: number };
export type Design = {
  template: string;
  height: number;
  wall: number;
  base: number;
  density: number;
  allowance: number;
  sections: Section[];
};
export const templates: Record<
  string,
  { label: string; height: number; points: [string, number, number, number?][] }
> = {
  vase: {
    label: "Footed vase",
    height: 32,
    points: [
      ["Foot", 0, 6],
      ["Stem", 0.15, 3.4],
      ["Belly", 0.575, 8.45],
      ["Neck", 0.755, 6.6],
      ["Shoulder", 0.84, 9.45, -1.7],
      ["Rim", 1, 4.65],
    ],
  },
  moon: {
    label: "Moon jar",
    height: 25,
    points: [
      ["Foot", 0, 5.3],
      ["Foot neck", 0.07, 5.2],
      ["Lower body", 0.24, 10.25, 0.25],
      ["Belly", 0.53, 12.5, 0.2],
      ["Shoulder", 0.75, 10.3, -2.3],
      ["Rim", 1, 5.9],
    ],
  },
  cylinder: {
    label: "Cylinder",
    height: 20,
    points: [
      ["Base", 0, 6],
      ["Lower body", 0.25, 6],
      ["Middle", 0.5, 6],
      ["Upper body", 0.75, 6],
      ["Rim", 1, 6],
    ],
  },
  jug: {
    label: "Rounded jug",
    height: 20,
    points: [
      ["Foot", 0, 4.1],
      ["Lower body", 0.15, 8.15],
      ["Belly", 0.4, 8.05],
      ["Shoulder", 0.6, 6.2],
      ["Neck", 0.84, 2.6],
      ["Rim", 1, 4.7],
    ],
  },
};
export function makeDesign(template: string): Design {
  const t = templates[template];
  return {
    template,
    height: t.height,
    wall: 6,
    base: 8,
    density: 1.8,
    allowance: 15,
    sections: t.points.map(([name, y, r, curve = 0]) => ({
      name,
      y,
      r,
      curve,
    })),
  };
}
// Scale the outer form uniformly; thickness remains a separate making choice.
export function resizeProportionally(design: Design, height: number): Design {
  const factor = height / design.height;
  return {
    ...design,
    height,
    sections: design.sections.map((s) => ({
      ...s,
      r: s.r * factor,
      curve: s.curve * factor,
    })),
  };
}
export const clamp = (n: number, min: number, max: number) =>
  Math.max(min, Math.min(max, n));
// Shape-preserving cubic Hermite interpolation shares a tangent at each section.
// This avoids a forced horizontal tangent (and visible bump) at every control point.
function tangent(sections: Section[], i: number): number {
  const slope = (j: number) =>
    (sections[j + 1].r - sections[j].r) / (sections[j + 1].y - sections[j].y);
  const last = sections.length - 1;
  if (i === 0 || i === last) {
    const j = i === 0 ? 0 : last - 1;
    if (last === 1) return slope(j);
    const k = i === 0 ? 1 : last - 2;
    const h = sections[j + 1].y - sections[j].y,
      adjacent = sections[k + 1].y - sections[k].y;
    const d = slope(j),
      next = slope(k);
    const m = ((2 * h + adjacent) * d - h * next) / (h + adjacent);
    if (m * d <= 0) return 0;
    return d * next <= 0 && Math.abs(m) > 3 * Math.abs(d) ? 3 * d : m;
  }
  const before = slope(i - 1),
    after = slope(i);
  if (before * after <= 0) return 0;
  const h0 = sections[i].y - sections[i - 1].y,
    h1 = sections[i + 1].y - sections[i].y;
  const w0 = 2 * h1 + h0,
    w1 = h1 + 2 * h0;
  return (w0 + w1) / (w0 / before + w1 / after);
}
export function radiusAt(sections: Section[], y: number): number {
  let i = 0;
  while (i < sections.length - 2 && y > sections[i + 1].y) i++;
  const a = sections[i],
    b = sections[i + 1],
    h = b.y - a.y,
    t = clamp((y - a.y) / h, 0, 1);
  const t2 = t * t,
    t3 = t2 * t;
  const radius =
    (2 * t3 - 3 * t2 + 1) * a.r +
    (t3 - 2 * t2 + t) * h * tangent(sections, i) +
    (-2 * t3 + 3 * t2) * b.r +
    (t3 - t2) * h * tangent(sections, i + 1);
  // A localized bulge with zero first and second derivatives at both endpoints.
  const bulge = 64 * t3 * (1 - t) ** 3;
  return Math.max(
    Math.min(...sections.map((s) => s.r)) * 0.1,
    radius + a.curve * bulge,
  );
}
// Provisional correction after a real PSH 515 bisque example exceeded the
// earlier wet-vessel estimate. This is not a measured clay density or a
// wet-to-bisque conversion; revise when wet weights and thickness are known.
export const VESSEL_MASS_FACTOR = 1.25;

// Axisymmetric shell: radial wall thickness, solid base, open top. cm³ × g/cm³ → kg.
export function estimate(d: Design) {
  const n = 1600,
    dy = d.height / n,
    wall = d.wall / 10,
    bottom = d.base / 10;
  let clay = 0,
    capacity = 0,
    maxRadius = 0;
  for (let i = 0; i < n; i++) {
    const h = (i + 0.5) * dy,
      r = radiusAt(d.sections, h / d.height);
    const inner = h < bottom ? 0 : Math.max(0, r - wall);
    clay += Math.PI * (r * r - inner * inner) * dy;
    capacity += Math.PI * inner * inner * dy;
    maxRadius = Math.max(maxRadius, r);
  }
  const unadjustedNet = (clay * d.density) / 1000;
  const net = unadjustedNet * VESSEL_MASS_FACTOR;
  return {
    unadjustedNet,
    calibrationFactor: VESSEL_MASS_FACTOR,
    net,
    total: net * (1 + d.allowance / 100),
    capacity: capacity / 1000,
    diameter: maxRadius * 2,
  };
}
