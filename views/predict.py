import pandas as pd
import streamlit as st

from ignis.data import load_atlas, load_models
from ignis.evidence import PSI_PAGE, evidence_lookup, outcome_summary
from ignis.scenarios import SCENARIOS

st.title("Predict a droplet flame - with the NASA runs behind the number")
st.caption("Models trained on NASA's FLEX experiment: 274 fuel-droplet fires on the ISS (PSI-69). "
           "Every number comes with the closest real NASA runs and a check of whether NASA ever tested there.")
m = load_models()
meta = m["clf"]["meta"]

PRESETS = {SCENARIOS[k][0]: (SCENARIOS[k][2], SCENARIOS[k][1]) for k in SCENARIOS}   # label: (p, O2)
PRESETS["Custom"] = None
preset = st.selectbox("Start from a crew atmosphere", list(PRESETS))
p0, o0 = PRESETS[preset] or (1.0, 0.21)
c1, c2 = st.columns(2)
fuel = c1.selectbox("Fuel", ["Heptane", "Methanol"], help="FLEX burned n-heptane and methanol droplets.")
p_atm = c1.slider("Pressure (atm)", 0.3, 3.5, float(p0), 0.01, help="1 atm = sea level / ISS cabin.")
x_o2 = c1.slider("O2 mole fraction", 0.10, 0.40, float(o0), 0.01, help="0.21 = normal air.")
diluent = c2.selectbox("Added suppressant gas", ["none (N2 only)", "CO2", "He"],
                       help="FLEX tested CO2 and helium as fire suppressants mixed into the cabin gas.")
frac = 0.0 if diluent.startswith("none") else c2.slider(f"{diluent} mole fraction", 0.0, 0.70, 0.20, 0.01)
d0 = c2.slider("Initial droplet diameter (mm)", 1.0, 5.0, 3.0, 0.05)

q = {"fuel": fuel, "p_atm": p_atm, "x_o2": x_o2, "d0_mm": d0,
     "x_co2": frac if diluent == "CO2" else 0.0, "x_he": frac if diluent == "He" else 0.0}
if q["x_o2"] + q["x_co2"] + q["x_he"] > 1:
    st.error("Gas fractions exceed 1 - reduce O2 or the suppressant.")
    st.stop()
X = pd.DataFrame([q])[meta["features"]]

# ---------------------------------------------------------------- trust check first
light, reasons, nearest = evidence_lookup(m["evidence"], q)
(st.success if light.startswith("GREEN") else st.warning if light.startswith("AMBER") else st.error)(light)
for r in reasons:
    st.write("- " + r)

p_ext = float(m["clf"]["model"].predict_proba(X)[0, 1])
k_hat = float(m["k"]["model"].predict(X)[0])
half = m["k"]["q"]["80%"]
base = meta["base_rate_extinction"]

if light.startswith("RED"):
    st.markdown("#### Model numbers withheld")
    st.write("FLEX never tested these conditions, so any number here would be a guess. "
             "The investigations below did test near this oxygen level and pressure:")
    atlas = pd.DataFrame(load_atlas())
    hit = atlas[(atlas["tested_o2_max"] >= x_o2 - 0.01) & (atlas["tested_p_min_atm"] <= p_atm + 0.05)
                & (atlas["tested_p_max_atm"].fillna(9) >= p_atm - 0.05)]
    if len(hit):
        st.dataframe(hit[["acronym", "title", "fuel_type", "tested_o2_max", "tested_p_min_atm", "page"]],
                     column_config={"page": st.column_config.LinkColumn("PSI page", display_text="open")},
                     hide_index=True)
    else:
        st.info("No PSI investigation with a curated test envelope covers this atmosphere: a research gap.")
    with st.expander("Show the raw model output anyway (NOT validated)"):
        st.write(f"P(extinction) = {p_ext:.0%}, K = {k_hat:.2f} mm²/s")
else:
    a, b, c = st.columns(3)
    a.metric("Chance the visible flame goes out before burnout", f"{p_ext:.0%}",
             delta=f"{(p_ext - base) * 100:+.0f} pts vs NASA average ({base:.0%})", delta_color="off",
             help="Calibrated logistic regression. Across all FLEX runs used, 87% of flames went out early.")
    b.metric("Burning-rate constant K", f"{k_hat:.2f} ± {half:.2f} mm²/s",
             help="How fast the droplet's surface area shrinks (d² law). The ± range contained the true "
                  "value for ~80% of NASA runs from conditions the model never saw.")
    c.metric("Time to burn out completely (d² law: d0²/K)", f"{d0 ** 2 / k_hat:.1f} s",
             help="Only meaningful if the flame does not go out first.")
    if light.startswith("AMBER"):
        st.warning("AMBER: inside the tested ranges but far from any single NASA run - use with caution.")

# ---------------------------------------------------------------- what NASA actually saw
st.subheader("What NASA actually saw at the 5 closest real runs")
seen = outcome_summary(nearest)
cols = st.columns(len(seen))
for col, (outcome, n) in zip(cols, seen.items()):
    col.metric(outcome, f"{n} of 5")
if seen.get("Disruption", 0) >= 3:
    st.warning("Most nearby NASA runs ended in **Disruption** (the droplet broke apart). The model was not "
               "trained on Disruption runs because NASA suspects fuel-needle contamination "
               "(NASA/TP-2015-216046 sec. 5.2), so it cannot predict that outcome here.")
st.dataframe(nearest, hide_index=True,
             column_config={"distance": st.column_config.NumberColumn(help="0 = identical conditions")})
st.markdown(f"Source: [NASA PSI-69 FLEX]({PSI_PAGE}); identifiers match NASA/TP-2015-216046 Table IX. "
            "Model outputs are correlations learned from these runs, not physical laws.")

with st.expander("How to read this page"):
    st.markdown(
        "- **GREEN / AMBER / RED** checks whether NASA tested anything like your settings. "
        "RED means the model would be extrapolating, so we do not show its numbers.\n"
        "- **Chance the flame goes out**: probability that the visible flame extinguishes before the "
        "droplet is used up. Tested honestly: when it says 90-100%, NASA's flames went out ~95% of the time.\n"
        "- **K (burning-rate constant)**: in microgravity a droplet's diameter squared shrinks linearly "
        "with time (the d² law); K is the slope. Bigger K = faster burning.\n"
        "- **Closest real runs**: the actual ISS tests with the most similar conditions, with their real "
        "outcomes - check the model against them.")
