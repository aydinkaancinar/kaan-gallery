import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(new URL("../lib/clay.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const context = vm.createContext({ exports: {} });
vm.runInContext(compiled, context);
const { makeDesign, estimate } = context.exports;

function close(actual, expected) {
  assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
}

function cylinderMass(design) {
  const radius = design.sections[0].r;
  const inner = radius - design.wall / 10;
  const base = design.base / 10;
  const volume = Math.PI * radius ** 2 * base +
    Math.PI * (radius ** 2 - inner ** 2) * (design.height - base);
  return volume * design.density / 1000;
}

test("vessel correction increases analytic cylinder mass by 25%", () => {
  const design = { ...makeDesign("cylinder"), allowance: 0 };
  const result = estimate(design);
  const raw = cylinderMass(design);
  close(result.unadjustedNet, raw);
  close(result.net, raw * 1.25);
  close(result.total, result.net);
});

test("trimming allowance is added once, after the vessel correction", () => {
  const design = { ...makeDesign("cylinder"), allowance: 15 };
  const result = estimate(design);
  close(result.total, cylinderMass(design) * 1.25 * 1.15);
  close(result.net, estimate({ ...design, allowance: 0 }).net);
});

test("mass correction does not inflate geometric capacity or diameter", () => {
  const design = makeDesign("cylinder");
  const result = estimate(design);
  const inner = design.sections[0].r - design.wall / 10;
  close(result.capacity, Math.PI * inner ** 2 * (design.height - design.base / 10) / 1000);
  close(result.diameter, design.sections[0].r * 2);
  const denser = estimate({ ...design, density: design.density * 1.1 });
  close(denser.net, result.net * 1.1);
  close(denser.capacity, result.capacity);
});
