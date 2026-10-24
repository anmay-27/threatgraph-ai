import csv
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from app.analyzers.url.features import features, domain


def load(path, seed=42, max_rows=0):
    unique = {}
    with open(path, encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            url = row["url"].strip()
            label = int(row["label"])
            if label not in (0, 1):
                raise ValueError("Labels must be 0 benign, 1 phishing/malware")
            if url in unique and unique[url] != label:
                raise ValueError("Contradictory labels for the same URL")
            unique[url] = label
    items = list(unique.items())
    rng = np.random.default_rng(seed)
    rng.shuffle(items)
    if max_rows:
        items = items[:max_rows]
    urls, y = zip(*items)
    x = np.asarray([features(url) for url in urls], dtype=np.float32)
    groups = np.asarray([domain(url) for url in urls])
    y = np.asarray(y)
    trainval, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(
            x, y, groups
        )
    )
    train_index, val_index = next(
        GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1).split(
            x[trainval], y[trainval], groups[trainval]
        )
    )
    train, val = trainval[train_index], trainval[val_index]
    assert not set(groups[train]) & set(groups[test])
    assert not set(groups[train]) & set(groups[val])
    assert not set(groups[val]) & set(groups[test])
    for indices in (train, val, test):
        if len(np.unique(y[indices])) != 2:
            raise ValueError("Every split must contain both classes")
    return x, y, groups, {"train": train, "validation": val, "test": test}
