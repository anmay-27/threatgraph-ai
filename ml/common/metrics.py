import json
from pathlib import Path
import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    balanced_accuracy_score,
    brier_score_loss,
    roc_curve,
)


def metrics(y, p, threshold=0.5):
    y, p = np.asarray(y), np.asarray(p)
    prediction = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    ece = 0.0
    for low in np.linspace(0, 0.9, 10):
        mask = (p >= low) & (p < low + 0.1 if low < 0.89 else p <= 1)
        if mask.any():
            ece += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    two_classes = len(np.unique(y)) == 2
    eer = None
    if two_classes:
        fpr, tpr, _ = roc_curve(y, p)
        i = np.argmin(abs(fpr - (1 - tpr)))
        eer = float((fpr[i] + 1 - tpr[i]) / 2)
    return {
        "accuracy": float(np.mean(prediction == y)),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "roc_auc": float(roc_auc_score(y, p)) if two_classes else None,
        "pr_auc": float(average_precision_score(y, p)) if two_classes else None,
        "brier": float(brier_score_loss(y, p)),
        "ece": float(ece),
        "false_positive_rate": float(fp / max(1, fp + tn)),
        "eer": eer,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "count": len(y),
    }


def plots(y, p, output, threshold=0.5):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import (
        RocCurveDisplay,
        PrecisionRecallDisplay,
        ConfusionMatrixDisplay,
    )
    from sklearn.calibration import CalibrationDisplay

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, display in [
        ("roc", RocCurveDisplay),
        ("precision_recall", PrecisionRecallDisplay),
        ("calibration", CalibrationDisplay),
    ]:
        display.from_predictions(y, p)
        plt.savefig(output / f"{name}.png", bbox_inches="tight")
        plt.close()
    ConfusionMatrixDisplay.from_predictions(y, np.asarray(p) >= threshold, labels=[0, 1])
    plt.savefig(output / "confusion_matrix.png", bbox_inches="tight")
    plt.close()


def save_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8"
    )
