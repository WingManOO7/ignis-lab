"""Investigation atlas: SUMMARIZE + RANK + COMPARE every NASA PSI combustion investigation."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ignis import ui
from ignis.data import load_atlas, load_summaries
from ignis.scenarios import P_TOL, SCENARIOS, coverage

# ---------------------------------------------------------------- honesty helpers (pure; tests/test_honesty.py)
# Phenomenon tag: what kind of experiment an investigation is, derived ONLY from existing NASA PSI fields
# (project_type, family, fuel_type), so a relevance score never silently compares a droplet with a fabric fire.
# First matching rule wins (field, lower-case text it contains, tag):
PHENOMENON_RULES = [
    ("project_type", "ground", "modelling/ground"),   # ground or modelling study: no new microgravity tests
    ("family", "ground", "modelling/ground"),
    ("family", "smoke", "smoke/aerosol"),             # SAME, SAME-R, DAFT: smoke or dust detection, no flame studied
    ("family", "droplet", "droplet"),                 # FLEX, FLEX-2, CFI: free liquid fuel droplets
    ("family", "large-scale fires", "solid fuel"),    # Saffire: large solid samples in a Cygnus vehicle
    ("family", "acme gas flames", "gas flame"),       # ACME: gaseous-fuel burners (BRE emulates a solid with gas)
    ("fuel_type", "solid", "solid fuel"),             # BASS, BASS-II in the MSG flow duct
    ("fuel_type", "gas", "gas flame"),                # SLICE, SPICE gas jets in the MSG flow duct
]
PHENOMENA = ("droplet", "gas flame", "solid fuel", "smoke/aerosol", "modelling/ground")
PHENOMENON_HELP = ("What kind of experiment this is, from NASA PSI's project type, family and fuel/sample fields: "
                   "droplet = liquid fuel droplets; gas flame = gaseous-fuel burners and gas jets; solid fuel = solid "
                   "materials burned; smoke/aerosol = smoke or dust detection, no flame studied; modelling/ground = "
                   "ground or modelling study, no new microgravity tests.")


def phenomenon(r):
    """Phenomenon tag of one investigation (dict or row); 'unclassified' if no rule matches."""
    for field, text, tag in PHENOMENON_RULES:
        if text in str(r.get(field) or "").lower():
            return tag
    return "unclassified"


# The 7 evidence-completeness fields and the short word shown when one is empty (we never fill them in).
COMPLETENESS_WORDS = {"tested_o2_min": "O2 min", "tested_o2_max": "O2 max", "tested_p_min_atm": "P min",
                      "tested_p_max_atm": "P max", "rows": "table rows", "outcomes": "outcomes"}


def _blank(v):
    return (isinstance(v, str) and not v.strip()) or (pd.api.types.is_scalar(v) and pd.isna(v))


def missing_fields(r):
    """Short names of the empty completeness fields of one investigation, in a fixed order; the 7th is the phase
    tag, which counts only when curated."""
    out = [word for field, word in COMPLETENESS_WORDS.items() if _blank(r.get(field))]
    return out + ([] if r.get("phase_source") == "curated" else ["phase tag"])


ui.page_header("Investigation atlas",
               "NASA's fire experiments in orbit. Pick a habitat and see which ones speak to it.",
               f"NASA PSI metadata, {len(load_atlas())} combustion investigations")

atlas = pd.DataFrame(load_atlas())
for col in atlas.columns:            # pandas 3 reads JSON nulls in text columns as NaN, which is truthy
    if atlas[col].dtype == object or str(atlas[col].dtype).startswith("str"):
        atlas[col] = atlas[col].astype(object).where(atlas[col].notna(), None)
atlas["phase_txt"] = atlas["phase"].apply(lambda ph: ", ".join(ph) if ph else "-")
atlas["flight"] = atlas["project_type"].str.contains("Microgravity", na=False)
atlas["tests_near"] = atlas["tests_near"].apply(lambda v: v if isinstance(v, dict) else None)
atlas["phenomenon"] = atlas.apply(phenomenon, axis=1)

# ---------------------------------------------------------------- controls
c1, c2, c3 = st.columns([2.2, 2, 1.5], vertical_alignment="bottom")
skey = c1.selectbox("Habitat scenario", list(SCENARIOS), format_func=lambda k: SCENARIOS[k][0],
                    key="atlas_scenario")
need = c2.pills("Fire-safety need", ["prevention", "detection", "suppression"], selection_mode="multi",
                default=["prevention", "suppression"]) or []
scenario, o2_t, p_t, _ = SCENARIOS[skey]
if c3.button("Try it in Predict", type="primary", icon=":material/online_prediction:", width="stretch",
             help=f"Opens Predict with this atmosphere: {o2_t:.0%} O2, {p_t:.2f} atm."):
    st.session_state["preset"] = scenario          # Predict's preset selectbox uses key="preset"
    st.switch_page("views/predict.py")

hero = st.container()
counted = atlas[atlas["tests_near"].notna()]
# Ranked = a verified test envelope exists (scenario-independent); everything else is 'not enough data'.
cov = atlas.apply(lambda r: coverage(r, o2_t, p_t, skey), axis=1)
atlas["cov_status"], atlas["covers_target"] = cov.str[0], cov.str[1]
N_ALL = len(atlas)
N_RANKED = int((atlas["cov_status"] != "unknown").sum())
N_UNRANKED = N_ALL - N_RANKED
atlas["doi_url"] = atlas["doi"].apply(lambda d: f"https://doi.org/{d}" if d else None)
tab_env, tab_unranked, tab_sum, tab_cmp, tab_how = st.tabs(
    ["Tested envelope", f"Not enough data ({N_UNRANKED})", "Summaries", "Compare", "How the ranking works"])

STATUS_SCORE = {"yes": 1.0, "likely": 0.7, "partial": 0.4, "no": 0.0}   # 'unknown' is NOT scored
with tab_how:
    st.caption("Move the weights; the ranking above updates.")
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
    st.info("**Limitation:** only some investigations have a verified test envelope, so this ranking reflects what has "
            "been checked so far against NASA's tables and papers. It is our transparent heuristic, not a NASA ranking, "
            "and data-availability flags say nothing about how important the research is.")

wsum = max(w_atm + w_need + w_tab + w_flt, 1e-9)
atlas["N"] = atlas["phase"].apply(lambda ph: sum(n in ph for n in need) / len(need) if need else 0.0)
atlas["relevance"] = [
    None if st_ == "unknown" else round(100 * (w_atm * STATUS_SCORE[st_] + w_need * n_ + w_tab * float(t_)
                                               + w_flt * float(f_)) / wsum)
    for st_, n_, t_, f_ in zip(atlas["cov_status"], atlas["N"], atlas["has_outcome_table"], atlas["flight"])]
atlas["missing"] = atlas.apply(missing_fields, axis=1)       # completeness and 'what is missing' share one rule
atlas["completeness"] = 7 - atlas["missing"].str.len()
atlas["missing_txt"] = atlas["missing"].apply(lambda m: ", ".join(m) or "-")
atlas["completeness_txt"] = atlas["completeness"].astype(str) + "/7"


def rng(lo, hi, fmt="{:.2f}"):
    if pd.isna(lo) and pd.isna(hi):
        return "-"
    return f"{'?' if pd.isna(lo) else fmt.format(lo)} - {'?' if pd.isna(hi) else fmt.format(hi)}"


atlas["O2 tested"] = [rng(a, b) for a, b in zip(atlas["tested_o2_min"], atlas["tested_o2_max"])]
atlas["P tested (atm)"] = [rng(a, b) for a, b in zip(atlas["tested_p_min_atm"], atlas["tested_p_max_atm"])]

COLS = {"relevance": st.column_config.ProgressColumn("relevance to scenario", min_value=0, max_value=100,
                                                     format="%d", color=ui.DATA),
        "completeness": st.column_config.ProgressColumn("evidence completeness", min_value=0, max_value=7,
                                                        format="%d/7", color="#9FB3D1"),
        "phase_txt": "phase", "has_outcome_table": "per-test table", "n_publications": "pubs",
        "phenomenon": st.column_config.TextColumn("phenomenon", help=PHENOMENON_HELP),
        "missing_txt": st.column_config.TextColumn("what is missing", width="medium",
                                                   help="Which of the 7 evidence-completeness fields are empty: O2 "
                                                        "min/max and P min/max = tested envelope, table rows, "
                                                        "outcomes, phase tag (not curated). Never filled in by us."),
        "covers_target": "tested near target?",
        "page": st.column_config.LinkColumn("PSI source", display_text="open",
                                            help="The investigation's page in NASA's PSI repository"),
        "doi_url": st.column_config.LinkColumn("dataset DOI", display_text="doi",
                                               help="Persistent DOI of the NASA PSI dataset"),
        "curation_source": st.column_config.TextColumn("verified from", width="medium",
                                                       help="The PSI table columns or NASA documents the envelope "
                                                            "and outcome facts were checked against")}

# ---------------------------------------------------------------- hero: research gap + ranked table
with hero:
    short = scenario.split(" (")[0]
    found = [(r["acronym"], r["tests_near"].get(skey, 0), r["fuel_type"]) for _, r in counted.iterrows()]
    cells = [{"v": str(n), "l": f"{a} tests nearby", "t": f"{a}: {fuel}",
              "tone": "data" if n else "flame"} for a, n, fuel in found]
    gap = not any(n for _, n, _ in found)
    ui.section("Real flame tests near this habitat",
               help=f"Microgravity flame tests within +/-{P_TOL} atm and with O2 at least {o2_t:.0%}, counted "
                    "from NASA's per-test experimental tables (FLEX, ACME CFI-G).")
    ui.readouts(cells)
    if gap:
        ui.note("**Research gap:** no per-test NASA flame data here.", tone="caution")

    t1, t2, t3 = st.columns([4.4, 1.05, 1.25], vertical_alignment="bottom")
    with t2.popover("Filters", icon=":material/filter_list:", width="stretch"):
        families = st.multiselect("Hardware family", sorted(atlas["family"].unique()),
                                  default=sorted(atlas["family"].unique()))
        flight_only = st.toggle("Flight experiments only", value=False)
    view = atlas[atlas["family"].isin(families) & (atlas["flight"] | (not flight_only))]
    ranked = view[view["relevance"].notna()].sort_values(["relevance", "completeness", "n_publications"],
                                                          ascending=False).reset_index(drop=True)
    ranked.insert(0, "rank", ranked.index + 1)
    unranked = view[view["relevance"].isna()].sort_values("completeness", ascending=False)
    with t1:
        ui.section(f"Ranked for the {short}", f"{len(ranked)} of {len(view)} ranked",
                   help=f"{len(ranked)} of {len(view)} shown have a verified test envelope; "
                        f"{int(view['cov_status'].isin(['yes', 'likely']).sum())} tested at or near this "
                        f"atmosphere; {int(view['n_publications'].sum())} NASA publications linked.")
    export = pd.concat([ranked.assign(group="ranked"), unranked.assign(group="not enough data")])
    t3.download_button("Download CSV",
                       export[["group", "rank", "relevance", "completeness", "missing_txt", "accession", "acronym",
                               "title", "phenomenon", "family", "phase_txt", "covers_target", "O2 tested",
                               "P tested (atm)", "has_outcome_table", "n_publications", "page", "doi_url",
                               "curation_source"]].to_csv(index=False),
                       file_name=f"ignis_atlas_ranking_{skey}.csv", mime="text/csv", icon=":material/download:",
                       width="stretch")
    ui.note(f"**Coverage:** only investigations with verified evidence are ranked: **{N_RANKED} of {N_ALL}**. "
            f"The other **{N_UNRANKED}** are listed under *Not enough data* (information missing or unverified): "
            "relevance unknown, not low.", tone="info",
            details="Ranked = a tested oxygen/pressure envelope verified against a PSI experimental table or a quoted "
                    "NASA document (source shown in 'verified from'). Investigations without one get no relevance "
                    "score at all, so a missing fact can never look like low relevance.")
    ui.note("Relevance compares experiments of different kinds; read the **phenomenon** tag.", tone="caution",
            details="A gas-flame burner, a fuel droplet and a burning fabric can all score high for the same "
                    "atmosphere; what they show about a cabin fire differs. " + PHENOMENON_HELP)
    st.dataframe(ranked[["rank", "relevance", "completeness", "acronym", "phenomenon", "family", "phase_txt",
                         "covers_target", "O2 tested", "P tested (atm)", "has_outcome_table", "n_publications",
                         "page", "doi_url", "curation_source"]],
                 column_config=COLS, hide_index=True, width="stretch", height=min(38 + 35 * len(ranked), 400))
    st.caption("Our heuristic, **not a NASA ranking**.",
               help=f"A transparent heuristic with adjustable weights (see How the ranking works). {len(unranked)} "
                    "investigations without a verified test envelope are under Not enough data: unknown, never "
                    "scored low. Only some investigations have a verified envelope, so the ranking reflects what "
                    "has been checked so far; data-availability flags say nothing about how important the research is.")

# ---------------------------------------------------------------- envelope / gap chart
with tab_env:
    fig = go.Figure()
    palette = [ui.DATA, ui.FLAME, "#B39DFF", "#3FD6C5", "#E8C872", "#FF8FB8", "#9FB3D1"]
    boxes = atlas.dropna(subset=["tested_o2_min", "tested_o2_max", "tested_p_min_atm", "tested_p_max_atm"])
    for k, (_, r) in enumerate(boxes.iterrows()):
        col = palette[k % len(palette)]
        fig.add_shape(type="rect", x0=r["tested_o2_min"], x1=r["tested_o2_max"], y0=r["tested_p_min_atm"],
                      y1=r["tested_p_max_atm"], line=dict(color=col, width=2), fillcolor=col, opacity=0.15)
        fig.add_trace(go.Scatter(x=[r["tested_o2_min"]], y=[r["tested_p_max_atm"]], mode="text",
                                 text=[r["acronym"]], textposition="bottom right",
                                 textfont=dict(color=col, size=13), showlegend=False, hoverinfo="skip"))
    partial = atlas[atlas["tested_o2_max"].notna() & ~atlas.index.isin(boxes.index)]
    fig.add_trace(go.Scatter(x=partial["tested_o2_max"],
                             y=partial["tested_p_min_atm"].fillna(1.0), mode="markers+text",
                             text=partial["acronym"], textposition="top center", name="max O2 tested (partial info)",
                             marker=dict(size=10, symbol="diamond", color="#9FB3D1")))
    star_colors = {"iss": "#FFFFFF", "lunar": "#FFD696", "exploration": ui.FLAME}
    for _key, (name, o2, p, _src) in SCENARIOS.items():
        fig.add_trace(go.Scatter(x=[o2], y=[p], mode="markers", name=name.split(" (")[0],
                                 marker=dict(size=18 if _key == skey else 14, symbol="star",
                                             color=star_colors.get(_key, "#FFFFFF"),
                                             line=dict(width=1.5, color=ui.SPACE))))
    fig.update_layout(xaxis_title="O2 mole fraction", yaxis_title="pressure (atm)", height=470,
                      title="Where NASA tested vs where habitats will live")
    ui.chart(fig)
    st.caption("A star outside every box = a research gap.",
               help="Boxes = tested O2 x pressure ranges computed from PSI experimental tables (FLEX-2 box = design "
                    "ranges). Diamonds = investigations where only the maximum O2 is known (plotted at their lowest "
                    "known pressure, or 1 atm). Ranges are independent: a box does not prove every O2/pressure "
                    "combination inside it was run - the test counts above use real per-test data instead.")

with tab_unranked:
    st.caption(f"{len(unranked)} investigations: relevance unknown, not low.",
               help="Their tested O2/pressure envelope has not been verified yet, so relevance is UNKNOWN - not low. "
                    "Curate them in data/atlas/curation.json (with a source) to bring them into the ranking.")
    st.dataframe(unranked[["completeness", "acronym", "phenomenon", "missing_txt", "family", "phase_txt", "fuel_type",
                           "n_publications", "page", "doi_url"]],
                 column_config=COLS, hide_index=True, width="stretch")

# ---------------------------------------------------------------- summaries
with tab_sum:
    st.caption("Verbatim NASA PSI metadata plus team-verified fields.",
               help="Text fields come verbatim from NASA PSI metadata; envelope/outcome fields are team-verified "
                    "(source shown). Rows marked 'not curated' have not been checked yet.")
    summaries = load_summaries()
    for _, r in pd.concat([ranked, unranked]).iterrows():
        rel = "not enough data" if pd.isna(r["relevance"]) else f"relevance {r['relevance']:.0f}"
        with st.expander(f"{r['acronym']} - {r['title']}  ({rel}, evidence {r['completeness_txt']})"):
            ai = summaries.get(r["accession"], {}).get("summary")
            if ai:
                st.markdown("**AI-generated summary of NASA metadata:**")
                st.text(ai)
                st.caption(f"AI-generated offline by {summaries[r['accession']].get('model', 'an LLM')}, reviewed by "
                           "the team; automatic citation, number and keyword check against the NASA text below - not a "
                           "guarantee. NASA's original text follows.")
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
                f"**Covers '{short}':** {r['covers_target']}  \n"
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
with tab_cmp:
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
    else:
        st.caption("Pick at least two investigations to compare them.")
