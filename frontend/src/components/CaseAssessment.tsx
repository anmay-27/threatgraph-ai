import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api } from '../api';
import { client, ErrorBox } from './shared';

export type CaseAssessmentData = {
  title: string; scope: string; total:number; completed:number; partial:number;
  scenarios: {id:string;label:string;explanation:string;analysis_id:string;evidence_ids:string[];missing_evidence?:string[];asset_path?:string[];asset_path_labels?:string[]}[];
  correlations:{entity_id:string;entity_type:string;value:string;case_id:string;case_title:string;significance:string}[];
  conflicts:{id:string;explanation:string;analysis_id:string}[];
  gaps:{analysis_id:string;reason:string}[];
  synthetic_findings:{analysis_id:string;evidence_id:string;verdict:string;score:number|null}[];
  recommendations:string[];
};

export default function CaseAssessment({caseId,data}:{caseId:string;data:CaseAssessmentData}) {
  const [analyst,setAnalyst]=useState(false);
  const upload=useMutation({mutationFn:async(file:File)=>{
    const form=new FormData();form.append('file',file);
    const row=await api<{id:string}>('/analyze/file',{method:'POST',body:form});
    try {await api(`/cases/${caseId}/analyses/${row.id}`,{method:'POST'});}
    catch {throw new Error('Upload started, but linking to the case failed. Find the investigation in History and add it from the Analyses tab.');}
    return row;
  },onSuccess:()=>{client.invalidateQueries({queryKey:['case',caseId]});client.invalidateQueries({queryKey:['history']});}});
  return <section className="card case-form" aria-label="Case assessment">
    <div className="case-actions"><h2>{data.title}</h2><button type="button" aria-pressed={analyst} onClick={()=>setAnalyst(!analyst)}>{analyst?'Switch to simple view':'Switch to analyst view'}</button></div>
    <p>{data.scope}</p>
    <p>{data.total} investigations · {data.completed} complete · {data.partial} partial</p>
    <label>Add email, PDF, image or document to this case<input type="file" accept=".eml,.pdf,.txt,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp" disabled={upload.isPending} onChange={e=>{const file=e.target.files?.[0];if(file)upload.mutate(file);e.target.value='';}} /></label>
    {upload.isPending&&<p role="status">Uploading and linking investigation…</p>}
    {upload.isError&&<ErrorBox error={upload.error}/>}
    {upload.isSuccess&&<p role="status">Investigation added. Results update here as checks finish.</p>}
    <h3>Fraud hypotheses</h3>
    {!data.scenarios.length&&<p>No supported scenario yet. This does not establish safety; add evidence or review incomplete checks.</p>}
    {data.scenarios.map(s=><article key={s.analysis_id+s.id}><h4>{s.label}</h4><p>{s.explanation}</p><p><strong>Observed chain:</strong> {(s.asset_path_labels?.length?s.asset_path_labels:s.asset_path)?.join(" ? ")||"Evidence within one asset"}</p><Link to={'/analysis/'+s.analysis_id}>Inspect supporting investigation</Link>{analyst&&<><p>Evidence references: {s.evidence_ids.join(', ')}</p><p>Observed path: {(s.asset_path_labels?.length?s.asset_path_labels:s.asset_path)?.join(' → ')||'Same-asset evidence'}</p><p>Still to verify: {s.missing_evidence?.join('; ')}</p></>}</article>)}
    <h3>Connections to other cases</h3>
    {!data.correlations.length&&<p>No shared identifiers found in accessible cases.</p>}
    {data.correlations.map(c=><p key={c.case_id+c.entity_id}><Link to={'/entities/'+c.entity_id}>{c.value}</Link> ({c.entity_type}) also appears in <Link to={'/cases/'+c.case_id}>{c.case_title}</Link>. {c.significance}</p>)}
    <h3>What to do next</h3><ol>{data.recommendations.map(a=><li key={a}>{a}</li>)}</ol>
    <details open={analyst}><summary>Coverage gaps ({data.gaps.length}) and evidence conflicts ({data.conflicts.length})</summary>{data.gaps.map((g,i)=><p key={i}><Link to={'/analysis/'+g.analysis_id}>Investigation</Link>: {g.reason}</p>)}{data.conflicts.map(c=><p key={c.id}>{c.explanation}</p>)}</details>
    <details open={analyst}><summary>Synthetic-media findings ({data.synthetic_findings.length})</summary><p>AI-generated content alone is not evidence of fraud and does not increase the cybersecurity risk score.</p>{data.synthetic_findings.map(s=><p key={s.analysis_id+s.evidence_id}><Link to={'/analysis/'+s.analysis_id}>{s.verdict.replaceAll('_',' ')}</Link>{s.score!==null?` · model score ${(s.score*100).toFixed(1)}%`:''}</p>)}</details>
  </section>;
}
