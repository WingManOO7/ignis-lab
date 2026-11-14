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
with st.expander("Ranking weights and formula (transparent by design)"):
    w1, w2, w3, w4 = st.columns(4)
    w_atm = w1.slider("Tested near this atmosphere", 0.0, 1.0, 0.40, 0.05)
    w_out = w2.slider("Per-test outcome table", 0.0, 1.0, 0.25, 0.05)
    w_need = w3.slider("Matches selected need", 0.0, 1.0, 0.25, 0.05)
    w_flt = w4.slider("Flown in microgravity", 0.0, 1.0, 0.10, 0.05)
    st.markdown(
        "**score = 100 x (w_atm x A + w_out x O + w_need x N + w_flight x F) / sum(w)**, where  \n"
        f"A = 1 if real tests exist near the target (within +/-{P_TOL} atm, O2 at least the target's; "
        "counted from the experimental tables for FLEX and ACME CFI-G). Otherwise A = mean of "
        "min(1, O2_max_tested / O2_target) and min(1, P_target / P_min_tested), halved when the table shows "
        "no real test there, 0 if the envelope is not curated yet - O = 1 if a per-test outcome table exists - "
        "N = share of the selected needs the investigation addresses - F = 1 for ISS/Cygnus flight data.")


def range_score(row):
    parts = []
    if pd.notna(row["tested_o2_max"]):
        parts.append(min(1.0, row["tested_o2_max"] / o2_t))
    if pd.notna(row["tested_p_min_atm"]):
        parts.append(min(1.0, p_t / row["tested_p_min_atm"]))
    return sum(parts) / 2 if parts else 0.0      # missing half counts as 0: unknown is not "covered"


def atm_component(row):
    near = row["tests_near"]
    if near is None:
        return range_score(row)
    return 1.0 if near.get(skey, 0) > 0 else 0.5 * range_score(row)   # ranges overlap but no real test


wsum = max(w_atm + w_out + w_need + w_flt, 1e-9)
atlas["A"] = atlas.apply(atm_component, axis=1)
atlas["N"] = atlas["phase"].apply(lambda ph: sum(n in ph for n in need) / len(need) if need else 0.0)
atlas["score"] = (100 * (w_atm * atlas["A"] + w_out * atlas["has_outcome_table"].astype(float)
                         + w_need * atlas["N"] + w_flt * atlas["flight"].astype(float)) / wsum).round(0)
atlas["covers_target"] = atlas.apply(lambda r: coverage(r, o2_t, p_t, skey)[1], axis=1)


def rng(lo, hi, fmt="{:.2f}"):
    if pd.isna(lo) and pd.isna(hi):
        return "-"
    return f"{'?' if pd.isna(lo) else fmt.format(lo)} - {'?' if pd.isna(hi) else fmt.format(hi)}"


atlas["O2 tested"] = [rng(a, b) for a, b in zip(atlas["tested_o2_min"], atlas["tested_o2_max"])]
atlas["P tested (atm)"] = [rng(a, b) for a, b in zip(atlas["tested_p_min_atm"], atlas["tested_p_max_atm"])]

# ---------------------------------------------------------------- filters + ranked table
f1, f2 = st.columns([3, 1])
families = f1.multiselect("Hardware family", sorted(atlas["family"].unique()),
                          default=sorted(atlas["family"].unique()))
flight_only = f2.toggle("Flight experiments only", value=False)
view = atlas[atlas["family"].isin(families) & (atlas["flight"] | (not flight_only))]
view = view.sort_values(["score", "n_publications"], ascending=False).reset_index(drop=True)
view.insert(0, "rank", view.index + 1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Investigations shown", len(view))
m2.metric("Tested at/beyond target", int(view["covers_target"].str.startswith("YES").sum()))
m3.metric("With per-test outcome tables", int(view["has_outcome_table"].sum()))
m4.metric("NASA publications linked", int(view["n_publications"].sum()))

counted = atlas[atlas["tests_near"].notna()]
found = [(r["acronym"], r["tests_near"].get(skey, 0), r["fuel_type"]) for _, r in counted.iterrows()]
lines = "  \n".join(f"- **{a}**: {n} real tests ({fuel})" for a, n, fuel in found)
box = st.success if any(n for _, n, _ in found) else st.error
box(f"**Real microgravity flame tests near the {scenario.split(' (')[0]}** "
    f"(within +/-{P_TOL} atm, O2 at least {o2_t:.0%}), counted from NASA's experimental tables:  \n{lines}")

st.dataframe(
    view[["rank", "score", "acronym", "family", "phase_txt", "covers_target", "O2 tested",
          "P tested (atm)", "has_outcome_table", "n_publications", "page"]],
    column_config={
        "score": st.column_config.ProgressColumn("score", min_value=0, max_value=100, format="%d"),
        "phase_txt": "phase", "has_outcome_table": "outcome table", "n_publications": "pubs",
        "page": st.column_config.LinkColumn("PSI page", display_text="open")},
    hide_index=True, width="stretch")

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
                             marker=dict(size=16, symbol="star",
                                         line=dict(width=1, color="white"))))
fig.update_layout(xaxis_title="O2 mole fraction", yaxis_title="pressure (atm)", height=470,
                  legend=dict(orientation="h", y=-0.2), margin=dict(t=10))
st.plotly_chart(fig, width="stretch")
st.caption("Boxes = tested O2 x pressure ranges computed from PSI experimental tables (FLEX-2 box = design "
           "ranges). Diamonds = investigations where only the maximum O2 is known (plotted at their lowest "
           "known pressure, or 1 atm). A star outside every box is a research gap. Ranges are independent: "
           "a box does not prove every O2/pressure combination inside it was run.")

# ---------------------------------------------------------------- summaries
st.subheader("Investigation summaries")
st.caption("Text fields come verbatim from NASA PSI metadata; envelope/outcome fields are team-verified "
           "(source shown). Rows marked 'not curated' have not been checked yet.")
for _, r in view.iterrows():
    with st.expander(f"#{r['rank']}  {r['acronym']} - {r['title']}  (score {r['score']:.0f})"):
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
            "has_outcome_table": "outcome table", "outcomes": "outcomes", "rows": "table rows",
            "n_publications": "publications", "data_size_gb": "data size (GB)", "start": "start", "end": "end"}
    comp = atlas.set_index("acronym").loc[pick, list(cols)].rename(columns=cols).T.astype(str)
    st.dataframe(comp, width="stretch")
