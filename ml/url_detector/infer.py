import argparse
import joblib
from app.analyzers.url.features import features

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--url", required=True)
    a = p.parse_args()
    print(float(joblib.load(a.checkpoint).predict_proba([features(a.url)])[0, 1]))
