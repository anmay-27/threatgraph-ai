# Research methodology and current evidence

Hypothesis: conflict-aware, uncertainty-aware multimodal evidence fusion improves reliability over independent detectors and weighted averaging. **This hypothesis has not been validated by the current repository's results.** No fabricated multimodal training labels or measurements are supplied.

Measured results now include a lexical URL baseline and two bounded CPU image-transfer experiments. Neither is an evaluation of the full platform. Image dataset protocol, exact metrics, per-generator artifacts, calibration, confusion matrices, cross-generator comparison and real upload results are recorded in [image training results](IMAGE_TRAINING_RESULTS.md) and `research/results/image_training_comparison.json`. ConvNeXt wins the fixed validation selection rule but achieves only 63% test accuracy; the test-set degradation is retained, not hidden or tuned away. EfficientNet achieves 67.75% test accuracy. No research-superiority or general-purpose accuracy claim follows from these experiments.

URL exact metrics and selected registry metadata are in `research/results/url_metrics.json` and `url_registry.json`.

| Selected model | Validation F1 | Test F1 | Test ROC-AUC | Test PR-AUC | Test FPR |
|---|---:|---:|---:|---:|---:|
| Calibrated histogram gradient boosting | 0.998261 | 0.994170 | 0.997135 | 0.997773 | 0.002596 |

Test count: 5,787. Test confusion matrix: TN=3,458, FP=9, FN=18, TP=2,302. Brier score=0.004138; ECE=0.002433. Validation has 6,850 rows; domain grouping causes counts to differ from exact 60/20/20 proportions. The checkpoint is locally retained at `models/url/best.joblib` and excluded from Git.

These high values warrant caution. Source selection and lexical artifacts can make a dataset easier than real attacks. In the full source CSV, every benign URL is HTTPS, while 51,749 malicious URLs are HTTP and 49,196 are HTTPS. Domain separation prevents same-domain leakage, but does not remove source bias. The model has no demonstrated temporal, campaign, language, new-TLD, or external-feed generalization. No accuracy claim should be made for current websites based on this benchmark alone.

**Observed external failure:** the frozen checkpoint assigns `https://example.com/` raw phishing probability **0.9994696244**. This is a false positive on a known benign reference URL and directly demonstrates the generalization limitation. The checkpoint remains experimental: deployed evidence confidence is capped at 0.35, leading to review-level uncertainty rather than a confident security verdict. The raw probability is preserved; weights, labels and recorded benchmark metrics were not altered. This confidence cap is a conservative deployment policy, not a learned calibration fix. Independent-source retraining and validation are required before removing it.

## Planned experiments

`research/experiments/compare_fusion.py` writes CSV, JSON, Markdown, LaTeX rows and plots for independent maximum, weighted average, learned fusion, learned+conflict, and learned+conflict+uncertainty on a common group-disjoint holdout. It requires real labeled investigations with out-of-fold base predictions. Ablations are predefined and not selected by test score. Report coverage alongside accuracy because empty evidence abstains.

Media training records precision/recall/F1, balanced accuracy, ROC/PR-AUC, Brier/ECE, EER and confusion matrices where defined; one-class slices have undefined AUC represented as null. GenImage cross-generator tests and ASVspoof cross-attack tests must be separate from in-domain performance. Video face-frame metrics do not replace video-level evaluation. OOD distance thresholds use validation data; measure actual OOD sensitivity/false-alarm rates on independent unknown sources.

Required before claiming the hypothesis: approved media training data, independent campaign-labeled fusion data, baseline training, model calibration, preregistered ablations, uncertainty/coverage curves, cross-source testing, confidence intervals and failure analysis. No such scores are present yet. See IMPLEMENTATION_STATUS.md for exact acceptance gaps.

Experimental URL outputs are retained as informational screening signals and excluded from numeric risk fusion until independently validated. False-positive generalization is unresolved. The report exposes missing page checks; it does not equate an unavailable fetch with a safe or malicious page.
