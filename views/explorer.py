import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis import ui
from ignis.data import load_flex
from ignis.droplets import droplet_index, fit_k, load_history
from ignis.glossary import glossary_list

df = load_flex()
ui.page_header("FLEX run explorer",
               f"All {len(df)} ISS droplet fires. Click a point to open one.",
               f"NASA PSI-69 FLEX, {len(df)} ISS droplet burns")

c1, c2, c3, c4 = st.columns([1.1, 1.05, 1.95, 1.2])
fuels = c1.pills("Fuel", sorted(df["fuel"].unique()), selection_mode="multi",
                 default=sorted(df["fuel"].unique())) or []
dil = c2.pills("Diluent", ["N2", "CO2", "He"], selection_mode="multi", default=["N2", "CO2", "He"]) or []
outcomes = c3.pills("Outcome", ["Extinction", "Completion", "Disruption"], selection_mode="multi",
                    default=["Extinction", "Completion", "Disruption"]) or []
pmin, pmax = c4.slider("Pressure range (atm)", 0.0, 3.2, (0.0, 3.2), 0.05)
in_p = df["p_atm"].between(pmin, pmax) | (df["p_atm"].isna() & (pmin <= 0.0) & (pmax >= 3.2))
view = df[df["fuel"].isin(fuels) & df["diluent"].isin(dil) & df["test_end"].isin(outcomes) & in_p]

FLEX_ID_POS = 0   # custom_data=["flex_id"] puts the id first in each point's customdata (checked in tests)


def _mark(source):   # remember which input the user touched last; the most recent one wins
    st.session_state["explorer_last"] = source


left, right = st.columns([1.75, 1], gap="large")
with left:
    fig = px.scatter(view, x="x_o2", y="d0_mm", color="test_end", facet_col="fuel",
                     custom_data=["flex_id"], color_discrete_map=ui.OUTCOME_COLORS,
                     category_orders={"test_end": ["Extinction", "Completion", "Disruption"],
                                      "fuel": ["Heptane", "Methanol"]},
                     hover_data=["flex_id", "diluent", "test_date", "p_atm", "x_co2", "x_he", "k_mm2_s", "dext_mm"],
                     labels={"x_o2": "O2 mole fraction", "d0_mm": "initial droplet diameter (mm)",
                             "test_end": "outcome", "diluent": "diluent"},
                     title="Outcome by oxygen and droplet size")
    fig.update_traces(marker=dict(size=8, opacity=0.85, line=dict(width=0.5, color=ui.SPACE)))
    fig.update_layout(height=470, legend=dict(orientation="h", y=-0.16, x=0, title_text=""))
    event = ui.chart(fig, on_select=lambda: _mark("picked"), selection_mode="points", key="explorer_scatter")
    st.caption(f"{len(view)} of {len(df)} runs shown. Disruption may be needle contamination.",
               help="Disruption outcomes may be caused by needle-coating contamination (NASA/TP-2015-216046, "
                    "sec. 5.2). Pressures above 1 atm only occur together with ~70% CO2. One run (C11M201) has an "
                    "unknown pressure and only appears when the full pressure range is selected.")

picked = None
for point in (event or {}).get("selection", {}).get("points", []):
    cd = point.get("customdata")
    if cd:
        picked = cd[FLEX_ID_POS]

