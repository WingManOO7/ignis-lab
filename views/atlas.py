"""Investigation atlas: SUMMARIZE + RANK + COMPARE every NASA PSI combustion investigation."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ignis.data import load_atlas
from ignis.scenarios import P_TOL, SCENARIOS, coverage

st.title("Investigation atlas")
st.caption("All NASA PSI Combustion Science investigations, summarized from NASA's own metadata and "
           "ranked for a crew habitat. The ranking is our transparent heuristic with adjustable "
           "weights - NOT a NASA ranking.")

atlas = pd.DataFrame(load_atlas())
atlas["phase_txt"] = atlas["phase"].apply(lambda ph: ", ".join(ph) if ph else "-")
atlas["flight"] = atlas["project_type"].str.contains("Microgravity", na=False)
atlas["tests_near"] = atlas["tests_near"].apply(lambda v: v if isinstance(v, dict) else None)

# ---------------------------------------------------------------- controls
c1, c2 = st.columns([3, 2])
skey = c1.selectbox("Habitat scenario", list(SCENARIOS), format_func=lambda k: SCENARIOS[k][0],
                    key="atlas_scenario")
need = c2.multiselect("Fire-safety need", ["prevention", "detection", "suppression"],
                      default=["prevention", "suppression"])
scenario, o2_t, p_t, _ = SCENARIOS[skey]
if st.button(f"Test this atmosphere in Predict ->  ({o2_t:.0%} O2, {p_t:.2f} atm)", type="primary"):
    st.session_state["preset"] = scenario          # Predict's preset selectbox uses key="preset"
    st.switch_page("views/predict.py")

STATUS_SCORE = {"yes": 1.0, "likely": 0.7, "partial": 0.4, "no": 0.0}   # 'unknown' is NOT scored
with st.expander("How the ranking works (weights and formula)"):
    w1, w2, w3, w4 = st.columns(4)
    w_atm = w1.slider("Tested near this atmosphere", 0.0, 1.0, 0.50, 0.05)
    w_need = w2.slider("Matches selected need", 0.0, 1.0, 0.30, 0.05)
    w_tab = w3.slider("Data availability: per-test results table", 0.0, 1.0, 0.10, 0.05,
                      help="Measures whether usable per-test data exist, not how important the research is.")
    w_flt = w4.slider("Data availability: flown in microgravity", 0.0, 1.0, 0.10, 0.05,
                      help="Flight (ISS/Cygnus) data vs ground studies - a data-type flag, not a safety value.")
    st.markdown(
        "**Relevance = 100 x (w_atm x A + w_need x N + w_table x T + w_flight x F) / sum(w)**  \n"
        f"- **A**: 1 if real tests exist near the target (within +/-{P_TOL} atm, O2 at least the target's, counted "
        "from the FLEX and ACME CFI-G tables); 0.7 if the curated O2 and pressure ranges both include it; "
        "0.4 if only one range does; 0 if neither.  \n"
        "- **N**: share of the selected needs the investigation addresses. **T**, **F**: data-availability flags.  \n"
        "- If an investigation's tested envelope has not been curated, A is **unknown**, so no relevance is "
        "computed: it is listed separately as *not enough data*, never as a low score.  \n"
        "- **Evidence completeness** = how many of 7 key fields are verified (O2 min/max, pressure min/max, "
        "table rows, outcome description, phase tag).")

wsum = max(w_atm + w_need + w_tab + w_flt, 1e-9)
cov = atlas.apply(lambda r: coverage(r, o2_t, p_t, skey), axis=1)
atlas["cov_status"], atlas["covers_target"] = cov.str[0], cov.str[1]
atlas["N"] = atlas["phase"].apply(lambda ph: sum(n in ph for n in need) / len(need) if need else 0.0)
atlas["relevance"] = [
    None if st_ == "unknown" else round(100 * (w_atm * STATUS_SCORE[st_] + w_need * n_ + w_tab * float(t_)
                                               + w_flt * float(f_)) / wsum)
    for st_, n_, t_, f_ in zip(atlas["cov_status"], atlas["N"], atlas["has_outcome_table"], atlas["flight"])]
FIELDS = ["tested_o2_min", "tested_o2_max", "tested_p_min_atm", "tested_p_max_atm", "rows", "outcomes"]
atlas["completeness"] = atlas[FIELDS].notna().sum(axis=1) + (atlas["phase_source"] == "curated").astype(int)
atlas["completeness_txt"] = atlas["completeness"].astype(str) + "/7"


def rng(lo, hi, fmt="{:.2f}"):
    if pd.isna(lo) and pd.isna(hi):
        return "-"
    return f"{'?' if pd.isna(lo) else fmt.format(lo)} - {'?' if pd.isna(hi) else fmt.format(hi)}"


atlas["O2 tested"] = [rng(a, b) for a, b in zip(atlas["tested_o2_min"], atlas["tested_o2_max"])]
atlas["P tested (atm)"] = [rng(a, b) for a, b in zip(atlas["tested_p_min_atm"], atlas["tested_p_max_atm"])]

# ---------------------------------------------------------------- filters + ranked tables
f1, f2 = st.columns([3, 1])
families = f1.multiselect("Hardware family", sorted(atlas["family"].unique()),
                          default=sorted(atlas["family"].unique()))
flight_only = f2.toggle("Flight experiments only", value=False)
view = atlas[atlas["family"].isin(families) & (atlas["flight"] | (not flight_only))]
ranked = view[view["relevance"].notna()].sort_values(["relevance", "completeness", "n_publications"],
                                                      ascending=False).reset_index(drop=True)
ranked.insert(0, "rank", ranked.index + 1)
unranked = view[view["relevance"].isna()].sort_values("completeness", ascending=False)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Investigations shown", len(view))
m2.metric("Ranked (envelope verified)", len(ranked))
m3.metric("Tested at / near target", int(view["cov_status"].isin(["yes", "likely"]).sum()))
m4.metric("NASA publications linked", int(view["n_publications"].sum()))

counted = atlas[atlas["tests_near"].notna()]
found = [(r["acronym"], r["tests_near"].get(skey, 0), r["fuel_type"]) for _, r in counted.iterrows()]
lines = "  \n".join(f"- **{a}**: {n} real tests ({fuel})" for a, n, fuel in found)
box = st.success if any(n for _, n, _ in found) else st.error
box(f"**Real microgravity flame tests near the {scenario.split(' (')[0]}** "
    f"(within +/-{P_TOL} atm, O2 at least {o2_t:.0%}), counted from NASA's experimental tables:  \n{lines}")

COLS = {"relevance": st.column_config.ProgressColumn("relevance to scenario", min_value=0, max_value=100,
                                                     format="%d"),
        "completeness": st.column_config.ProgressColumn("evidence completeness", min_value=0, max_value=7,
                                                        format="%d/7"),
        "phase_txt": "phase", "has_outcome_table": "per-test results table", "n_publications": "pubs",
        "covers_target": "tested near target?", "page": st.column_config.LinkColumn("PSI page", display_text="open")}
st.markdown("##### Ranked by relevance to this scenario")
st.dataframe(ranked[["rank", "relevance", "completeness", "acronym", "family", "phase_txt", "covers_target",
                     "O2 tested", "P tested (atm)", "has_outcome_table", "n_publications", "page"]],
             column_config=COLS, hide_index=True, width="stretch")
st.markdown(f"##### Not enough curated data to rank ({len(unranked)})")
st.caption("Their tested O2/pressure envelope has not been verified yet, so relevance is UNKNOWN - not low. "
           "Curate them in data/atlas/curation.json (with a source) to bring them into the ranking.")
st.dataframe(unranked[["completeness", "acronym", "family", "phase_txt", "fuel_type", "n_publications", "page"]],
             column_config=COLS, hide_index=True, width="stretch")
st.info("**Limitation:** only some investigations have a verified test envelope, so this ranking reflects what has "
        "been checked so far against NASA's tables and papers. It is our transparent heuristic, not a NASA ranking, "
        "and data-availability flags say nothing about how important the research is.")
export = pd.concat([ranked.assign(group="ranked"), unranked.assign(group="not enough data")])
st.download_button("Download this ranking (CSV)",
                   export[["group", "rank", "relevance", "completeness", "accession", "acronym", "title", "family",
                           "phase_txt", "covers_target", "O2 tested", "P tested (atm)", "has_outcome_table",
                           "n_publications", "page"]].to_csv(index=False),
                   file_name=f"ignis_atlas_ranking_{skey}.csv", mime="text/csv")

# ---------------------------------------------------------------- envelope / gap chart
st.subheader("Where NASA has tested - and where future habitats will live")
fig = go.Figure()
palette = ["#4FA3FF", "#FF922B", "#51CF66", "#CC5DE8", "#FFD43B", "#FF6B6B", "#22B8CF"]
boxes = atlas.dropna(subset=["tested_o2_min", "tested_o2_max", "tested_p_min_atm", "tested_p_max_atm"])
for k, (_, r) in enumerate(boxes.iterrows()):
    col = palette[k % len(palette)]
    fig.add_shape(type="rect", x0=r["tested_o2_min"], x1=r["tested_o2_max"], y0=r["tested_p_min_atm"],
                  y1=r["tested_p_max_atm"], line=dict(color=col, width=2), fillcolor=col, opacity=0.15)
    fig.add_trace(go.Scatter(x=[r["tested_o2_min"]], y=[r["tested_p_max_atm"]], mode="text",
                             text=[r["acronym"]], textposition="bottom right",
                             textfont=dict(color=col), showlegend=False, hoverinfo="skip"))
partial = atlas[atlas["tested_o2_max"].notna() & ~atlas.index.isin(boxes.index)]
fig.add_trace(go.Scatter(x=partial["tested_o2_max"],
                         y=partial["tested_p_min_atm"].fillna(1.0), mode="markers+text",
                         text=partial["acronym"], textposition="top center", name="max O2 tested (partial info)",
                         marker=dict(size=10, symbol="diamond", color="#ADB5BD")))
for _key, (name, o2, p, _src) in SCENARIOS.items():
    fig.add_trace(go.Scatter(x=[o2], y=[p], mode="markers", name=name.split(" (")[0],
                             marker=dict(size=16, symbol="star", line=dict(width=1, color="white"))))
fig.update_layout(xaxis_title="O2 mole fraction", yaxis_title="pressure (atm)", height=470,
                  legend=dict(orientation="h", y=-0.2), margin=dict(t=10))
st.plotly_chart(fig, width="stretch")
st.caption("Boxes = tested O2 x pressure ranges computed from PSI experimental tables (FLEX-2 box = design "
           "ranges). Diamonds = investigations where only the maximum O2 is known (plotted at their lowest "
           "known pressure, or 1 atm). A star outside every box is a research gap. Ranges are independent: "
           "a box does not prove every O2/pressure combination inside it was run - the green box above uses "
           "real test counts instead.")

# ---------------------------------------------------------------- summaries
st.subheader("Investigation summaries")
st.caption("Text fields come verbatim from NASA PSI metadata; envelope/outcome fields are team-verified "
           "(source shown). Rows marked 'not curated' have not been checked yet.")
for _, r in pd.concat([ranked, unranked]).iterrows():
    rel = "not enough data" if pd.isna(r["relevance"]) else f"relevance {r['relevance']:.0f}"
    with st.expander(f"{r['acronym']} - {r['title']}  ({rel}, evidence {r['completeness_txt']})"):
        a, b = st.columns([3, 2])
        a.markdown(f"**Objective.** {r['objective'] or '-'}")
        if r["approach"]:
            a.markdown(f"**Approach.** {r['approach'][:900]}{'...' if len(r['approach']) > 900 else ''}")
        b.markdown(
            f"**Accession:** [{r['accession']}]({r['page']})  \n"
            f"**Family:** {r['family']}  \n**Platform:** {r['platform']}  \n"
            f"**Hardware:** {r['hardware'] or '-'}  \n**Dates:** {r['start'] or '?'} to {r['end'] or '?'}  \n"
            f"**Fuel / sample:** {r['fuel_type'] or '-'}  \n"
            f"**O2 tested:** {r['O2 tested']} - **P tested:** {r['P tested (atm)']} atm  \n"
            f"**Covers '{scenario.split(' (')[0]}':** {r['covers_target']}  \n"
            f"**Phase:** {r['phase_txt']} ({r['phase_source']})  \n"
            f"**Outcome data:** {r['outcomes'] or 'not curated'}  \n"
            f"**DOI:** {('https://doi.org/' + r['doi']) if r['doi'] else '-'}  \n"
            f"**Licence:** {r['license'] or '-'} - **Data size:** {r['data_size_gb'] or '?'} GB")
        if r["notes"]:
            st.info(r["notes"])
        if r["publications"]:
            st.markdown(f"**Publications ({r['n_publications']}, first {len(r['publications'])}):**  \n- "
                        + "  \n- ".join(r["publications"]))
        st.caption(f"Curation source: {r['curation_source'] or 'not curated yet'}")

# ---------------------------------------------------------------- side-by-side comparison
st.subheader("Compare investigations side by side")
pick = st.multiselect("Choose 2-4 investigations", list(atlas["acronym"]),
                      default=[a for a in ["FLEX", "ACME CFI-G", "BASS-II"] if a in set(atlas["acronym"])],
                      max_selections=4)
if len(pick) >= 2:
    cols = {"family": "family", "platform": "platform", "hardware": "hardware", "fuel_type": "fuel / sample",
            "O2 tested": "O2 tested", "P tested (atm)": "P tested (atm)", "phase_txt": "phase",
            "has_outcome_table": "per-test results table", "outcomes": "outcomes", "rows": "table rows",
            "n_publications": "publications", "data_size_gb": "data size (GB)", "start": "start", "end": "end",
            "completeness_txt": "evidence completeness"}
    comp = atlas.set_index("acronym").loc[pick, list(cols)].rename(columns=cols).T.astype(str)
    st.dataframe(comp, width="stretch")
