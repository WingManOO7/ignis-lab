import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ignis import ui
from ignis.data import load_atlas, load_flex, load_models
from ignis.explore import O2_AXIS, P_AXIS, risk_grid, sweep
from ignis.glossary import glossary_list
from ignis.messages import CHART_SCOPE, MODEL_SCOPE, SCOPE_RECORD, scope_note, why_and_scope
from ignis.evidence import PSI_PAGE, evidence_lookup, outcome_summary
from ignis.scenarios import SCENARIOS, covering_investigations

ui.page_header("Predict a droplet flame",
               "Will the flame go out early? Checked against real NASA runs.",
               f"NASA PSI-69 FLEX, {len(load_flex())} ISS droplet burns")
scope_note()
m = load_models()
meta = m["clf"]["meta"]

PRESETS = {SCENARIOS[k][0]: (SCENARIOS[k][2], SCENARIOS[k][1]) for k in SCENARIOS}   # label: (p, O2)
PRESETS["Custom"] = None
if st.session_state.get("preset") not in PRESETS:      # e.g. stale value from an older version
    st.session_state.pop("preset", None)
# Keyed widgets get their defaults through session state (never both value= and state, which warns),
# so the guided tour can reset them.
DEFAULTS = {"pred_fuel": "Heptane", "pred_diluent": "none (N2 only)", "pred_d0": 3.0}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

inputs, hero = st.columns([1, 1.85], gap="large")
with inputs.container(border=True, key="pred_inputs"):
    preset = st.selectbox("Start from a crew atmosphere", list(PRESETS), key="preset",
                          help="The Atlas page can send its selected habitat here.")
    p0, o0 = PRESETS[preset] or (1.0, 0.21)
    c1, c2 = st.columns(2)
    fuel = c1.selectbox("Fuel", ["Heptane", "Methanol"], key="pred_fuel",
                        help="FLEX burned n-heptane and methanol droplets.")
    diluent = c2.selectbox("Suppressant", ["none (N2 only)", "CO2", "He"], key="pred_diluent",
                           format_func=lambda v: "none" if v.startswith("none") else v,
                           help="FLEX tested CO2 and helium as fire suppressants mixed into the cabin gas "
                                "(none = nitrogen only).")
    p_atm = st.slider("Pressure (atm)", 0.3, 3.5, float(p0), 0.01, help="1 atm = sea level / ISS cabin.")
    x_o2 = st.slider("O2 mole fraction", 0.10, 0.40, float(o0), 0.01, help="0.21 = normal air.")
    frac = 0.0 if diluent.startswith("none") else st.slider(f"{diluent} mole fraction", 0.0, 0.70, 0.20, 0.01)
    d0 = st.slider("Initial droplet diameter (mm)", 1.0, 5.0, step=0.05, key="pred_d0")
actions = inputs.container()

q = {"fuel": fuel, "p_atm": p_atm, "x_o2": x_o2, "d0_mm": d0,
     "x_co2": frac if diluent == "CO2" else 0.0, "x_he": frac if diluent == "He" else 0.0}
if q["x_o2"] + q["x_co2"] + q["x_he"] > 1:
    hero.error("Gas fractions exceed 1 - reduce O2 or the suppressant.")
    st.stop()
X = pd.DataFrame([q])[meta["features"]]

# ---------------------------------------------------------------- hero: evidence light first, then the numbers
light, reasons, nearest = evidence_lookup(m["evidence"], q)
p_ext = float(m["clf"]["model"].predict_proba(X)[0, 1])
k_hat = float(m["k"]["model"].predict(X)[0])
half = m["k"]["q"]["80%"]
base = meta["base_rate_extinction"]
seen = outcome_summary(nearest)

