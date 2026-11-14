import streamlit as st

from ignis.data import load_atlas, load_cv, load_flex, load_models
from ignis.droplets import k_comparison
from ignis.messages import why_and_scope

st.title("IGNIS LAB")
st.subheader("Which NASA microgravity fire experiments matter for a crew habitat - "
             "and how far can we trust what they predict?")
st.caption("NASA has studied fire in microgravity for decades. Its results sit in the Physical Sciences Informatics "
           "(PSI) repository: valuable, but hard to find, compare and interpret. IGNIS LAB summarizes, ranks and "
           "interprets them - and shows the real NASA evidence behind every number.")

flex, atlas, cv, meta = load_flex(), load_atlas(), load_cv(), load_models()["clf"]["meta"]
near = {a["acronym"]: a["tests_near"] for a in atlas if isinstance(a.get("tests_near"), dict)}
a_task = cv[cv["task"] == "A extinction"]
brier = a_task.groupby("model")["brier"].mean()
comp = k_comparison()
ok = comp.dropna(subset=["k_fit", "k_nasa"]) if len(comp) else comp

c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.markdown("##### A research gap")
    st.markdown(f"At NASA's **exploration atmosphere** (8.2 psia, 34% O2), FLEX has "
                f"**{near.get('FLEX', {}).get('exploration', '?')} real tests**; ACME CFI-G has "
                f"**{near.get('ACME CFI-G', {}).get('exploration', '?')}**. Counted from NASA's tables, not guessed.")
    st.page_link("views/atlas.py", label="See it in the Atlas", icon=":material/travel_explore:")
with c2.container(border=True):
    st.markdown("##### Honest predictions")
    st.markdown(f"Calibrated probabilities (Brier **{brier.get(meta['classifier'], float('nan')):.3f}** vs "
                f"**{brier.get('Dummy (base rate)', float('nan')):.3f}** baseline), the 5 closest real ISS runs, "
                "and numbers withheld (RED) wherever NASA never tested.")
    st.page_link("views/predict.py", label="Try a prediction", icon=":material/science:")
with c3.container(border=True):
    st.markdown("##### Checked against raw data")
    if len(ok):
        st.markdown(f"Refitting the d² law to NASA's raw droplet recordings reproduces NASA's burning rates within a "
                    f"median **{ok['diff_pct'].abs().median():.1f}%** ({len(ok)} droplets).")
    else:
        st.markdown("Droplet recordings not downloaded yet.")
    st.page_link("views/d2law.py", label="See the d² check", icon=":material/show_chart:")

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
    "- New here? Press **Start the 5-step tour** in the sidebar.\n"
    "- Main data: NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451) = NASA/TP-2015-216046 Table IX; "
    "metadata for all investigations from NASA PSI.")
why_and_scope()
