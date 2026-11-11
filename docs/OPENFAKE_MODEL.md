# Modern-generator detector integration

The active candidate is `s-gehring/detectra-openfake`, revision `c84565e5bf8969d95908e12844f551e77ae87105`, ONNX SHA-256 `b5bd0fd699469b721b00f6a5626a2616b2b0a34283eece124d90451147ab7fc6`. Read the upstream model card saved beside the model for training data, attribution, and noncommercial license conditions. Personal uploads are never sent to the publisher.

This is a publisher-fine-tuned model, not a new local training claim. It uses the documented ImageNet normalization, 440-short-edge/384-center crop, Platt transform `sigmoid(0.552*logit+0.1933)`, and 0.95 AI cutoff. The documented optional 576/768 passes apply only when the original score is between 0.5 and 0.95. The maximum publisher-scaled score is retained. We do not tune thresholds on the user's examples.

Local diagnostic benchmark: first 20 examples per class, ordered by path, in each of the existing poster, modern, and diverse test groups. 120 total; 112 correct binary decisions at the publisher cutoff, no false positives among 60 real examples, eight misses among 60 synthetic examples (all in the diverse group). These previously examined research sets are not independent field validation. Upstream training overlap is unknown. Binary threshold metrics do not measure the UI's abstention coverage.

The user's portrait and event poster are regression examples only, excluded from fitting and aggregate metrics. Scores before activation were approximately 0.9683 and 0.9910 respectively. These scores are not probabilities of verified origin. No logo detector contributes to them.

`scripts/benchmark_openfake.py` produces local predictions and results; `scripts/activate_openfake.py` performs the explicit local experimental switch. All previous checkpoints remain intact. Roll back by copying `models/image/registry-before-openfake.json` onto `models/image/registry.json` and running a new investigation. Existing reports retain their original model version and results.

Model card: https://huggingface.co/s-gehring/detectra-openfake
