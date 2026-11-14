"""Cached what-if computations for the Predict page: risk map and one-variable sweeps.
Predictions are only returned where NASA tested (status GREEN/AMBER); RED cells are NaN."""
import numpy as np
import pandas as pd
import streamlit as st

from ignis.data import load_models
from ignis.evidence import evidence_status

O2_AXIS = np.round(np.arange(0.10, 0.4001, 0.01), 2)
P_AXIS = np.round(np.arange(0.30, 3.5001, 0.05), 2)
SWEEP_RANGES = {"x_o2": (0.10, 0.40), "p_atm": (0.30, 3.50), "suppressant": (0.0, 0.70)}


def _frame(fuel, p, o2, co2, he, d0, n=None):
    """Model-input table; scalars are broadcast to n rows (or to the length of an array input)."""
    return pd.DataFrame({"fuel": fuel, "p_atm": p, "x_o2": o2, "x_co2": co2, "x_he": he, "d0_mm": d0},
                        index=range(n) if n else None)


@st.cache_data(show_spinner="Computing the risk map...")
def risk_grid(fuel, d0, co2, he):
    """P(extinction) on an O2 x pressure grid; NaN where NASA never tested (RED)."""
    m = load_models()
    O, P = np.meshgrid(O2_AXIS, P_AXIS)
    g = _frame(fuel, P.ravel(), O.ravel(), co2, he, d0)
    status = evidence_status(m["evidence"], fuel, g)
    status[(g["x_o2"] + g["x_co2"] + g["x_he"]).to_numpy() > 1] = 2      # impossible gas mix
    prob = m["clf"]["model"].predict_proba(g[m["clf"]["meta"]["features"]])[:, 1]
    z = np.where(status < 2, prob, np.nan).reshape(P.shape)
    return z, status.reshape(P.shape)


@st.cache_data(show_spinner=False)
def sweep(fuel, d0, p, o2, co2, he, variable, gas=None, n=61):
    """Vary one input, hold the others: returns DataFrame with x, P(ext), K, K_lo, K_hi, status.
    For variable='suppressant', gas ('x_co2' or 'x_he') names the chosen diluent - it must come from the
    user's diluent choice, not from which fraction happens to be > 0 (the slider can be at 0)."""
    m = load_models()
    lo, hi = SWEEP_RANGES[variable]
    xs = np.linspace(lo, hi, n)
    g = _frame(fuel, p, o2, co2, he, d0, n=n)
    if variable == "suppressant":
        if gas not in ("x_co2", "x_he"):
            raise ValueError("suppressant sweep needs gas='x_co2' or 'x_he'")
        g[gas] = xs
    else:
        g[variable] = xs
    status = evidence_status(m["evidence"], fuel, g)
    status[(g["x_o2"] + g["x_co2"] + g["x_he"]).to_numpy() > 1] = 2
    X = g[m["clf"]["meta"]["features"]]
    half = m["k"]["q"]["80%"]
    k = m["k"]["model"].predict(X)
    out = pd.DataFrame({"x": xs, "p_ext": m["clf"]["model"].predict_proba(X)[:, 1], "K": k,
                        "K_lo": k - half, "K_hi": k + half, "status": status})
    out.loc[out["status"] == 2, ["p_ext", "K", "K_lo", "K_hi"]] = np.nan
    return out
