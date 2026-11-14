"""Real FLEX droplet histories (diameter vs time, 30 fps) and an independent d-squared-law check.

Files: data/raw/droplet_histories/FLEX-###_DropletData.txt (tab-separated, CR line endings) with
DropletTime_sec, DropletDiameter_mm, ... ; index.json maps each file to its FLEX Identifier.
NASA defines K as the slope of a linear fit of d^2 against time (NASA/TP-2015-216046).
Our fit window is fixed in advance: the quasi-steady burn from 20% of NASA's burn time to the end
of the burn (skips the ignition/heat-up transient; stops at visible extinction). Fits with R² below
LOW_R2 are flagged, never refit with another window."""
import json

import numpy as np
import pandas as pd
import streamlit as st

from ignis.data import ROOT, load_flex

DIR = ROOT / "data/raw/droplet_histories"
WINDOW = (0.2, 1.0)   # fractions of NASA's burn time
LOW_R2 = 0.8          # below this fit R², d^2(t) is not a straight line in the window: the K is flagged, never refit


@st.cache_data
def droplet_index():
    """One row per known DropletData file: join status, whether it is on disk, NASA's table values."""
    path = DIR / "index.json"
    if not path.exists():
        return pd.DataFrame()
    idx = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    idx["on_disk"] = idx["file_name"].apply(lambda f: (DIR / f).exists())
    flex = load_flex()[["flex_id", "fuel", "d0_mm", "k_mm2_s", "dext_mm", "burn_time_s", "test_end",
                        "p_atm", "x_o2", "x_co2", "x_he"]].drop_duplicates("flex_id")
    out = idx.merge(flex, on="flex_id", how="left")
    out["joinable"] = out["flex_id"].notna() & out["fuel"].notna()
    return out


@st.cache_data
def load_history(file_name):
    d = pd.read_csv(DIR / file_name, sep="\t", lineterminator="\r").dropna(how="all")
    d = d.rename(columns={"DropletTime_sec": "t_s", "DropletDiameter_mm": "d_mm"})[["t_s", "d_mm"]].dropna()
    d["d2_mm2"] = d["d_mm"] ** 2
    return d


def fit_k(hist, burn_time_s, window=WINDOW):
    """Least-squares line through d^2(t) inside the fixed window -> dict (or None if not fittable)."""
    if not np.isfinite(burn_time_s) or burn_time_s <= 0:
        return None
    t0, t1 = window[0] * burn_time_s, window[1] * burn_time_s
    w = hist[(hist["t_s"] >= t0) & (hist["t_s"] <= t1)]
    if len(w) < 10:
        return None
    slope, intercept = np.polyfit(w["t_s"], w["d2_mm2"], 1)
    pred = slope * w["t_s"] + intercept
    ss_res, ss_tot = ((w["d2_mm2"] - pred) ** 2).sum(), ((w["d2_mm2"] - w["d2_mm2"].mean()) ** 2).sum()
    return {"k_fit": -slope, "intercept": intercept, "r2": 1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
            "n_points": len(w), "t0": t0, "t1": t1}


@st.cache_data
def k_comparison():
    """Fitted vs NASA K for every joinable file on disk."""
    rows = []
    for _, r in droplet_index().iterrows():
        if not (r["on_disk"] and r["joinable"]):
            continue
        fit = fit_k(load_history(r["file_name"]), r["burn_time_s"])
        rows.append({"file_name": r["file_name"], "flex_number": r["flex_number"], "flex_id": r["flex_id"],
                     "fuel": r["fuel"], "test_end": r["test_end"], "d0_mm": r["d0_mm"],
                     "burn_time_s": r["burn_time_s"], "k_nasa": r["k_mm2_s"],
                     "k_fit": fit["k_fit"] if fit else np.nan, "r2": fit["r2"] if fit else np.nan,
                     "n_points": fit["n_points"] if fit else 0})
    out = pd.DataFrame(rows)
    if len(out):
        out["diff_pct"] = 100 * (out["k_fit"] - out["k_nasa"]) / out["k_nasa"]
        out["flag"] = out["r2"].apply(r2_flag)
    return out


# ---------------------------------------------------------------- honest summary of the comparison
def comparable(comp):
    """Droplets with both our refit K and NASA's K: the only ones the gap statistics use."""
    return comp.dropna(subset=["k_fit", "k_nasa"]) if len(comp) else comp


def r2_flag(r2, threshold=LOW_R2):
    """'low R²' when the fit R² is below the threshold, '' otherwise (also '' when there is no fit)."""
    return "low R²" if pd.notna(r2) and r2 < threshold else ""


def worst_gap(comp):
    """Largest |fitted - NASA| % among comparable droplets -> dict (signed diff_pct), or None if none."""
    ok = comparable(comp)
    if ok.empty:
        return None
    r = ok.loc[ok["diff_pct"].abs().idxmax()]
    return {"flex_id": r["flex_id"], "diff_pct": float(r["diff_pct"]), "fuel": r.get("fuel"),
            "test_end": r.get("test_end"), "r2": float(r["r2"])}


def sample_counts(idx):
    """Recordings on disk vs listed in index.json, and whether the on-disk ones are simply the first by FLEX number
    (download_psi.py --droplets N takes index.json in FLEX-number order)."""
    on = idx[idx["on_disk"]] if len(idx) else idx
    n_disk, n_all = len(on), len(idx)
    first = set(idx.nsmallest(n_disk, "flex_number")["file_name"]) if n_disk else set()
    return {"on_disk": n_disk, "total": n_all, "earliest": n_disk > 0 and set(on["file_name"]) == first,
            "first_flex": int(on["flex_number"].min()) if n_disk else None,
            "last_flex": int(on["flex_number"].max()) if n_disk else None}


def sample_line(counts):
    """One line that states the sample, e.g. '30 of 260 recordings, the earliest runs - not a random sample'."""
    if counts["on_disk"] == counts["total"]:
        return f"All {counts['total']} recordings"
    how = "the earliest runs" if counts["earliest"] else "a partial download"
    return f"{counts['on_disk']} of {counts['total']} recordings, {how} - not a random sample"


def d2_summary(comp, idx):
    """Everything the page summary states, computed live: median and worst gap, low-R² flags, sample size."""
    ok = comparable(comp)
    flagged = comp["r2"].apply(r2_flag) != "" if len(comp) else pd.Series(dtype=bool)
    return {"n_joined": len(comp), "n_comparable": len(ok),
            "median_gap_pct": float(ok["diff_pct"].abs().median()) if len(ok) else float("nan"),
            "worst": worst_gap(comp),
            "low_r2": comp.loc[flagged, "flex_id"].tolist() if len(comp) else [],
            "low_r2_comparable": int((ok["r2"].apply(r2_flag) != "").sum()) if len(ok) else 0,
            "sample": sample_counts(idx)}
