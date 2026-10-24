import { ShieldCheck, ShieldAlert, CircleHelp } from 'lucide-react';
import type { Analysis } from '../types';
import { submittedUrlEvidence } from '../urlAssessment';

const labels: Record<string,string> = {findings:'Review findings',partial:'Partial coverage',unavailable:'Unavailable',not_checked:'Not checked',completed:'Completed'};
export default function SecurityChecks({row}: {row:Analysis}) {
  const checks = row.report?.checks;
  if (!checks?.length) return null;
  const page = row.input_type === 'url' ? submittedUrlEvidence(row).page : undefined;
  const collections = row.report!.evidence.filter(e => e.label === 'collection_surface' && (row.input_type !== 'url' || e.asset_id === page?.asset_id));
  const browsers = row.report!.evidence.filter(e => e.label === 'browser_observation');
  return <section className="security-checks" aria-labelledby="security-checks-title">
    <div className="assessment-separator"><span className="eyebrow">INVESTIGATION COVERAGE</span><h2 id="security-checks-title">What did we actually check?</h2><p>Each capability has its own result. “Completed” means the check ran; it does not certify the content as safe.</p></div>
    <div className="check-grid">{checks.map(check => <details className="card check-card" key={check.id} open={check.status === 'findings'}>
      <summary><span>{check.status === 'findings' ? <ShieldAlert size={20}/> : check.status === 'completed' ? <ShieldCheck size={20}/> : <CircleHelp size={20}/>}<strong>{check.title}</strong></span><small>{labels[check.status] || check.status}</small></summary>
      <p>{check.summary}</p><p>{check.limitations}</p>
      {check.status === 'findings' && <ul>{row.report!.evidence.filter(e => check.evidence_ids.includes(e.id) && e.score !== null && e.score >= .5 && e.severity !== 'info').map(e => <li key={e.id}><strong>{e.label.replaceAll('_', ' ')}:</strong> {e.explanation}</li>)}</ul>}
      {check.unavailable_reasons.length > 0 && <ul>{check.unavailable_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>}
      <small>{check.evidence_ids.length} recorded evidence items</small>
    </details>)}</div>
    {collections.map(item => <details className="card collection-card" key={item.id} open><summary>Declared data collection</summary><p>{item.explanation}</p>
      {(item.metadata.forms || []).map((form:any,i:number) => <div className="collection-row" key={i}><strong>{(form.displayed_field_types || form.field_types).join(', ') || 'Question types not established'}</strong><span>{form.method.toUpperCase()} → {form.destination}</span><small>{form.external_domain ? 'Different registrable domain' : 'Same domain or non-HTTP destination'}</small>{form.fields?.some((field:any) => field.disabled) && <small>Includes disabled preview controls; labels do not establish active submission.</small>}</div>)}
      <p>External scripts referenced: {(item.metadata.third_party_scripts || []).length}. Inline API references: {(item.metadata.script_api_references || []).join(', ') || 'none detected'}.</p><small>{item.metadata.limitations}</small>
    </details>)}
    {browsers.map(item => <details className="card collection-card" key={item.id}><summary>Rendered page and initial requests</summary><p>{item.metadata.limitations}</p><p>Requested data after rendering: {[...new Set((item.metadata.rendered_collection?.forms || []).flatMap((form:any) => form.displayed_field_types || form.field_types))].join(', ') || 'Not established'}.</p><ul>{(item.metadata.requests || []).map((request:any,index:number) => <li key={index}>{request.method} · {request.host} · {request.type} · {request.status}</li>)}</ul></details>)}
  </section>;
}
