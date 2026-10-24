import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Analysis } from '../types';
import { ErrorBox } from './shared';
import { submittedUrlEvidence, groupedMissing } from '../urlAssessment';

export default function UrlAssessment({ row }: { row: Analysis }) {
  const navigate = useNavigate();
  const summary = row.report?.url_summary;
  const { rootEvidence, chain, page } = submittedUrlEvidence(row);
  const browser = row.report?.evidence.find(e => e.label === 'browser_observation' && e.asset_id === page?.asset_id);
  const experimental = rootEvidence.filter(e => e.source === 'url_detector' && e.score !== null && e.metadata.deployment_status !== 'validated_external');
  const missing = groupedMissing(row);
  const structure = rootEvidence.find(e => e.source === 'url_structure' && e.label === 'url_structure');
  const listed = (structure?.metadata.listed_first_party_domains || []) as { brand: string; base_domain: string }[];
  const finalUrl = chain.at(-1)?.[1];
  const finalLocation = (() => { try { if (!finalUrl) return ''; const parsed = new URL(finalUrl); return parsed.origin + parsed.pathname; } catch { return ''; } })();
  const authGate = /\/(?:signin|ServiceLogin)(?:\/|$)/i.test(finalLocation);
  const pageTitle = String(page?.metadata.title || '').trim();
  const collection = browser?.metadata.rendered_collection || page?.metadata.data_collection;
  const declaredForms = Array.isArray(collection?.forms) ? collection.forms : [];
  const formHosts = [...new Set(declaredForms.map((form: { destination?: string }) => { try { return new URL(form.destination || '').hostname; } catch { return ''; } }).filter(Boolean))];
  const current = row.report!.fusion_method.startsWith('security-indicators-only-v3');
  const rerun = useMutation({ mutationFn: () => api<{id:string}>('/analyze/url', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: row.name}) }), onSuccess: result => navigate('/analysis/' + result.id) });
  return <section className="card authenticity-card" aria-labelledby="url-assessment-title">
    <span className="eyebrow">URL ASSESSMENT</span>
    <h2 id="url-assessment-title">{summary?.title || (!current && experimental.length > 0 ? 'Saved result uses an older scoring policy' : row.report!.risk_score === null ? page ? 'Page inspected; security verification incomplete' : 'Page inspection could not complete' : 'Review the observed security indicators')}</h2>
    {summary ? <div className="analysis-explanation"><section><h3>What the evidence supports</h3><p>{summary.meaning}</p><ul>{summary.observations.map(text => <li key={text}>{text}</li>)}</ul></section><section><h3>What to do next</h3><ol>{summary.actions.map(text => <li key={text}>{text}</li>)}</ol></section></div> : <p>{page ? 'The public page was inspected for declared forms and suspicious content. This does not verify the operator or establish that the page is safe.' : 'The scanner could not inspect the submitted page.'}</p>}
    <div className="analysis-explanation"><section><h3>What was inspected?</h3><p>{page ? authGate ? 'The URL redirected to a sign-in page. Only that public sign-in response was inspected; the original service content behind authentication was not visible.' : browser ? 'Static HTML and restricted initial browser rendering were inspected. No form submissions, logins or later user interactions were tested.' : 'A page response was inspected. Scripts, signed-in content and later behavior were not observed.' : 'No page content was available for static inspection. The assessment is limited to URL structure and any completed network observations.'}</p></section><section><h3>Site and redirects</h3><p>{listed.length ? `The submitted host matches the local first-party domain list for ${listed.map(x => x.brand + ' (' + x.base_domain + ')').join(', ')}. Domain ownership alone does not certify page safety.` : 'No locally listed first-party domain match was recorded for the submitted host.'} {chain.length ? `The fetch followed ${chain.length} validated redirect${chain.length === 1 ? '' : 's'}${finalLocation ? ` and reached ${finalLocation}` : ''}.` : 'No redirect chain was recorded.'}</p></section></div>
    {page && <div className="analysis-explanation"><section><h3>Page claim and data collection</h3><p>{pageTitle ? `The page title says “${pageTitle}”. That title is supplied by the page and does not verify who operates the form. ` : ''}{declaredForms.length ? `${declaredForms.length} form${declaredForms.length === 1 ? '' : 's'} declared${formHosts.length ? `; submission host${formHosts.length === 1 ? '' : 's'}: ${formHosts.join(', ')}` : ''}. ` : 'No form submission destination was declared in the static HTML. '}{browser ? 'Initial rendered fields and requests were observed with restrictions. Actual submissions were not performed.' : 'Dynamic fields, scripts, and actual submissions were not observed.'}</p></section></div>}
    {experimental.length > 0 && <p>The experimental URL model has known false positives. {current ? 'Its raw predictions are preserved in Models and exported JSON, but do not contribute to the security-risk score.' : 'This saved report used an older scoring policy. Its numeric risk may include that weak signal. Run a new check to apply the updated policy.'}</p>}
    {missing.length > 0 && <details className="diagnostic-details" open><summary>What could not be checked ({missing.length})</summary><ul>{missing.map(e => <li key={e.source + e.explanation}><strong>{e.source === 'clamav' ? 'Malware scan' : e.source === 'recursion' ? 'Linked resources' : e.source.replaceAll('_', ' ')}:</strong> {e.explanation}{e.count > 1 ? ` Affected ${e.count} assets.` : ''}</li>)}</ul></details>}
    <p>Independent page findings remain visible below. The score summarizes observed indicators; it is not a percentage chance of phishing.</p>
    <button onClick={() => rerun.mutate()} disabled={rerun.isPending}>{rerun.isPending ? 'Starting check…' : 'Run a new URL check'}</button>
    {rerun.isError && <ErrorBox error={rerun.error} />}
  </section>;
}
