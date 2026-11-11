# Source-balanced follow-up experiment

The completed 10k experiment improved modern-image recall but failed the release gate because modern real-image false positives reached 12.5%. Preserve that experiment unchanged.

Run `.venv/Scripts/python.exe -u scripts/train_image_balanced.py` from the repository root. The script verifies the cached encoder fingerprint and reuses features from all 14,492 images. It fits a new residual classification head on the same 10,568 training images; it does not download additional images or fine-tune the encoder.

Before evaluating regression sets, this follow-up fixes the following procedure:

- Give each source/class training stratum equal total weight.
- Select regularization from 0.1, 1, and 10 using worst-source validation log loss.
- Fit temperature using equally weighted source calibration losses.
- Select a threshold maximizing worst-source calibration balanced accuracy, subject to a false-positive rate at most 2.5% in each calibration source. This is an empirical calibration constraint, not a statistical guarantee.
- Save the adapter before calculating regression results.

The earlier test sets have already influenced the choice to investigate source balance. Consequently, their new scores are regression checks, not a fresh unbiased estimate of accuracy. No automatic installation is permitted even if they improve. Promotion requires a newly collected, deduplicated holdout of real photographs, human-designed posters, edited images, and multiple synthetic generators, plus transformation-stability evaluation. Neither the old tests nor the new holdout may be added to fitting data or used to repeatedly tune a candidate.

Artifacts are local under `research/experiments/image-balanced-v1/`. A finalized run cannot be overwritten by rerunning the script.
