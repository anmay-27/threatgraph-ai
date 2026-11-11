import type { Analysis } from '../types';
export type Decision = {title:string;meaning:string;findings:{id:string;label:string;explanation:string}[];scenarios:{label:string;explanation:string}[];actions:string[];gaps:string[];conflict_count:number;evidence_count:number};
export default function DecisionBrief({row}:{row:Analysis}) {
  const brief=row.report?.decision_summary;
  if(!brief)return null;
  return <section className="card decision-brief" aria-label="Investigation conclusion"><span className="eyebrow">YOUR INVESTIGATION AT A GLANCE</span><h2>{brief.title}</h2><p>{brief.meaning}</p><div className="decision-grid"><div><h3>What we found</h3>{brief.findings.length ? brief.findings.slice(0,4).map(f=><p key={f.id}><strong>{f.label}</strong><br/>{f.explanation}</p>):<p>No actionable security indicator was established. Review the completed checks and limitations below.</p>}{brief.scenarios.filter(s=>!brief.findings.some(f=>f.explanation===s.explanation)).map((s,i)=><p key={i}><strong>{s.label}</strong><br/>{s.explanation}</p>)}</div><div><h3>What you should do</h3><ol>{brief.actions.map(a=><li key={a}>{a}</li>)}</ol><p>{brief.evidence_count} evidence records · {brief.conflict_count} conflicts</p><details><summary>Unchecked or incomplete items ({brief.gaps.length})</summary>{brief.gaps.map(g=><p key={g}>{g}</p>)}</details></div></div></section>;
}
