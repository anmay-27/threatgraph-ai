# Local temporal video screening

The local installation now includes VideoMAE-base, a temporal video classifier, through the offline `huggingface_video` adapter. This is an experimental third-party checkpoint, not a model trained or independently benchmarked by this project.

Source: [SoraExplora/VideoMae model card](https://huggingface.co/SoraExplora/VideoMae), pinned revision `8456c9f29444cda60484d5403513d1bc695fb1ad`. The mirror declares MIT and attributes training to Vansh Momaya on a FaceForensics++ C23 subset. The attributed original repository returned HTTP 401 during setup. Its reported validation metrics are publisher claims, deliberately not copied into the project's test-metrics field. File SHA-256 values are saved in `models/video/videomae-ffpp/source.json`.

Only safetensors and built-in Transformers classes are loaded, with local files only. No repository Python or remote custom code executes. Re-fetch with `python scripts/download_video_model.py`; the download itself does not silently activate a checkpoint.

The adapter samples 16 whole RGB frames uniformly over a clip, then applies the checkpoint's resize, center crop and normalization. A Haar face detector checks domain suitability without replacing frames with face crops. Fewer than eight sampled frames with detectable faces, fewer than 16 video frames, decode failures or duration over ten minutes produce an unavailable result. This conservative gate can miss profile/occluded faces. Whole-frame center cropping can miss off-center manipulation.

The UI shows the raw manipulation score and model class suggestion, exact sample timestamps, facial coverage and an unverified conclusion. There is no calibrated probability, independent accuracy claim, per-frame manipulation timeline or pixel localization. Audio is a separate capability. This detector contributes no security-risk score.

`scripts/verify_video_runtime.py` ran the actual checkpoint on a translated astronaut still-image fixture. Sixteen frames were decoded, 16 had detectable faces and the model returned a finite score. This validates runtime plumbing only; it is not a real-versus-deepfake accuracy test. The fixture derives from scikit-image's public astronaut image and must never be presented as a successful deepfake benchmark.

Before claiming field accuracy, evaluate untouched, identity-disjoint real/manipulated videos with documented rights, varied compression and unseen generators, then calibrate on a separate partition. Current standalone audio cloning detection still lacks a trained checkpoint.
