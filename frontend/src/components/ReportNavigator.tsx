import { useEffect, useState } from 'react';
const sections=[['report-summary','Summary'],['report-checks','Checks'],['report-context','Connections'],['report-graph','Graph'],['report-evidence','Evidence']];
export default function ReportNavigator(){
 const [active,setActive]=useState('report-summary');
 useEffect(()=>{const observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting);if(visible.length)setActive(visible[0].target.id);},{rootMargin:'-12% 0px -55% 0px'});sections.forEach(([id])=>{const el=document.getElementById(id);if(el)observer.observe(el);});return()=>observer.disconnect();},[]);
 return <nav className="report-navigator" aria-label="Report sections">{sections.map(([id,label])=><a key={id} href={'#'+id} aria-current={active===id?'location':undefined} onClick={()=>setActive(id)}>{label}</a>)}</nav>;
}
