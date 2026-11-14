"""STARTER CODE - IGNIS LAB entry point.  Run:  streamlit run streamlit_app.py"""
import streamlit as st

from ignis.tour import tour_controls

st.set_page_config(page_title="IGNIS LAB - microgravity fire-safety insights", layout="wide")

pages = [
    st.Page("views/home.py", title="Mission brief", default=True),
    st.Page("views/atlas.py", title="Investigation atlas (summarize + rank)"),
    st.Page("views/explorer.py", title="FLEX run explorer"),
    st.Page("views/d2law.py", title="d² law on real droplets"),
    st.Page("views/predict.py", title="Predict + NASA evidence"),
    st.Page("views/trust.py", title="Can you trust this?"),
    st.Page("views/ask_docs.py", title="Ask the NASA documents"),
]
nav = st.navigation(pages)
tour_controls()          # guided tour: sidebar step list + 'Next step' box (only while the tour is active)
nav.run()
st.sidebar.caption("Data: NASA Physical Sciences Informatics (PSI), CC0. "
                   "Not affiliated with or endorsed by NASA. SI/AI assistance disclosed in README.")
