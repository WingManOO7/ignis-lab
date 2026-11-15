"""Safety controls: which NASA investigations could inform detection, suppression and material screening, plus how
fires are fought in space and on Earth, and what past spacecraft fires taught.
Evidence (what NASA measured / reported) is kept separate from our interpretation (the safety question, the link)."""
import streamlit as st

from ignis import ui
from ignis.data import load_atlas
from ignis.safety import CARDS, EXTINGUISHERS, INCIDENTS, ISS_RESPONSE, ISS_RESPONSE_SRC, NTRS, PILLARS, PRACTICE, SOURCES

ui.page_header("Safety controls",
               "What NASA's experiments could inform, how fires are fought in space, and what past fires taught.",
               "NASA PSI investigations + NASA reports and history")
ui.note("**Interpretation, not NASA findings.** Each safety question and each link to IGNIS below is our reading, not "
        "a NASA conclusion or an engineering recommendation. Facts carry their source.", tone="caution",
        details="Each card keeps three things apart: what NASA actually measured or studied (from the PSI record and "
                "facts we verified against PSI tables and NASA papers), an optional NASA-reported result quoted with "
                "its source, and the safety question the work may help inform, which is our interpretation. The "
                "history tabs use NASA sources (one news report is marked as such). Real design decisions need the "
                "original NASA reports and expert review.")


def sources(keys):
    return "Sources: " + " · ".join(f"[{SOURCES[k][0]}]({SOURCES[k][1]})" for k in keys)


def link(text, explore=None):
    st.markdown(f":orange-badge[Link to IGNIS (ours)] {text}")
    if explore:
        st.page_link(explore[0], label=explore[1], icon=":material/arrow_forward:")


atlas = {a["accession"]: a for a in load_atlas()}
tabs = st.tabs([PILLARS[k][0] for k in PILLARS] + ["Extinguishers: Earth vs space", "Lessons from past fires"])
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

with tabs[3]:
    st.caption("What puts a fire out in a sealed cabin, and why space chose differently from Earth.")
    cols = st.columns(2)
    for i, ex in enumerate(EXTINGUISHERS):
        with cols[i % 2].container(border=True):
            st.markdown(f"#### {ex['name']}")
            st.markdown(f":blue-badge[Space] {ex['space']}  \n:gray-badge[Earth] {ex['earth']}")
            st.markdown(f"**How it works:** {ex['how']}")
            st.markdown(f"**In a sealed cabin:** {ex['cabin']}")
            st.caption(sources(ex["src"]))
    with st.container(border=True):
        st.markdown("#### How the ISS fights a fire today")
        for i, (step, text) in enumerate(ISS_RESPONSE, 1):
            st.markdown(f"**{i}. {step}.** {text}")
        st.caption(sources(ISS_RESPONSE_SRC))
        link("FLEX tested CO2 (up to 70%) and helium mixed into the cabin gas: Predict shows when they make a droplet "
             "flame go out early. In the 3D wiring station, the fan-off and CO2 buttons act out steps 2 and 5 "
             "(illustrative).", ("views/predict.py", "Try CO2 in Predict (FLEX droplets only)"))

with tabs[4]:
    st.caption("Spacecraft fires and what changed afterwards. Each one shaped today's fire-safety rules.")
    for inc in INCIDENTS:
        with st.container(border=True):
            st.markdown(f"#### {inc['year']} · {inc['title']}")
            st.caption(inc["when"])
            st.markdown(f"**What happened:** {inc['what']}")
            st.markdown(f"**Why:** {inc['why']}")
            st.markdown("**What changed afterwards:**\n" + "\n".join(f"- {c}" for c in inc["changed"]))
            link(inc["link"], inc["explore"])
            st.caption(sources(inc["src"]))
    st.markdown("#### How fire safety is done now")
    for pr in PRACTICE:
        with st.container(border=True):
            st.markdown(f"**{pr['title']}.** {pr['text']}")
            link(pr["link"])
            st.caption(sources(pr["src"]))

with st.expander("Sources and scope"):
    st.markdown("**NASA reports cited on the investigation cards:**  \n" +
                "  \n".join(f"- [{label}]({url})" for label, url in NTRS.values()))
    st.markdown("**History and practice sources:**  \n" + "  \n".join(f"- [{label}]({url})" for label, url in SOURCES.values()))
    st.markdown("Investigation facts come from NASA PSI metadata and `data/atlas/curation.json` (each value with its "
                "source). Our prediction models cover only isolated FLEX droplets; they do not predict smoke, solid "
                "materials or whole spacecraft fires, and none of these cards uses a model output.")
