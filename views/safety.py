"""Safety controls: which NASA investigations could inform detection, suppression and material screening.
Evidence (what NASA measured / reported) is kept separate from our interpretation (the safety question)."""
import streamlit as st

from ignis import ui
from ignis.data import load_atlas
from ignis.safety import CARDS, NTRS, PILLARS

ui.page_header("Safety controls",
               "What NASA's experiments could inform: detection, suppression, prevention.",
               "NASA PSI investigations + NASA reports")
ui.note("**Interpretation, not NASA findings.** Each safety question below is our reading of what an investigation "
        "could inform, not a NASA conclusion or an engineering recommendation.", tone="caution",
        details="Each card keeps three things apart: what NASA actually measured or studied (from the PSI record and "
                "facts we verified against PSI tables and NASA papers), an optional NASA-reported result quoted with "
                "its source, and the safety question the work may help inform, which is our interpretation. Real "
                "design decisions need the original NASA reports and expert review.")

atlas = {a["accession"]: a for a in load_atlas()}
tabs = st.tabs([PILLARS[k][0] for k in PILLARS])
for tab, (key, (name, blurb)) in zip(tabs, PILLARS.items()):
    with tab:
        st.caption(blurb)
        for card in [c for c in CARDS if c["pillar"] == key]:
            with st.container(border=True):
                links = " · ".join(f"[{atlas[a]['acronym']} ({a})]({atlas[a]['page']})" for a in card["accessions"])
                st.markdown(f"#### {card['title']}")
                st.caption(f"NASA PSI source: {links}")
                st.markdown(f"**What NASA measured or studied:** {card['measured']}")
                if card["reported"]:
                    label, url = NTRS[card["reported_src"]]
                    st.markdown(f"**NASA-reported result:** {card['reported']} ([{label}]({url}))")
                st.markdown(f":orange-badge[Interpretation (ours)] **Safety question it may help inform:** "
                            f"{card['question']}")
                if card["explore"]:
                    st.page_link(card["explore"][0], label=card["explore"][1], icon=":material/arrow_forward:")

with st.expander("Sources and scope"):
    st.markdown("**NASA reports cited:**  \n" + "  \n".join(f"- [{label}]({url})" for label, url in NTRS.values()))
    st.markdown("Investigation facts come from NASA PSI metadata and `data/atlas/curation.json` (each value with its "
                "source). Our prediction models cover only isolated FLEX droplets; they do not predict smoke, solid "
                "materials or whole spacecraft fires, and none of these cards uses a model output.")
