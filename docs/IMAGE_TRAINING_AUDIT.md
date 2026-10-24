# Image module audit (2026-10-03)

The project already has the required API and report pipeline. No duplicate API or frontend is needed.

| Existing component | Finding | Required completion |
|---|---|---|
| `ml/image_detector/{data,model,train,evaluate,infer}.py` | Thin wrappers over shared media training | Extend the shared implementation, retain wrappers |
| `ml/common/train.py` | Transfer learning, augmentation, temperature calibration, embedding OOD, checkpoints | ConvNeXt support, bounded CPU configuration, accuracy, correct threshold plots, separated calibration, generator evaluation |
| `ml/common/data.py` | Manifest validation, group/hash split checks | Dataset acquisition and group-preserving preparation |
| `backend/app/analyzers/image/inspect.py` | Real decoding, metadata, OCR, QR, C2PA and detector call | Keep existing invocation |
| `backend/app/services/registry.py` | Cached model loaders and missing-checkpoint fallback | Register the selected project-trained artifact and expose its calibration/uncertainty |
| `backend/app/schemas/evidence.py` | Bounded score/confidence/uncertainty and comparable hypothesis | Reuse schema |
| `backend/app/services/investigation.py` | Persistence, evidence/model results, graph and report | Reuse propagation and JSON export |
| `backend/app/fusion/engine.py` | Same-asset conflicts; all scored categories currently feed risk | Separate synthetic origin from malicious intent; contextualize risk |
| `frontend/src/components/ImageAssessment.tsx` | Experimental external-model suggestion and limitations | Display genuine calibrated score, class, confidence, uncertainty, architecture/version |
| Current `models/image/registry.json` | External SigLIP checkpoint; no local training or evaluation | Preserve it as a fallback/archive; install a measured local checkpoint only after verification |

Compute: PyTorch 2.11 CPU build, CUDA unavailable; approximately 147 GB free at audit. CPU experiments will be bounded and their limits documented. Full GenImage is too large for this run, so preparation must retain source identities, use a seeded subset and reserve an unseen generator. Official GenImage `val` is benchmark test data, not model-selection validation.

## Implemented follow-through (October 9)

The initial audit above is historical. Actual experiment and browser evidence is in [IMAGE_TRAINING_RESULTS.md](IMAGE_TRAINING_RESULTS.md).

Changed implementation areas:
- `datasets/scripts/download_genimage_subset.py`, `prepare_genimage_subset.py`: pinned acquisition, resumable checksummed downloads, provenance, deduplication, stratified separate calibration/test/OOD partitions.
- `ml/common/{model,media,data,train,metrics,inference,evaluate}.py`, image config and ML requirements: ConvNeXt, augmentation, separated calibration, complete measured metrics, OOD and sensitivity-aware inference, threshold-correct plots.
- `scripts/install_trained_image.py`, `summarize_image_training.py`, `install_image_model.py`: validation-only candidate selection, local artifact registration/archive, measured report generation and accidental downgrade protection.
- `backend/app/services/registry.py`, `fusion/engine.py`, `schemas/evidence.py`: model metadata propagation; synthetic origin is informational and independent of security risk.
- `frontend/src/{main.tsx,theme.css,Graph.tsx,imageAssessment.ts}`, `components/ImageAssessment.tsx`, `pages/Result.tsx`, font package/lock: bundled Inter, preview and probability summary, uncertainty/model facts, expandable explanations, responsive navigation and graph fit.
- Backend and frontend tests, trained-image browser upload tests, screenshots, research artifacts and README/ML_PIPELINE/RESEARCH/IMPLEMENTATION_STATUS/models documentation.

Integration is verified. Accuracy remains a research limitation rather than a completed production-quality claim.
