# Local experimental image model

Active version: `image-detector-v4-diversity-experimental`.

The user requested replacement of the older model after reviewing the experiment results. This is an explicit local experimental activation, not a passed production release gate. Original experiment metrics remain unchanged. The previous model files and registry remain available.

The trained residual linear head is fused into the frozen encoder checkpoint's classifier. Exported logits match the cached training computations within 0.001 (observed maximum absolute error approximately 0.00000372). Calibration temperature and threshold travel with the new checkpoint. The app reloads the registry for predictions, and its inference cache is keyed by checkpoint path and modification time.

A fixed 12-image validation smoke check exercised original, mirrored, and JPEG85 views: two examples were unstable and correctly remained inconclusive. This is an integration check, not full transformation robustness validation. The existing uncertainty policy has not been weakened.

Evaluation: 12,568 training images; 97.6% original-view accuracy on the newly reserved 500-image same-source test. Real-image false positives: 1/250. AI detections: 239/250. Earlier test sets are regression checks, and some scores decreased. Midjourney entered training and is no longer an unseen-generator benchmark. No guarantee applies to arbitrary uploads, and data license restrictions remain.

## Use and rollback

Create a new investigation or use **Run image detector again** on a retained image. Existing reports retain the model and scores originally used.

To roll back from the project root in PowerShell:

```powershell
Copy-Item -LiteralPath models/image/registry-before-diversity-v1.json -Destination models/image/registry.json -Force
```

New analyses will then use the preserved older checkpoint. No model binaries or uploaded samples need to be removed. Installation artifacts and the API smoke result are under `research/experiments/image-diversity-v1/`.
