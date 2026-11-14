"""3D "fire story" for the Simulate page: Earth flame -> orbit -> cabin -> FLEX droplet burn -> cabin spark.

The scene is a self-contained HTML/JS file (ignis/sim_assets/fire_story.html) rendered in Streamlit's components
iframe. Python only injects JSON objects, built by `simulation_params` from the same models and evidence lookup as
the Predict page. See ignis/sim_assets/README.md for what is data-driven and what is illustrative.

three.js 0.160.0 (MIT, licence in static/vendor/three-0.160.0/LICENSE) is vendored under static/ and served by
Streamlit static file serving (server.enableStaticServing in .streamlit/config.toml) at <app>/app/static/..., so the
lab works with no internet. The page checks the local copy before any module loads and otherwise uses the same
pinned files from jsDelivr, verified with the SRI hashes in THREE_FILES (import-map "integrity").

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
import os
import threading
from pathlib import Path

import pandas as pd

from ignis.evidence import FAR, NUM, evidence_lookup

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "ignis" / "sim_assets"
TEMPLATE = ASSETS / "fire_story.html"
MODEL_JS = ASSETS / "ignis_model.js"
PLACEHOLDER = "/*__IGNIS_PARAMS__*/null"
MODEL_JS_PLACEHOLDER = "/*__IGNIS_MODEL_JS__*/"
CAT_JS = ASSETS / "astro_cat.js"                 # Nova, the astronaut-cat mascot (decoration only)
CAT_JS_PLACEHOLDER = "/*__IGNIS_CAT_JS__*/"
MODEL_DATA_PLACEHOLDER = "/*__IGNIS_MODEL_DATA__*/null"
THREE_PLACEHOLDER = "/*__IGNIS_THREE__*/null"

# three.js, pinned. Files the scene imports (three + the examples/jsm modules and their relative imports), with the
# SHA-384 of the official jsDelivr copy (= the vendored bytes). Same list for the local copy and the CDN fallback.
THREE_VERSION = "0.160.0"
THREE_DIR = ROOT / "static" / "vendor" / f"three-{THREE_VERSION}"
THREE_LOCAL_URL = f"app/static/vendor/three-{THREE_VERSION}/"      # relative to the Streamlit app's base URL
THREE_CDN_URL = f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/"
THREE_FILES = {
    "build/three.module.js": "sha384-61S/Nu32S3E5+n+KpCOTb2eRYps6fVKm+9Gz1QBvSePFthb46f063Aa/qe/lykFZ",
    "examples/jsm/controls/OrbitControls.js": "sha384-qlO/ZugKPxAQUAvTlQoo0QECzxJIJySZmCF/DHdb2Xn/hHndFwX/vfUAC9Hbk6LP",
    "examples/jsm/postprocessing/EffectComposer.js": "sha384-L+Ns9skCAqjab7aG8LH5VLknBCoENW7p37sOj39jnITwlWZFabWc29JwzgYf6ygy",
    "examples/jsm/postprocessing/MaskPass.js": "sha384-SDM80tiGflO8UDV/QzR/mASjcc/+wF7KfRVFNHJUIPcTctwoPI8GoWVTlccZw7V4",
    "examples/jsm/postprocessing/OutputPass.js": "sha384-RJJc+pg+Ue2ZwXlf8n78cPHMiHrqfr+AxxabF5vkXMXjNPF6nSUoqb20IQXkMo6c",
    "examples/jsm/postprocessing/Pass.js": "sha384-gSqIFh8vMmp1veyOysIS3KPVUl/A5JPefYvW4b89OeYeW0bwkrjN7qcC1h0XJK/K",
    "examples/jsm/postprocessing/RenderPass.js": "sha384-LwKrkOBAkmQ2KT4cv6P6q9Rb9L01GIFU34Zp16tGWZoBnrVuujfjpYZb7OxEMb0J",
    "examples/jsm/postprocessing/ShaderPass.js": "sha384-zetU6HhR/vTtgSvnS9DE+GQPZhVT/ZOSLa/1+DSM6rkM9hvBgQWr9bCEosZt93ch",
    "examples/jsm/postprocessing/UnrealBloomPass.js": "sha384-R734/7SvtqjjeteDKG4qcQA0adDCZ1ZcKfYUZsbVr9qqHGlgSXH9eNN4b3NIgwuc",
    "examples/jsm/shaders/CopyShader.js": "sha384-kzVlcj2amFaRNIWZ5zE0PmIN+QTNWWvrgKk31S8N/7w0nf7Qq3xqxHRLbD2UPPSl",
    "examples/jsm/shaders/LuminosityHighPassShader.js": "sha384-621kiA/kIdX8rtH6VU6+SwMVx+B8g7MQ6x0fei5dZVX3CQZSLkpOlglIk9sxE+/g",
    "examples/jsm/shaders/OutputShader.js": "sha384-fT4woAJJtXcAxElHG1cGfIZkiSxaj7u+24LHlfNVDZZ9aSjZvr2emMGPmcD9eF0V",
}


def _static_serving_enabled():
    try:
        import streamlit as st
        return bool(st.get_option("server.enableStaticServing"))
    except Exception:            # no Streamlit config available: let the browser try the local copy anyway
        return True


def three_config(static_serving: bool | None = None, local_url: str = THREE_LOCAL_URL) -> dict:
    """How the page loads three.js: the vendored copy if it is complete and Streamlit serves static/, then the CDN.
    The integrity hashes are used for the CDN URLs only (a local checkout may have rewritten line endings).
    `page` is the standalone full-screen page (FIRE_LAB_URL), relative to the Streamlit app."""
    if static_serving is None:
        static_serving = _static_serving_enabled()
    local_ok = static_serving and all((THREE_DIR / f).is_file() for f in THREE_FILES)
    return {"version": THREE_VERSION, "local": local_url if local_ok else None, "cdn": THREE_CDN_URL,
            "files": list(THREE_FILES), "integrity": dict(THREE_FILES), "page": FIRE_LAB_URL}


# The same fire lab as a standalone page (full screen in a new tab), served by Streamlit static serving next to the
# vendored three.js. Rebuilt by ensure_fire_lab_page() whenever the template, ignis_model.js or the models change.
FIRE_LAB_PAGE = ROOT / "static" / "fire_lab.html"
FIRE_LAB_URL = "app/static/fire_lab.html"          # relative to the Streamlit app's base URL
_PAGE_LOCK = threading.Lock()
_PAGE_STAMP = {}


def scenario_presets():
    """The habitat presets the fire lab offers (label, O2, pressure), from ignis.scenarios."""
    from ignis.scenarios import SCENARIOS
    return [{"label": lab, "x_o2": o2, "p_atm": p} for lab, o2, p, _ in SCENARIOS.values()]


def default_query():
    """The fire lab's starting droplet: n-heptane, 3 mm, ISS cabin air."""
    from ignis.scenarios import SCENARIOS
    label, o2, p, _ = SCENARIOS["iss"]
    return {"fuel": "Heptane", "p_atm": p, "x_o2": o2, "x_co2": 0.0, "x_he": 0.0, "d0_mm": 3.0}, label


