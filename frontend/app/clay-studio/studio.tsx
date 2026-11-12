"use client";
import GalleryHeader from "@/components/GalleryHeader";
import GalleryFooter from "@/components/GalleryFooter";
import ThemeToggle from "@/components/ThemeToggle";
import { useEffect, useRef, useState } from "react";
import {
  clamp,
  estimate,
  makeDesign,
  radiusAt,
  resizeProportionally,
  templates,
  type Design,
} from "@/lib/clay";
import {
  CYLINDER_DOT_LIMIT,
  DOT_SPACING,
  isClayDesign,
  makeDesignLink,
} from "@/lib/clay-design-link";
import "./studio.css";

const CM_PER_INCH = 2.54;
const POUNDS_PER_KG = 2.20462262185;
const LITRES_PER_US_GALLON = 3.785411784;
const HAND_HEIGHT_CM = 18;
const PREVIEW_ROWS = 160;
const SAVE_KEY = "kaan-clay-design-v1";

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
  displayFactor = 1,
  precision,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (n: number) => void;
  displayFactor?: number;
  precision?: number;
}) {
  const displayValue = (value * displayFactor).toFixed(
    precision ?? (step < 1 ? 1 : 0),
  );
  return (
    <label className="cs-slider">
      <span>
        {label}
        <output>
          {displayValue} {unit}
        </output>
      </span>
      <input
        type="range"
        aria-valuetext={`${displayValue} ${unit}`}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}
// Sample the same curved profile used by the vessel, rather than connecting section dots.
function templateOutline(template: string) {
  const design = makeDesign(template);
  const samples = Array.from({ length: 101 }, (_, i) => ({
    y: i / 100,
    r: radiusAt(design.sections, i / 100),
  }));
  const size =
    44 / Math.max(design.height, 2 * Math.max(...samples.map((p) => p.r)));
  const bottom = 32 + (design.height * size) / 2;
  const side = (p: { y: number; r: number }, direction: number) =>
    `${30 + direction * p.r * size},${bottom - p.y * design.height * size}`;
  return `M ${samples.map((p) => side(p, -1)).join(" L ")} L ${[...samples]
    .reverse()
    .map((p) => side(p, 1))
    .join(" L ")} Z`;
}
export default function ClayStudio({
  initialDesign,
  initialImperial,
  initialShowHand,
  invalidLink,
  websiteHost,
}: {
  initialDesign?: Design;
  initialImperial: boolean;
  initialShowHand: boolean;
  invalidLink: boolean;
  websiteHost: string;
}) {
  const [design, setDesign] = useState<Design>(
    () => initialDesign ?? makeDesign("vase"),
  );
  const [imperial, setImperial] = useState(initialImperial);
  const [showHand, setShowHand] = useState(initialShowHand);
  const [shareLink, setShareLink] = useState<{
    url: string;
    design: Design;
    imperial: boolean;
    showHand: boolean;
  }>();
  const visibleShareLink =
    shareLink?.design === design &&
    shareLink.imperial === imperial &&
    shareLink.showHand === showHand
      ? shareLink.url
      : undefined;
  const lengthUnit = imperial ? "in" : "cm";
  const weightUnit = imperial ? "lb" : "kg";
  const lengthFactor = imperial ? 1 / CM_PER_INCH : 1;
  const weightFactor = imperial ? POUNDS_PER_KG : 1;
  const formatLength = (cm: number) =>
    `${(cm * lengthFactor).toFixed(imperial ? 2 : 1)} ${lengthUnit}`;
  const formatWeight = (kg: number) => (kg * weightFactor).toFixed(2);
  const [darkMode, setDarkMode] = useState(false);
  useEffect(() => {
    const root = document.documentElement;
    const syncTheme = () => setDarkMode(root.dataset.theme === "dark");
    syncTheme();
    const observer = new MutationObserver(syncTheme);
    observer.observe(root, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  const [selectedSectionIndex, setSelectedSectionIndex] = useState(
      initialDesign ? 0 : 2,
    ),
    [rotateMode, setRotateMode] = useState(false),
    [angle, setAngle] = useState(0.35),
    [tilt, setTilt] = useState(0.16);
  const [history, setHistory] = useState<Design[]>([]),
    [future, setFuture] = useState<Design[]>([]),
    [message, setMessage] = useState("");
  const canvas = useRef<HTMLCanvasElement>(null),
    svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{
    index: number;
    x: number;
    y: number;
    angle: number;
    tilt: number;
  } | null>(null);
  const result = estimate(design),
    section = design.sections[selectedSectionIndex] ?? design.sections[0];
  const floor = 510,
    center = 310;
  const pitch = rotateMode ? tilt : 0.16;
  const depthFactor = Math.abs(Math.sin(pitch));
  const projectedHeight = Math.max(
    ...Array.from({ length: PREVIEW_ROWS + 1 }, (_, i) => {
      const y = i / PREVIEW_ROWS;
      return y * design.height + radiusAt(design.sections, y) * depthFactor;
    }),
  );
  const scale = Math.min(
    390 / Math.max(design.height, showHand ? HAND_HEIGHT_CM : 0),
    225 / Math.max(...design.sections.map((s) => s.r + Math.abs(s.curve))),
    (floor - 52) / projectedHeight,
  );
  function remember() {
    setHistory((h) => [...h.slice(-49), structuredClone(design)]);
    setFuture([]);
  }
  function change(p: Partial<Design>) {
    setDesign((v) => ({ ...v, ...p }));
  }
  function changeSection(p: Partial<typeof section>) {
    setDesign((v) => ({
      ...v,
      sections: v.sections.map((s, i) =>
        i === selectedSectionIndex ? { ...s, ...p } : s,
      ),
    }));
  }
  function undo() {
    if (!history.length) return;
    setFuture((f) => [...f, design]);
    setDesign(history[history.length - 1]);
    setHistory((h) => h.slice(0, -1));
    setSelectedSectionIndex(0);
  }
  function redo() {
    if (!future.length) return;
    setHistory((h) => [...h, design]);
    setDesign(future[future.length - 1]);
    setFuture((f) => f.slice(0, -1));
    setSelectedSectionIndex(0);
  }
  useEffect(() => {
    function handleHistoryShortcut(event: KeyboardEvent) {
      if (
        event.defaultPrevented ||
        event.isComposing ||
        event.altKey ||
        !(event.metaKey || event.ctrlKey)
      )
        return;
      const target = event.target;
      // Let text fields keep their native text undo/redo behavior.
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          target.closest(
            'textarea, input:not([type="range"]):not([type="button"]):not([type="submit"])',
          ))
      )
        return;
      const key = event.key.toLowerCase();
      const isUndo = key === "z" && !event.shiftKey;
      const isRedo =
        (key === "z" && event.shiftKey) ||
        (key === "y" && event.ctrlKey && !event.metaKey && !event.shiftKey);
      if (!isUndo && !isRedo) return;
      event.preventDefault();
      if (event.repeat) return;
      if (isRedo) redo();
      else undo();
    }
    window.addEventListener("keydown", handleHistoryShortcut);
    return () => window.removeEventListener("keydown", handleHistoryShortcut);
  });
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, 620, 600);
    const a = rotateMode ? angle : 0.35;
    function project(r: number, y: number, t: number) {
      const x = r * Math.cos(t + a),
        z = r * Math.sin(t + a);
      return {
        x: center + x * scale,
        y: floor - y * scale + z * Math.sin(pitch) * scale,
        z: z * Math.cos(pitch) + y * Math.sin(pitch),
      };
    }
    // Soft contact shadow anchors the pot to the work surface.
    ctx.save();
    ctx.translate(center, floor + 5);
    ctx.scale(Math.max(...design.sections.map((s) => s.r)) * scale * 1.15, 17);
    const shadow = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
    shadow.addColorStop(0, "rgba(0,0,0,.20)");
    shadow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = shadow;
    ctx.fillRect(-1, -1, 2, 2);
    ctx.restore();
    type Face = {
      p: { x: number; y: number; z: number }[];
      depth: number;
      color: string;
    };
    const faces: Face[] = [];
    const rows = PREVIEW_ROWS,
      sides = 96;
    function ring(
      r0: number,
      y0: number,
      r1: number,
      y1: number,
      inner = false,
    ) {
      for (let j = 0; j < sides; j++) {
        const t = (j / sides) * Math.PI * 2,
          next = ((j + 1) / sides) * Math.PI * 2;
        const p = [
          project(r0, y0, t),
          project(r0, y0, next),
          project(r1, y1, next),
          project(r1, y1, t),
        ];
        // Surface normals include the profile slope, so shoulders catch light too.
        const mid = (t + next) / 2 + a,
          dr = r1 - r0,
          dy = y1 - y0;
        const length = Math.hypot(dy, dr) || 1,
          direction = inner ? -1 : 1;
        const nx = (direction * dy * Math.cos(mid)) / length;
        const ny = (-direction * dr) / length;
        const nz = (direction * dy * Math.sin(mid)) / length;
        const diffuse = Math.max(0, -0.45 * nx + 0.7 * ny + 0.55 * nz);
        const highlight = Math.max(0, -0.26 * nx + 0.42 * ny + 0.87 * nz) ** 20;
        const depth = clamp((y0 + y1) / 2 / design.height, 0, 1);
        const occlusion = inner ? 0.5 + 0.28 * depth : 0.9 + 0.1 * depth;
        const shade = Math.round(
          clamp(
            (darkMode
              ? 128 + 96 * diffuse + 26 * highlight
              : 43 + 79 * diffuse + 25 * highlight) * occlusion,
            24,
            250,
          ),
        );
        faces.push({
          p,
          depth: p.reduce((s, v) => s + v.z, 0) / 4,
          color: `rgb(${shade},${shade},${shade})`,
        });
      }
    }
    for (let i = 0; i < rows; i++) {
      const y0 = (i / rows) * design.height,
        y1 = ((i + 1) / rows) * design.height;
      ring(
        radiusAt(design.sections, i / rows),
        y0,
        radiusAt(design.sections, (i + 1) / rows),
        y1,
      );
      const b = design.base / 10,
        h0 = b + ((design.height - b) * i) / rows,
        h1 = b + ((design.height - b) * (i + 1)) / rows;
      ring(
        Math.max(
          0,
          radiusAt(design.sections, h0 / design.height) - design.wall / 10,
        ),
        h0,
        Math.max(
          0,
          radiusAt(design.sections, h1 / design.height) - design.wall / 10,
        ),
        h1,
        true,
      );
    }
    const top = radiusAt(design.sections, 1),
      bottom = design.base / 10;
    ring(
      top,
      design.height,
      Math.max(0, top - design.wall / 10),
      design.height,
    );
    ring(
      0,
      bottom,
      Math.max(
        0,
        radiusAt(design.sections, bottom / design.height) - design.wall / 10,
      ),
      bottom,
      true,
    );
    ring(0, 0, radiusAt(design.sections, 0), 0);
    faces.sort((a, b) => a.depth - b.depth);
    for (const f of faces) {
      ctx.beginPath();
      f.p.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
      ctx.closePath();
      ctx.fillStyle = f.color;
      ctx.fill();
      ctx.strokeStyle = f.color;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }
  }, [design, angle, pitch, rotateMode, scale, darkMode]);
  function pointer(e: React.PointerEvent<SVGSVGElement>) {
    if (!drag.current || !svg.current) return;
    const rect = svg.current.getBoundingClientRect();
    if (drag.current.index === -1) {
      setAngle(drag.current.angle + (e.clientX - drag.current.x) * 0.012);
      setTilt(
        clamp(
          drag.current.tilt + (e.clientY - drag.current.y) * 0.005,
          -0.45,
          0.6,
        ),
      );
      return;
    }
    const x = ((e.clientX - rect.left) * 620) / rect.width,
      y = ((e.clientY - rect.top) * 600) / rect.height,
      index = drag.current.index;
    setDesign((v) => ({
      ...v,
      sections: v.sections.map((s, i) =>
        i !== index
          ? s
          : {
              ...s,
              r: clamp(
                (x - center) / scale,
                Math.min(1, s.r),
                Math.max(25, s.r),
              ),
              y:
                i === 0
                  ? 0
                  : i === v.sections.length - 1
                    ? 1
                    : clamp(
                        (floor - y) / scale / v.height,
                        v.sections[i - 1].y + DOT_SPACING,
                        v.sections[i + 1].y - DOT_SPACING,
                      ),
            },
      ),
    }));
  }
  function addCylinderDot() {
    if (
      design.template !== "cylinder" ||
      design.sections.length >= CYLINDER_DOT_LIMIT
    )
      return;
    const sections = [...design.sections];
    let gapIndex = 0;
    for (let index = 1; index < sections.length - 1; index++) {
      if (
        sections[index + 1].y - sections[index].y >
        sections[gapIndex + 1].y - sections[gapIndex].y
      ) {
        gapIndex = index;
      }
    }
    const height = (sections[gapIndex].y + sections[gapIndex + 1].y) / 2;
    const radius = radiusAt(sections, height);
    let dotNumber = 1;
    while (
      sections.some((section) => section.name === `Added dot ${dotNumber}`)
    )
      dotNumber++;
    sections.splice(gapIndex + 1, 0, {
      name: `Added dot ${dotNumber}`,
      y: height,
      r: radius,
      curve: 0,
    });
    remember();
    change({ sections });
    setSelectedSectionIndex(gapIndex + 1);
    setRotateMode(false);
  }

  function removeCylinderDot() {
    const lastIndex = design.sections.length - 1;
    if (design.template !== "cylinder" || lastIndex < 2) return;

    // Keep the base and rim. If either is selected, remove the highest interior dot.
    const removeIndex =
      selectedSectionIndex > 0 && selectedSectionIndex < lastIndex
        ? selectedSectionIndex
        : lastIndex - 1;
    const sections = design.sections.filter(
      (_, index) => index !== removeIndex,
    );
    remember();
    change({ sections });
    setSelectedSectionIndex(removeIndex - 1);
    setRotateMode(false);
  }

  function save() {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(design));
      setMessage("Design saved in this browser.");
    } catch {
      setMessage(
        "Browser storage is unavailable. You can still create a share link.",
      );
    }
  }

  function load() {
    try {
      const saved = localStorage.getItem(SAVE_KEY);
      if (!saved) {
        setMessage("No saved design in this browser yet.");
        return;
      }
      const savedDesign: unknown = JSON.parse(saved);
      if (!isClayDesign(savedDesign)) throw new Error("Invalid design");
      remember();
      setDesign(savedDesign);
      setSelectedSectionIndex(0);
      setMessage("Saved design restored.");
    } catch {
      setMessage("Could not restore this saved design.");
    }
  }

  async function shareDesign() {
    const url =
      visibleShareLink ??
      (await makeDesignLink(window.location.href, design, imperial, showHand));
    setShareLink({ url, design, imperial, showHand });
    try {
      await navigator.clipboard.writeText(url);
      setMessage("Design link copied.");
    } catch {
      setMessage("Your design link is ready to copy.");
    }
  }

  return (
    <div className="gallery-shell">
      <ThemeToggle />
      <GalleryHeader currentPage="clay-studio" />
      <main className="cs">
        <div className="cs-intro">
          <div>
            <h1>
              Clay studio{" "}
              <span className="cs-beta">
                <span tabIndex={0} aria-describedby="clay-beta-note">
                  Beta
                </span>
                <span id="clay-beta-note" className="cs-beta-note" role="tooltip">
                  I’m still testing the dimensions and clay estimates against
                  pots I make. I’ll update the tool as I go.
                </span>
              </span>
            </h1>
            <p>
              Design a pottery vessel, adjust its proportions and wall
              thickness, and estimate how much wet clay to prepare.
            </p>
          </div>
          <div className="cs-actions">
            <button
              title="Undo (⌘Z / Ctrl+Z)"
              aria-keyshortcuts="Meta+Z Control+Z"
              disabled={!history.length}
              onClick={undo}
            >
              ↶ Undo
            </button>
            <button
              title="Redo (⌘⇧Z / Ctrl+Shift+Z / Ctrl+Y)"
              aria-keyshortcuts="Meta+Shift+Z Control+Shift+Z Control+Y"
              disabled={!future.length}
              onClick={redo}
            >
              ↷ Redo
            </button>
            <button onClick={save}>Save design</button>
            <button onClick={load}>Restore saved</button>
            <label className="cs-unit-select">
              Units
              <select
                value={imperial ? "imperial" : "metric"}
                onChange={(event) =>
                  setImperial(event.target.value === "imperial")
                }
              >
                <option value="metric">Metric (cm, kg)</option>
                <option value="imperial">Imperial (in, lb)</option>
              </select>
            </label>
          </div>
        </div>
        {invalidLink && (
          <p role="status">
            This design link couldn’t be loaded. The studio opened with its
            default shape.
          </p>
        )}
        <div className="cs-workspace">
          <aside className="cs-panel">
            <p className="cs-eyebrow">01 — START WITH A FORM</p>
            <div className="cs-templates">
              {Object.entries(templates).map(([key, t]) => (
                <button
                  key={key}
                  aria-pressed={design.template === key}
                  onClick={() => {
                    remember();
                    setDesign(makeDesign(key));
                    setSelectedSectionIndex(2);
                  }}
                >
                  <svg viewBox="0 0 60 64" aria-hidden="true">
                    <defs>
                      <linearGradient id={`template-grey-${key}`}>
                        <stop
                          offset="0%"
                          stopColor={darkMode ? "#eeeeee" : "#919191"}
                        />
                        <stop
                          offset="40%"
                          stopColor={darkMode ? "#cccccc" : "#686868"}
                        />
                        <stop
                          offset="100%"
                          stopColor={darkMode ? "#929292" : "#373737"}
                        />
                      </linearGradient>
                    </defs>
                    <path
                      fill={`url(#template-grey-${key})`}
                      d={templateOutline(key)}
                    />
                  </svg>
                  {t.label}
                </button>
              ))}
            </div>
            <div
              className="cs-proportions"
              onPointerDown={remember}
              onKeyDown={(e) => {
                if (e.key.startsWith("Arrow")) remember();
              }}
            >
              <p className="cs-eyebrow">02 — SET THE PROPORTIONS</p>
              {design.template === "cylinder" && (
                <div
                  className="cs-dot-controls"
                  onPointerDown={(event) => event.stopPropagation()}
                >
                  <span id="cylinder-dot-count-label">Dots</span>
                  <div
                    className="cs-dot-stepper"
                    role="group"
                    aria-labelledby="cylinder-dot-count-label"
                  >
                    <button
                      type="button"
                      aria-label="Remove dot"
                      title="Remove the selected interior dot"
                      onClick={removeCylinderDot}
                      disabled={design.sections.length <= 2}
                    >
                      ▾
                    </button>
                    <output aria-label="Dot count">
                      {design.sections.length}
                    </output>
                    <button
                      type="button"
                      aria-label="Add dot"
                      onClick={addCylinderDot}
                      disabled={design.sections.length >= CYLINDER_DOT_LIMIT}
                    >
                      ▴
                    </button>
                  </div>
                </div>
              )}
              <Slider
                label="Overall height"
                value={design.height}
                min={5}
                max={60}
                step={0.5}
                unit={lengthUnit}
                displayFactor={lengthFactor}
                precision={imperial ? 2 : 1}
                onChange={(height) =>
                  setDesign((v) => resizeProportionally(v, height))
                }
              />
              <p className="cs-small">
                Height scales the whole form proportionally. Wall and base
                thickness stay unchanged.
              </p>
              <label className="cs-select">
                Selected section
                <select
                  value={selectedSectionIndex}
                  onChange={(e) => setSelectedSectionIndex(+e.target.value)}
                >
                  {design.sections.map((s, i) => (
                    <option key={i} value={i}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <Slider
                label={`${section.name} diameter`}
                value={section.r * 2}
                min={Math.min(2, section.r * 2)}
                max={Math.max(50, section.r * 2)}
                step={0.1}
                unit={lengthUnit}
                displayFactor={lengthFactor}
                precision={imperial ? 2 : 1}
                onChange={(n) => changeSection({ r: n / 2 })}
              />
              {selectedSectionIndex > 0 &&
                selectedSectionIndex < design.sections.length - 1 && (
                  <Slider
                    label="Height from base"
                    value={section.y * design.height}
                    min={
                      (design.sections[selectedSectionIndex - 1].y +
                        DOT_SPACING) *
                      design.height
                    }
                    max={
                      (design.sections[selectedSectionIndex + 1].y -
                        DOT_SPACING) *
                      design.height
                    }
                    step={0.1}
                    unit={lengthUnit}
                    displayFactor={lengthFactor}
                    precision={imperial ? 2 : 1}
                    onChange={(n) => changeSection({ y: n / design.height })}
                  />
                )}
              {selectedSectionIndex < design.sections.length - 1 && (
                <>
                  <Slider
                    label="Curve to next section"
                    value={section.curve}
                    min={-Math.max(3, Math.abs(section.curve))}
                    max={Math.max(3, Math.abs(section.curve))}
                    step={0.1}
                    unit={lengthUnit}
                    displayFactor={lengthFactor}
                    precision={imperial ? 2 : 1}
                    onChange={(curve) => changeSection({ curve })}
                  />
                  <div className="cs-scale">
                    <span>Concave</span>
                    <span>Convex</span>
                  </div>
                </>
              )}
            </div>
          </aside>
          <section className="cs-stage">
            <div className="cs-stage-top">
              <span>
                YOUR VESSEL <b> / {templates[design.template].label}</b>
              </span>
              <div>
                <button
                  aria-pressed={!rotateMode}
                  onClick={() => setRotateMode(false)}
                >
                  Shape
                </button>
                <button
                  aria-pressed={rotateMode}
                  onClick={() => setRotateMode(true)}
                >
                  Rotate 3D
                </button>
              </div>
            </div>
            <div className="cs-view">
              {showHand && (
                <svg
                  className="cs-hand"
                  viewBox="0 0 620 600"
                  aria-hidden="true"
                >
                  <g
                    transform={`translate(${Math.max(12, center - (result.diameter * scale) / 2 - 7 * scale)}, ${floor - HAND_HEIGHT_CM * scale}) scale(${scale / 10})`}
                  >
                    <path
                      d="M 36 180 L 36 162 C 36 151 29 141 24 131 L 5 103
                         C -1 95 1 87 7 86 C 12 85 18 90 23 95 L 36 108
                         L 28 29 C 27 20 29 15 35 15 C 40 14 43 18 44 26 L 53 78
                         L 52 10 C 52 4 55 0 61 0 C 66 0 69 4 69 10 L 71 76
                         L 77 17 C 78 11 82 8 87 9 C 92 10 94 14 93 21 L 88 81
                         L 98 42 C 99 36 103 33 108 35 C 113 36 114 41 112 47
                         L 102 110 C 101 130 94 146 82 159 L 82 180 Z"
                    />
                    <path
                      className="cs-hand-crease"
                      d="M 36 108 Q 59 117 63 141 M 53 83 Q 74 79 89 90 M 57 112 Q 75 102 91 107"
                    />
                  </g>
                </svg>
              )}
              <canvas
                ref={canvas}
                width={620}
                height={600}
                aria-label="Shaded three dimensional vessel preview"
              />
              <svg
                ref={svg}
                viewBox="0 0 620 600"
                onPointerMove={pointer}
                onPointerUp={() => {
                  drag.current = null;
                }}
                onPointerCancel={() => {
                  drag.current = null;
                }}
                onPointerDown={(e) => {
                  if (rotateMode) {
                    e.currentTarget.setPointerCapture(e.pointerId);
                    drag.current = {
                      index: -1,
                      x: e.clientX,
                      y: e.clientY,
                      angle,
                      tilt,
                    };
                  }
                }}
              >
                <defs>
                  <pattern
                    id="cs-grid"
                    width="25"
                    height="25"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 25 0 L 0 0 0 25"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth=".5"
                      opacity=".15"
                    />
                  </pattern>
                </defs>
                <rect
                  width="620"
                  height="600"
                  fill="url(#cs-grid)"
                  pointerEvents="none"
                />
                <text
                  className="cs-watermark"
                  x={center}
                  y={floor - projectedHeight * scale - 15}
                  textAnchor="middle"
                >
                  {websiteHost}
                </text>
                <line
                  x1="85"
                  y1={floor}
                  x2="535"
                  y2={floor}
                  stroke="#8a8074"
                  opacity=".4"
                />
                {!rotateMode &&
                  design.sections.map((s, i) => {
                    const x = center + s.r * scale,
                      y = floor - s.y * design.height * scale;
                    return (
                      <g key={i}>
                        <line
                          x1={center - s.r * scale}
                          y1={y}
                          x2={x}
                          y2={y}
                          stroke={
                            i === selectedSectionIndex ? "#8d3927" : "#796e60"
                          }
                          strokeDasharray="3 5"
                          opacity=".55"
                        />
                        <circle
                          data-selected={i === selectedSectionIndex}
                          cx={x}
                          cy={y}
                          r={i === selectedSectionIndex ? 7 : 5}
                          fill={
                            i === selectedSectionIndex ? "#8d3927" : "#fff9ef"
                          }
                          stroke="#8d3927"
                          strokeWidth="2"
                          tabIndex={0}
                          role="slider"
                          aria-label={`${s.name} diameter`}
                          aria-valuemin={Math.min(2, s.r * 2)}
                          aria-valuemax={Math.max(50, s.r * 2)}
                          aria-valuenow={Number((s.r * 2).toFixed(1))}
                          aria-valuetext={formatLength(s.r * 2)}
                          onKeyDown={(e) => {
                            if (
                              e.key === "ArrowLeft" ||
                              e.key === "ArrowRight"
                            ) {
                              e.preventDefault();
                              remember();
                              setSelectedSectionIndex(i);
                              setDesign((v) => ({
                                ...v,
                                sections: v.sections.map((p, j) =>
                                  i === j
                                    ? {
                                        ...p,
                                        r: clamp(
                                          p.r +
                                            (e.key === "ArrowRight"
                                              ? 0.05
                                              : -0.05),
                                          Math.min(1, p.r),
                                          Math.max(25, p.r),
                                        ),
                                      }
                                    : p,
                                ),
                              }));
                            }
                          }}
                          onPointerDown={(e) => {
                            e.stopPropagation();
                            svg.current?.setPointerCapture(e.pointerId);
                            remember();
                            setSelectedSectionIndex(i);
                            drag.current = {
                              index: i,
                              x: e.clientX,
                              y: e.clientY,
                              angle,
                              tilt,
                            };
                          }}
                        />
                        <text x={x + 15} y={y + 4} fill="#684d3b" fontSize="11">
                          {formatLength(s.r * 2)}
                        </text>
                      </g>
                    );
                  })}
              </svg>
            </div>
            <label className="cs-hand-toggle">
              <input
                type="checkbox"
                checked={showHand}
                onChange={(event) => setShowHand(event.target.checked)}
              />
              Show hand for scale ({formatLength(HAND_HEIGHT_CM)})
            </label>
            <p className="cs-stage-hint">
              {rotateMode
                ? "Drag to turn and tilt the vessel."
                : "Drag a dot to change diameter and section height."}
            </p>
            <div className="cs-dimensions">
              <span>
                HEIGHT <b>{formatLength(design.height)}</b>
              </span>
              <span>
                MAX. DIAMETER <b>{formatLength(result.diameter)}</b>
              </span>
              <span>
                CAPACITY{" "}
                <b>
                  ≈{" "}
                  {(
                    result.capacity / (imperial ? LITRES_PER_US_GALLON : 1)
                  ).toFixed(2)}{" "}
                  {imperial ? "US gal" : "L"}
                </b>
              </span>
            </div>
          </section>
          <aside className="cs-panel cs-estimate">
            <p className="cs-eyebrow">03 — PREPARE YOUR CLAY</p>
            <div className="cs-weight" aria-live="polite" aria-atomic="true">
              {formatWeight(result.total)}
              <span>{weightUnit}</span>
            </div>
            <p className="cs-weight-caption">Estimated wet clay to prepare</p>
            <div className="cs-breakdown">
              <p>
                Vessel clay{" "}
                <b>
                  {formatWeight(result.net)} {weightUnit}
                </b>
              </p>
              <p>
                Vessel adjustment{" "}
                <b>+{Math.round((result.calibrationFactor - 1) * 100)}%</b>
              </p>
              <p>
                Extra allowance <b>{design.allowance}%</b>
              </p>
            </div>
            <div
              onPointerDown={remember}
              onKeyDown={(e) => {
                if (e.key.startsWith("Arrow")) remember();
              }}
            >
              <Slider
                label="Wall thickness"
                value={design.wall}
                min={2}
                max={15}
                step={0.5}
                unit={imperial ? "in" : "mm"}
                displayFactor={imperial ? 1 / 25.4 : 1}
                precision={imperial ? 2 : 1}
                onChange={(wall) => change({ wall })}
              />
              <Slider
                label="Base thickness"
                value={design.base}
                min={3}
                max={25}
                step={0.5}
                unit={imperial ? "in" : "mm"}
                displayFactor={imperial ? 1 / 25.4 : 1}
                precision={imperial ? 2 : 1}
                onChange={(base) => change({ base })}
              />
              <Slider
                label="Wet clay density"
                value={design.density}
                min={1}
                max={2.5}
                step={0.1}
                unit={imperial ? "lb/in³" : "g/cm³"}
                displayFactor={
                  imperial ? (POUNDS_PER_KG * CM_PER_INCH ** 3) / 1000 : 1
                }
                precision={imperial ? 3 : 1}
                onChange={(density) => change({ density })}
              />
              <Slider
                label="Extra for trimming & loss"
                value={design.allowance}
                min={0}
                max={40}
                unit="%"
                onChange={(allowance) => change({ allowance })}
              />
            </div>
            <details>
              <summary>How the estimate works</summary>
              <p>
                Use this as a starting estimate for wet clay, including your
                trimming allowance. Enter dimensions before drying and firing.
              </p>
              <p>
                The model is based on my experience, with a provisional 25%
                adjustment informed by a PSH 515 bisque-fired piece. I’ll refine
                it as I make and measure more pots.
              </p>
              <p>
                Adjust the density for your clay and allow more for steep
                shoulders. Shrinkage, lids, handles and spouts aren’t included.
              </p>
            </details>
            <div className="cs-share">
              <button onClick={shareDesign}>
                {visibleShareLink ? "Copy design link" : "Create share link"}
              </button>
              {visibleShareLink && (
                <label>
                  Design link
                  <input
                    readOnly
                    value={visibleShareLink}
                    onFocus={(event) => event.currentTarget.select()}
                  />
                </label>
              )}
            </div>
          </aside>
        </div>
        <p className="cs-save-status" role="status">
          {message ||
            "Save keeps one design in this browser. A share link opens a copy of your current design."}
        </p>
      </main>
      <GalleryFooter />
    </div>
  );
}
