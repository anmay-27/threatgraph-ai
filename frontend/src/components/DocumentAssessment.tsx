import type { Analysis } from '../types';

export default function DocumentAssessment({row}: {row:Analysis}) {
  const evidence=row.report?.evidence || [];
  const documents=evidence.filter(e=>e.label==='document_summary');
  if(!documents.length)return null;
  return <>{documents.map(document=>{
    const m=document.metadata;
    const flags=evidence.filter(e=>e.asset_id===document.asset_id && e.source==='document_inspector' && e.score!==null && e.score>=.5);
    const gaps=m.limitations || [];
    return <section className="card demo-summary" key={document.id}>
      <span className="eyebrow">DOCUMENT INVESTIGATION</span>
      <h2>{flags.length ? `${flags.length} document indicators need review` : gaps.length ? 'Document inspected with coverage gaps' : 'Document inspected; no active-content indicator identified'}</h2>
      <p>{document.explanation}</p>
      <div className="demo-actions"><span className="readiness-pill">{m.units_inspected} pages / parts inspected</span><span className="readiness-pill">{m.text_characters} text characters</span><span className="readiness-pill">{(m.links || []).length} recorded links</span></div>
      {flags.length>0 && <ul>{flags.map(flag=><li key={flag.id}>{flag.explanation}</li>)}</ul>}
      {gaps.length>0 && <ul>{gaps.map((gap:string)=><li key={gap}>{gap}</li>)}</ul>}
      <p><strong>Next step:</strong> {flags.length ? 'Keep macros and scripts disabled. Verify the sender and review the malware scan before opening embedded content.' : 'Review the extracted text and sender. Check malware scan coverage separately; structural checks do not authenticate a certificate or its claims.'}</p>
      <details><summary>Read extracted text</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{m.text_preview || 'No readable text extracted. A scanned document may require OCR.'}</pre></details>
      {(m.links || []).length>0 && <details><summary>Declared external links</summary><p>Recorded without opening these destinations. Submit a selected URL separately to investigate it.</p><ul>{m.links.map((link:string)=><li style={{overflowWrap:'anywhere'}} key={link}>{link}</li>)}</ul></details>}
    </section>;
  })}</>;
}