def fire_lab_page_html(models) -> str:
    """Standalone HTML: default params + browser model + three.js from ./vendor (relative to the page), CDN fallback.
    The page reads its state from the URL (place, fuel, o2, p, d0, co2, he, fan, gravity, speed)."""
    q, label = default_query()
    params, _ = simulation_params(models, q, scenario=label)
    params["scenarios"] = scenario_presets()
    three = three_config(static_serving=True, local_url=f"vendor/three-{THREE_VERSION}/")
    return build_html(params, web_model_payload(models), three=three)


def _page_stamp():
    files = [TEMPLATE, MODEL_JS, CAT_JS, Path(__file__), ROOT / "ignis" / "evidence.py", ROOT / "ignis" / "scenarios.py",
             *sorted((ROOT / "models").glob("*.joblib"))]
    return tuple((str(f), f.stat().st_mtime_ns) for f in files if f.exists())


def ensure_fire_lab_page(models=None, path: Path = FIRE_LAB_PAGE) -> bool:
    """(Re)write static/fire_lab.html if it is missing or out of date. Returns True if it was written.
    Cheap when nothing changed (a few stat calls); never raises."""
    try:
        stamp = _page_stamp()
        with _PAGE_LOCK:
            if _PAGE_STAMP.get(str(path)) == stamp and path.is_file():
                return False
            if models is None:
                from ignis.data import load_models
                models = load_models()
            html = fire_lab_page_html(models)
            if path.is_file() and path.read_text(encoding="utf-8") == html:
                _PAGE_STAMP[str(path)] = stamp
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(html, encoding="utf-8", newline="\n")
            os.replace(tmp, path)
            _PAGE_STAMP[str(path)] = stamp
            return True
    except Exception as e:                # read-only file system etc.: the in-page full screen still works
        print(f"IGNIS: could not write {path}: {type(e).__name__}: {e}")
        return False