with right:
    ids = [""] + sorted(view["flex_id"].dropna().unique().tolist())
    typed = st.selectbox("Open a run (NASA FLEX ID)", ids, key="explorer_pick",
                         on_change=lambda: _mark("typed"), placeholder="Click a point, or pick a run")
    first, second = (picked, typed) if st.session_state.get("explorer_last") == "picked" else (typed, picked)
    run_id = first or second or None

    if not run_id:
        ui.note("Click a point or pick a run.", tone="quiet")
    else:
        run = df[df["flex_id"] == run_id]
        r0 = run.iloc[0]

        def num(v, fmt):
            return "-" if v is None or (isinstance(v, float) and np.isnan(v)) else fmt.format(v)

        ui.section(f"Run {run_id}", f"{r0['fuel']}, {r0['diluent']}, ended in {r0['test_end']}")
        ui.readouts(size="sm", cols="1fr 1fr", items=[{"v": num(r0["x_o2"], "{:.2f}"), "l": "O2 mole fraction"},
                     {"v": num(r0["p_atm"], "{:.2f}"), "u": "atm", "l": "pressure"},
                     {"v": num(r0["d0_mm"], "{:.2f}"), "u": "mm", "l": "initial diameter"},
                     {"v": num(r0["k_mm2_s"], "{:.3f}"), "u": "mm²/s", "l": "NASA K"}])
        idx = droplet_index()
        match = idx[(idx["flex_id"] == run_id) & idx["on_disk"]] if len(idx) else idx
        if len(match):
            hist = load_history(match.iloc[0]["file_name"])
            fit = fit_k(hist, r0["burn_time_s"])
            f2 = go.Figure(go.Scatter(x=hist["t_s"], y=hist["d2_mm2"], mode="markers",
                                      marker=dict(size=4, color=ui.DATA), name="measured d²"))
            if fit:
                tt = np.array([fit["t0"], fit["t1"]])
                f2.add_trace(go.Scatter(x=tt, y=fit["intercept"] - fit["k_fit"] * tt, mode="lines",
                                        name=f"fit K = {fit['k_fit']:.3f}", line=dict(width=3, color=ui.FLAME)))
            f2.update_layout(height=270, xaxis_title="time (s)", yaxis_title="d² (mm²)", margin=dict(t=36),
                             title="d² over time (NASA recording)", legend=dict(y=-0.3))
            ui.chart(f2)
            a, b = st.columns(2)
            a.metric("NASA K", "-" if np.isnan(r0["k_mm2_s"]) else f"{r0['k_mm2_s']:.3f} mm²/s")
            b.metric("Our refit K", f"{fit['k_fit']:.3f} mm²/s" if fit else "not fittable")
        else:
            st.caption("No d² recording on disk for this run.",
                       help="30 of 260 droplet recordings are downloaded - see the d² law page.")
        with st.expander("All fields for this run"):
            # one column per table row: a FLEX ID can appear twice in NASA's table (e.g. 193F001)
            cols = ["value"] if len(run) == 1 else [f"value (table row {n})" for n in run["row_no"]]
            st.dataframe(run.T.set_axis(cols, axis=1).astype(str), width="stretch")
        st.caption("Source: NASA PSI-69 FLEX table.",
                   help="NASA PSI-69 FLEX experimental table (DOI 10.60555/mbq8-0451) = NASA/TP-2015-216046 Table IX.")

tab_k, tab_table, tab_read = st.tabs(["Burning rate vs oxygen", "All shown runs", "How to read this"])
with tab_k:
    fig2 = px.scatter(view.dropna(subset=["k_mm2_s"]), x="x_o2", y="k_mm2_s", color="diluent",
                      facet_col="fuel", hover_data=["flex_id"],
                      category_orders={"diluent": ["N2", "CO2", "He"], "fuel": ["Heptane", "Methanol"]},
                      color_discrete_sequence=[ui.DATA, ui.FLAME, "#B39DFF"],
                      labels={"k_mm2_s": "burning-rate constant K (mm²/s)", "x_o2": "O2 mole fraction"},
                      title="Burning rate vs oxygen")
    fig2.update_layout(height=420)
    ui.chart(fig2)
with tab_table:
    st.download_button("Download shown runs (CSV)", view.to_csv(index=False),
                       file_name="flex_filtered_runs.csv", mime="text/csv", icon=":material/download:")
    st.dataframe(view, hide_index=True)
with tab_read:
    st.markdown("- **Each point** is one droplet fire on the ISS. Colour = how it ended; hover for the added gas.\n"
                "- **Left panel per fuel**: oxygen level across, starting droplet size up.")
    glossary_list(["outcomes", "K", "d2 law"])