with hero:
    ui.evidence_lamp(light, reasons)
    if light.startswith("RED"):
        ui.section("Model numbers withheld", "FLEX never tested here. These investigations did:",
                   help="FLEX never tested these conditions, so any number here would be a guess. These NASA "
                        "investigations did test at or near this oxygen level and pressure.")
        hit = covering_investigations(pd.DataFrame(load_atlas()), x_o2, p_atm)
        if len(hit):
            st.dataframe(hit, column_config={"page": st.column_config.LinkColumn("PSI page", display_text="open")},
                         hide_index=True, width="stretch")
        else:
            ui.note("**Research gap:** no curated PSI investigation covers this atmosphere.", tone="caution")
        st.page_link("views/atlas.py", label="Compare them in the Atlas", icon=":material/travel_explore:")
        with st.expander("Show the raw model output anyway (NOT validated)"):
            st.write(f"P(extinction) = {p_ext:.0%}, K = {k_hat:.2f} mm²/s")
    else:
        st.write("")
        ui.readouts(size="md", cols="1fr 1.45fr 0.9fr", items=[
            {"v": f"{p_ext:.0%}", "tone": "flame", "l": "chance flame goes out early",
             "s": f"{(p_ext - base) * 100:+.0f} pts vs NASA avg ({base:.0%})",
             "t": "Calibrated probability that the visible flame goes out before the droplet burns away."},
            {"v": f"{k_hat:.2f} ± {half:.2f}", "u": "mm²/s", "l": "burning rate K", "s": "80% interval",
             "t": "How fast the droplet shrinks (d² law). The ± range contained the true value for ~80% of NASA "
                  "runs from conditions the model never saw."},
            {"v": f"{d0 ** 2 / k_hat:.1f}", "u": "s", "l": "burnout time", "s": "if it keeps burning",
             "t": "d0²/K: only meaningful if the flame does not go out first.", "tone": "ink"}])
        if light.startswith("AMBER"):
            ui.note("**AMBER:** no close NASA run. Use with caution.", tone="caution",
                    details="Inside the tested ranges but far from any single NASA run.")
    st.write("")
    ui.section("NASA's 5 closest real runs", help="What NASA actually observed at the 5 most similar ISS tests "
                                                   "(see the Closest NASA runs tab).")
    ui.chips("", {k: f"{v} of 5" for k, v in seen.items()})
    if seen.get("Disruption", 0) >= 3:
        ui.note("**Mostly Disruption nearby:** the model can't predict that.", tone="caution",
                details="Most nearby NASA runs ended in Disruption (the droplet broke apart). The model was not "
                        "trained on Disruption runs because NASA suspects fuel-needle contamination "
                        "(NASA/TP-2015-216046 sec. 5.2), so it cannot predict that outcome here.")

record = {"inputs": q, "traffic_light": light, "reasons": reasons,
          "outputs": None if light.startswith("RED") else {
              "p_visible_flame_goes_out_early": round(p_ext, 4), "K_mm2_per_s": round(k_hat, 4),
              "K_80pct_interval_half_width": round(half, 4), "burnout_time_s_if_no_extinction": round(d0 ** 2 / k_hat, 2)},
          "nearest_nasa_runs": nearest.to_dict("records"),
          "model_scope": SCOPE_RECORD,
          "source": "Models trained on NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451); IGNIS LAB"}
with actions:
    if st.button("Watch this droplet in the 3D fire story", type="primary", icon=":material/local_fire_department:",
                 width="stretch"):
        st.session_state["sim_query"] = {**q, "preset": preset, "diluent": diluent}
        st.switch_page("views/simulate.py")
    st.download_button("Download this prediction (JSON)", json.dumps(record, indent=1, default=str),
                       file_name="ignis_prediction.json", mime="application/json", icon=":material/download:",
                       width="stretch")

# ---------------------------------------------------------------- secondary material
CONFOUND = ("In FLEX, pressures above 1 atm only occur together with about 70% CO2, so pressure and CO2 effects "
            "cannot be separated. Grey = NASA never tested there, so no prediction is shown.")
tab_runs, tab_map, tab_sweep, tab_read = st.tabs(["Closest NASA runs", "Risk map", "Sweep", "How to read"])

with tab_runs:
    st.dataframe(nearest, hide_index=True, width="stretch",
                 column_config={"distance": st.column_config.NumberColumn(help="0 = identical conditions")})
    st.caption(f"Source: [NASA PSI-69 FLEX]({PSI_PAGE}).",
               help="Identifiers match NASA/TP-2015-216046 Table IX. Distance 0 = identical conditions. Model outputs "
                    "are correlations learned from these runs, not physical laws.")