def fire_lab_url(q: dict, place: str = "chamber") -> str:
    """Link to the standalone page with this droplet as the starting state."""
    from urllib.parse import urlencode
    args = {"place": place, "fuel": q.get("fuel", "Heptane"), "o2": f"{float(q.get('x_o2', 0.21)):.3f}",
            "p": f"{float(q.get('p_atm', 1.0)):.3f}", "d0": f"{float(q.get('d0_mm', 3.0)):.2f}"}
    for k, key in (("co2", "x_co2"), ("he", "x_he")):
        if float(q.get(key) or 0) > 0:
            args[k] = f"{float(q[key]):.3f}"
    return FIRE_LAB_URL + "?" + urlencode(args)


def _linear_model(pipe):
    """A scikit-learn pipeline ColumnTransformer[OneHotEncoder(fuel), StandardScaler(NUM)] -> linear model,
    flattened to plain numbers so ignis_model.js can evaluate it exactly in the browser."""
    pre, est = pipe.steps[-2][1], pipe.steps[-1][1]   # [FunctionTransformer(fuel slopes)], ColumnTransformer, model
    first = pipe.steps[0][1]
    if first is not pre and getattr(first, "func", None).__name__ != "add_fuel_interactions":
        raise ValueError("unknown feature step - ignis_model.js only mirrors add_fuel_interactions")
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


def build_html(params: dict, model_data: dict | None = None, three: dict | None = None) -> str:
    """The scene template with `params` (and, if the template asks for it, the browser model and the three.js
    loader config, default `three_config()`) injected."""
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError(f"placeholder {PLACEHOLDER!r} missing from {TEMPLATE}")
    html = html.replace(PLACEHOLDER, _js_json(params), 1)
    if THREE_PLACEHOLDER in html:
        html = html.replace(THREE_PLACEHOLDER, _js_json(three if three is not None else three_config()), 1)
    if MODEL_DATA_PLACEHOLDER in html:
        if model_data is None:
            raise ValueError("template needs the browser model: pass model_data=web_model_payload(models)")
        html = html.replace(MODEL_DATA_PLACEHOLDER, _js_json(model_data), 1)
    if MODEL_JS_PLACEHOLDER in html:
        js = MODEL_JS.read_text(encoding="utf-8")
        if "</script" in js.lower():
            raise ValueError("ignis_model.js must not contain '</script'")
        html = html.replace(MODEL_JS_PLACEHOLDER, js, 1)
    if CAT_JS_PLACEHOLDER in html:
        cat = CAT_JS.read_text(encoding="utf-8") if CAT_JS.exists() else ""   # missing mascot = no mascot, never an error
        if "</script" in cat.lower() or "<!--" in cat:
            raise ValueError("astro_cat.js must not contain '</script' or '<!--'")
        html = html.replace(CAT_JS_PLACEHOLDER, cat, 1)
    return html


def render_simulation(params: dict, height: int = 680, models=None):
    """Embed the 3D fire story in the page (an iframe of fixed height)."""
    import streamlit as st
    try:
        import streamlit.components.v1 as components
    except Exception:                        # module removed in a future Streamlit: use st.iframe below
        components = None
    if models is None:
        from ignis.data import load_models
        models = load_models()
    html = build_html(params, web_model_payload(models))
    if components is not None and hasattr(components, "html"):   # deprecated in Streamlit 1.5x+, works in 1.67
        return components.html(html, height=height, scrolling=False)
    return st.iframe(html, height=height)    # replacement API once components.v1.html is removed
