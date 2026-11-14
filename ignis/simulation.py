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

from ignis.evidence import FAR, NUM, evidence_lookup

ASSETS = Path(__file__).resolve().parent / "sim_assets"
TEMPLATE = ASSETS / "fire_story.html"
MODEL_JS = ASSETS / "ignis_model.js"
PLACEHOLDER = "/*__IGNIS_PARAMS__*/null"
MODEL_JS_PLACEHOLDER = "/*__IGNIS_MODEL_JS__*/"
MODEL_DATA_PLACEHOLDER = "/*__IGNIS_MODEL_DATA__*/null"


def _linear_model(pipe):
    """A scikit-learn pipeline ColumnTransformer[OneHotEncoder(fuel), StandardScaler(NUM)] -> linear model,
    flattened to plain numbers so ignis_model.js can evaluate it exactly in the browser."""
    pre, est = pipe.steps[0][1], pipe.steps[-1][1]
    ohe, scaler = pre.named_transformers_["fuel"], pre.named_transformers_["num"]
    num_cols = [t[2] for t in pre.transformers_ if t[0] == "num"][0]
    coef = est.coef_[0] if getattr(est.coef_, "ndim", 1) == 2 else est.coef_
    return {"fuel_categories": [str(c) for c in ohe.categories_[0]], "num": list(num_cols),
            "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
            "coef": [float(c) for c in coef], "intercept": float(pd.Series(est.intercept_).iloc[0])}


def web_model_payload(models):
    """Everything ignis_model.js needs: both linear models, the K interval, and per fuel the evidence index
    (scaler, 95th-percentile neighbour distance, tested ranges and every real run in scaled units)."""
    evidence = {}
    for fuel, e in models["evidence"].items():
        runs = e["runs"]
        Z = e["scaler"].transform(runs[NUM])
        evidence[fuel] = {
            "mean": e["scaler"].mean_.tolist(), "scale": e["scaler"].scale_.tolist(),
            "threshold": float(e["threshold"]), "ranges": {c: [float(lo), float(hi)] for c, (lo, hi) in e["ranges"].items()},
            "runs": [{"flex_id": str(r["flex_id"]), "test_end": str(r["test_end"]), "dext_mm": r["dext_mm"],
                      "k_mm2_s": r["k_mm2_s"], "p_atm": r["p_atm"], "x_o2": r["x_o2"], "x_co2": r["x_co2"],
                      "x_he": r["x_he"], "d0_mm": r["d0_mm"], "z": [float(v) for v in z]}
                     for r, z in zip(runs.to_dict("records"), Z)],
        }
    return {"clf": _linear_model(models["clf"]["model"]), "k": _linear_model(models["k"]["model"]),
            "k_half": float(models["k"]["q"]["80%"]), "far": FAR, "tol": 0.02, "evidence": evidence,
            "source": "Models trained on NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451)"}


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


def _js_json(obj):
    payload = json.dumps(_clean(obj), allow_nan=False, ensure_ascii=False)
    return payload.replace("</", "<\\/").replace("<!--", "<\\!--")   # cannot close the <script> tag


def build_html(params: dict, model_data: dict | None = None) -> str:
    """The scene template with `params` (and, if the template asks for it, the browser model) injected."""
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError(f"placeholder {PLACEHOLDER!r} missing from {TEMPLATE}")
    html = html.replace(PLACEHOLDER, _js_json(params), 1)
    if MODEL_DATA_PLACEHOLDER in html:
        if model_data is None:
            raise ValueError("template needs the browser model: pass model_data=web_model_payload(models)")
        html = html.replace(MODEL_DATA_PLACEHOLDER, _js_json(model_data), 1)
    if MODEL_JS_PLACEHOLDER in html:
        js = MODEL_JS.read_text(encoding="utf-8")
        if "</script" in js.lower():
            raise ValueError("ignis_model.js must not contain '</script'")
        html = html.replace(MODEL_JS_PLACEHOLDER, js, 1)
    return html


def render_simulation(params: dict, height: int = 680, models=None):
    """Embed the 3D fire story in the page (an iframe of fixed height)."""
    import streamlit as st
    import streamlit.components.v1 as components
    if models is None:
        from ignis.data import load_models
        models = load_models()
    html = build_html(params, web_model_payload(models))
    if hasattr(components, "html"):          # deprecated in Streamlit 1.5x+, still works in 1.67
        return components.html(html, height=height, scrolling=False)
    return st.iframe(html, height=height)    # replacement API once components.v1.html is removed
