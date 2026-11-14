"""Unit tests for the logic behind the pages.  Run:  python -m pytest -q"""
import math

import numpy as np
import pandas as pd
import pytest

from ignis.data import load_models
from ignis.evidence import evidence_lookup, evidence_status
from ignis.rag import number_supported, split_sentences, verify
from ignis.scenarios import SCENARIOS, coverage, near_mask, scenario_key_for

ISS_HEPTANE = {"fuel": "Heptane", "p_atm": 1.0, "x_o2": 0.21, "x_co2": 0.0, "x_he": 0.0, "d0_mm": 3.0}


@pytest.fixture(scope="module")
def models():
    return load_models()


# ---------------------------------------------------------------- scenarios
def test_scenarios_are_physical():
    assert set(SCENARIOS) == {"iss", "lunar", "exploration"}
    for label, o2, p, src in SCENARIOS.values():
        assert 0 < o2 < 1 and 0 < p < 2 and label and src
    assert scenario_key_for(0.34, 0.56) == "exploration" and scenario_key_for(0.25, 0.8) is None


def test_near_mask_and_coverage():
    o2, p = pd.Series([0.21, 0.35, 0.30]), pd.Series([1.0, 0.55, 0.70])
    assert near_mask(o2, p, 0.34, 0.56).tolist() == [False, True, False]
    counted = {"test_points": [[0.21, 1.0], [0.30, 0.70]], "tested_o2_max": 0.4, "tested_p_min_atm": 0.5}
    assert coverage(counted, 0.34, 0.56, "exploration")[0] == "no"          # real test points beat ranges
    assert coverage(counted, 0.30, 0.69)[0] == "yes"
    ranges = {"tests_near": None, "tested_o2_max": 0.4, "tested_p_min_atm": 0.5, "tested_p_max_atm": 3.0}
    assert coverage(ranges, 0.34, 0.56)[0] == "likely"
    unknown = {"tests_near": None, "tested_o2_max": np.nan, "tested_p_min_atm": np.nan, "tested_p_max_atm": np.nan}
    assert coverage(unknown, 0.34, 0.56)[0] == "unknown"                     # unknown is not 'no'


# ---------------------------------------------------------------- evidence / traffic light
def test_in_range_query_is_not_red(models):
    light, reasons, nearest = evidence_lookup(models["evidence"], ISS_HEPTANE)
    assert light.split()[0] in ("GREEN", "AMBER") and len(nearest) == 5


def test_out_of_range_query_is_red_with_reason(models):
    q = {**ISS_HEPTANE, "p_atm": 0.56, "x_o2": 0.34}                         # exploration atmosphere
    light, reasons, _ = evidence_lookup(models["evidence"], q)
    assert light.startswith("RED") and reasons and "p_atm" in reasons[0]


def test_never_tested_combination_is_red(models):
    q = {**ISS_HEPTANE, "p_atm": 2.5}                                         # high pressure without CO2
    light, reasons, _ = evidence_lookup(models["evidence"], q)
    assert light.startswith("RED") and reasons


def test_vectorised_status_matches_single_lookup(models):
    qs = pd.DataFrame([ISS_HEPTANE, {**ISS_HEPTANE, "p_atm": 0.56, "x_o2": 0.34}, {**ISS_HEPTANE, "p_atm": 2.5}])
    status = evidence_status(models["evidence"], "Heptane", qs)
    expected = [{"GREEN": 0, "AMBER": 1, "RED": 2}[evidence_lookup(models["evidence"], r)[0].split()[0]]
                for r in qs.to_dict("records")]
    assert status.tolist() == expected


# ---------------------------------------------------------------- models
@pytest.mark.parametrize("fuel", ["Heptane", "Methanol"])
def test_model_output_shape_and_range(models, fuel):
    X = pd.DataFrame([{**ISS_HEPTANE, "fuel": fuel}])[models["clf"]["meta"]["features"]]
    proba = models["clf"]["model"].predict_proba(X)
    assert proba.shape == (1, 2) and 0.0 <= proba[0, 1] <= 1.0 and math.isclose(proba.sum(), 1.0)
    k = models["k"]["model"].predict(X)
    assert k.shape == (1,) and k[0] > 0
    assert models["k"]["q"]["80%"] > 0 and models["clf"]["meta"]["classifier"].endswith("(fuel-specific slopes)")


# ---------------------------------------------------------------- verifier
PASSAGES = [{"text": "FLEX measured burning-rate constants of 0.25 to 0.65 mm2/s; 1,200 frames were recorded."},
            {"text": "Nayagam et al. reported cool flames after radiative extinction at 1 atm."}]


