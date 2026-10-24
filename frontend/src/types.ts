export type Evidence = {
  id: string;
  asset_id: string;
  source: string;
  category: string;
  label: string;
  score: number | null;
  confidence: number;
  uncertainty: number;
  severity: string;
  explanation: string;
  metadata: Record<string, any>;
  model_version: string;
};
export type Graph = {
  nodes: {
    id: string;
    type: string;
    label: string;
    severity?: string;
    evidence_id?: string;
  }[];
  edges: { id: string; source: string; target: string; relation: string }[];
};
export type Report = {
  url_summary?: { title: string; meaning: string; observations: string[]; requested_data: string[]; actions: string[]; gaps: string[]; page_inspected: boolean; findings: { id: string; label: string; explanation: string }[] };
  checks?: { id: string; title: string; status: string; summary: string; evidence_ids: string[]; limitations: string; unavailable_reasons: string[] }[];
  risk_score: number | null;
  risk_level: string;
  confidence: number;
  uncertainty: number;
  uncertainty_level: string;
  verdict: string;
  explanation: string;
  evidence: Evidence[];
  conflicts: { id: string; explanation: string; type: string }[];
  graph: Graph;
  scenarios: { label: string; explanation: string }[];
  recommendations: string[];
  fusion_method: string;
  model_results: Evidence[];
  provenance: Evidence[];
};
export type Analysis = {
  id: string;
  name: string;
  input_type: string;
  state: string;
  created_at: string;
  sha256: string;
  mime: string;
  size: number;
  progress: { step: string; state: string }[];
  report: Report | null;
  error: string | null;
};
