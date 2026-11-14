"""
STARTER CODE - a learning reference. Rewrite/adapt it yourselves during the event.

1) Split-conformal prediction intervals for K, calibrated on WHOLE held-out condition
   groups (replicates are not exchangeable with other rows), with measured coverage.
2) An "evidence index": for any query, the nearest REAL NASA FLEX runs + an
   out-of-distribution traffic light (range check + nearest-neighbour distance).

Run after clean_flex.py and train.py:   python scripts/calibrate_and_evidence.py
"""
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from train import FEATURES, K_MODEL, NUM, SEED, regressors   # same features and model as train.py

DATA = Path("data/processed/flex_clean.csv")
MODELS = Path("models")
ALPHAS = {"80%": 0.20, "90%": 0.10}


def make_model():
    return regressors()[K_MODEL]


def conformal_q(residuals, alpha):
    """Split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest absolute residual."""
    r = np.sort(np.abs(residuals))
    k = math.ceil((len(r) + 1) * (1 - alpha))
    return float(r[min(k, len(r)) - 1])


def fit_with_calibration(X, y, groups, seed=SEED):
    """Fit on ~75% of condition groups, calibrate the interval on the other ~25%."""
    fit_idx, cal_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
                            .split(X, y, groups))
    model = make_model().fit(X.iloc[fit_idx], y.iloc[fit_idx])
    resid = y.iloc[cal_idx].to_numpy() - model.predict(X.iloc[cal_idx])
    return model, {lvl: conformal_q(resid, a) for lvl, a in ALPHAS.items()}, len(cal_idx)


def coverage_check(X, y, groups):
    """Does the '80%' interval really contain ~80% of runs from conditions never seen?"""
    out = []
    for fold, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, y, groups)):
        model, q, _ = fit_with_calibration(X.iloc[tr].reset_index(drop=True),
                                           y.iloc[tr].reset_index(drop=True),
                                           groups.iloc[tr].reset_index(drop=True), seed=fold)
        err = np.abs(y.iloc[te].to_numpy() - model.predict(X.iloc[te]))
        for lvl, qv in q.items():
            out.append({"fold": fold, "level": lvl, "half_width": qv, "coverage": float(np.mean(err <= qv))})
    return pd.DataFrame(out)


def build_evidence_index(df):
    """Per fuel: scaler + nearest-neighbour index over ALL real runs with complete inputs (evidence shown
    to users, Disruption included), while the tested RANGES come from the rows the extinction classifier
    was trained on (Disruption excluded) - so GREEN never covers inputs the classifier never saw."""
    trained = df[df["y_extinction"].notna() & ~df["dup_id"] & df[NUM].notna().all(axis=1)]
    index = {}
    for fuel, sub in df[df[NUM].notna().all(axis=1)].groupby("fuel"):
        sub = sub.reset_index(drop=True)
        dom = trained[trained["fuel"] == fuel]
        scaler = StandardScaler().fit(sub[NUM])
        Z = scaler.transform(sub[NUM])
        nn = NearestNeighbors(n_neighbors=6).fit(Z)
        dist, _ = nn.kneighbors(Z)                       # dist[:, 0] is the point itself
        index[fuel] = {
            "scaler": scaler, "nn": nn,
            "threshold": float(np.percentile(dist[:, 1], 95)),
            "ranges": {c: (float(dom[c].min()), float(dom[c].max())) for c in NUM},
            "runs": sub[["flex_id", "test_date", "fuel", "p_atm", "x_o2", "x_co2", "x_he", "d0_mm",
                         "k_mm2_s", "dext_mm", "burn_time_s", "test_end", "dup_id"]],
        }
    return index


if __name__ == "__main__":
    df = pd.read_csv(DATA)
    d = df[df["k_target"].notna() & df[NUM].notna().all(axis=1) & ~df["dup_id"]].reset_index(drop=True)
    X, y, g = d[FEATURES], d["k_target"], d["condition_id"]

    cov = coverage_check(X, y, g)
    print(cov.groupby("level")[["half_width", "coverage"]].agg(["mean", "min", "max"]).round(3))

    model, q, n_cal = fit_with_calibration(X, y, g)
    joblib.dump({"model": model, "q": q, "n_cal": n_cal,
                 "coverage_check": cov.to_dict("records")}, MODELS / "k_interval.joblib")
    joblib.dump(build_evidence_index(df), MODELS / "evidence_index.joblib")
    print(f"saved interval model (calibrated on {n_cal} runs) and evidence index")
