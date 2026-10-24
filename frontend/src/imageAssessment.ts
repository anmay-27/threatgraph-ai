import type { Evidence } from "./types";

export function imageAssessment(evidence: Evidence[]) {
  // Scope to the submitted image, never a QR-linked image or page.
  const asset = evidence.find((e) => e.label === "image_metadata")?.asset_id;
  const items = evidence.filter((e) => e.asset_id === asset);
  const model = items.find((e) => e.source === "image_detector" && e.score !== null);
  const aiClaim = items.some((e) => e.label === "declared_ai_generation");
  const cameraClaim = items.some((e) => e.label === "trusted_camera_claim");
  const score = model?.score ?? null;
  const calibrated = model?.metadata.calibration === "temperature_scaling";
  const predictedAi = calibrated ? model?.metadata.predicted_class === "ai_generated" : score !== null && score >= 0.8;
  const predictedReal = calibrated ? model?.metadata.predicted_class === "real" : score !== null && score <= 0.2;
  const abstained = calibrated && model?.metadata.verdict === "inconclusive";
  const ood = model?.metadata.ood === "possibly_out_of_distribution";
  const unstable = model?.metadata.unstable === true;
  const classChanged = model?.metadata.stability_class_changed === true;
  const generation = items.find((e) => e.label === "generation_metadata");
  const metadata = items.find((e) => e.label === "image_metadata")?.metadata;
  const ocr = String(items.find((e) => e.label === "image_metadata")?.metadata.ocr || "");
  const documentLike = /\b(certificate|certification|diploma|transcript|invoice)\b/i.test(ocr) || ocr.trim().split(/\s+/).length >= 80;
  const conflict = (aiClaim && cameraClaim) || (aiClaim && score !== null && score <= 0.2) || (cameraClaim && score !== null && score >= 0.8);
  let title = "Unable to determine whether this image is AI-generated";
  let explanation = "The image detector did not produce a prediction for this report. Missing metadata or credentials cannot tell us whether an image is AI-generated.";
  if (conflict) {
    title = "Conflicting signals — manual review needed";
    explanation = "The image model and signed origin claims disagree. Neither should be treated as a definitive answer.";
  } else if (aiClaim) {
    title = "Signed provenance declares AI generation";
    explanation = "An intact signed credential declares algorithmic generation. This describes the origin claim, not whether the depicted content is true.";
  } else if (cameraClaim) {
    title = "Signed provenance declares camera capture";
    explanation = "A trusted signed credential declares camera capture. This does not prove the image is unedited or its contents are true.";
  } else if (model && score !== null) {
    title = ood ? "Unable to determine — outside the model’s familiar domain" : score >= 0.8 ? "Model suggests: likely AI-generated" : score <= 0.2 ? "Model suggests: likely non-AI" : "Uncertain — no clear AI or non-AI signal";
    explanation = "This is an experimental visual classifier suggestion. A non-AI prediction does not establish that an image, certificate, identity or claim is genuine. Mixed images can contain both real and generated elements.";
    if (calibrated && !ood) {
      title = abstained ? "Uncertain — the model needs independent evidence" : predictedAi ? "Model suggests: likely AI-generated" : "Model suggests: likely non-AI";
      explanation = model.metadata.pretrained_source
        ? "This pretrained research classifier was temperature-calibrated on a limited local partition; overlap with its original training data cannot be ruled out. A non-AI suggestion can miss AI-generated images, including convincing portraits and unfamiliar generators. The score is not a verified real-world probability or proof of camera origin."
        : "This classifier was trained and temperature-calibrated on separate research partitions. Its probability is dataset-specific. A real-image prediction does not authenticate the subject or establish that a document is genuine.";
    }
    if (documentLike) {
      title = "Document-like image — AI origin remains uncertain";
      explanation = "Extracted text suggests a document or text-heavy design. Whole-image AI classifiers can misread these layouts. The model output below is a screening signal, not a reliable verdict for this type of image. Verify the document with its issuer.";
    }
  }
  if (!conflict && !aiClaim && !cameraClaim && generation) {
    title = "Embedded metadata suggests an AI-generation workflow";
    explanation = "The file contains explicit generation-tool metadata. This is a useful origin clue, even when the visual classifier misses it, but editable metadata cannot prove that the entire image was generated.";
  } else if (!conflict && !aiClaim && !cameraClaim && unstable) {
    title = "Unstable prediction — AI origin is uncertain";
    explanation = classChanged ? "A flip or recompression changed which side of the model’s decision threshold this image falls on. The original probability is retained, but the class prediction is not stable." : "Small transformations changed the model’s AI score substantially. The original score is retained below, but this result should not be relied on as a clear AI/non-AI verdict.";
  }
  return {
    title, explanation, score, model, calibrated, abstained,
    diagnostics: (model?.metadata.stability_checks || []) as { name: string; score: number }[],
    observations: [
      generation ? `Generation metadata: ${(generation.metadata.markers || []).join("; ")}. These fields can be edited.` : "No explicit generation-tool metadata was detected in this report. Many generators remove it, so absence is not evidence of a real photograph.",
      metadata ? `Inspected ${metadata.width} × ${metadata.height} pixels (${metadata.encoding || "image"}). The classifier resizes the image; fine details may be lost.` : "Image dimensions were not available.",
      classChanged ? "At least one flip/recompression check changed the predicted class, even if the score difference was small." : unstable ? "The score varies by at least 25 percentage points under flip/recompression checks. This is a sensitivity warning, not an accuracy measurement." : model?.metadata.stability_checks?.length ? "The tested transformations did not trigger the sensitivity warning. A stable model can still be wrong." : "Transformation stability was not tested in this saved report. Rerun with the updated detector to check it.",
    ],
    modelSuggestion: score === null ? null : predictedAi ? "Model leans AI-generated" : predictedReal ? "Model leans non-AI" : "Model has no clear preference",
    reasons: [
      model ? `Image classifier: ${model.model_version}. ${model.metadata.limitations || "Performance can vary on unfamiliar images and generators."}` : "No image-model prediction is available in this saved report. Run it again with the current detector.",
      model?.metadata.ood === "not_estimated" ? "This report did not estimate whether this image falls outside the model's training domain; a stable low score can still be a false negative." : "A low AI score can still be a false negative on an unfamiliar generator or edited image.",
      aiClaim || cameraClaim ? "Signed origin information was found; inspect the Provenance tab for validation details." : "No verified AI-generation or camera-origin claim supports a definite conclusion.",
      !conflict && !abstained && !unstable && !ood && ((aiClaim && predictedAi) || (cameraClaim && predictedReal)) ? "The classifier and signed origin claim point in the same direction. Agreement supports the origin assessment, not the truth of the depicted content." : "AI generation alone is not evidence of fraud or malicious intent.",
      "EXIF data, JPEG compression and image dimensions alone are not reliable proof of AI generation.",
    ],
    recommendations: [
      "Ask for the original image and its source or editing history; screenshots and forwarded copies can remove useful evidence.",
      "For a certificate or document, verify its ID and details directly with the issuing organization. This model cannot authenticate documents.",
      "Check an independent source or reverse-image search before relying on the image. Visual oddities alone do not prove AI generation.",
    ],
  };
}
