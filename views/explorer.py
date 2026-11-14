import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis.data import load_flex
from ignis.droplets import droplet_index, fit_k, load_history
from ignis.glossary import glossary_panel

st.title("FLEX run explorer - 274 real ISS droplet burns")
st.caption("Every row is one droplet fire on the ISS (NASA PSI-69 = NASA/TP-2015-216046 Table IX). "
           "Click a point to inspect that run.")
df = load_flex()

c1, c2, c3 = st.columns(3)
fuels = c1.multiselect("Fuel", sorted(df["fuel"].unique()), default=sorted(df["fuel"].unique()))
dil = c2.multiselect("Diluent", ["N2", "CO2", "He"], default=["N2", "CO2", "He"])
outcomes = c3.multiselect("Outcome", ["Extinction", "Completion", "Disruption"],
                          default=["Extinction", "Completion", "Disruption"])
pmin, pmax = st.slider("Pressure range (atm)", 0.0, 3.2, (0.0, 3.2), 0.05)
in_p = df["p_atm"].between(pmin, pmax) | (df["p_atm"].isna() & (pmin <= 0.0) & (pmax >= 3.2))
view = df[df["fuel"].isin(fuels) & df["diluent"].isin(dil) & df["test_end"].isin(outcomes) & in_p]
st.caption(f"{len(view)} of {len(df)} runs shown. One run (C11M201) has an unknown pressure and only appears when "
           "the full pressure range is selected.")

FLEX_ID_POS = 0   # custom_data=["flex_id"] puts the id first in each point's customdata (checked in tests)
fig = px.scatter(view, x="x_o2", y="d0_mm", color="test_end", symbol="diluent", facet_col="fuel",
                 custom_data=["flex_id"],
                 hover_data=["flex_id", "test_date", "p_atm", "x_co2", "x_he", "k_mm2_s", "dext_mm"],
                 labels={"x_o2": "O2 mole fraction", "d0_mm": "initial droplet diameter (mm)"},
                 title="Outcome of every run by oxygen level and droplet size (click a point)")
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="explorer_scatter", width="stretch")

picked = None
for point in (event or {}).get("selection", {}).get("points", []):
    cd = point.get("customdata")
    if cd:
        picked = cd[FLEX_ID_POS]
ids = [""] + sorted(view["flex_id"].dropna().unique().tolist())
typed = st.selectbox("...or pick a run by its NASA FLEX Identifier", ids, key="explorer_pick")
run_id = picked or typed or None

if run_id:
    run = df[df["flex_id"] == run_id]
    st.subheader(f"Run {run_id}")
    st.dataframe(run.T.rename(columns=lambda _: "value").astype(str), width="stretch")
    st.caption("Source: NASA PSI-69 FLEX experimental table (DOI 10.60555/mbq8-0451) = NASA/TP-2015-216046 Table IX.")
    idx = droplet_index()
    match = idx[(idx["flex_id"] == run_id) & idx["on_disk"]] if len(idx) else idx
    if len(match):
        r0 = run.iloc[0]
        hist = load_history(match.iloc[0]["file_name"])
        fit = fit_k(hist, r0["burn_time_s"])
        f2 = go.Figure(go.Scatter(x=hist["t_s"], y=hist["d2_mm2"], mode="markers", marker=dict(size=4),
                                  name="measured d²"))
        if fit:
            tt = np.array([fit["t0"], fit["t1"]])
            f2.add_trace(go.Scatter(x=tt, y=fit["intercept"] - fit["k_fit"] * tt, mode="lines",
                                    name=f"fit K = {fit['k_fit']:.3f}", line=dict(width=3)))
        f2.update_layout(height=320, xaxis_title="time (s)", yaxis_title="d² (mm²)", margin=dict(t=30),
                         title="Droplet diameter² over time (NASA recording)")
        st.plotly_chart(f2, width="stretch")
        a, b = st.columns(2)
        a.metric("NASA K", "-" if np.isnan(r0["k_mm2_s"]) else f"{r0['k_mm2_s']:.3f} mm²/s")
        b.metric("Our refit K", f"{fit['k_fit']:.3f} mm²/s" if fit else "not fittable")
    else:
        st.caption("No droplet recording downloaded for this run (30 of 260 are on disk) - see the d² law page.")

fig2 = px.scatter(view.dropna(subset=["k_mm2_s"]), x="x_o2", y="k_mm2_s", color="diluent",
                  facet_col="fuel", hover_data=["flex_id"],
                  labels={"k_mm2_s": "burning-rate constant K (mm²/s)", "x_o2": "O2 mole fraction"},
                  title="Burning rate vs oxygen")
st.plotly_chart(fig2, width="stretch")
st.caption("Disruption outcomes may be caused by needle-coating contamination (NASA/TP-2015-216046, sec. 5.2). "
           "Pressures above 1 atm only occur together with ~70% CO2.")
st.download_button("Download the filtered runs (CSV)", view.to_csv(index=False), file_name="flex_filtered_runs.csv",
                   mime="text/csv")
st.dataframe(view, hide_index=True)
glossary_panel(["outcomes", "K", "d2 law"])
