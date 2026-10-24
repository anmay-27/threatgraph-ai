import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Check, Copy, FileSearch, Image, Link2, MessageSquare, ShieldCheck } from 'lucide-react';
import { api } from '../api';
import { PageTitle } from '../components/shared';

const message = 'Congratulations! You have been selected for a job. Pay a registration fee immediately to secure your position. Send your bank details and OTP now. Do not tell anyone about this offer.';

export default function Demo() {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const health = useQuery({queryKey:['demo-health'], queryFn:()=>api<{malware_scanner?:{available:boolean}}>('/health'),refetchInterval:15000});
  const models = useQuery({queryKey:['models'],queryFn:()=>api<{name:string;available:boolean}[]>('/models')});
  return <>
    <PageTitle eyebrow="A GUIDED FIRST INVESTIGATION" title="From suspicious content to clear evidence." text="Four ways to explore ThreatGraph. Every submitted sample runs through the real analysis pipeline." />
    <section className="demo-status card" aria-label="Live system status">
      <ShieldCheck size={24}/><div><strong>Live system readiness</strong><p>{health.isError ? 'API unavailable. Start the local services before presenting.' : health.isPending ? 'Checking services…' : 'API connected. Ready to submit an investigation.'}</p></div>
      <span className="readiness-pill">Image model: {models.isError ? 'check failed' : !models.data ? 'checking' : models.data.some(m=>m.name==='image' && m.available) ? 'available' : 'unavailable'}</span>
      <span className="readiness-pill">Malware scanner: {health.isError ? 'check failed' : !health.data ? 'checking' : health.data.malware_scanner?.available ? 'ready' : 'unavailable'}</span>
    </section>
    <div className="demo-grid">
      <article className="card demo-step"><Link2/><span className="eyebrow">01 / WEBSITE INSPECTION</span><h2>Follow the destination</h2><p>Submit a public URL. Inspect redirects, requested form data, and security findings separately.</p><code>https://example.com</code><p className="hint">A benign comparison: a successful fetch should not become a phishing finding just because a URL was submitted.</p><Link className="button" to="/analyze">Check a URL <ArrowUpRight size={16}/></Link></article>
      <article className="card demo-step"><MessageSquare/><span className="eyebrow">02 / FRAUD INDICATORS</span><h2>Investigate a suspicious offer</h2><p>This invented sample contains urgency, an advance fee, and requests for sensitive information. It has no external links.</p><blockquote>{message}</blockquote><div className="demo-actions"><button onClick={async()=>{try {await navigator.clipboard.writeText(message);setCopied(true);setCopyError(false);}catch{setCopyError(true);}}}>{copied ? <Check size={16}/> : <Copy size={16}/>} {copied ? 'Copied sample' : 'Copy sample'}</button><Link to="/messages">Open message analysis <ArrowUpRight size={16}/></Link></div>{copyError && <p role="status">Clipboard unavailable. Select and copy the sample text above.</p>}</article>
      <article className="card demo-step"><Image/><span className="eyebrow">03 / IMAGE ORIGIN</span><h2>Compare known originals</h2><p>Upload a photograph you took and an image you generated. Keep the originals and their creation history for comparison.</p><ul><li>Read the model suggestion and stability checks.</li><li>Compare metadata and provenance findings.</li><li>Record incorrect predictions honestly.</li></ul><p className="hint">AI generation is not automatically a security threat. The research classifier can miss generated images.</p><Link className="button" to="/analyze">Investigate an image <ArrowUpRight size={16}/></Link></article>
      <article className="card demo-step"><FileSearch/><span className="eyebrow">04 / INVESTIGATION REPORT</span><h2>Make your findings reviewable</h2><p>Open a completed investigation, inspect a graph node, then export the PDF and JSON.</p><ul><li>PDF: findings, context, next actions, and coverage gaps.</li><li>JSON: structured evidence for technical review.</li><li>A missing check is not a clean result.</li></ul><Link className="button" to="/history">Open investigation history <ArrowUpRight size={16}/></Link></article>
    </div>
    <section className="card demo-summary"><h2>Your presentation in three minutes</h2><p><strong>Problem:</strong> suspicious content needs more than a single score. <strong>Demonstration:</strong> submit a sample, explain an observed finding, and export its report. <strong>Limitations:</strong> distinguish completed checks from unavailable capabilities and model uncertainty.</p></section>
  </>;
}
