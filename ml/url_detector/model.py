from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier


def candidates(seed=42):
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000, class_weight="balanced", random_state=seed
            ),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150,
            max_depth=20,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=2,
            random_state=seed,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=200, max_leaf_nodes=31, early_stopping=True, random_state=seed
        ),
    }
