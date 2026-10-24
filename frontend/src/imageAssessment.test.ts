import { describe, expect, it } from "vitest";
import { imageAssessment } from "./imageAssessment";
import type { Evidence } from "./types";

const entry = (values: Partial<Evidence>): Evidence => ({ id: "e", asset_id: "root", source: "image_forensics", category: "metadata", label: "image_metadata", score: null, confidence: 0, uncertainty: 1, severity: "info", explanation: "", metadata: {}, model_version: "test", ...values });
const metadata = entry({});
const prediction = (score: number) => entry({ source: "image_detector", label: "synthetic_probability", score });
describe("image authenticity assessment", () => {
  it("distinguishes upstream pretraining from local calibration", () => {
    const model = entry({...prediction(.95), metadata:{calibration:'temperature_scaling',pretrained_source:'OwensLab/commfor-model-384',predicted_class:'ai_generated',verdict:'likely_ai_generated'}});
    const result = imageAssessment([metadata,model]);
    expect(result.explanation).toContain('pretrained research classifier');
    expect(result.explanation).toContain('overlap');
    expect(result.explanation).not.toContain('trained and temperature-calibrated on separate');
  });
  it("explains small score changes that cross the class cutoff", () => {
    const result = imageAssessment([metadata, entry({ ...prediction(.1), metadata: { unstable: true, stability_class_changed: true } })]);
    expect(result.title).toContain("Unstable");
    expect(result.explanation).toContain("decision threshold");
    expect(result.observations.join(" ")).not.toContain("25 percentage points");
    expect(result.score).toBe(.1);
  });
  it("does not infer AI generation from missing credentials", () => {
    expect(imageAssessment([metadata, entry({ label: "not_present" })]).title).toContain("Unable to determine");
  });
  it("distinguishes AI, non-AI and uncertain model suggestions", () => {
    expect(imageAssessment([metadata, prediction(0.95)]).title).toContain("likely AI-generated");
    expect(imageAssessment([metadata, prediction(0.05)]).title).toContain("likely non-AI");
    expect(imageAssessment([metadata, prediction(0.5)]).title).toContain("Uncertain");
  });
  it("never applies a linked asset prediction to the submitted image", () => {
    expect(imageAssessment([metadata, entry({ ...prediction(0.99), asset_id: "linked" })]).score).toBeNull();
  });
  it("retains a generation-metadata clue even when the classifier misses it", () => {
    const result = imageAssessment([metadata, prediction(0.02), entry({ label: "generation_metadata", metadata: { markers: ["PNG generation parameters"] } })]);
    expect(result.title).toContain("metadata suggests");
    expect(result.score).toBe(0.02);
  });
  it("abstains on unstable scores without changing the original prediction", () => {
    const result = imageAssessment([metadata, entry({ ...prediction(0.99), metadata: { unstable: true } })]);
    expect(result.title).toContain("Unstable prediction");
    expect(result.score).toBe(0.99);
  });
  it("does not turn a document classifier score into an authenticity verdict", () => {
    const result = imageAssessment([entry({ metadata: { ocr: "CERTIFICATE OF APPRECIATION" } }), prediction(0.99999)]);
    expect(result.title).toContain("AI origin remains uncertain");
    expect(result.modelSuggestion).toContain("leans AI-generated");
  });
  it("abstains on OOD and conflicting origin evidence", () => {
    expect(imageAssessment([metadata, entry({ ...prediction(0.99), metadata: { ood: "possibly_out_of_distribution" } })]).title).toContain("Unable to determine");
    expect(imageAssessment([metadata, prediction(0.99), entry({ label: "trusted_camera_claim" })]).title).toContain("Conflicting");
  });
  it("uses a calibrated decision while retaining abstention and raw probability", () => {
    const model = entry({ ...prediction(.7), metadata: { calibration: "temperature_scaling", predicted_class: "ai_generated", verdict: "inconclusive", threshold: .6 } });
    const result = imageAssessment([metadata, model]);
    expect(result.calibrated).toBe(true);
    expect(result.title).toContain("Uncertain");
    expect(result.score).toBe(.7);
    expect(result.modelSuggestion).toContain("AI-generated");
    model.metadata.verdict = "likely_ai_generated";
    expect(imageAssessment([metadata, model]).title).toContain("likely AI-generated");
  });
});
