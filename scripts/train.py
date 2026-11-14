"""
STARTER CODE - a learning reference. Rewrite/adapt it yourselves during the event.

Grouped cross-validation on the cleaned FLEX table, always against baselines:
  Task A  classification: will the visible flame go out before burnout?
          (Test end = Extinction -> 1, Completion -> 0; Disruption rows excluded)
  Task B  regression: burning-rate constant K (mm^2/s)
Only PRE-IGNITION inputs are used. K, burn time and extinction diameter are never inputs.

Run from the repository root:   python scripts/train.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (balanced_accuracy_score, brier_score_loss, confusion_matrix, f1_score,
                             mean_absolute_error, r2_score, recall_score, roc_auc_score,
                             root_mean_squared_error)
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

DATA = Path("data/processed/flex_clean.csv")
MODELS, REPORTS = Path("models"), Path("reports")
NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]   # x_n2 dropped: fractions sum to ~1
CAT = ["fuel"]
FEATURES = CAT + NUM
SEED = 0
K_MODEL = "Ridge"   # set to whichever regressor wins YOUR grouped CV (Ridge did in our smoke test)


def preprocessor():
    return ColumnTransformer([("fuel", OneHotEncoder(handle_unknown="ignore"), CAT),
                              ("num", StandardScaler(), NUM)])


def classifiers():
    return {
        "Dummy (always majority)": DummyClassifier(strategy="most_frequent"),
        "One-split rule (depth-1 tree)": make_pipeline(
            preprocessor(), DecisionTreeClassifier(max_depth=1, class_weight="balanced", random_state=SEED)),
        "Logistic regression": make_pipeline(
            preprocessor(), LogisticRegression(class_weight="balanced", max_iter=2000)),
        "Random forest": make_pipeline(preprocessor(), RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=SEED)),
    }


def regressors():
    return {
        "Dummy (global mean)": DummyRegressor(strategy="mean"),
        "Ridge": make_pipeline(preprocessor(), Ridge(alpha=1.0)),
        "kNN (k=5)": make_pipeline(preprocessor(), KNeighborsRegressor(n_neighbors=5)),
        "Random forest": make_pipeline(preprocessor(), RandomForestRegressor(
            n_estimators=300, min_samples_leaf=3, random_state=SEED)),
    }


def task_a(df, n_repeats=5):
    d = df[df["y_extinction"].notna() & df[NUM].notna().all(axis=1) & ~df["dup_id"]].reset_index(drop=True)
    X, y, g = d[FEATURES], d["y_extinction"].astype(int), d["condition_id"]
    rows, oof = [], {}
    for name, model in classifiers().items():
        # Only 27 Completion runs: one random fold assignment can swing the score a lot,
        # so repeat grouped CV with several shuffles and report the whole spread.
        for rep in range(n_repeats):
            cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=rep)
            pred, prob = np.zeros(len(d), dtype=int), np.zeros(len(d))
            for fold, (tr, te) in enumerate(cv.split(X, y, g)):
                model.fit(X.iloc[tr], y.iloc[tr])
                pred[te], prob[te] = model.predict(X.iloc[te]), model.predict_proba(X.iloc[te])[:, 1]
                yt = y.iloc[te]
                rows.append({"task": "A extinction", "model": name, "repeat": rep, "fold": fold,
                             "n_test": len(te),
                             "balanced_acc": balanced_accuracy_score(yt, pred[te]),
                             "recall_completion": recall_score(yt, pred[te], pos_label=0, zero_division=0),
                             "f1_macro": f1_score(yt, pred[te], average="macro", zero_division=0),
                             "roc_auc": roc_auc_score(yt, prob[te]) if yt.nunique() == 2 else np.nan,
                             "brier": brier_score_loss(yt, prob[te])})
            if rep == 0:   # pooled out-of-fold confusion matrix, for display only
                oof[name] = confusion_matrix(y, pred, labels=[0, 1]).tolist()
    print(f"Task A rows={len(d)}  extinction={int(y.sum())}  completion={int((y == 0).sum())}  "
          f"groups={g.nunique()}")
    return d, pd.DataFrame(rows), oof


def task_b(df, exclude_disruption=False):
    mask = df["k_target"].notna() & df[NUM].notna().all(axis=1) & ~df["dup_id"]
    if exclude_disruption:
        mask &= df["test_end"] != "Disruption"
    d = df[mask].reset_index(drop=True)
    X, y, g = d[FEATURES], d["k_target"], d["condition_id"]
    rows = []
    models = regressors()
    models["Per-fuel mean (physics-style baseline)"] = None
    for name, model in models.items():
        for fold, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, y, g)):
            if model is None:   # predict the mean K of the same fuel in the training fold
                means = y.iloc[tr].groupby(X["fuel"].iloc[tr]).mean()
                p = X["fuel"].iloc[te].map(means).fillna(y.iloc[tr].mean()).to_numpy()
            else:
                model.fit(X.iloc[tr], y.iloc[tr])
                p = model.predict(X.iloc[te])
            yt = y.iloc[te]
            rows.append({"task": "B burning-rate K", "model": name, "fold": fold, "n_test": len(te),
                         "MAE": mean_absolute_error(yt, p), "RMSE": root_mean_squared_error(yt, p),
                         "R2": r2_score(yt, p)})
    print(f"Task B rows={len(d)}  groups={g.nunique()}  K range={y.min():.2f}-{y.max():.2f} mm^2/s")
    return d, pd.DataFrame(rows)


def training_ranges(d):
    return {fuel: {c: [float(sub[c].min()), float(sub[c].max())] for c in NUM}
            for fuel, sub in d.groupby("fuel")}


if __name__ == "__main__":
    MODELS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    df = pd.read_csv(DATA)
    da, res_a, conf = task_a(df)
    db, res_b = task_b(df)
    results = pd.concat([res_a, res_b], ignore_index=True)
    results.to_csv(REPORTS / "cv_folds.csv", index=False)
    (REPORTS / "confusion_oof.json").write_text(json.dumps(conf, indent=1))
    metric_cols = ["balanced_acc", "recall_completion", "roc_auc", "brier", "MAE", "R2"]
    summary = results.groupby(["task", "model"])[metric_cols].agg(["mean", "min", "max"]).round(3)
    print(summary.dropna(axis=1, how="all").to_string())

    # Final models on ALL usable rows (the CV above is what we report, not training scores).
    clf = classifiers()["Logistic regression"].fit(da[FEATURES], da["y_extinction"].astype(int))
    reg = regressors()[K_MODEL].fit(db[FEATURES], db["k_target"])
    meta = {"features": FEATURES, "sklearn_version": sklearn.__version__,
            "source": "NASA PSI-69 FLEX experimental table (DOI 10.60555/mbq8-0451)",
            "n_rows_clf": len(da), "n_rows_k": len(db), "ranges": training_ranges(db)}
    joblib.dump({"model": clf, "meta": meta}, MODELS / "extinction_clf.joblib")
    joblib.dump({"model": reg, "meta": meta}, MODELS / "k_reg.joblib")
    print("saved models/extinction_clf.joblib and models/k_reg.joblib")
