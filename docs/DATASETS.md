# Dataset access, licensing, and preparation

No restricted dataset is automatically fetched. Never visit malicious URLs while preparing training rows. Obtain and cite each dataset from its owner; derived samples can remain subject to source-image and speaker restrictions.

| Dataset | Source and access | Use / limitations |
|---|---|---|
| PhiUSIIL | [UCI dataset 967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), CC BY 4.0 | Open local URL baseline; legitimate label 1 is inverted to risk label 0. Cite Prasad & Chandra (2024), DOI 10.1016/j.cose.2023.103545. |
| PhishTank | [Developer feed](https://www.phishtank.com/developer_info.php) | Obtain an authorized current verified feed; quotas and feed access apply. Feed parser accepts verified online entries. |
| URLhaus | [API](https://urlhaus.abuse.ch/api/) | Malware URL CSV ingestion and optional Auth-Key reputation adapter. Follow current fair-use/access requirements. |
| Tranco | [Research rankings](https://tranco-list.eu/) | Record exact list ID/date and cite Le Pochat et al. (2019). Top-ranked domains are weak benign labels, not guaranteed safe pages. |
| GenImage | [Official repository](https://github.com/GenImage-Dataset/GenImage) | Follow dataset/license and underlying source-image terms. Cite Zhu et al., GenImage, NeurIPS 2023. Keep one generator entirely out of train and validation. |
| ASVspoof | [Official 2021 page](https://www.asvspoof.org/index2021.html), linked Zenodo records | Obtain 2019 training/development and authorized 2021 evaluation data and protocol keys. 2021 does not provide matched training/development data. Follow the exact chosen record's license and citations. |
| FaceForensics++ | [Official repository](https://github.com/ondyari/FaceForensics), [terms](https://kaldir.vc.in.tum.de/faceforensics_tos.pdf) | Requires access request and agreement. Noncommercial/research restrictions apply. Code license is distinct from dataset terms. Cite Rössler et al., ICCV 2019. |
| DFDC | [Official competition](https://www.kaggle.com/c/deepfake-detection-challenge/data) | Authenticate and accept dataset/competition terms yourself. Record the accepted version and cite Dolhansky et al. |

## URL records

```sh
python datasets/scripts/download_open_urls.py
python datasets/scripts/prepare_urls.py --source datasets/raw/phiusiil/urls.csv --kind phiusiil --output datasets/prepared/urls.csv
python datasets/scripts/prepare_urls.py --source datasets/raw/verified_online.json --kind phishtank --output datasets/prepared/phishtank.csv
python datasets/scripts/prepare_urls.py --source datasets/raw/urlhaus.csv --kind urlhaus --output datasets/prepared/urlhaus.csv
python datasets/scripts/prepare_urls.py --source datasets/raw/tranco.csv --kind toplist --output datasets/prepared/benign.csv
```

Prepared CSV: `url,label,source`, where 1 means phishing/malware and 0 means benign. Preserve source/date metadata when combining feeds. Deduplicate URLs, reject conflicting labels, and split by registrable domain. Avoid artificial features such as all malicious URLs using HTTP and all benign URLs using HTTPS.

## Media manifests

Each approved data directory contains `manifest.csv` with:

```csv
path,label,split,group,generator
images/example-real.jpg,0,train,source-identity-0001,camera
images/example-generated.jpg,1,train,source-identity-0002,generator-a
```

The example only describes the schema; these files are not supplied. Real manifests must contain both classes in train, validation, and test. Allowed splits: `train`, `validation`, `test`, `ood`. Labels: 0 natural/bona fide; 1 synthetic/manipulated. Group must capture the source identity (speaker, original video and all derivatives, or original image), not an individual frame filename. Training rejects group and exact-content overlap across splits. Near-duplicate and semantic identity review remains the researcher's responsibility.

For GenImage, retain generator identity, hold an entire generator in `ood`, and use `--held-out-generator`. For ASVspoof, preserve official attack/speaker protocols; use short utterances or pre-chunk all splits consistently to at most four seconds. Long recordings use chunked inference, but training validation uses the first chunk of a manifest item; do not silently compare these as identical protocols.

For video, first create a source-video manifest and run:

```sh
python datasets/scripts/prepare_video.py --manifest datasets/raw/ffpp/manifest.csv --output-dir datasets/prepared/video
```

This extracts up to 24 largest-face crops per clip. Source group/split and timestamps are preserved. It is a Haar face-crop baseline, not landmark alignment or a face tracker. Frame metrics and video aggregation metrics must be reported separately.
