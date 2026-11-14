import streamlit as st

from ignis.data import load_atlas, load_flex
from ignis.messages import why_and_scope

st.title("IGNIS LAB")
st.subheader("Which NASA microgravity fire experiments matter for a crew habitat - "
             "and how far can we trust what they predict?")
flex, atlas = load_flex(), load_atlas()
c1, c2, c3, c4 = st.columns(4)
c1.metric("PSI combustion investigations", len(atlas))
c2.metric("FLEX droplet burns on the ISS", len(flex))
c3.metric("Distinct FLEX test conditions", flex["condition_id"].nunique())
c4.metric("NASA publications linked", sum(a["n_publications"] for a in atlas))
st.markdown(
    "- **Summarize + rank**: the *Investigation atlas* covers every PSI Combustion Science investigation "
    "and ranks them for an ISS, lunar or exploration atmosphere.\n"
    "- **Interpret**: predictions on real FLEX data always come with the NASA runs behind them, "
    "an uncertainty interval, and a warning when we extrapolate.\n"
    "- **Prevention / Detection / Suppression**: NASA's fire-safety framework, used to tag every investigation.\n"
    "- Main data: NASA PSI-69 FLEX (DOI 10.60555/mbq8-0451) = NASA/TP-2015-216046 Table IX; "
    "metadata for all investigations from NASA PSI.")
why_and_scope()
