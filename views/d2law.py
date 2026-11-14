"""The d-squared law, checked on real ISS droplet recordings (independent of NASA's tabulated K)."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis.droplets import WINDOW, droplet_index, fit_k, k_comparison, load_history
from ignis.glossary import glossary_panel

st.title("The d² law on real ISS droplets")
st.markdown("In microgravity a burning droplet's **diameter squared shrinks linearly with time**: "
            "d(t)² = d₀² - K·t. NASA reports K as the slope of a straight-line fit of d² against time "
            "(NASA/TP-2015-216046). Here we refit K **ourselves** from NASA's raw diameter-vs-time recordings "
            "(30 frames per second) and compare it with the K in NASA's results table.")

idx = droplet_index()
comp = k_comparison()
if comp.empty:
    st.warning("No droplet files found. Run: python scripts/download_psi.py --droplets 30")
    st.stop()
ok = comp.dropna(subset=["k_fit", "k_nasa"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Droplet files on disk", int(idx["on_disk"].sum()), help=f"of {len(idx)} available on NASA PSI")
c2.metric("Joined to NASA's table", len(comp))
c3.metric("Fitted and comparable", len(ok))
c4.metric("Median |fitted - NASA| K", f"{ok['diff_pct'].abs().median():.1f}%" if len(ok) else "-")
skipped = idx[idx["on_disk"] & ~idx["joinable"]]
if len(skipped):
    st.caption(f"Skipped {len(skipped)} file(s) that cannot be joined to NASA's table (early runs whose folder ends "
               f"in '_Air' carry no FLEX Identifier): {', '.join(skipped['file_name'].str.replace('_DropletData.txt', ''))}.")

# ---------------------------------------------------------------- one droplet
labels = {f"{r.flex_id} - {r.fuel}, {r.test_end} ({r.file_name.split('_')[0]})": r.file_name
          for r in comp.itertuples()}
choice = st.selectbox("Pick a real ISS droplet", list(labels), key="d2_pick")
row = comp[comp["file_name"] == labels[choice]].iloc[0]
hist = load_history(row["file_name"])
fit = fit_k(hist, row["burn_time_s"])

fig = go.Figure()
fig.add_trace(go.Scatter(x=hist["t_s"], y=hist["d2_mm2"], mode="markers", name="measured d² (NASA recording)",
                         marker=dict(size=4, color="#4FA3FF")))
if fit:
    tt = np.array([fit["t0"], fit["t1"]])
    fig.add_trace(go.Scatter(x=tt, y=fit["intercept"] - fit["k_fit"] * tt, mode="lines",
                             name=f"our fit: K = {fit['k_fit']:.3f} mm²/s", line=dict(color="#FF922B", width=3)))
    fig.add_vrect(x0=fit["t0"], x1=fit["t1"], fillcolor="#FF922B", opacity=0.08, line_width=0,
                  annotation_text="fit window", annotation_position="top left")
if np.isfinite(row["burn_time_s"]):
    fig.add_vline(x=row["burn_time_s"], line_dash="dot", annotation_text="NASA burn end")
fig.update_layout(xaxis_title="time (s)", yaxis_title="d² (mm²)", height=430, legend=dict(orientation="h", y=-0.2),
                  title=f"{row['flex_id']} ({row['fuel']}, d0 {row['d0_mm']:.2f} mm, {row['test_end']})")
st.plotly_chart(fig, width="stretch")
a, b, c = st.columns(3)
a.metric("NASA K (results table)", "-" if np.isnan(row["k_nasa"]) else f"{row['k_nasa']:.3f} mm²/s")
b.metric("Our K (refit from recording)", "-" if not fit else f"{fit['k_fit']:.3f} mm²/s",
         delta=None if (not fit or np.isnan(row["k_nasa"])) else f"{row['diff_pct']:+.1f}% vs NASA",
         delta_color="off")
c.metric("Straight-line fit quality (R²)", "-" if not fit else f"{fit['r2']:.3f}",
         help="1.0 = d² falls on a perfect straight line, as the d² law predicts.")
if not fit:
    st.info("Not fittable: NASA's table has no burn time for this run, or fewer than 10 frames fall in the window.")
st.caption(f"Fit window fixed in advance: {WINDOW[0]:.0%}-{WINDOW[1]:.0%} of NASA's burn time (skips ignition and "
           "heat-up; stops at visible extinction - after that the droplet keeps evaporating without a visible flame). "
           "Low R² usually marks a Disruption run, where the droplet broke apart.")

# ---------------------------------------------------------------- all droplets
st.subheader("Our K vs NASA's K, every comparable droplet")
fig2 = px.scatter(ok, x="k_nasa", y="k_fit", color="fuel", symbol="test_end", hover_data=["flex_id", "r2"],
                  labels={"k_nasa": "NASA K (mm²/s)", "k_fit": "our refit K (mm²/s)"})
lo, hi = float(min(ok["k_nasa"].min(), ok["k_fit"].min())) * 0.95, float(max(ok["k_nasa"].max(), ok["k_fit"].max())) * 1.05
fig2.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="perfect agreement",
                          line=dict(dash="dash", color="gray")))
fig2.update_layout(height=420)
st.plotly_chart(fig2, width="stretch")
st.dataframe(comp[["flex_id", "fuel", "test_end", "d0_mm", "burn_time_s", "k_nasa", "k_fit", "diff_pct", "r2",
                   "n_points"]].round(3), hide_index=True, width="stretch")
st.caption(f"{len(ok)} of {len(comp)} joined droplets are comparable (others lack a NASA K or burn time). "
           "Only 30 of 260 recordings are downloaded; run `python scripts/download_psi.py --droplets 260` for all. "
           "Source: NASA PSI-69 FLEX DropletData files; K definition from NASA/TP-2015-216046.")
glossary_panel(["K", "d2 law", "outcomes"])