def test_verify_keeps_correct_cited_sentences():
    kept, dropped = verify("K ranged from 0.25 to 0.65 mm2/s [1]. Nayagam et al. saw cool flames [2].", PASSAGES)
    assert "0.25 to 0.65" in kept and "Nayagam et al. saw cool flames [2]." in kept and not dropped


def test_verify_drops_uncited_and_invalid_citations():
    kept, dropped = verify("Cool flames are invisible. See also [9].", PASSAGES)
    assert kept == "" and len(dropped) == 2


def test_verify_drops_numbers_not_in_cited_passage():
    kept, dropped = verify("The flame lasted 45 minutes [1]. Tests ran at 3 atm [2]. Tests ran at 1 atm [2].",
                           PASSAGES)
    assert kept == "Tests ran at 1 atm [2]." and len(dropped) == 2


def test_number_matching_is_whole_number():
    assert not number_supported("5", ["0.25 mm"]) and number_supported("1200", ["1,200 frames"])
    assert split_sentences("Nayagam et al. found it. K is 0.5 mm2/s.") == ["Nayagam et al. found it.",
                                                                            "K is 0.5 mm2/s."]


# ---------------------------------------------------------------- explore, droplets, tour
def test_risk_grid_hides_untested_cells():
    from ignis.explore import P_AXIS, risk_grid
    z, status = risk_grid("Heptane", 3.0, 0.0, 0.0)
    assert np.isnan(z[status == 2]).all() and np.isfinite(z[status < 2]).all()
    assert np.isnan(z[list(P_AXIS).index(2.5)]).all()                       # 2.5 atm without CO2: never tested


def test_d2_refit_matches_nasa_k_on_at_least_5_droplets():
    from ignis.droplets import k_comparison
    ok = k_comparison().dropna(subset=["k_fit", "k_nasa"])
    assert len(ok) >= 5 and ok["diff_pct"].abs().median() < 10


def test_tour_steps_point_to_real_pages_and_presets():
    from ignis.tour import steps
    labels = {v[0] for v in SCENARIOS.values()}
    for s in steps():
        assert s["page"].startswith("views/") and s["title"] and s["text"]
        if "preset" in s["state"]:
            assert s["state"]["preset"] in labels
        if "atlas_scenario" in s["state"]:
            assert s["state"]["atlas_scenario"] in SCENARIOS


# ---------------------------------------------------------------- regressions from the code review (14 Nov)
def test_verify_keeps_sentence_with_citation_after_full_stop():
    kept, dropped = verify("K ranged from 0.25 to 0.65 mm2/s. [1]", PASSAGES)
    assert "0.25 to 0.65" in kept and kept.strip() != "[1]" and not dropped


def test_verify_accepts_range_citations_and_rejects_bare_stubs():
    kept, _ = verify("FLEX saw cool flames at 1 atm [1-2].", PASSAGES)
    assert "1 atm" in kept
    kept, dropped = verify("[1] [2]", PASSAGES)
    assert kept == "" and dropped


def test_co2_sweep_varies_co2_even_when_slider_is_zero():
    from ignis.explore import sweep
    s = sweep("Heptane", 3.0, 1.0, 0.21, 0.0, 0.0, "suppressant", gas="x_co2").dropna(subset=["K"])
    assert s["K"].iloc[-1] < s["K"].iloc[0]                    # CO2 slows burning (helium would speed it up)
    with pytest.raises(ValueError):
        sweep("Heptane", 3.0, 1.0, 0.21, 0.0, 0.0, "suppressant")


def test_coverage_counts_real_tests_for_any_atmosphere_and_bounds_missing_pmax():
    flex_like = {"test_points": [[0.21, 1.0], [0.21, 0.7]], "tested_o2_max": 0.34, "tested_p_min_atm": 0.69,
                 "tested_p_max_atm": 3.05}
    assert coverage(flex_like, 0.21, 2.5)[0] == "no"            # ranges overlap, but no real test at 2.5 atm
    no_pmax = {"test_points": None, "tested_o2_max": 0.40, "tested_p_min_atm": 0.56, "tested_p_max_atm": np.nan}
    assert coverage(no_pmax, 0.21, 2.0)[0] == "partial"         # unknown upper pressure is not 'unbounded'


def test_light_uses_classifier_training_domain(models):
    q = {"fuel": "Heptane", "p_atm": 3.0, "x_o2": 0.15, "x_co2": 0.70, "x_he": 0.0, "d0_mm": 3.0}
    assert evidence_lookup(models["evidence"], q)[0].startswith("RED")   # only a Disruption run exists there


