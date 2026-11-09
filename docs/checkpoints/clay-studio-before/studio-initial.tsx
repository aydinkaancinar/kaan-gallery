'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { clamp, estimate, makeDesign, radiusAt, templates, type Design } from '@/lib/clay';
import './studio.css';

function Slider({label,value,min,max,step=1,unit='',onChange}:{label:string;value:number;min:number;max:number;step?:number;unit?:string;onChange:(n:number)=>void}) {
  return <label className="cs-slider"><span>{label}<output>{value.toFixed(step<1?1:0)} {unit}</output></span><input type="range" min={min} max={max} step={step} value={value} onChange={e=>onChange(Number(e.target.value))}/></label>;
}
export default function ClayStudio() {
  const [d,setD]=useState<Design>(()=>makeDesign('vase'));
  const [selected,setSelected]=useState(2), [orbit,setOrbit]=useState(false), [angle,setAngle]=useState(.35), [tilt,setTilt]=useState(.16);
  const [history,setHistory]=useState<Design[]>([]), [future,setFuture]=useState<Design[]>([]), [message,setMessage]=useState('');
  const canvas=useRef<HTMLCanvasElement>(null), svg=useRef<SVGSVGElement>(null);
  const drag=useRef<{index:number; x:number; y:number; angle:number; tilt:number}|null>(null);
  const result=estimate(d), section=d.sections[selected]??d.sections[0];
  const scale= Math.min(390/d.height,225/Math.max(...d.sections.map(s=>s.r+Math.abs(s.curve))));
  const floor=510, center=310;
  function remember() {setHistory(h=>[...h.slice(-49),structuredClone(d)]);setFuture([]);}
  function change(p:Partial<Design>) {setD(v=>({...v,...p}));}
  function changeSection(p:Partial<typeof section>) {setD(v=>({...v,sections:v.sections.map((s,i)=>i===selected?{...s,...p}:s)}));}
  function undo() {if(!history.length)return;setFuture(f=>[...f,d]);setD(history[history.length-1]);setHistory(h=>h.slice(0,-1));setSelected(0);}
  function redo() {if(!future.length)return;setHistory(h=>[...h,d]);setD(future[future.length-1]);setFuture(f=>f.slice(0,-1));setSelected(0);}
  useEffect(()=>{
    const ctx=canvas.current?.getContext('2d'); if(!ctx)return;
    ctx.clearRect(0,0,620,600);
    const a=orbit?angle:.35, pitch=orbit?tilt:.16;
    function project(r:number,y:number,t:number) {
      const x=r*Math.cos(t+a), z=r*Math.sin(t+a);
      return {x:center+x*scale,y:floor-y*scale+z*Math.sin(pitch)*scale,z:z*Math.cos(pitch)+y*Math.sin(pitch)};
    }
    type Face={p:{x:number;y:number;z:number}[];depth:number;color:string};
    const faces:Face[]=[]; const rows=96, sides=64;
    function ring(r0:number,y0:number,r1:number,y1:number,inner=false) {
      for(let j=0;j<sides;j++) {
        const t=j/sides*Math.PI*2, next=(j+1)/sides*Math.PI*2;
        const p=[project(r0,y0,t),project(r0,y0,next),project(r1,y1,next),project(r1,y1,t)];
        const normal=Math.sin(t+a+.05)*.65-Math.cos(t+a+.05)*.35;
        const light=clamp((inner?.43:.69)+normal*(inner?-.18:.23),.23,.96);
        faces.push({p,depth:p.reduce((s,v)=>s+v.z,0)/4,color:`rgb(${Math.round(194*light+37)},${Math.round(147*light+30)},${Math.round(114*light+24)})`});
      }
    }
    for(let i=0;i<rows;i++) {
      const y0=i/rows*d.height,y1=(i+1)/rows*d.height;
      ring(radiusAt(d.sections,i/rows),y0,radiusAt(d.sections,(i+1)/rows),y1);
      const b=d.base/10, h0=b+(d.height-b)*i/rows,h1=b+(d.height-b)*(i+1)/rows;
      ring(Math.max(0,radiusAt(d.sections,h0/d.height)-d.wall/10),h0,Math.max(0,radiusAt(d.sections,h1/d.height)-d.wall/10),h1,true);
    }
    const top=radiusAt(d.sections,1), bottom=d.base/10;
    ring(top,d.height,Math.max(0,top-d.wall/10),d.height);
    ring(0,bottom,Math.max(0,radiusAt(d.sections,bottom/d.height)-d.wall/10),bottom,true);
    ring(0,0,radiusAt(d.sections,0),0);
    faces.sort((a,b)=>a.depth-b.depth);
    for(const f of faces) {ctx.beginPath();f.p.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.fillStyle=f.color;ctx.fill();ctx.strokeStyle=f.color;ctx.lineWidth=.5;ctx.stroke();}
  },[d,angle,tilt,orbit,scale]);
  function pointer(e:React.PointerEvent<SVGSVGElement>) {
    if(!drag.current || !svg.current)return;
    const rect=svg.current.getBoundingClientRect();
    if(drag.current.index===-1) {setAngle(drag.current.angle+(e.clientX-drag.current.x)*.012);setTilt(clamp(drag.current.tilt+(e.clientY-drag.current.y)*.005,-.45,.6));return;}
    const x=(e.clientX-rect.left)*620/rect.width, y=(e.clientY-rect.top)*600/rect.height, index=drag.current.index;
    setD(v=>({...v,sections:v.sections.map((s,i)=>i!==index?s:{...s,r:clamp((x-center)/scale,1,25),y:i===0?0:i===v.sections.length-1?1:clamp((floor-y)/scale/v.height,v.sections[i-1].y+.025,v.sections[i+1].y-.025)})}));
  }
  function save() {try{localStorage.setItem('kaan-clay-design-v1',JSON.stringify(d));setMessage('Design saved in this browser.');}catch{setMessage('Browser storage is unavailable. Use Download design.');}}
  function load() {try{const v=JSON.parse(localStorage.getItem('kaan-clay-design-v1')??'null'); if(!v) {setMessage('No saved design in this browser yet.');return;}
    if(!templates[v.template]||!Array.isArray(v.sections)||v.sections.length<2||v.sections.length>12||!['height','wall','base','density','allowance'].every(k=>typeof v[k]==='number'&&Number.isFinite(v[k]))||v.height<5||v.height>60||v.wall<2||v.wall>15||v.base<3||v.base>25||v.density<1||v.density>2.5||v.allowance<0||v.allowance>40||!v.sections.every((s:{name:string;y:number;r:number;curve:number},i:number)=>typeof s.name==='string'&&Number.isFinite(s.y)&&s.y>=0&&s.y<=1&&Number.isFinite(s.r)&&s.r>=1&&s.r<=25&&Number.isFinite(s.curve)&&Math.abs(s.curve)<=3&&(i===0?s.y===0:s.y>v.sections[i-1].y))||v.sections.at(-1).y!==1) throw Error();
    remember();setD(v);setSelected(0);setMessage('Saved design restored.');}catch{setMessage('Could not restore this saved design.');}}
  function download() {const url=URL.createObjectURL(new Blob([JSON.stringify({design:d,estimate:result,units:'cm, mm, g/cm³, kg'},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='clay-studio-design.json';a.click();URL.revokeObjectURL(url);}
  return <main className="cs"><header className="cs-header"><Link href="/">← Kaan Gallery</Link><span>THE MAKER’S WORKBENCH</span><span>01 / CLAY STUDIO</span></header>
    <div className="cs-intro"><div><p className="cs-eyebrow">FROM AN IDEA TO THE WHEEL</p><h1>Give your next pot a shape.</h1><p>Explore a form. Find its proportions. Know how much clay to prepare.</p></div><div className="cs-actions"><button disabled={!history.length} onClick={undo}>↶ Undo</button><button disabled={!future.length} onClick={redo}>↷ Redo</button><button onClick={save}>Save design</button><button onClick={load}>Restore saved</button></div></div>
    <div className="cs-workspace"><aside className="cs-panel"><p className="cs-eyebrow">01 — START WITH A FORM</p><div className="cs-templates">{Object.entries(templates).map(([key,t])=><button key={key} aria-pressed={d.template===key} onClick={()=>{remember();setD(makeDesign(key));setSelected(2);}}><svg viewBox="0 0 60 64" aria-hidden="true"><path d={`M ${t.points.map((p,i)=>`${30-p[2]*1.4},${58-p[1]*50}`).join(' L ')} L ${[...t.points].reverse().map(p=>`${30+p[2]*1.4},${58-p[1]*50}`).join(' L ')} Z`}/></svg>{t.label}</button>)}</div><p className="cs-small">Vase and rounded jug inspired by your reference pieces. Open vessels; no separate lid, handle or spout.</p>
    <div onPointerDown={remember} onKeyDown={e=>{if(e.key.startsWith('Arrow'))remember();}}><p className="cs-eyebrow">02 — SET THE PROPORTIONS</p><Slider label="Overall height" value={d.height} min={5} max={60} step={.5} unit="cm" onChange={height=>change({height})}/><label className="cs-select">Selected section<select value={selected} onChange={e=>setSelected(+e.target.value)}>{d.sections.map((s,i)=><option key={i} value={i}>{s.name}</option>)}</select></label><Slider label={`${section.name} diameter`} value={section.r*2} min={2} max={50} step={.1} unit="cm" onChange={n=>changeSection({r:n/2})}/>{selected>0&&selected<d.sections.length-1&&<Slider label="Height from base" value={section.y*d.height} min={(d.sections[selected-1].y+.025)*d.height} max={(d.sections[selected+1].y-.025)*d.height} step={.1} unit="cm" onChange={n=>changeSection({y:n/d.height})}/>}{selected<d.sections.length-1&&<><Slider label="Curve to next section" value={section.curve} min={-3} max={3} step={.1} unit="cm" onChange={curve=>changeSection({curve})}/><div className="cs-scale"><span>Concave</span><span>Convex</span></div></>}</div></aside>
    <section className="cs-stage"><div className="cs-stage-top"><span>YOUR VESSEL <b> / {templates[d.template].label}</b></span><div><button aria-pressed={!orbit} onClick={()=>setOrbit(false)}>Shape</button><button aria-pressed={orbit} onClick={()=>setOrbit(true)}>Rotate 3D</button></div></div><div className="cs-view"><canvas ref={canvas} width={620} height={600} aria-label="Shaded three dimensional vessel preview"/><svg ref={svg} viewBox="0 0 620 600" onPointerMove={pointer} onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}} onPointerDown={e=>{if(orbit){e.currentTarget.setPointerCapture(e.pointerId);drag.current={index:-1,x:e.clientX,y:e.clientY,angle,tilt};}}}>
      <defs><pattern id="cs-grid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M 25 0 L 0 0 0 25" fill="none" stroke="currentColor" strokeWidth=".5" opacity=".15"/></pattern></defs><rect width="620" height="600" fill="url(#cs-grid)" pointerEvents="none"/>
      <line x1="85" y1={floor} x2="535" y2={floor} stroke="#8a8074" opacity=".4"/>{!orbit&&d.sections.map((s,i)=>{const x=center+s.r*scale,y=floor-s.y*d.height*scale;return <g key={i}><line x1={center-s.r*scale} y1={y} x2={x} y2={y} stroke={i===selected?'#8d3927':'#796e60'} strokeDasharray="3 5" opacity=".55"/><circle cx={x} cy={y} r={i===selected?7:5} fill={i===selected?'#8d3927':'#fff9ef'} stroke="#8d3927" strokeWidth="2" tabIndex={0} role="slider" aria-label={`${s.name} diameter`} aria-valuemin={2} aria-valuemax={50} aria-valuenow={+(s.r*2).toFixed(1)} onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();remember();setSelected(i);setD(v=>({...v,sections:v.sections.map((p,j)=>i===j?{...p,r:clamp(p.r+(e.key==='ArrowRight'?.05:-.05),1,25)}:p)}));}}} onPointerDown={e=>{e.stopPropagation();svg.current?.setPointerCapture(e.pointerId);remember();setSelected(i);drag.current={index:i,x:e.clientX,y:e.clientY,angle,tilt};}}/><text x={x+15} y={y+4} fill="#684d3b" fontSize="11">{(s.r*2).toFixed(1)} cm</text></g>;})}
    </svg></div><p className="cs-stage-hint">{orbit?'Drag to turn and tilt the vessel.':'Drag a dot to change diameter and section height.'}</p><div className="cs-dimensions"><span>HEIGHT <b>{d.height.toFixed(1)} cm</b></span><span>MAX. DIAMETER <b>{result.diameter.toFixed(1)} cm</b></span><span>CAPACITY <b>≈ {result.capacity.toFixed(2)} L</b></span></div></section>
    <aside className="cs-panel cs-estimate"><p className="cs-eyebrow">03 — PREPARE YOUR CLAY</p><div className="cs-weight" aria-live="polite" aria-atomic="true">{result.total.toFixed(2)}<span>kg</span></div><p className="cs-weight-caption">Estimated wet clay to prepare</p><div className="cs-breakdown"><p>Vessel clay <b>{result.net.toFixed(2)} kg</b></p><p>Extra allowance <b>{d.allowance}%</b></p></div><div onPointerDown={remember} onKeyDown={e=>{if(e.key.startsWith('Arrow'))remember();}}><Slider label="Wall thickness" value={d.wall} min={2} max={15} step={.5} unit="mm" onChange={wall=>change({wall})}/><Slider label="Base thickness" value={d.base} min={3} max={25} step={.5} unit="mm" onChange={base=>change({base})}/><Slider label="Wet clay density" value={d.density} min={1} max={2.5} step={.1} unit="g/cm³" onChange={density=>change({density})}/><Slider label="Extra for trimming & loss" value={d.allowance} min={0} max={40} unit="%" onChange={allowance=>change({allowance})}/></div><details><summary>How the estimate works</summary><p>Dimensions are wet, before drying and firing. We integrate the clay in the hollow body and solid base, then multiply by your wet-clay density and add the allowance.</p><p>Walls use a horizontal radial thickness. Steep shoulders may need more clay than this model predicts. Use your clay supplier’s density or calibrate against a weighed piece. Shrinkage, lids, handles and spouts are not included.</p></details><button className="cs-download" onClick={download}>Download design ↓</button></aside></div>
    <footer className="cs-footer"><span>A study in form, made for your studio.</span><span role="status">{message||'Save keeps one design in this browser. Download keeps a separate copy.'}</span></footer>
  </main>;
}
