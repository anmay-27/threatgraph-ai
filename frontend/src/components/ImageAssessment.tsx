import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { ScanEye, Fingerprint, CircleHelp, RefreshCw } from "lucide-react";
import { api } from "../api";
import type { Analysis } from "../types";
import { imageAssessment } from "../imageAssessment";
import { ErrorBox, client } from "./shared";

export default function ImageAssessment({ row }: { row: Analysis }) {
  const navigate = useNavigate();
  const result = imageAssessment(row.report!.evidence);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [originBasis, setOriginBasis] = useState("");
  const uncertainty = result.model?.uncertainty;
  const feedback = useQuery({
    queryKey: ["feedback", row.id],
    queryFn: () => api<{ id: string; evidence_id: string; verdict: string; note: string; created_at: string }[]>(`/analyses/${row.id}/feedback`),
  });
  const knownAiFeedback = feedback.data?.find((item) => item.evidence_id === result.model?.id && item.verdict === "incorrect" && item.note.startsWith("User reports known AI-generated origin."));
  const originCorrection = useMutation({
    mutationFn: () => api(`/analyses/${row.id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        evidence_id: result.model?.id,
        verdict: "incorrect",
        note: `User reports known AI-generated origin. Basis: ${originBasis.trim()}`,
      }),
    }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["feedback", row.id] });
      setOriginBasis("");
    },
  });
  const rerun = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/v1/analyses/${row.id}/media`);
      if (!response.ok) throw new Error("The original image is no longer available. Upload it again to run the detector.");
      const body = new FormData();
      body.append("file", await response.blob(), row.name);
      return api<{ id: string }>("/analyze/file", { method: "POST", body });
    },
    onSuccess: ({ id }) => {
      client.invalidateQueries({ queryKey: ["history"] });
      navigate("/analysis/" + id);
    },
  });
  return <section className="card authenticity-card" aria-labelledby="authenticity-title">
    <div className="assessment-kicker"><span className="eyebrow"><ScanEye size={16} /> IMAGE ORIGIN</span><span className="research-pill">{result.calibrated ? "Calibrated research model" : "Experimental model"}</span></div>
    <div className="assessment-hero"><div className="assessment-copy">
    <h2 id="authenticity-title">{knownAiFeedback ? "Reviewer reports AI-made; detector disagreed" : result.title}</h2>
    <p>{knownAiFeedback ? "A reviewer supplied an AI-origin statement for this image. ThreatGraph has not independently verified that statement. The original detector output remains below as a documented possible false negative." : result.explanation}</p>
    {result.score !== null && <div className="authenticity-score">
      <strong>{result.modelSuggestion}</strong>
      <span>AI-pattern model score: <b>{result.score > 0.999 ? ">99.9" : result.score < 0.001 ? "<0.1" : (result.score * 100).toFixed(1)}%</b></span>
      <progress aria-label="AI model score" max={1} value={result.score} />
      <div className="score-endpoints"><span>Real-image patterns</span><span>AI-image patterns</span></div>
      <small>{result.calibrated ? "Calibrated on a limited research partition. This is not the chance that your image is AI-made; false negatives remain possible." : "Raw model output, not a calibrated probability or certainty of AI generation."}</small>
      {result.calibrated && typeof result.model?.metadata.threshold === "number" && <small>AI class cutoff: {(result.model.metadata.threshold * 100).toFixed(1)}%, selected on calibration data. The class suggestion uses this cutoff; uncertainty can still require an inconclusive result.</small>}
    </div>}
    </div><figure className="assessment-preview">{previewFailed ? <div><Fingerprint size={40} /><p>Original preview expired</p></div> : <img src={`/api/v1/analyses/${row.id}/media`} alt="Submitted image being assessed" onError={() => setPreviewFailed(true)} />}<figcaption>Submitted original · analyzed locally</figcaption></figure></div>
    <div className="assessment-facts"><div><span>Model confidence</span><strong>{result.model ? `${Math.round(result.model.confidence * 100)}%` : "Unavailable"}</strong><small>Heuristic confidence, not accuracy</small></div><div><span>Uncertainty</span><strong>{uncertainty === undefined ? "Unknown" : uncertainty >= .65 ? "High" : uncertainty >= .3 ? "Medium" : "Low"}</strong><small>{result.model?.metadata.ood === "possibly_out_of_distribution" ? "Unfamiliar image patterns" : "Prediction ambiguity"}</small></div><div><span>Image detector</span><strong className="model-name">{result.model?.metadata.architecture || "Visual classifier"}</strong><small>{result.model?.model_version || "No prediction available"}</small></div></div>
    {feedback.data?.filter((item) => item.evidence_id === result.model?.id).map((item) => <div className="origin-correction" key={item.id}><strong>Reviewer correction: {item.verdict}</strong><p>{item.note}</p><small>Reviewer statement, not independently verified. The saved model score remains {result.score === null ? "unavailable" : `${(result.score * 100).toFixed(1)}%`}. This correction is included in a newly exported PDF.</small></div>)}
    {result.model && !knownAiFeedback && result.modelSuggestion === "Model leans non-AI" && <form className="origin-correction" onSubmit={(event) => { event.preventDefault(); originCorrection.mutate(); }}><h3>Know the true origin?</h3><p>If you created this image with an AI tool, record the miss for investigation. This preserves the model output and adds your statement to future PDF exports.</p><label>How do you know? <input required maxLength={500} value={originBasis} onChange={(event) => setOriginBasis(event.target.value)} placeholder="For example: I generated it in [tool] from my prompt" /></label><button type="submit" disabled={originCorrection.isPending || !originBasis.trim()}>Record AI-made correction</button>{originCorrection.isError && <ErrorBox error={originCorrection.error} />}</form>}
    <h3 className="explanation-heading"><CircleHelp size={18} /> Understand this result</h3>
    <div className="analysis-explanation">
      <section><h3>What was actually detected?</h3><p>{result.score === null ? "No visual-model prediction is available. The report can only describe the metadata and provenance checks that completed." : `${result.modelSuggestion}. This comes from a whole-image classifier, not a verified record of how the image was created.`}</p></section>
      <section><h3>Where is the image wrong?</h3><p>This detector does not locate altered pixels or diagnose hands, lighting, faces or text. It cannot honestly point to a specific visual defect. An AI-generated image may also have no obvious defect.</p></section>
      <section><h3>Why might the result be wrong?</h3><p>Unseen generators, editing, resizing and screenshots can change the patterns this model learned. A low score can be a false negative even when the image is fully AI-generated. {result.calibrated ? "Evaluation covers a small public research subset, not every image type or generator." : "The external model's publisher reports overfitting; a high score is not high real-world accuracy."}</p></section>
      <section><h3>How should I verify it?</h3><p>Compare the original source and creation history, inspect any signed provenance, and verify consequential claims independently. For a document, check its identifier with the issuer.</p></section>
    </div>
    <details className="diagnostic-details" open><summary>Observed evidence</summary>
    <ul>{result.observations.map((observation) => <li key={observation}>{observation}</li>)}</ul>
    </details>
    {result.diagnostics.length > 0 && <details className="diagnostic-details"><summary>Explore prediction stability</summary><p>Same model, three views. These are sensitivity checks, not three independent votes.</p>{result.diagnostics.map((check) => <div className="diagnostic-row" key={check.name}><span>{check.name}</span><progress max={1} value={check.score} aria-label={`${check.name} AI score`} /><strong>{(check.score * 100).toFixed(1)}%</strong></div>)}</details>}
    <details className="diagnostic-details"><summary>Model and provenance context</summary>
    <ul>{result.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
    {result.model?.metadata.test_metrics && <p>Held-out subset: {result.model.metadata.test_metrics.count} images · balanced accuracy {(result.model.metadata.test_metrics.balanced_accuracy * 100).toFixed(1)}% · F1 {result.model.metadata.test_metrics.f1.toFixed(3)}. These are dataset measurements, not a guarantee for this upload.</p>}
    {result.model?.metadata.poster_external_metrics && <p>Separate poster check: {Math.round(result.model.metadata.poster_external_metrics.ai_recall * result.model.metadata.poster_external_metrics.ai_posters)}/{result.model.metadata.poster_external_metrics.ai_posters} AI posters flagged; {result.model.metadata.poster_external_metrics.inconclusive_count}/{result.model.metadata.poster_external_metrics.count} total posters inconclusive under the uncertainty rule. {result.model.metadata.poster_external_metrics.limitation}</p>}
    </details>
    <div className="image-result-actions"><button disabled={rerun.isPending} onClick={() => rerun.mutate()}><RefreshCw size={15} />{rerun.isPending ? "Starting analysis…" : "Run image detector again"}</button><small>A rerun uses the retained original and current detector. The same model may give the same score; rerunning is most useful after a validated model update.</small></div>
    {rerun.isError && <ErrorBox error={rerun.error} />}
  </section>;
}
