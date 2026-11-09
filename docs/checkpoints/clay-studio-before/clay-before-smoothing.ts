export type Section = { name: string; y: number; r: number; curve: number };
export type Design = { template: string; height: number; wall: number; base: number; density: number; allowance: number; sections: Section[] };
export const templates: Record<string, { label: string; height: number; points: [string, number, number, number?][] }> = {
  vase: { label: 'Footed vase', height: 32, points: [['Foot',0,6],['Stem',.15,3.4],['Belly',.575,8.45],['Neck',.755,6.6],['Shoulder',.84,9.45,-1.7],['Rim',1,4.65]] },
  moon: { label: 'Moon jar', height: 25, points: [['Foot',0,5],['Lower body',.22,10.5],['Belly',.5,12.5],['Shoulder',.77,10.3,-1.7],['Rim',1,4.9]] },
  cylinder: { label: 'Cylinder', height: 20, points: [['Base',0,6],['Lower body',.25,6],['Middle',.5,6],['Upper body',.75,6],['Rim',1,6]] },
  jug: { label: 'Rounded jug', height: 20, points: [['Foot',0,4.1],['Lower body',.15,8.15],['Belly',.4,8.05],['Shoulder',.6,6.2],['Neck',.84,2.6],['Rim',1,4.7]] },
};
export function makeDesign(template: string): Design {
  const t = templates[template];
  return {template, height:t.height, wall:6, base:8, density:1.8, allowance:15, sections:t.points.map(([name,y,r,curve=0])=>({name,y,r,curve}))};
}
export const clamp = (n:number, min:number, max:number) => Math.max(min,Math.min(max,n));
// Monotone smoothstep preserves section radii; the per-segment bulge is zero at both ends.
export function radiusAt(sections:Section[], y:number):number {
  let i=0; while(i<sections.length-2 && y>sections[i+1].y) i++;
  const a=sections[i], b=sections[i+1], t=clamp((y-a.y)/(b.y-a.y),0,1);
  return Math.max(.8,a.r+(b.r-a.r)*t*t*(3-2*t)+a.curve*Math.sin(Math.PI*t)**2);
}
// Axisymmetric shell: radial wall thickness, solid base, open top. cm³ × g/cm³ → kg.
export function estimate(d:Design) {
  const n=1600, dy=d.height/n, wall=d.wall/10, bottom=d.base/10;
  let clay=0, capacity=0, maxRadius=0;
  for(let i=0;i<n;i++) {
    const h=(i+.5)*dy, r=radiusAt(d.sections,h/d.height);
    const inner=h<bottom?0:Math.max(0,r-wall);
    clay+=Math.PI*(r*r-inner*inner)*dy;
    capacity+=Math.PI*inner*inner*dy;
    maxRadius=Math.max(maxRadius,r);
  }
  const net=clay*d.density/1000;
  return {net, total:net*(1+d.allowance/100), capacity:capacity/1000, diameter:maxRadius*2};
}
