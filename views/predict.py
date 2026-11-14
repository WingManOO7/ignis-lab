import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ignis.data import load_atlas, load_flex, load_models
from ignis.explore import O2_AXIS, P_AXIS, risk_grid, sweep
from ignis.glossary import glossary_panel
from ignis.messages import why_and_scope
from ignis.evidence import PSI_PAGE, evidence_lookup, outcome_summary
from ignis.scenarios import SCENARIOS, covering_investigations

st.title("Predict a droplet flame - with the NASA runs behind the number")
st.caption("Models trained on NASA's FLEX experiment: 274 fuel-droplet fires on the ISS (PSI-69). "
           "Every number comes with the closest real NASA runs and a check of whether NASA ever tested there.")
why_and_scope()
m = load_models()
meta = m["clf"]["meta"]

PRESETS = {SCENARIOS[k][0]: (SCENARIOS[k][2], SCENARIOS[k][1]) for k in SCENARIOS}   # label: (p, O2)
PRESETS["Custom"] = None
if st.session_state.get("preset") not in PRESETS:      # e.g. stale value from an older version
    st.session_state.pop("preset", None)
preset = st.selectbox("Start from a crew atmosphere", list(PRESETS), key="preset",
                      help="The Atlas page can send its selected habitat here.")
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
             "These NASA investigations did test at or near this oxygen level and pressure:")
    hit = covering_investigations(pd.DataFrame(load_atlas()), x_o2, p_atm)
    if len(hit):
        st.dataframe(hit, column_config={"page": st.column_config.LinkColumn("PSI page", display_text="open")},
                     hide_index=True)
    else:
        st.info("No PSI investigation with a curated test envelope covers this atmosphere: a research gap.")
    st.page_link("views/atlas.py", label="Compare them in the Investigation Atlas", icon=":material/travel_explore:")
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

record = {"inputs": q, "traffic_light": light, "reasons": reasons,
          "outputs": None if light.startswith("RED") else {
              "p_visible_flame_goes_out_early": round(p_ext, 4), "K_mm2_per_s": round(k_hat, 4),
              "K_80pct_interval_half_width": round(half, 4), "burnout_time_s_if_no_extinction": round(d0 ** 2 / k_hat, 2)},
          "nearest_nasa_runs": nearest.to_dict("records"),
          "source": "Models trained on NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451); IGNIS LAB"}
st.download_button("Download this prediction (JSON)", json.dumps(record, indent=1, default=str),
                   file_name="ignis_prediction.json", mime="application/json")

# ---------------------------------------------------------------- explore around this point
st.subheader("Explore around this point")
CONFOUND = ("In FLEX, pressures above 1 atm only occur together with about 70% CO2, so pressure and CO2 effects "
            "cannot be separated. Grey = NASA never tested there, so no prediction is shown.")
tab_map, tab_sweep = st.tabs(["Risk map: oxygen x pressure", "Sweep one variable"])

with tab_map:
    z, status = risk_grid(fuel, d0, q["x_co2"], q["x_he"])
    fig = go.Figure(go.Heatmap(
        x=O2_AXIS, y=P_AXIS, z=z, zmin=0, zmax=1, colorscale="RdYlBu", name="P(goes out)",
        colorbar=dict(title="chance flame<br>goes out early"),
        hovertemplate="O2 %{x:.2f}, %{y:.2f} atm<br>P(goes out early) %{z:.0%}<extra></extra>"))
    amber = np.where(status == 1, 1.0, np.nan)
    fig.add_trace(go.Heatmap(x=O2_AXIS, y=P_AXIS, z=amber, showscale=False, hoverinfo="skip",
                             colorscale=[[0, "rgba(255,255,255,0.35)"], [1, "rgba(255,255,255,0.35)"]]))
    flex = load_flex()
    same = flex[(flex["fuel"] == fuel) & ((flex["x_co2"] > 0) == (q["x_co2"] > 0))
                & ((flex["x_he"] > 0) == (q["x_he"] > 0))]
    fig.add_trace(go.Scatter(x=same["x_o2"], y=same["p_atm"], mode="markers", name="real NASA runs (same diluent)",
                             marker=dict(size=6, color="black", line=dict(width=1, color="white")),
                             text=same["flex_id"] + " - " + same["test_end"], hoverinfo="text"))
    for _k, (lab, o2s, ps, _src) in SCENARIOS.items():
        fig.add_trace(go.Scatter(x=[o2s], y=[ps], mode="markers", name=lab.split(" (")[0],
                                 marker=dict(symbol="star", size=15, line=dict(width=1, color="white"))))
    fig.add_trace(go.Scatter(x=[x_o2], y=[p_atm], mode="markers", name="your query",
                             marker=dict(symbol="x", size=14, color="white", line=dict(width=2, color="black"))))
    fig.update_layout(plot_bgcolor="#5b6068", height=520, xaxis_title="O2 mole fraction",
                      yaxis_title="pressure (atm)", legend=dict(orientation="h", y=-0.18), margin=dict(t=30),
                      title=f"{fuel}, {d0:.1f} mm droplet, {diluent}" + (f" {frac:.2f}" if frac else ""))
    st.plotly_chart(fig, width="stretch")
    st.caption(CONFOUND + " Light-washed cells = inside the tested ranges but far from any single run (AMBER).")

with tab_sweep:
    options = {"O2 mole fraction": "x_o2", "Pressure (atm)": "p_atm"}
    if not diluent.startswith("none"):
        options[f"{diluent} mole fraction"] = "suppressant"
    var_label = st.radio("Vary", list(options), horizontal=True)
    s = sweep(fuel, d0, p_atm, x_o2, q["x_co2"], q["x_he"], options[var_label])
    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                         subplot_titles=("Chance the visible flame goes out early", "Burning-rate constant K (mm²/s)"))
    fig2.add_trace(go.Scatter(x=s["x"], y=s["p_ext"], mode="lines", name="P(goes out early)"), 1, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K_hi"], mode="lines", line=dict(width=0), showlegend=False,
                              hoverinfo="skip"), 2, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K_lo"], mode="lines", line=dict(width=0), fill="tonexty",
                              fillcolor="rgba(79,163,255,0.25)", name="80% interval"), 2, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K"], mode="lines", name="K"), 2, 1)
    red = s["status"].to_numpy() == 2
    step = (s["x"].iloc[1] - s["x"].iloc[0]) / 2
    start = None
    for i, r in enumerate(np.append(red, False)):
        if r and start is None:
            start = i
        elif not r and start is not None:
            fig2.add_vrect(x0=s["x"].iloc[start] - step, x1=s["x"].iloc[i - 1] + step, fillcolor="grey",
                           opacity=0.35, line_width=0, row="all", col=1)
            start = None
    current = {"x_o2": x_o2, "p_atm": p_atm, "suppressant": frac}[options[var_label]]
    fig2.add_vline(x=current, line_dash="dot", line_color="white")
    fig2.update_yaxes(range=[0, 1], row=1, col=1)
    fig2.update_layout(height=520, xaxis2_title=var_label, legend=dict(orientation="h", y=-0.15), margin=dict(t=40))
    st.plotly_chart(fig2, width="stretch")
    st.caption(CONFOUND + " Dotted line = your current value.")

glossary_panel(["light", "K", "d2 law", "conformal", "calibration", "outcomes", "cool flame"])
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
