"""STARTER CODE - IGNIS LAB entry point.  Run:  streamlit run streamlit_app.py"""
import streamlit as st

from ignis import ui
from ignis.selfcheck import problem_message, startup_problems
from ignis.simulation import ensure_fire_lab_page
from ignis.tour import tour_controls

st.set_page_config(page_title="IGNIS LAB - microgravity fire-safety insights", layout="wide",
                   page_icon=":material/local_fire_department:", initial_sidebar_state="auto")
ui.inject_css()
ui.logo()

problems = startup_problems()      # data files + models + scikit-learn version, checked once per server process
if problems:
    st.error(problem_message(problems), icon=":material/error:")
    startup_problems.clear()       # re-check on the next reload, after the fix
    st.stop()
ensure_fire_lab_page()             # static/fire_lab.html (full-screen Fire lab); cheap when up to date, never raises

pages = {
    "Start": [
        st.Page("views/home.py", title="Mission brief", icon=":material/rocket_launch:", default=True),
        st.Page("views/simulate.py", title="Fire story (3D)", icon=":material/local_fire_department:"),
    ],
    "Explore NASA data": [
        st.Page("views/atlas.py", title="Investigation atlas", icon=":material/travel_explore:"),
        st.Page("views/safety.py", title="Safety controls", icon=":material/health_and_safety:"),
        st.Page("views/explorer.py", title="FLEX run explorer", icon=":material/scatter_plot:"),
        st.Page("views/d2law.py", title="d² law check", icon=":material/show_chart:"),
    ],
    "Predict & trust": [
        st.Page("views/predict.py", title="Predict", icon=":material/online_prediction:"),
        st.Page("views/trust.py", title="Can you trust this?", icon=":material/verified:"),
    ],
    "Sources": [
        st.Page("views/ask_docs.py", title="Ask the NASA documents", icon=":material/menu_book:"),
    ],
}
nav = st.navigation(pages)
tour_controls()          # guided tour: sidebar step list + 'Next step' box (only while the tour is active)
nav.run()
st.sidebar.caption("NASA PSI data, CC0. Not affiliated with NASA. AI use disclosed.",
                   help="Data: NASA Physical Sciences Informatics (PSI), CC0. Not affiliated with or endorsed by "
                        "NASA. SI/AI assistance is disclosed in the README.")