NEVER = "#475066"          # 'never tested' cells (plot background shows through NaN cells)
with tab_map:
    z, status = risk_grid(fuel, d0, q["x_co2"], q["x_he"])
    fig = go.Figure(go.Heatmap(
        x=O2_AXIS, y=P_AXIS, z=z, zmin=0, zmax=1, name="P(goes out)",
        colorscale=[[0, ui.FLAME], [0.5, "#F2E8DC"], [1, "#3D8BFF"]],
        colorbar=dict(title=dict(text="chance flame<br>goes out early", font=dict(color=ui.DIM)), tickformat=".0%",
                      outlinewidth=0, tickfont=dict(color=ui.DIM)),
        hovertemplate="O2 %{x:.2f}, %{y:.2f} atm<br>P(goes out early) %{z:.0%}<extra></extra>"))
    amber = np.where(status == 1, 1.0, np.nan)
    fig.add_trace(go.Heatmap(x=O2_AXIS, y=P_AXIS, z=amber, showscale=False, hoverinfo="skip",
                             colorscale=[[0, "rgba(255,255,255,0.35)"], [1, "rgba(255,255,255,0.35)"]]))
    flex = load_flex()
    same = flex[(flex["fuel"] == fuel) & ((flex["x_co2"] > 0) == (q["x_co2"] > 0))
                & ((flex["x_he"] > 0) == (q["x_he"] > 0))]
    fig.add_trace(go.Scatter(x=same["x_o2"], y=same["p_atm"], mode="markers", name="real NASA runs (same diluent)",
                             marker=dict(size=6, color=ui.SPACE, line=dict(width=1, color="white")),
                             text=same["flex_id"] + " - " + same["test_end"], hoverinfo="text"))
    star_colors = {"iss": "#FFFFFF", "lunar": "#FFD696", "exploration": ui.FLAME}
    for _k, (lab, o2s, ps, _src) in SCENARIOS.items():
        fig.add_trace(go.Scatter(x=[o2s], y=[ps], mode="markers", name=lab.split(" (")[0],
                                 marker=dict(symbol="star", size=15, color=star_colors.get(_k, "#FFFFFF"),
                                             line=dict(width=1.5, color=ui.SPACE))))
    fig.add_trace(go.Scatter(x=[x_o2], y=[p_atm], mode="markers", name="your query",
                             marker=dict(symbol="x", size=15, color="white", line=dict(width=2, color=ui.SPACE))))
    fig.update_layout(plot_bgcolor=NEVER, height=520, xaxis_title="O2 mole fraction", yaxis_title="pressure (atm)",
                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                      title=f"{fuel}, {d0:.1f} mm droplet, {diluent}" + (f" {frac:.2f}" if frac else ""))
    ui.chart(fig)
    st.caption(f"Grey = never tested. Pale wash = AMBER. {CHART_SCOPE}",
               help=CONFOUND + " Light-washed cells = inside the tested ranges but far from any single run (AMBER). "
                    + MODEL_SCOPE)

with tab_sweep:
    options = {"O2 mole fraction": "x_o2", "Pressure (atm)": "p_atm"}
    if not diluent.startswith("none"):
        options[f"{diluent} mole fraction"] = "suppressant"
    var_label = st.radio("Vary", list(options), horizontal=True)
    s = sweep(fuel, d0, p_atm, x_o2, q["x_co2"], q["x_he"], options[var_label],
              gas={"CO2": "x_co2", "He": "x_he"}.get(diluent))
    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                         subplot_titles=("Chance flame goes out early", "Burning rate K (mm²/s)"))
    fig2.add_trace(go.Scatter(x=s["x"], y=s["p_ext"], mode="lines", name="P(goes out early)",
                              line=dict(color=ui.FLAME, width=3)), 1, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K_hi"], mode="lines", line=dict(width=0), showlegend=False,
                              hoverinfo="skip"), 2, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K_lo"], mode="lines", line=dict(width=0), fill="tonexty",
                              fillcolor="rgba(92,179,255,0.22)", name="80% interval"), 2, 1)
    fig2.add_trace(go.Scatter(x=s["x"], y=s["K"], mode="lines", name="K", line=dict(color=ui.DATA, width=3)), 2, 1)
    red = s["status"].to_numpy() == 2
    step = (s["x"].iloc[1] - s["x"].iloc[0]) / 2
    start = None
    for i, r in enumerate(np.append(red, False)):
        if r and start is None:
            start = i
        elif not r and start is not None:
            fig2.add_vrect(x0=s["x"].iloc[start] - step, x1=s["x"].iloc[i - 1] + step, fillcolor=NEVER,
                           opacity=0.55, line_width=0, row="all", col=1)
            start = None
    current = {"x_o2": x_o2, "p_atm": p_atm, "suppressant": frac}[options[var_label]]
    fig2.add_vline(x=current, line_dash="dot", line_color="white")
    fig2.update_yaxes(range=[0, 1], row=1, col=1)
    fig2.update_layout(height=520, xaxis2_title=var_label, margin=dict(t=40))
    ui.chart(fig2)
    st.caption(f"Grey = never tested. Dotted line = your value. {CHART_SCOPE}", help=CONFOUND + " " + MODEL_SCOPE)

with tab_read:
    st.markdown(
        "- **GREEN / AMBER / RED** checks whether NASA tested anything like your settings. "
        "RED means the model would be extrapolating, so we do not show its numbers.\n"
        "- **Chance the flame goes out**: probability that the visible flame extinguishes before the "
        "droplet is used up. Tested honestly: when it says 90-100%, NASA's flames went out ~95% of the time. "
        f"Calibrated logistic regression; across all FLEX runs used, {base:.0%} of flames went out early.\n"
        "- **K (burning-rate constant)**: in microgravity a droplet's diameter squared shrinks linearly "
        "with time (the d² law); K is the slope. Bigger K = faster burning. The ± range contained the true "
        "value for ~80% of NASA runs from conditions the model never saw.\n"
        "- **Time to burn out** (d0²/K) is only meaningful if the flame does not go out first.\n"
        "- **Closest real runs**: the actual ISS tests with the most similar conditions, with their real "
        "outcomes - check the model against them.")
    why_and_scope()
    glossary_list(["light", "K", "d2 law", "conformal", "calibration", "outcomes", "cool flame"])
