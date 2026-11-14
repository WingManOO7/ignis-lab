"""Fire story: a guided 3D cinematic, Earth flame -> orbit -> cabin -> FLEX droplet burn -> cabin spark.
Scene 4 (the droplet burn) uses the same models and evidence lookup as the Predict page.

Another page can hand over its inputs before switching here:
    st.session_state["sim_query"] = {"fuel": "Heptane", "p_atm": 1.0, "x_o2": 0.21, "d0_mm": 3.0,
                                     "x_co2": 0.0, "x_he": 0.0, "preset": "<SCENARIOS label>"}   # preset optional
"""
import streamlit as st

from ignis.data import load_models
from ignis.evidence import PSI_PAGE
from ignis.scenarios import SCENARIOS
from ignis.simulation import render_simulation, simulation_params

st.title("Fire story: Earth vs. microgravity")
st.caption("A guided 3D story in five scenes. Scene 4 burns a fuel droplet with the burning rate and the chance of "
           "early extinction predicted by our models trained on NASA's FLEX experiment (274 droplet fires on the ISS, "
           "PSI-69). Shapes, colours and the cabin are illustrative.")
m = load_models()

PRESETS = {SCENARIOS[k][0]: (SCENARIOS[k][2], SCENARIOS[k][1]) for k in SCENARIOS}   # label: (p, O2)
PRESETS["Custom"] = None
DILUENTS = ["none (N2 only)", "CO2", "He"]

init = st.session_state.get("sim_query")
init = init if isinstance(init, dict) else {}


def _num(key, default, lo, hi):
    try:
        return min(max(float(init.get(key, default)), lo), hi)
    except (TypeError, ValueError):
        return default


# initial values: from the handed-over query if there is one, else the first preset
init_p, init_o2 = _num("p_atm", 1.0, 0.3, 3.5), _num("x_o2", 0.21, 0.10, 0.40)
init_preset = init.get("preset") or init.get("scenario")
if init_preset not in PRESETS:
    match = [lab for lab, v in PRESETS.items() if v and abs(v[0] - init_p) < 0.005 and abs(v[1] - init_o2) < 0.005]
    init_preset = match[0] if match else ("Custom" if init else list(PRESETS)[0])
init_fuel = init.get("fuel") if init.get("fuel") in ("Heptane", "Methanol") else "Heptane"
init_dil = init.get("diluent") if init.get("diluent") in DILUENTS else (
    "CO2" if _num("x_co2", 0, 0, 1) > 0 else "He" if _num("x_he", 0, 0, 1) > 0 else DILUENTS[0])
init_frac = _num("x_co2" if init_dil == "CO2" else "x_he" if init_dil == "He" else "frac", 0.20, 0.0, 0.70) or 0.20
init_d0 = _num("d0_mm", 3.0, 1.0, 5.0)

with st.expander("Change the conditions (atmosphere, fuel, suppressant, droplet size)", expanded=False):
    preset = st.selectbox("Start from a crew atmosphere", list(PRESETS), index=list(PRESETS).index(init_preset))
    p0, o0 = (init_p, init_o2) if (init and preset == init_preset) else (PRESETS[preset] or (1.0, 0.21))
    c1, c2 = st.columns(2)
    fuel = c1.selectbox("Fuel", ["Heptane", "Methanol"], index=["Heptane", "Methanol"].index(init_fuel),
                        help="FLEX burned n-heptane and methanol droplets.")
    p_atm = c1.slider("Pressure (atm)", 0.3, 3.5, float(p0), 0.01, help="1 atm = sea level / ISS cabin.")
    x_o2 = c1.slider("O2 mole fraction", 0.10, 0.40, float(o0), 0.01, help="0.21 = normal air.")
    diluent = c2.selectbox("Added suppressant gas", DILUENTS, index=DILUENTS.index(init_dil),
                           help="FLEX tested CO2 and helium as fire suppressants mixed into the cabin gas.")
    frac = 0.0 if diluent.startswith("none") else c2.slider(f"{diluent} mole fraction", 0.0, 0.70, float(init_frac), 0.01)
    d0 = c2.slider("Initial droplet diameter (mm)", 1.0, 5.0, float(init_d0), 0.05)

q = {"fuel": fuel, "p_atm": p_atm, "x_o2": x_o2, "d0_mm": d0,
     "x_co2": frac if diluent == "CO2" else 0.0, "x_he": frac if diluent == "He" else 0.0}
if q["x_o2"] + q["x_co2"] + q["x_he"] > 1:
    st.error("Gas fractions exceed 1 - reduce O2 or the suppressant.")
    st.stop()

params, nearest = simulation_params(m, q, scenario=preset)
light = params["light"]
summary = (f"**{preset}** · {fuel} · {p_atm:.2f} atm · O2 {x_o2:.0%} · "
           f"{'no suppressant' if diluent.startswith('none') else f'{diluent} {frac:.0%}'} · d0 {d0:.2f} mm")
if light == "RED":
    st.error(f"{summary}  \n{params['light_text']}. Scene 4 will not play a data-driven burn.")
else:
    st.markdown(f"{summary}  \n:{'green' if light == 'GREEN' else 'orange'}[{params['light_text']}] · "
                f"K = {params['k_mm2_s']:.2f} ± {params['k_half_mm2_s']:.2f} mm²/s · "
                f"P(flame goes out early) = {params['p_ext']:.0%}")

render_simulation(params, height=680)
st.caption("Controls: play / pause (space), previous / next scene (arrow keys), click a scene in the progress bar, "
           "speed 0.5-2x, and the ventilation fan switch in scene 5. Needs WebGL and internet access (three.js from a CDN).")

with st.expander("What is data and what is illustration"):
    st.markdown(
        "| In the story | Source |\n|---|---|\n"
        "| Burning-rate constant K, so how fast the droplet shrinks (d² law: d² = d0² − K·t) and the burn time | "
        "**Data**: ridge model trained on NASA FLEX (PSI-69), 80% conformal interval |\n"
        "| Whether the visible flame goes out early (P ≥ 50%) | **Data**: calibrated classifier trained on FLEX |\n"
        "| The diameter at which the flame goes out | **Data**: median extinction diameter of the 5 nearest real "
        "NASA runs that ended in Extinction |\n"
        "| GREEN / AMBER / RED, and \"not simulated\" when RED | **Data**: distance to the nearest NASA runs and the "
        "tested ranges |\n"
        "| Cool flame after extinction (heptane only) | NASA finding (Nayagam et al., 2012); the glow is drawn, "
        "not modelled |\n"
        "| Flame shapes and colours, Earth candle, spacecraft, cabin, spark, smoke, fan airflow | **Illustrative** |\n"
        "| Bigger / brighter cabin fire at higher O2 | **Illustrative**, qualitative only |\n\n"
        "The real seconds in the HUD come from the model; screen time is stretched or compressed so the burn plays "
        "in 10-20 s. After the visible flame goes out, the droplet's further shrinking is not modelled. "
        "There is no Moon or Mars scene: NASA's PSI has no partial-gravity combustion data.")

st.subheader("The 5 nearest real NASA runs")
st.dataframe(nearest, hide_index=True,
             column_config={"distance": st.column_config.NumberColumn(help="0 = identical conditions")})
st.markdown(f"Source: [NASA PSI-69 FLEX]({PSI_PAGE}); identifiers match NASA/TP-2015-216046 Table IX. "
            "This project is not affiliated with or endorsed by NASA.")
