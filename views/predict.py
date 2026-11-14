import pandas as pd
import streamlit as st

from ignis.data import load_models
from ignis.evidence import PSI_PAGE, evidence_lookup

st.title("Predict a droplet flame - with the NASA runs behind the number")
m = load_models()
PRESETS = {  # (pressure atm, O2 mole fraction)
    "ISS cabin air (1 atm, 21% O2)": (1.0, 0.21),
    "Lunar habitat per challenge brief (10.2 psi = 0.69 atm, 30% O2)": (0.69, 0.30),
    "Exploration atmosphere (8.2 psia = 0.56 atm, 34% O2)": (0.56, 0.34),
    "Custom": None,
}
preset = st.selectbox("Start from", list(PRESETS))
p0, o0 = PRESETS[preset] or (1.0, 0.21)
c1, c2 = st.columns(2)
fuel = c1.selectbox("Fuel", ["Heptane", "Methanol"])
p_atm = c1.slider("Pressure (atm)", 0.3, 3.5, float(p0), 0.01)
x_o2 = c1.slider("O2 mole fraction", 0.10, 0.40, float(o0), 0.01)
diluent = c2.selectbox("Added suppressant gas", ["none (N2 only)", "CO2", "He"])
frac = 0.0 if diluent.startswith("none") else c2.slider(f"{diluent} mole fraction", 0.0, 0.70, 0.20, 0.01)
d0 = c2.slider("Initial droplet diameter (mm)", 1.0, 5.0, 3.0, 0.05)

q = {"fuel": fuel, "p_atm": p_atm, "x_o2": x_o2, "d0_mm": d0,
     "x_co2": frac if diluent == "CO2" else 0.0, "x_he": frac if diluent == "He" else 0.0}
if q["x_o2"] + q["x_co2"] + q["x_he"] > 1:
    st.error("Gas fractions exceed 1 - reduce O2 or the suppressant.")
    st.stop()
X = pd.DataFrame([q])[m["clf"]["meta"]["features"]]

light, reasons, nearest = evidence_lookup(m["evidence"], q)
(st.success if light.startswith("GREEN") else st.warning if light.startswith("AMBER") else st.error)(light)
for r in reasons:
    st.write("- " + r)

p_ext = float(m["clf"]["model"].predict_proba(X)[0, 1])
k_hat = float(m["k"]["model"].predict(X)[0])
half = m["k"]["q"]["80%"]
a, b, c = st.columns(3)
a.metric("P(visible flame goes out before burnout)", f"{p_ext:.0%}")
b.metric("Burning-rate constant K", f"{k_hat:.2f} mm²/s", help=f"80% interval ±{half:.2f} (split-conformal)")
c.metric("Burnout time if no extinction (d² law: d0²/K)", f"{d0**2 / k_hat:.1f} s")
st.caption("Model outputs are only as good as the evidence below. Correlation, not causation.")

st.subheader("Closest real NASA FLEX runs")
st.dataframe(nearest, hide_index=True)
st.markdown(f"Source: [NASA PSI-69 FLEX]({PSI_PAGE}); identifiers match NASA/TP-2015-216046 Table IX.")
