import { describe, expect, it } from 'vitest';
import { groupedMissing, submittedUrlEvidence } from './urlAssessment';
import type { Analysis } from './types';

const report = () => ({ name: 'https://docs.google.com/forms/viewform', report: {
  graph: { nodes: [{ id: 'root', type: 'url', label: 'https://docs.google.com/forms/viewform' }], edges: [
    { source: 'root', target: 'page', relation: 'contains' },
    { source: 'page', target: 'image-url', relation: 'contains' },
    { source: 'image-url', target: 'w3c', relation: 'redirects_to' },
    { source: 'w3c', target: 'namespace-page', relation: 'contains' },
  ] }, evidence: [
    { id: 'page-e', asset_id: 'page', label: 'page_metadata', metadata: { title: 'Form' } },
    { id: 'child-e', asset_id: 'image-url', label: 'redirect_chain', metadata: { chain: [['https://asset.example/svg', 'https://www.w3.org/2000/svg']] } },
    { id: 'namespace-e', asset_id: 'namespace-page', label: 'page_metadata', metadata: { title: 'SVG namespace' } },
    { id: 'missing1', asset_id: 'page', label: 'unavailable', source: 'clamav', explanation: 'Scanner offline' },
    { id: 'missing2', asset_id: 'namespace-page', label: 'unavailable', source: 'clamav', explanation: 'Scanner offline' },
  ],
} } as unknown as Analysis);

describe('submitted URL evidence', () => {
  it('does not attribute a resource redirect to the submitted page', () => {
    const result = submittedUrlEvidence(report());
    expect(result.chain).toEqual([]);
    expect(result.page?.metadata.title).toBe('Form');
  });
  it('groups repeated unavailable checks while retaining affected asset counts', () => {
    expect(groupedMissing(report())).toEqual([{ source: 'clamav', explanation: 'Scanner offline', count: 2 }]);
  });
});