# ---------------------------------------------------------------- 3D fire story
def test_simulation_params_follow_the_evidence(models):
    from ignis.simulation import simulation_params
    green, _ = simulation_params(models, ISS_HEPTANE, scenario="ISS")
    assert green["validated"] and 0 <= green["p_ext"] <= 1 and green["k_mm2_s"] > 0 and len(green["nearest_ids"]) == 5
    if green["d_ext_mm"] is not None:                                        # median of real NASA extinction runs
        assert green["n_ext_runs"] >= 1 and green["d_ext_mm"] > 0
    red, _ = simulation_params(models, {**ISS_HEPTANE, "p_atm": 0.56, "x_o2": 0.34}, scenario="exploration")
    assert red["light"] == "RED" and red["validated"] is False


def test_simulation_html_injects_params_safely(models):
    from ignis.simulation import (MODEL_DATA_PLACEHOLDER, MODEL_JS_PLACEHOLDER, PLACEHOLDER, build_html,
                                  web_model_payload)
    html = build_html({"scenario": "</script><script>alert(1)</script>", "x": float("nan")}, web_model_payload(models))
    assert PLACEHOLDER not in html and "</script><script>alert(1)" not in html and '"x": null' in html
    assert MODEL_JS_PLACEHOLDER not in html and MODEL_DATA_PLACEHOLDER not in html and "window.IGNIS = {" in html
    with pytest.raises(ValueError):                         # the template needs the browser model
        build_html({"scenario": "x"})


# ---------------------------------------------------------------- browser model parity (ignis_model.js)
def test_browser_model_matches_python_exactly(models, tmp_path):
    import json
    import shutil
    import subprocess
    from ignis.evidence import evidence_lookup
    from ignis.simulation import MODEL_JS, _js_json, web_model_payload
    node = shutil.which("node")
    if node is None:
        pytest.skip("node.js not installed")
    rng = np.random.default_rng(0)
    flex = models["evidence"]["Heptane"]["runs"]
    qs = [{**ISS_HEPTANE, "p_atm": p, "x_o2": o2} for _, o2, p, _ in SCENARIOS.values()]
    qs += [{**ISS_HEPTANE, "fuel": "Methanol", "p_atm": p, "x_o2": o2} for _, o2, p, _ in SCENARIOS.values()]
    for _ in range(300):                                        # random queries over the whole slider space
        dil = rng.choice(["none", "co2", "he"])
        frac = float(rng.uniform(0, 0.6))
        qs.append({"fuel": str(rng.choice(["Heptane", "Methanol"])), "p_atm": float(rng.uniform(0.3, 3.5)),
                   "x_o2": float(rng.uniform(0.10, 0.40)), "x_co2": frac if dil == "co2" else 0.0,
                   "x_he": frac if dil == "he" else 0.0, "d0_mm": float(rng.uniform(1, 5))})
    for r in flex.sample(40, random_state=0).to_dict("records"):   # near real runs -> GREEN / AMBER cases
        qs.append({"fuel": r["fuel"], "p_atm": r["p_atm"], "x_o2": r["x_o2"], "x_co2": r["x_co2"],
                   "x_he": r["x_he"], "d0_mm": r["d0_mm"] + float(rng.normal(0, 0.05))})
    qs = [q for q in qs if q["x_o2"] + q["x_co2"] + q["x_he"] <= 1]
    script = tmp_path / "parity.js"
    script.write_text("global.window = {};\nwindow.IGNIS_MODEL_DATA = " + _js_json(web_model_payload(models)) + ";\n"
                      + MODEL_JS.read_text(encoding="utf-8") + "\nconst qs = " + json.dumps(qs) + ";\n"
                      "console.log(JSON.stringify(qs.map(q => window.IGNIS.predict(q))));\n", encoding="utf-8")
    out = json.loads(subprocess.run([node, str(script)], capture_output=True, text=True, check=True).stdout)
    feats = models["clf"]["meta"]["features"]
    lights = set()
    for q, js in zip(qs, out):
        X = pd.DataFrame([q])[feats]
        assert abs(js["p_ext"] - models["clf"]["model"].predict_proba(X)[0, 1]) < 1e-9
        assert abs(js["k"] - models["k"]["model"].predict(X)[0]) < 1e-9
        light, _, nearest = evidence_lookup(models["evidence"], q)
        assert js["light"] == light.split()[0], (q, js["light"], light)
        assert np.allclose([n["distance"] for n in js["nearest"]], nearest["distance"], atol=0.0101)
        lights.add(js["light"])
    assert lights == {"GREEN", "AMBER", "RED"} and len(qs) > 300   # all three branches exercised


