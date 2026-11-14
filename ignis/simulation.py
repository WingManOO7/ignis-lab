"""3D "fire story" for the Simulate page: Earth flame -> orbit -> cabin -> FLEX droplet burn -> cabin spark.

The scene is a self-contained HTML/JS file (ignis/sim_assets/fire_story.html, three.js from a pinned CDN URL)
rendered in Streamlit's components iframe. Python only injects one JSON object, built by `simulation_params`
from the same models and evidence lookup as the Predict page. See ignis/sim_assets/README.md for what is
data-driven and what is illustrative.

Params contract (keys of the dict passed to `render_simulation`; None = unknown / not applicable):
    scenario            str    label shown in the HUD (preset label or "Custom")
    fuel                str    "Heptane" | "Methanol"
    p_atm               float  pressure, atm
    x_o2, x_co2, x_he   float  mole fractions
    diluent             str    "none (N2 only)" | "CO2" | "He"
    diluent_frac        float  mole fraction of the added suppressant (0 for none)
    d0_mm               float  initial droplet diameter, mm
    k_mm2_s             float  burning-rate constant K from the ridge model (mm^2/s)
    k_half_mm2_s        float  half-width of the 80% split-conformal interval for K
    p_ext               float  P(visible flame goes out before burnout) from the calibrated classifier
    light               str    "GREEN" | "AMBER" | "RED"  (ignis.evidence.evidence_lookup)
    light_text          str    full traffic-light sentence
    reasons             list   reasons for AMBER / RED
    validated           bool   light is not RED; if False the scene does not play a data-driven burn
    d_ext_mm            float  median extinction diameter of the nearest runs that ended in Extinction
    n_ext_runs          int    how many nearest runs that median uses
    cool_flame_possible bool   fuel is Heptane and p_ext >= 0.5
    nearest_ids         list   flex_id of the 5 nearest NASA runs
    nearest_outcomes    list   their test_end values (same order)
    start_scene         int    optional, 1-5: scene to open on (default: 1, or the last scene viewed)
"""
import json
import math
from pathlib import Path

import pandas as pd

from ignis.evidence import evidence_lookup

ASSETS = Path(__file__).resolve().parent / "sim_assets"
TEMPLATE = ASSETS / "fire_story.html"
PLACEHOLDER = "/*__IGNIS_PARAMS__*/null"


def _diluent(q):
    if q.get("x_co2", 0) > 0:
        return "CO2", float(q["x_co2"])
    if q.get("x_he", 0) > 0:
        return "He", float(q["x_he"])
    return "none (N2 only)", 0.0


def simulation_params(models, q, scenario="Custom"):
    """Return (params, nearest_runs_table) for one query dict with keys
    fuel, p_atm, x_o2, x_co2, x_he, d0_mm (same dict as views/predict.py builds)."""
    meta = models["clf"]["meta"]
    X = pd.DataFrame([q])[meta["features"]]
    p_ext = float(models["clf"]["model"].predict_proba(X)[0, 1])
    k_hat = float(models["k"]["model"].predict(X)[0])
    half = float(models["k"]["q"]["80%"])
    light_text, reasons, nearest = evidence_lookup(models["evidence"], q)
    light = light_text.split(" ", 1)[0]          # "GREEN" / "AMBER" / "RED"
    ext = nearest.loc[(nearest["test_end"] == "Extinction") & (nearest["dext_mm"] > 0), "dext_mm"]
    diluent, frac = _diluent(q)
    params = {
        "scenario": scenario, "fuel": q["fuel"],
        "p_atm": float(q["p_atm"]), "x_o2": float(q["x_o2"]),
        "x_co2": float(q.get("x_co2", 0.0)), "x_he": float(q.get("x_he", 0.0)),
        "diluent": diluent, "diluent_frac": frac, "d0_mm": float(q["d0_mm"]),
        "k_mm2_s": k_hat, "k_half_mm2_s": half, "p_ext": p_ext,
        "light": light, "light_text": light_text, "reasons": list(reasons),
        "validated": light != "RED",
        "d_ext_mm": float(ext.median()) if len(ext) else None, "n_ext_runs": int(len(ext)),
        "cool_flame_possible": q["fuel"] == "Heptane" and p_ext >= 0.5,
        "nearest_ids": [str(v) for v in nearest["flex_id"].head(5)],
        "nearest_outcomes": [str(v) for v in nearest["test_end"].head(5)],
    }
    return params, nearest


def _clean(v):
    """Make params JSON-safe: numpy scalars -> Python, NaN/inf -> None."""
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def build_html(params: dict) -> str:
    """The scene template with `params` injected as a JS object literal."""
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError(f"placeholder {PLACEHOLDER!r} missing from {TEMPLATE}")
    payload = json.dumps(_clean(params), allow_nan=False, ensure_ascii=False)
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")   # cannot close the <script> tag
    return html.replace(PLACEHOLDER, payload, 1)


def render_simulation(params: dict, height: int = 680):
    """Embed the 3D fire story in the page (an iframe of fixed height)."""
    import streamlit as st
    import streamlit.components.v1 as components
    html = build_html(params)
    if hasattr(components, "html"):          # deprecated in Streamlit 1.5x+, still works in 1.67
        return components.html(html, height=height, scrolling=False)
    return st.iframe(html, height=height)    # replacement API once components.v1.html is removed
