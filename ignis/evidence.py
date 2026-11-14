"""Query helpers used by the Predict page: nearest real NASA FLEX runs + an out-of-range light."""
import numpy as np
import pandas as pd

NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69"
FAR = 2.0   # nearest run more than FAR x the usual neighbour distance = no comparable NASA test
# The extinction model never learned 'Disruption' (excluded as a label: possible needle contamination), so a query
# whose nearest real runs mostly disrupted is a blind spot, not a confident GREEN.
DISRUPT_AMBER, K_NEAR = 3, 5          # >= 3 of the 5 nearest runs Disruption -> at most AMBER; all 5 -> RED
RED_DISRUPT = "RED - every nearby NASA run ended in Disruption, an outcome the model was never trained on"
AMBER_DISRUPT = "AMBER - most nearby NASA runs ended in Disruption, which the model was not trained on"


def _disruption_reason(n, k):
    return (f"{n} of {k} nearest NASA runs ended in Disruption (the droplet broke apart), an outcome the model was "
            "not trained on")


def evidence_lookup(index, query, k=K_NEAR, tol=0.02):
    """Return (traffic_light, reasons, nearest_runs_table) for one query dict.
    RED   = outside a tested range, far from every real run, or every nearby run ended in Disruption
    AMBER = inside the ranges but no close NASA run, or most nearby runs ended in Disruption
    GREEN = close to real NASA runs whose outcomes the model was trained on.
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
    n_dis = int((nearest["test_end"] == "Disruption").sum())
    if n_dis >= DISRUPT_AMBER:
        reasons.append(_disruption_reason(n_dis, len(nearest)))
        if not light.startswith("RED"):
            if n_dis == len(nearest):
                light = RED_DISRUPT
            elif light.startswith("GREEN"):
                light = AMBER_DISRUPT
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
    dist, idx = entry["nn"].kneighbors(entry["scaler"].transform(X), n_neighbors=K_NEAR)
    d, thr = dist[:, 0], entry["threshold"]
    base = np.where(outside | (d > FAR * thr), 2, np.where(d > thr, 1, 0))
    n_dis = (entry["runs"]["test_end"].to_numpy()[idx] == "Disruption").sum(axis=1)
    return np.where(base == 2, 2, np.where(n_dis == K_NEAR, 2,
                                           np.where((n_dis >= DISRUPT_AMBER) & (base == 0), 1, base)))


def outcome_summary(nearest):
    """What NASA actually observed at the nearest runs, e.g. {'Disruption': 3, 'Extinction': 2}."""
    return nearest["test_end"].value_counts().to_dict()
