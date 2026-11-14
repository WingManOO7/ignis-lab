"""Fire lab: an interactive 3D experience. Earth lab -> orbit -> inside the cabin, with NASA's FLEX combustion
chamber (driven live by our trained models, evaluated in the browser) and an illustrative cabin wiring fire.

Another page can hand over its inputs before switching here:
    st.session_state["sim_query"] = {"fuel": "Heptane", "p_atm": 1.0, "x_o2": 0.21, "d0_mm": 3.0,
                                     "x_co2": 0.0, "x_he": 0.0, "preset": "<SCENARIOS label>"}   # preset optional
"""
import streamlit as st

from ignis import ui
from ignis.data import load_flex, load_models
from ignis.scenarios import SCENARIOS
from ignis.simulation import render_simulation, simulation_params

ui.page_header("Fire lab: Earth vs. microgravity",
               "Explore a flame from Earth to orbit; the FLEX chamber runs our trained models live.",
               f"NASA PSI-69 FLEX, {len(load_flex())} ISS droplet burns")
ui.note("**Start here:** switch gravity off, launch to orbit, then open the FLEX chamber.", tone="quiet")

m = load_models()
init = st.session_state.get("sim_query")
init = init if isinstance(init, dict) else {}


def _num(key, default, lo, hi):
    try:
        return min(max(float(init.get(key, default)), lo), hi)
    except (TypeError, ValueError):
        return default


iss_label, iss_o2, iss_p, _ = SCENARIOS["iss"]
q = {"fuel": init.get("fuel") if init.get("fuel") in ("Heptane", "Methanol") else "Heptane",
     "p_atm": _num("p_atm", iss_p, 0.3, 3.5), "x_o2": _num("x_o2", iss_o2, 0.10, 0.40),
     "x_co2": _num("x_co2", 0.0, 0.0, 0.70), "x_he": _num("x_he", 0.0, 0.0, 0.70), "d0_mm": _num("d0_mm", 3.0, 1.0, 5.0)}
if q["x_co2"] > 0 and q["x_he"] > 0:          # the chamber offers one suppressant at a time
    q["x_he"] = 0.0
presets = {lab: (o2, p) for lab, o2, p, _ in SCENARIOS.values()}
scenario = init.get("preset") or init.get("scenario")
if scenario not in presets:
    match = [lab for lab, (o2, p) in presets.items() if abs(p - q["p_atm"]) < 0.005 and abs(o2 - q["x_o2"]) < 0.005]
    scenario = match[0] if match else "Custom"

params, _nearest = simulation_params(m, q, scenario=scenario)
params.setdefault("scenarios", [{"label": lab, "x_o2": o2, "p_atm": p} for lab, (o2, p) in presets.items()])
render_simulation(params, height=780, models=m)

with st.expander("What is data and what is illustration"):
    st.markdown(
        "| In the fire lab | Source |\n|---|---|\n"
        "| FLEX chamber: burning-rate constant K ± 80% range, so how fast the droplet shrinks (d² law: "
        "d² = d0² − K·t), the burnout time and the live d² plot | **Data**: ridge model trained on NASA FLEX (PSI-69), "
        "split-conformal interval |\n"
        "| FLEX chamber: whether the visible flame goes out early (P ≥ 50%) | **Data**: calibrated classifier trained "
        "on FLEX |\n"
        "| The diameter at which the flame goes out, the 5 nearest real runs | **Data**: nearest NASA runs that ended "
        "in Extinction (median) |\n"
        "| GREEN / AMBER / RED, the coloured bands on the sliders, \"not simulated\" when RED | **Data**: tested ranges "
        "and distance to the nearest NASA runs |\n"
        "| Cool-flame glow after extinction (heptane) | NASA finding (Nayagam et al., 2012); the glow is drawn, not "
        "modelled |\n"
        "| Flame size and brightness in the chamber | **Illustrative** mapping from K |\n"
        "| Earth candle, gravity-off flame, spacecraft, cabin | **Illustrative** (gravity-off flame based on NASA "
        "candle observations, no data) |\n"
        "| Cabin wiring fire: spark, fan on/off, oxygen effect, flash ignition, CO2 suppression | **Illustrative**, "
        "qualitative only, with NASA findings quoted (Urban et al., ICES 2021 and 2024; NASA Saffire) |\n\n"
        "The models run in your browser with the same numbers as the Predict page. Playback is 1×, 2× or 5× real "
        "time and the plot always shows real seconds. After the visible flame goes out, the droplet's further "
        "shrinking is not modelled. There is no Moon or Mars scene: NASA's PSI has no partial-gravity combustion data."
        "\n\n"
        "Needs WebGL and internet (three.js loads from a CDN). The narrator voice is your browser's text-to-speech. "
        "Not affiliated with or endorsed by NASA.")