# ---------------------------------------------------------------- every source file compiles
def test_every_python_file_compiles():
    """AppTest logs a page's SyntaxError without reporting it as an exception, so compile everything here."""
    import py_compile
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    files = [root / "streamlit_app.py", *root.glob("views/*.py"), *root.glob("ignis/*.py"), *root.glob("scripts/*.py")]
    for f in files:
        py_compile.compile(str(f), doraise=True)
    assert len(files) > 20


# ---------------------------------------------------------------- safety-control cards and model scope
def test_safety_cards_are_evidence_linked_and_labelled():
    import json
    from pathlib import Path
    from ignis.safety import CARDS, NTRS, PILLARS
    atlas = {a["accession"] for a in json.loads(
        (Path(__file__).resolve().parents[1] / "data/atlas/investigations.json").read_text(encoding="utf-8"))}
    assert {c["pillar"] for c in CARDS} == set(PILLARS)              # all three safety areas covered
    for c in CARDS:
        assert c["accessions"] and set(c["accessions"]) <= atlas      # every card links to real PSI investigations
        assert c["measured"] and c["question"].rstrip().endswith("?")  # interpretation phrased as a question
        assert (c["reported"] is None) == (c["reported_src"] is None)
        if c["reported_src"]:
            assert NTRS[c["reported_src"]][1].startswith("https://")  # NASA-reported results carry a source link


def test_model_scope_is_attached_to_downloads():
    from ignis.messages import MODEL_SCOPE, SCOPE_RECORD
    for phrase in ["whole spacecraft fires", "solid", "smoke", "partial-gravity"]:
        assert phrase in MODEL_SCOPE and any(phrase.split()[0] in s for s in SCOPE_RECORD["does_not_predict"])


# ---------------------------------------------------------------- hardening: Disruption-aware light, tour, tampering
LUNAR_HEPTANE = {"fuel": "Heptane", "p_atm": 0.69, "x_o2": 0.30, "x_co2": 0.0, "x_he": 0.0, "d0_mm": 3.0}


def test_lunar_heptane_is_not_green_when_neighbours_all_disrupted(models):
    light, reasons, nearest = evidence_lookup(models["evidence"], LUNAR_HEPTANE)
    assert not light.startswith("GREEN") and any("Disruption" in r for r in reasons)
    if (nearest["test_end"] == "Disruption").all():
        assert light.startswith("RED")
    status = evidence_status(models["evidence"], "Heptane", pd.DataFrame([LUNAR_HEPTANE]))
    assert status[0] == {"GREEN": 0, "AMBER": 1, "RED": 2}[light.split()[0]]


def test_tour_green_step_deserves_green(models):
    from ignis.tour import GREEN_QUERY, PREDICT_RESET, steps
    assert PREDICT_RESET["pred_fuel"] == GREEN_QUERY["fuel"]
    light, _, nearest = evidence_lookup(models["evidence"], GREEN_QUERY)
    p = models["clf"]["model"].predict_proba(pd.DataFrame([GREEN_QUERY])[models["clf"]["meta"]["features"]])[0, 1]
    assert light.startswith("GREEN") and p > 0.65 and (nearest["test_end"] == "Extinction").sum() >= 3
    green = [s for s in steps() if "GREEN" in s["title"]][0]
    assert green["state"]["pred_fuel"] == "Methanol" and green["state"]["preset"] == SCENARIOS["iss"][0]


def _predict_page(state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "streamlit_app.py"),
                           default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    at.switch_page("views/predict.py").run()
    return at


def test_raw_output_shown_only_for_red():
    green = _predict_page({"preset": SCENARIOS["iss"][0], "pred_fuel": "Methanol"})
    assert not green.exception and not [e for e in green.expander if "raw model output" in e.label]
    red = _predict_page({"preset": SCENARIOS["exploration"][0], "pred_fuel": "Heptane"})
    assert not red.exception and [e for e in red.expander if "raw model output" in e.label]


def test_tampered_sim_query_never_raises():
    from streamlit.testing.v1 import AppTest
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    for bad in [{"fuel": "Heptane", "p_atm": float("nan"), "x_o2": float("inf"), "d0_mm": "abc", "x_co2": -5,
                 "x_he": None}, {"p_atm": float("-inf")}, "not a dict"]:
        at = AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=180)
        at.session_state["sim_query"] = bad
        at.run()
        at.switch_page("views/simulate.py").run()
        assert not at.exception, (bad, [e.message for e in at.exception])
