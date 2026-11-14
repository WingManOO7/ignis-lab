"""Guided tour: 5 steps that set session state (presets) and switch pages. Rendered by streamlit_app.py
before the page runs, so it appears on every page (sidebar step list + a 'Next step' box)."""
import streamlit as st

from ignis.data import load_atlas
from ignis.scenarios import SCENARIOS


def _near(acronym, key):
    for a in load_atlas():
        if a["acronym"] == acronym and isinstance(a.get("tests_near"), dict):
            return a["tests_near"].get(key, 0)
    return "?"


PREDICT_RESET = {"pred_fuel": "Heptane", "pred_diluent": "none (N2 only)", "pred_d0": 3.0}   # same droplet each time


def steps():
    iss, expl = SCENARIOS["iss"][0], SCENARIOS["exploration"][0]
    return [
        {"title": "Pick the lunar habitat in the Atlas", "page": "views/atlas.py", "state": {"atlas_scenario": "lunar"},
         "text": "The Atlas summarizes and ranks every NASA PSI combustion investigation for a crew habitat. With the "
                 f"lunar habitat selected (30% O2, 0.69 atm), FLEX has {_near('FLEX', 'lunar')} real tests near it."},
        {"title": "Spot the research gap", "page": "views/atlas.py", "state": {"atlas_scenario": "exploration"},
         "text": "Now NASA's exploration atmosphere (8.2 psia, 34% O2). Scroll to the envelope chart: its star sits "
                 f"below FLEX's tested box. Counted from NASA's per-test tables, FLEX has "
                 f"{_near('FLEX', 'exploration')} tests there and ACME CFI-G has {_near('ACME CFI-G', 'exploration')} "
                 "(ACME BRE also ran this atmosphere but publishes only a day-level log)."},
        {"title": "Predict in ISS air: GREEN", "page": "views/predict.py", "state": {"preset": iss, **PREDICT_RESET},
         "text": "ISS cabin air with a heptane droplet: the light is GREEN, so the model's numbers are shown, next to "
                 "what NASA actually saw at the 5 closest real runs."},
        {"title": "Exploration atmosphere: RED", "page": "views/predict.py", "state": {"preset": expl, **PREDICT_RESET},
         "text": "Same droplet in the exploration atmosphere: RED. NASA never ran FLEX here, so numbers are withheld "
                 "and the page points to the investigations that did. Scroll to the risk map: grey = never tested."},
        {"title": "Can you trust it?", "page": "views/trust.py", "state": {},
         "text": "Grouped cross-validation against baselines, a reliability check of the probabilities, the honest "
                 "fold-to-fold spread, and which inputs the models rely on."},
    ]


def _go(i):
    step = steps()[i]
    st.session_state["tour_step"] = i
    for key, value in step["state"].items():
        st.session_state[key] = value
    st.switch_page(step["page"])


def tour_controls():
    tour = steps()
    current = st.session_state.get("tour_step")
    with st.sidebar:
        st.markdown("**Guided tour**")
        if current is None:
            if st.button("Start the 5-step tour", key="tour_start", type="primary"):
                _go(0)
        else:
            for i, s in enumerate(tour):
                if st.button(f"{i + 1}. {s['title']}", key=f"tour_jump_{i}",
                             type="primary" if i == current else "secondary"):
                    _go(i)
            if st.button("Exit tour", key="tour_exit"):
                st.session_state.pop("tour_step", None)
                st.rerun()
    if current is not None:
        s = tour[current]
        box = st.container(border=True)
        box.markdown(f"**Guided tour - step {current + 1} of {len(tour)}: {s['title']}**  \n{s['text']}")
        if current + 1 < len(tour):
            if box.button("Next step ->", key="tour_next", type="primary"):
                _go(current + 1)
        elif box.button("Finish tour", key="tour_finish"):
            st.session_state.pop("tour_step", None)
            st.rerun()
