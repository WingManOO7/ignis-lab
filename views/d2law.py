"""The d-squared law, checked on real ISS droplet recordings (independent of NASA's tabulated K)."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis import ui
from ignis.droplets import LOW_R2, WINDOW, d2_summary, droplet_index, fit_k, k_comparison, load_history, sample_line
from ignis.glossary import glossary_list

ui.page_header("d² law check",
               "We refit K from NASA's raw droplet recordings.",
               "NASA PSI-69 FLEX droplet recordings (30 fps)")

idx = droplet_index()
comp = k_comparison()
if comp.empty:
    st.warning("No droplet files found. Run: python scripts/download_psi.py --droplets 30")
    st.stop()
ok = comp.dropna(subset=["k_fit", "k_nasa"])
summ = d2_summary(comp, idx)
sample, worst = summ["sample"], summ["worst"]


def _span(rows):
    """'O2 21%-34%, 0 helium runs' for a set of index rows (computed, for the sample tooltip)."""
    return (f"O2 {rows['x_o2'].min():.0%}-{rows['x_o2'].max():.0%}, {int((rows['x_he'] > 0).sum())} helium runs"
            if len(rows) else "no joinable runs")


joined_disk, joined_all = idx[idx["on_disk"] & idx["joinable"]], idx[idx["joinable"]]
ui.note(sample_line(sample), tone="quiet",
        details=f"Files on disk: FLEX-{sample['first_flex']:03d} to FLEX-{sample['last_flex']:03d}"
                + (f", the first {sample['on_disk']} by FLEX number (the download takes index.json in order)"
                   if sample["earliest"] else "") +
                f". The {len(joined_disk)} joined ones span {_span(joined_disk)}; all {len(joined_all)} joinable "
                f"recordings span {_span(joined_all)}. Run `python scripts/download_psi.py --droplets "
                f"{sample['total']}` to check them all.")

left, right = st.columns([1, 1.9], gap="large")
with left:
    ui.readouts([{"v": f"{summ['median_gap_pct']:.1f}%" if len(ok) else "-", "tone": "flame",
                  "l": "median gap vs NASA K", "s": f"{len(ok)} droplets",
                  "t": f"Median |our K - NASA K| over {len(ok)} comparable droplets of {len(comp)} joined to "
                       f"NASA's results table ({summ['low_r2_comparable']} of them flagged low R², still counted)."},
                 {"v": f"{worst['diff_pct']:+.1f}%" if worst else "-", "tone": "ink", "l": "worst gap",
                  "s": worst["flex_id"] if worst else None,
                  "t": (f"Largest |our K - NASA K| among the {len(ok)} comparable droplets: {worst['flex_id']} "
                        f"({worst['fuel']}, {worst['test_end']}, fit R² {worst['r2']:.2f})." if worst else
                        "No comparable droplet.")}])
    labels = {f"{r.flex_id} - {r.fuel}, {r.test_end} ({r.file_name.split('_')[0]})": r.file_name
              for r in comp.itertuples()}
    # open on the 'typical' droplet: the comparable one whose |difference| is closest to the median
    typical = (ok.assign(gap=(ok["diff_pct"].abs() - ok["diff_pct"].abs().median()).abs())
               .sort_values("gap")["file_name"].iloc[0]) if len(ok) else None
    start = list(labels.values()).index(typical) if typical in labels.values() else 0
    choice = st.selectbox("Pick a real ISS droplet", list(labels), index=start, key="d2_pick",
                          help="Opens on the typical droplet: the one whose difference is closest to the median.")
    row = comp[comp["file_name"] == labels[choice]].iloc[0]
    hist = load_history(row["file_name"])
    fit = fit_k(hist, row["burn_time_s"])
    ui.readouts(size="sm", items=[
        {"v": "-" if np.isnan(row["k_nasa"]) else f"{row['k_nasa']:.3f}", "l": "NASA K (mm²/s)",
         "t": "K in NASA's results table (NASA/TP-2015-216046 Table IX)."},
        {"v": "-" if not fit else f"{fit['k_fit']:.3f}", "l": "Our K (mm²/s)",
         "s": None if (not fit or np.isnan(row["k_nasa"])) else f"{row['diff_pct']:+.1f}% vs NASA",
         "t": "Refit from NASA's raw diameter-vs-time recording."},
        {"v": "-" if not fit else f"{fit['r2']:.3f}", "tone": "ink", "l": "fit R²",
         "t": "Straight-line fit quality: 1.0 = d² falls on a perfect straight line, as the d² law predicts."}])
    if not fit:
        ui.note("Not fittable for this droplet.", tone="caution",
                details="NASA's table has no burn time for this run, or fewer than 10 frames fall in the window.")

with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["t_s"], y=hist["d2_mm2"], mode="markers", name="measured d² (NASA recording)",
                             marker=dict(size=4, color=ui.DATA)))
    if fit:
        tt = np.array([fit["t0"], fit["t1"]])
        fig.add_trace(go.Scatter(x=tt, y=fit["intercept"] - fit["k_fit"] * tt, mode="lines",
                                 name=f"our fit: K = {fit['k_fit']:.3f} mm²/s", line=dict(color=ui.FLAME, width=3)))
        fig.add_vrect(x0=fit["t0"], x1=fit["t1"], fillcolor=ui.FLAME, opacity=0.08, line_width=0,
                      annotation_text="fit window", annotation_position="top left")
    if np.isfinite(row["burn_time_s"]):
        fig.add_vline(x=row["burn_time_s"], line_dash="dot", line_color=ui.DIM, annotation_text="NASA burn end")
    fig.update_layout(xaxis_title="time (s)", yaxis_title="d² (mm²)", height=440,
                      title=f"{row['flex_id']} ({row['fuel']}, d0 {row['d0_mm']:.2f} mm, {row['test_end']})")
    ui.chart(fig)
    st.caption(f"Fit window: {WINDOW[0]:.0%}-{WINDOW[1]:.0%} of NASA's burn time.",
               help="Fixed in advance and the same for every droplet: skips ignition and heat-up, stops at visible "
                    f"extinction. Fits with R² below {LOW_R2} are flagged in the table, never refit.")

tab_all, tab_how, tab_src = st.tabs(["All droplets", "How it works", "Sources"])
with tab_all:
    fig2 = px.scatter(ok, x="k_nasa", y="k_fit", color="fuel", symbol="test_end", hover_data=["flex_id", "r2"],
                      color_discrete_sequence=[ui.DATA, ui.FLAME],
                      labels={"k_nasa": "NASA K (mm²/s)", "k_fit": "our refit K (mm²/s)"},
                      title="Our K vs NASA's K, every comparable droplet")
    lo, hi = (float(min(ok["k_nasa"].min(), ok["k_fit"].min())) * 0.95,
              float(max(ok["k_nasa"].max(), ok["k_fit"].max())) * 1.05)
    fig2.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="perfect agreement",
                              line=dict(dash="dash", color=ui.DIM)))
    fig2.update_traces(marker=dict(size=10, line=dict(width=0.5, color=ui.SPACE)), selector=dict(mode="markers"))
    fig2.update_layout(height=420)
    ui.chart(fig2)
    st.dataframe(comp[["flex_id", "fuel", "test_end", "d0_mm", "burn_time_s", "k_nasa", "k_fit", "diff_pct", "r2",
                       "flag", "n_points"]].round(3), hide_index=True, width="stretch",
                 column_config={"flag": st.column_config.TextColumn(
                     "flag", help=f"'low R²' = fit R² below {LOW_R2}: d² is not a straight line inside the fixed "
                                  "window, so this K is less reliable. The window is not changed for it, and "
                                  "comparable flagged droplets stay in the median.")})
with tab_how:
    st.markdown("In microgravity a burning droplet's **diameter squared shrinks linearly with time**: "
                "d(t)² = d₀² - K·t. NASA reports K as the slope of a straight-line fit of d² against time "
                "(NASA/TP-2015-216046). Here we refit K **ourselves** from NASA's raw diameter-vs-time recordings "
                "(30 frames per second) and compare it with the K in NASA's results table.")
    st.caption(f"Fit window fixed in advance: {WINDOW[0]:.0%}-{WINDOW[1]:.0%} of NASA's burn time (skips ignition "
               "and heat-up; stops at visible extinction - after that the droplet keeps evaporating without a visible "
               f"flame). Fits with R² below {LOW_R2} are flagged 'low R²' in the table, not refit.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Droplet files on disk", int(idx["on_disk"].sum()), help=f"of {len(idx)} available on NASA PSI")
    c2.metric("Joined to NASA's table", len(comp))
    c3.metric("Fitted and comparable", len(ok))
    c4.metric("Median |fitted - NASA| K", f"{ok['diff_pct'].abs().median():.1f}%" if len(ok) else "-")
    skipped = idx[idx["on_disk"] & ~idx["joinable"]]
    if len(skipped):
        st.caption(f"Skipped {len(skipped)} file(s) that cannot be joined to NASA's table (early runs whose folder "
                   f"ends in '_Air' carry no FLEX Identifier): "
                   f"{', '.join(skipped['file_name'].str.replace('_DropletData.txt', ''))}.")
    glossary_list(["K", "d2 law", "outcomes"])
with tab_src:
    st.caption(f"{len(ok)} of {len(comp)} joined droplets are comparable (others lack a NASA K or burn time). "
               f"{sample_line(sample)}; run `python scripts/download_psi.py --droplets {sample['total']}` for all. "
               "Source: NASA PSI-69 FLEX DropletData files; K definition from NASA/TP-2015-216046.")
