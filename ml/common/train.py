import argparse
import csv
import random
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from ml.common.data import read_manifest, MediaDataset
from ml.common.model import Detector
from ml.common.metrics import metrics, plots, save_json


def predict(model, loader, device):
    model.eval()
    ys, logits, embeddings = [], [], []
    with torch.inference_mode():
        for x, y in loader:
            z, e = model(x.to(device))
            ys.extend(y.numpy().tolist())
            logits.extend(z.cpu().numpy().tolist())
            embeddings.extend(e.cpu().numpy().tolist())
    return np.asarray(ys), np.asarray(logits), np.asarray(embeddings)


def main(modality):
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=0.0001)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument(
        "--architecture", choices=["resnet18", "efficientnet_b0", "convnext_tiny"], default="efficientnet_b0" if modality == "image" else "resnet18"
    )
    p.add_argument("--patience", type=int, default=3)
    p.add_argument("--held-out-generator", default="")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--freeze-backbone", action="store_true")
    p.add_argument("--trainable-blocks", type=int, default=0)
    p.add_argument("--selection-metric", choices=['f1', 'roc_auc'], default='f1')
    p.add_argument("--max-calibration-fpr", type=float)
    p.add_argument("--init-checkpoint", type=Path, help="Initialize network weights from an existing local checkpoint; old calibration is ignored")
    args = p.parse_args()
    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    output = args.output_dir
    if (output / "metrics.json").exists():
        raise ValueError("Already evaluated; choose a new experiment directory")
    output.mkdir(parents=True, exist_ok=True)
    rows = read_manifest(args.data_dir)
    splits = {
        s: [r for r in rows if r["split"] == s]
        for s in ("train", "validation", "calibration", "test", "ood")
    }
    if args.held_out_generator and any(
        r["generator"] == args.held_out_generator
        for r in splits["train"] + splits["validation"] + splits["calibration"]
    ):
        raise ValueError("Held-out generator leaked into model selection")
    labels = np.array([int(r["label"]) for r in splits["train"]])
    weights = 1 / np.bincount(labels)[labels]
    sampler = WeightedRandomSampler(
        torch.tensor(weights), len(labels), replacement=True
    )
    loaders = {
        s: DataLoader(
            MediaDataset(args.data_dir, r, modality, s == "train"),
            batch_size=args.batch_size,
            sampler=sampler if s == "train" else None,
            num_workers=0,
        )
        for s, r in splits.items()
        if r
    }
    model = Detector(modality, args.architecture, pretrained=modality != "audio" and not args.init_checkpoint).to(args.device)
    if args.init_checkpoint:
        initial = torch.load(args.init_checkpoint, map_location="cpu", weights_only=True)
        if initial.get("config", {}).get("architecture") != args.architecture or initial.get("config", {}).get("modality") != modality:
            raise ValueError("Initialization checkpoint modality/architecture mismatch")
        model.load_state_dict(initial["state_dict"])
    if args.freeze_backbone or args.trainable_blocks:
        for parameter in model.encoder.parameters():
            parameter.requires_grad_(False)
        if args.trainable_blocks:
            if not hasattr(model.encoder, "features"):
                raise ValueError("Partial unfreezing requires an encoder with features")
            for parameter in model.encoder.features[-args.trainable_blocks:].parameters():
                parameter.requires_grad_(True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, max(args.epochs, 1)
    )
    scaler = torch.amp.GradScaler("cuda", enabled=args.device.startswith("cuda"))
    loss_fn = nn.BCEWithLogitsLoss()
    best_score = -1.0
    stale = 0
    history = []
    config = {
        k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
    } | {"modality": modality}
    save_json(output / "config.json", config)
    save_json(output / "split_manifest.json", rows)
    for epoch in range(args.epochs):
        model.train()
        if args.freeze_backbone or args.trainable_blocks:
            model.encoder.eval()  # Keep frozen ImageNet normalization statistics fixed.
        losses = []
        for x, y in loaders["train"]:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(
                device_type="cuda" if args.device.startswith("cuda") else "cpu",
                enabled=args.device.startswith("cuda"),
            ):
                logits, _ = model(x.to(args.device))
                loss = loss_fn(logits, y.to(args.device))
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            losses.append(loss.item())
        scheduler.step()
        y, z, _ = predict(model, loaders["validation"], args.device)
        result = metrics(y, 1 / (1 + np.exp(-np.clip(z, -50, 50))))
        history.append(
            {
                "epoch": epoch + 1,
                "loss": float(np.mean(losses)),
                "validation_f1": result["f1"],
                "validation_auc": result["roc_auc"],
            }
        )
        checkpoint = {
            "state_dict": model.cpu().state_dict(),
            "config": config,
            "epoch": epoch + 1,
        }
        torch.save(checkpoint, output / "last.pt")
        if result[args.selection_metric] > best_score:
            best_score = result[args.selection_metric]
            stale = 0
            torch.save(checkpoint, output / "best.pt")
        else:
            stale += 1
        model.to(args.device)
        print(history[-1], flush=True)
        if stale >= args.patience:
            break
    checkpoint = torch.load(output / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    model.to(args.device)
    vy, vz, ve = predict(model, loaders["validation"], args.device)
    cy, cz, _ = predict(model, loaders.get("calibration", loaders["validation"]), args.device)
    # Dedicated calibration partition when present; never use test/OOD labels.
    temperatures = np.geomspace(0.25, 4, 25)
    temperature = float(
        min(
            temperatures,
            key=lambda t: metrics(cy, 1 / (1 + np.exp(-np.clip(cz / t, -50, 50))))[
                "brier"
            ],
        )
    )
    vp = 1 / (1 + np.exp(-np.clip(vz / temperature, -50, 50)))
    cp = 1 / (1 + np.exp(-np.clip(cz / temperature, -50, 50)))
    threshold = float(
        max(np.linspace(0.1, 0.9, 33), key=lambda t: metrics(cy, cp, t)["f1"])
    )
    if args.max_calibration_fpr is not None:
        if not 0 <= args.max_calibration_fpr <= 1:
            raise ValueError('Calibration FPR bound must be between 0 and 1')
        candidates = [(float(t), metrics(cy, cp, t)) for t in np.linspace(.01, 1, 100)]
        eligible = [(t, m) for t, m in candidates if m['false_positive_rate'] <= args.max_calibration_fpr]
        if not eligible:
            raise ValueError('No decision threshold meets the calibration FPR constraint')
        threshold = max(eligible, key=lambda pair: (pair[1]['recall'], pair[1]['balanced_accuracy'], pair[0]))[0]
    # OOD embedding statistics from training only; cutoff from validation.
    clean_train = DataLoader(
        MediaDataset(args.data_dir, splits["train"], modality, False),
        batch_size=args.batch_size,
    )
    _, _, te = predict(model, clean_train, args.device)
    mean = te.mean(0)
    variance = te.var(0) + 1e-4
    distances = np.mean((ve - mean) ** 2 / variance, axis=1)
    checkpoint.update(
        {
            "temperature": temperature,
            "threshold": threshold,
            "ood_mean": mean.tolist(),
            "ood_variance": variance.tolist(),
            "ood_threshold": float(np.quantile(distances, 0.99)),
            "calibration": "temperature_scaling",
            "calibration_partition": "calibration" if "calibration" in loaders else "validation",
        }
    )
    torch.save(checkpoint, output / "best.pt")
    ty, tz, _ = predict(model, loaders["test"], args.device)
    tp = 1 / (1 + np.exp(-np.clip(tz / temperature, -50, 50)))
    results = {
        "validation": metrics(vy, vp, threshold),
        "calibration": metrics(cy, cp, threshold),
        "calibration_before": metrics(cy, 1 / (1 + np.exp(-np.clip(cz, -50, 50))), threshold),
        "test": metrics(ty, tp, threshold),
        "per_generator": {},
    }
    for generator in {r["generator"] for r in splits["test"] if int(r["label"]) == 1}:
        # Each generator is evaluated against the same real-negative subset.
        mask = np.array([r["generator"] == generator or int(r["label"]) == 0 for r in splits["test"]])
        results["per_generator"][generator] = metrics(ty[mask], tp[mask], threshold)
    if "ood" in loaders:
        oy, oz, oe = predict(model, loaders["ood"], args.device)
        results["held_out_generator"] = metrics(
            oy, 1 / (1 + np.exp(-np.clip(oz / temperature, -50, 50))), threshold
        )
        results["ood_flag_rate"] = float(
            (
                np.mean((oe - mean) ** 2 / variance, axis=1)
                > checkpoint["ood_threshold"]
            ).mean()
        )
    save_json(output / "metrics.json", results)
    save_json(
        output / "registry.json",
        {
            "name": modality,
            "version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "architecture": "logmel-cnn" if modality == "audio" else args.architecture,
            "training_dataset": str(args.data_dir),
            "date_trained": datetime.now(timezone.utc).isoformat(),
            "validation_metrics": results["validation"],
            "test_metrics": results["test"],
            "threshold": threshold,
            "file_path": "best.pt",
            "runtime": "torch_media",
            "calibration": "temperature_scaling",
            "temperature": temperature,
            "classes": {"0": "real", "1": "ai_generated"},
            "deployment_status": "research_calibrated",
            "limitation": "Small public GenImage derivative subset; calibration is dataset-specific. Unseen generators and real-world inputs may generalize poorly. Synthetic origin does not establish malicious intent.",
            "held_out_generator": args.held_out_generator,
            "cross_generator_metrics": results.get("held_out_generator"),
        },
    )
    with (output / "training_history.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    save_json(output / "class_map.json", {"0": "real", "1": "ai_generated"})
    save_json(output / "test_predictions.json", [{"path": r["path"], "generator": r["generator"], "label": int(r["label"]), "probability": float(p)} for r, p in zip(splits["test"], tp)])
    plots(ty, tp, output / "plots", threshold)
    print(results)
