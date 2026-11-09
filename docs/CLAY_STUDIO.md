# Clay studio — 2026-11-08

Local route: `/clay-studio`, linked from the gallery header. No deployment or backend changes.

Four editable surfaces of revolution: reference-inspired footed vase and rounded jug, moon jar and cylinder. Reference photos guide silhouette only; the model does not reconstruct exact dimensions, decoration, lids, handles or spouts. Dimensions are wet dimensions.

Shape mode: drag right-hand section dots horizontally for radius and vertically for section position (endpoints stay fixed). Keyboard left/right changes diameter. Sliders allow height, diameter, intermediate section height and concave/convex segment bulges. Rotate mode: drag to turn/tilt. Uniform rotational geometry is symmetric around the vertical axis.

Clay is numerical integration of outer minus inner cross-sectional areas, with a solid bottom and open rim. Wall thickness is radial rather than surface-normal, so steep curves are approximations. Adjustable density defaults to an uncalibrated 1.8 g/cm³. Multiply volume by wet density, apply the provisional 1.25 vessel-mass correction described below, then add adjustable trimming/loss allowance. Capacity is to the rim. No firing shrinkage compensation.

Undo/redo is session-only. Save stores one design in this browser's localStorage; Restore saved recalls it. Create share link captures the current design, unit system, and hand visibility in a versioned URL. Opening the link loads an editable copy. Local preview links use localhost.

The unit selector converts displayed measurements without changing the metric values used for modeling. Cylinder designs start with five dots and allow up to ten total, including the base and rim. The scale hand is an 18 cm illustration and can be hidden below the preview.

## Restore point

Base Git revision before this feature: `81b755ac5051ecd7651b0882d34d98e80efcd2d3`.

The working tree already had unrelated changes to `frontend/app/artworks/[slug]/page.tsx` and `frontend/components/ArtworkImageGallery.tsx`. They are untouched. Their pre-feature patch is kept under `docs/checkpoints/clay-studio-before/pre-existing-edits.patch` for reference. Do not reset the entire repository to undo this feature.

To remove only this feature:

1. Restore `frontend/components/GalleryHeader.tsx` from `docs/checkpoints/clay-studio-before/GalleryHeader.tsx` (compare first if it has since been edited).
2. Remove the new `frontend/app/clay-studio/` directory and `frontend/lib/clay.ts` and `frontend/lib/clay-design-link.ts`.
3. Optionally remove this document and its checkpoint folder after verifying restoration.

## Verification

Production build and TypeScript passed with Node 24. Analytic cylinder clay-volume comparison passed, plus checks across all four templates for positive volume/capacity, increased thickness/base/height increasing clay, and the allowance multiplier.

Browser QA: rendered the local page at http://localhost:3000/clay-studio; verified moon jar selection changed dimensions and clay estimate, and Undo restored the vase and its original estimate. Existing local dev server reused; no new server left running. Detailed pointer, touch and mobile testing remains to be done.

## Gallery style update — 2026-11-08

Clay studio now uses the shared GalleryHeader and ThemeToggle inside the same gallery-shell as the homepage. Its colors inherit the gallery light/dark variables, with Arial typography, simple borders and the gallery accent color. The initial studio appearance is backed up as `docs/checkpoints/clay-studio-before/studio-initial.tsx` and `studio-initial.css`; restore these two files to undo only the style update.

## Smooth section transitions — 2026-11-08

Replaced independent smoothstep segments with shape-preserving cubic Hermite interpolation using shared tangents. Section diameters remain exact; ordinary segments avoid overshoot. Concave/convex adjustments use a localized bulge with zero first and second endpoint derivatives. Increased preview mesh resolution. Rendering and clay calculations use the same updated profile, so estimates may change for existing designs. Earlier curve implementation is preserved in `docs/checkpoints/clay-studio-before/clay-before-smoothing.ts` (restore only its interpolation block to undo smoothing without losing template updates).

Checks passed for exact section radii, tangent continuity at joins, bounded interpolation without bulges, positive estimates across templates, and analytic cylinder volume.

## Proportional overall height — 2026-11-08

Overall height uniformly scales section radii and curve amounts with height; normalized section positions remain fixed. Wall/base thickness remain independent. Diameter/curve controls accommodate scaled values and browser restoration accepts larger or smaller profiles. Verified proportion preservation at 5 and 60 cm, reversible scaling, independent thickness and positive estimates across all templates. Radius safety floor now scales with the profile too.

## Moon jar with foot — 2026-11-08

Updated default moon jar to a 25 cm form with 11.8 cm rim, shoulder at 18.75 cm and -2.3 cm shoulder curve. Added a 13.6 cm flared foot narrowing to an editable 11.8 cm foot neck at 2.125 cm, with gentle additional body fullness. Previous defaults are saved in `docs/checkpoints/clay-studio-before/clay-before-moon-foot.ts`. Foot is part of the continuous hollow profile in the current model, not a separately trimmed recessed foot ring; its clay is included in the estimate.

## Keyboard history — 2026-11-08

Command+Z / Ctrl+Z undo; Command+Shift+Z / Ctrl+Shift+Z redo. Ctrl+Y also redoes. Shortcuts use the same history as the buttons and preserve native undo inside text inputs. Button tooltips and accessibility metadata list the keys.

## Shared footer and readability — 2026-11-08

The homepage and Clay studio now use `frontend/components/GalleryFooter.tsx`, preserving the homepage’s kaancinar.com footer and styling. Studio save messages remain above the footer. Studio JSX, CSS, route and geometry code are formatted into readable blocks; principal state names now describe design, selection and rotation. Production build and TypeScript passed.

Rollback note: full feature removal now also requires inlining the GalleryFooter markup back into `frontend/app/page.tsx` before removing `frontend/components/GalleryFooter.tsx`. It is safe to retain the shared footer component when removing the studio.

## Provisional vessel mass correction — 2026-11-08

A PSH 515 cone-6 stoneware bisque example indicated that the previous vessel
estimate was optimistic. Apply a transparent 1.25 multiplier to calculated vessel
mass, before the independently adjustable trimming/loss allowance. The UI names
this adjustment separately. The calculation provides `unadjustedNet` and
`calibrationFactor` alongside the adjusted estimates. Volume, capacity, geometry,
and the selected density are unchanged. Existing saved designs receive the new
model correction when recalculated.

This is a provisional making adjustment based on one observation, not a
manufacturer density, fitted material model, or wet-to-bisque conversion. The
sample's original wet mass, exact wall distribution, and wet dimensions are not
known. Do not substitute cone-6 total shrinkage data for wet-to-bisque shrinkage.
The manufacturer's body reference is https://psh.ca/products/20kg-515-cone-6-cream-clay .
Collect wet/trimmed/dry/bisque weights and corresponding dimensions before making
clay-specific accuracy claims or further tuning the factor.
