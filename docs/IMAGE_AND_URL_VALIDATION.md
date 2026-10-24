# Image and URL validation, 19 October 2026

## Image model decision

The existing v3 Community Forensics model remains installed. The v4 candidate was trained locally on **1,000 labeled images** (500 real, 500 synthetic), with separate 100-image validation, 100-image calibration, 600-image test and 200-image held-out Midjourney split. The 1,000-image training set was repartitioned from the previously duplicate-filtered Tiny-GenImage v3 development images. Its source and limitations are recorded in `datasets/prepared/tiny-genimage-v4/preparation.json`. V4 was initialized from the existing local EfficientNet v2 checkpoint; only its weights, not its old calibration, were reused. The active registry was not changed.

| Model and split | Images | Balanced accuracy | AI recall | False-positive rate |
|---|---:|---:|---:|---:|
| New EfficientNet v4, test | 600 | 60.3% | 21.7% | 1.0% |
| New EfficientNet v4, held-out generator | 200 | 55.0% | 11.0% | 1.0% |
| Installed Community Forensics v3, prior same v3 test | 600 | 98.5% | 98.0% | 1.0% |
| Installed v3, prior held-out generator | 200 | 93.0% | 89.0% | 3.0% |

The candidate fails the deployment gate because it misses substantially more AI images. It is retained as an experiment at `research/experiments/image-efficientnet-v4`; the installed model is unchanged. The v3 benchmark may overlap the external model's unknown pretraining corpus, so its strong research scores are **not field accuracy**.

## Poster-specific external test

An untouched 100-image **CommercialPosters** slice was downloaded from the [TextRich dataset card](https://huggingface.co/datasets/Shuyiww/TextRich) at pinned revision `0cf15b6dce9d45e6f6593d95880727d3a493f93b`. It contains 50 real Crello-subset posters and 50 GPT-Image-2 synthetic posters, per the dataset authors. Neither model used this slice for training or calibration. Image hashes and source paths are in `datasets/external/textrich-commercial-posters/manifest.csv`.

| Model | Balanced accuracy | AI posters missed | Real posters falsely flagged | Inconclusive under current uncertainty rule |
|---|---:|---:|---:|---:|
| Installed v3 | 94.0% | 4 / 50 | 2 / 50 | 48 / 100 |
| Candidate v4 | 49.0% | 50 / 50 | 1 / 50 | 88 / 100 |

These are exploratory results on one generator and one real source. The poster slice is small and the installed model's upstream pretraining overlap has not been audited. The high abstention count means even a correct binary class on this test often does not yield a definite in-app verdict. More independent poster generators and human designs are needed before claiming broad poster accuracy. The user's saved AI portrait scored 9.9% AI and remains a documented false negative; no single sample justifies threshold tuning.

Metrics and per-file predictions: `research/experiments/image-poster-external/metrics.json` and its adjacent prediction files. Reproduce with `python scripts/evaluate_poster_models.py` after preparing the pinned poster subset with `python datasets/scripts/download_textrich_posters.py`.

## Google Meet URL reproduction

Google's [Meet help page](https://support.google.com/meet/answer/17302648) identifies `meet.google.com` as its homepage. The guarded fetch of the user-supplied `https://meet.google.com/home` returned HTTP 200 after redirects to `accounts.google.com` sign-in. Only the public sign-in response was inspectable; authenticated Meet content was not. The old static parser assigned a risk score merely because the page contained a password field, and an experimental URL-pattern model gave the official URL a near-100% phishing score despite its known field false positives.

The corrected pipeline treats password presence as neutral unless there is an independently scored concern such as a mismatched credential destination or unencrypted sensitive-data submission. The experimental lexical model is skipped for locally listed first-party domains and nested page resources; it remains available for other navigational URLs but is excluded from security-risk fusion. The report now shows the locally listed domain match, redirect destination, authentication gate and incomplete checks. The local first-party list is a screening reference, **not** a safety certificate.

The full rerun is analysis `be034138-140d-4cf9-a16c-83223852b594`: partial coverage, **UNKNOWN** security risk, no experimental URL score and a neutral password observation. Coverage is partial chiefly because the local ClamAV scanner was unavailable and external reputation was not configured. This is more honest than a phishing or safe verdict without complete evidence.
