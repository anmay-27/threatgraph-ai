import type { Analysis } from './types';

export function submittedUrlEvidence(row: Analysis) {
  const report = row.report!;
  const canonical = (value: string) => { try { const url = new URL(value); url.hash = ''; return url.href; } catch { return value; } };
  const root = report.graph.nodes.find(node => node.type === 'url' && canonical(node.label) === canonical(row.name));
  const rootEvidence = root ? report.evidence.filter(item => item.asset_id === root.id) : [];
  const redirect = rootEvidence.find(item => item.label === 'redirect_chain');
  const chain = (redirect?.metadata.chain || []) as [string, string][];
  const urlIds = new Set(root ? [root.id] : []);
  // Only follow redirects of the submitted URL, never URLs embedded in its page.
  for (let i = 0; i < report.graph.nodes.length; i++) {
    const previous = urlIds.size;
    report.graph.edges.filter(edge => edge.relation === 'redirects_to' && urlIds.has(edge.source)).forEach(edge => urlIds.add(edge.target));
    if (previous === urlIds.size) break;
  }
  const pageIds = new Set(report.graph.edges.filter(edge => edge.relation === 'contains' && urlIds.has(edge.source)).map(edge => edge.target));
  const page = report.evidence.find(item => item.label === 'page_metadata' && pageIds.has(item.asset_id));
  return { rootEvidence, chain, page };
}

export function groupedMissing(row: Analysis) {
  const groups = new Map<string, { source: string; explanation: string; count: number }>();
  for (const item of row.report!.evidence.filter(item => ['unavailable', 'verification_unavailable'].includes(item.label))) {
    const key = item.source + ':' + item.explanation;
    const existing = groups.get(key);
    if (existing) existing.count++;
    else groups.set(key, { source: item.source, explanation: item.explanation, count: 1 });
  }
  return [...groups.values()];
}
