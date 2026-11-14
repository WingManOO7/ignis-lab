"""Query helpers used by the Predict page: nearest real NASA FLEX runs + an out-of-range light."""
import numpy as np
import pandas as pd

NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69"
FAR = 2.0   # nearest run more than FAR x the usual neighbour distance = no comparable NASA test


def evidence_lookup(index, query, k=5, tol=0.02):
    """Return (traffic_light, reasons, nearest_runs_table) for one query dict.
    RED   = outside a tested range, or far from every real run (model not validated there)
    AMBER = inside the ranges but no close NASA run (treat numbers with caution)
    GREEN = close to real NASA runs.
    tol = 2% of each range, so values that differ only by rounding are not flagged."""
    entry = index[query["fuel"]]
    x = pd.DataFrame([{c: query[c] for c in NUM}])
    reasons = [f"{c} = {query[c]:.3g} is outside the tested range {lo:.3g}-{hi:.3g}"
               for c, (lo, hi) in entry["ranges"].items()
               if not lo - tol * (hi - lo) <= query[c] <= hi + tol * (hi - lo)]
    dist, idx = entry["nn"].kneighbors(entry["scaler"].transform(x), n_neighbors=k)
    nearest = entry["runs"].iloc[idx[0]].copy()
    nearest.insert(0, "distance", np.round(dist[0], 2))
    d0, thr = float(dist[0][0]), entry["threshold"]
    if reasons:
        light = "RED - outside NASA's tested conditions: the model was never validated here"
    elif d0 > FAR * thr:
        light = "RED - no comparable NASA run: this combination of conditions was never tested"
        reasons.append(f"nearest run is {d0:.2f} scaled units away; 95% of real runs have a neighbour "
                       f"within {thr:.2f} (each value is inside a tested range, but not together)")
    elif d0 > thr:
        light = "AMBER - inside the tested ranges, but no close NASA run"
        reasons.append(f"nearest run is {d0:.2f} scaled units away "
                       f"(95% of real runs have a neighbour within {thr:.2f})")
    else:
        light = "GREEN - close to real NASA runs"
    return light, reasons, nearest


def evidence_status(index, fuel, queries, tol=0.02):
    """Vectorised traffic light for many queries (DataFrame with the NUM columns):
    0 = GREEN, 1 = AMBER, 2 = RED, using exactly the same rules as evidence_lookup."""
    entry = index[fuel]
    X = queries[NUM]
    outside = np.zeros(len(X), dtype=bool)
    for c, (lo, hi) in entry["ranges"].items():
        pad = tol * (hi - lo)
        outside |= ~((X[c] >= lo - pad) & (X[c] <= hi + pad)).to_numpy()
    dist, _ = entry["nn"].kneighbors(entry["scaler"].transform(X), n_neighbors=1)
    d, thr = dist[:, 0], entry["threshold"]
    return np.where(outside | (d > FAR * thr), 2, np.where(d > thr, 1, 0))


def outcome_summary(nearest):
    """What NASA actually observed at the nearest runs, e.g. {'Disruption': 3, 'Extinction': 2}."""
    return nearest["test_end"].value_counts().to_dict()
