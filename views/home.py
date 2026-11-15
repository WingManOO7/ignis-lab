import streamlit as st

from ignis import ui
from ignis.data import load_atlas, load_cv, load_flex, load_models
from ignis.droplets import k_comparison
from ignis.messages import scope_note, why_and_scope
from ignis.tour import start_tour, steps

flex, atlas, cv, meta = load_flex(), load_atlas(), load_cv(), load_models()["clf"]["meta"]
near = {a["acronym"]: a["tests_near"] for a in atlas if isinstance(a.get("tests_near"), dict)}
a_task = cv[cv["task"] == "A extinction"]
brier = a_task.groupby("model")["brier"].mean()
comp = k_comparison()
ok = comp.dropna(subset=["k_fit", "k_nasa"]) if len(comp) else comp

# ---------------------------------------------------------------- hero
hero, orb = st.columns([1.55, 1], vertical_alignment="center", gap="large")
hero.html(
    '<div class="ig-hero" style="display:block;margin:0">'
    "<h1>IGNIS LAB</h1>"
    '<div class="promise">Which NASA fire experiments matter for a crew habitat?</div>'
    '<div style="margin:.9rem 0 .2rem"><span class="ig-src"><i></i><span>Data: <b>NASA Physical Sciences '
    "Informatics (PSI), CC0</b></span></span></div></div>")
with hero:
    if st.session_state.get("tour_step") is None:
        if st.button("Start the guided tour", key="tour_start_home", type="primary", icon=":material/play_arrow:",
                     help=f"{len(steps())} short steps. Also in the sidebar."):
            start_tour()
    else:
        st.caption("Tour in progress: see the box above.")
orb.html('<div class="ig-orb-wrap"><div class="ig-orb" role="img" aria-label="Illustration of a spherical '
         'droplet flame" title="In orbit there is no buoyancy, so a burning droplet wraps itself in a spherical '
         'flame."></div><div class="ig-orb-cap">Illustration: droplet flame in orbit</div></div>')

# ---------------------------------------------------------------- three ways in
CARDS = [
    ("cta_atlas", "Investigation atlas", f"{len(atlas)}", "NASA investigations",
     "Ranked for your habitat, where the data allows.", "views/atlas.py", "Open the atlas", ":material/travel_explore:"),
    ("cta_predict", "Predict", ui.lamps_html(), "evidence check",
     "Will a droplet flame go out?", "views/predict.py", "Make a prediction", ":material/online_prediction:"),
    ("cta_story", "Fire story (3D)", "3D", "Earth vs orbit",
     "A flame on Earth, then in orbit.", "views/simulate.py", "Play the fire story",
     ":material/local_fire_department:"),
]
for col, (key, title, kicker, kicker_lab, desc, page, cta, icon) in zip(st.columns(3), CARDS):
    with col.container(border=True, key=key):
        st.html(f'<div class="ig-card-k">{kicker}<small>{ui.esc(kicker_lab)}</small></div>'
                f'<div class="ig-card-t">{ui.esc(title)}</div><div class="ig-card-d">{ui.esc(desc)}</div>')
        st.page_link(page, label=cta, icon=icon)

# ---------------------------------------------------------------- live findings (computed from the data)
ui.section("What the data says", help="Computed live from NASA's tables and our saved cross-validation results.")
findings = [{"v": str(near.get("FLEX", {}).get("exploration", "?")), "tone": "flame",
             "l": "FLEX tests, exploration atmosphere",
             "s": f"ACME CFI-G: {near.get('ACME CFI-G', {}).get('exploration', '?')}",
             "t": "NASA's exploration atmosphere is 8.2 psia, 34% O2. Real tests counted from NASA's per-test "
                  "tables: a research gap."},
            {"v": f"{brier.get(meta['classifier'], float('nan')):.3f}", "l": "Brier score",
             "s": f"baseline {brier.get('Dummy (base rate)', float('nan')):.3f}",
             "t": "Probability error of our flame-out predictions (lower is better). Numbers are withheld (RED) "
                  "wherever NASA never tested."}]
if len(ok):
    findings.append({"v": f"{ok['diff_pct'].abs().median():.1f}%", "l": "d² refit vs NASA K",
                     "s": f"median, {len(ok)} droplets",
                     "t": "Median gap between our d² refit of NASA's raw droplet recordings and NASA's tabulated K."})
else:
    findings.append({"v": "-", "l": "d² check: no recordings yet", "tone": "ink"})
ui.readouts(findings)
f1, f2, f3 = st.columns(3)
f1.page_link("views/atlas.py", label="See the gap", icon=":material/travel_explore:")
f2.page_link("views/trust.py", label="How we tested", icon=":material/verified:")
f3.page_link("views/d2law.py", label="See the d² check", icon=":material/show_chart:")

st.write("")
scope_note()

# ---------------------------------------------------------------- everything else, folded away
with st.expander("About IGNIS LAB and its data", icon=":material/info:"):
    st.markdown(f"We summarize, rank and interpret NASA's microgravity combustion research: {len(atlas)} PSI "
                f"investigations and {len(flex)} droplet fires burned on the ISS, with the real NASA evidence "
                "behind every number.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PSI combustion investigations", len(atlas))
    m2.metric("FLEX droplet burns on the ISS", len(flex))
    m3.metric("Distinct FLEX test conditions", flex["condition_id"].nunique())
    m4.metric("NASA publications linked", sum(a["n_publications"] for a in atlas))
    st.markdown(
        "- **Summarize + rank**: the *Investigation atlas* covers every PSI Combustion Science investigation "
        "and ranks them for an ISS, lunar or exploration atmosphere.\n"
        "- **Interpret**: predictions on real FLEX data always come with the NASA runs behind them, "
        "an uncertainty interval, and a warning when we extrapolate.\n"
        "- **Prevention / Detection / Suppression**: NASA's fire-safety framework, used to tag every investigation.\n"
        "- **Sources**: search the NASA reports themselves on *Ask the NASA documents*.")
    why_and_scope()
    st.caption("Main data: NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451) = NASA/TP-2015-216046 Table IX; "
               "metadata for all investigations from NASA PSI.")
