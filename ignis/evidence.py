"""STARTER CODE - query helpers used by the Streamlit app (adapt during the event)."""
import numpy as np
import pandas as pd

NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69"


def evidence_lookup(index, query, k=5, tol=0.02):
    """Return (traffic_light, reasons, nearest_runs_table) for one query dict.
    tol = 2% of each range, so values that differ only by rounding are not flagged."""
    entry = index[query["fuel"]]
    x = pd.DataFrame([{c: query[c] for c in NUM}])
    reasons = [f"{c} = {query[c]:.3g} is outside the tested range {lo:.3g}-{hi:.3g}"
               for c, (lo, hi) in entry["ranges"].items()
               if not lo - tol * (hi - lo) <= query[c] <= hi + tol * (hi - lo)]
    dist, idx = entry["nn"].kneighbors(entry["scaler"].transform(x), n_neighbors=k)
    nearest = entry["runs"].iloc[idx[0]].copy()
    nearest.insert(0, "distance", np.round(dist[0], 2))
    if reasons:
        light = "RED - extrapolation: the model was never validated here"
    elif dist[0][0] > entry["threshold"]:
        light = "AMBER - inside the ranges, but no similar NASA run exists"
        reasons.append(f"nearest run is {dist[0][0]:.2f} scaled units away "
                       f"(95% of real runs have a neighbour within {entry['threshold']:.2f})")
    else:
        light = "GREEN - close to real NASA runs"
    return light, reasons, nearest
