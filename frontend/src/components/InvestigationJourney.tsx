import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, FileSearch, Network, ShieldCheck } from 'lucide-react';
const steps = [
 {icon:FileSearch,title:'Start with a clue',text:'A suspicious message, an unfamiliar link, or a file you want to verify. Choose one item to begin.',link:'/analyze',action:'Start an investigation'},
 {icon:Network,title:'Connect the evidence',text:'Group related investigations into a case. Follow attachments, QR destinations and identifiers shared with other cases.',link:'/cases',action:'Explore your cases'},
 {icon:ShieldCheck,title:'Make an informed decision',text:'Review findings alongside coverage gaps, then export a report with supporting evidence and next steps.',link:'/history',action:'Review investigations'},
];
export default function InvestigationJourney(){
 const [active,setActive]=useState(0);const step=steps[active];const Icon=step.icon;
 return <section className="journey" aria-label="Investigation guide"><div className="journey-heading"><span className="eyebrow">FROM CLUE TO CLARITY</span><span>Three steps. One connected investigation.</span></div><div className="journey-steps" role="tablist" aria-label="Investigation stages">{steps.map((s,i)=><button key={s.title} id={'journey-tab-'+i} role="tab" aria-selected={active===i} aria-controls="journey-panel" onClick={()=>setActive(i)} onKeyDown={e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?2:(active+(e.key==='ArrowRight'?1:2))%3;setActive(next);document.getElementById('journey-tab-'+next)?.focus();}}}><span>0{i+1}</span>{s.title}</button>)}</div><div id="journey-panel" role="tabpanel" aria-labelledby={'journey-tab-'+active} className="journey-panel"><Icon size={28}/><p>{step.text}</p><Link to={step.link}>{step.action}<ArrowUpRight size={16}/></Link></div></section>;
}
