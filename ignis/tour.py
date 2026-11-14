"""Guided tour: 5 steps that set session state (presets) and switch pages. Rendered by streamlit_app.py
before the page runs, so it appears on every page (sidebar step list + a 'Next step' box)."""
import streamlit as st

from ignis.data import load_atlas
from ignis.scenarios import SCENARIOS
from ignis.ui import esc


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
         "text": f"Lunar habitat (30% O2, 0.69 atm): FLEX has {_near('FLEX', 'lunar')} real tests nearby."},
        {"title": "Spot the research gap", "page": "views/atlas.py", "state": {"atlas_scenario": "exploration"},
         "text": f"Exploration atmosphere: FLEX {_near('FLEX', 'exploration')} tests, ACME CFI-G "
                 f"{_near('ACME CFI-G', 'exploration')} (ACME BRE: day-level log only). See the Tested envelope tab."},
        {"title": "Predict in ISS air: GREEN", "page": "views/predict.py", "state": {"preset": iss, **PREDICT_RESET},
         "text": "ISS cabin air: GREEN, so the numbers show beside the 5 closest NASA runs."},
        {"title": "Exploration atmosphere: RED", "page": "views/predict.py", "state": {"preset": expl, **PREDICT_RESET},
         "text": "Same droplet: RED. FLEX never ran here, so numbers are withheld. Risk map: grey = never tested."},
        {"title": "Can you trust it?", "page": "views/trust.py", "state": {},
         "text": "Grouped cross-validation, baselines, a reliability check, fold spread and input importance."},
    ]


def _go(i):
    step = steps()[i]
    st.session_state["tour_step"] = i
    for key, value in step["state"].items():
        st.session_state[key] = value
    st.switch_page(step["page"])


def start_tour():
    """Start at step 1 (used by the sidebar button and the home page)."""
    _go(0)


def tour_controls():
    tour = steps()
    current = st.session_state.get("tour_step")
    with st.sidebar:
        st.markdown("**Guided tour**")
        if current is None:
            st.caption(f"{len(tour)} short steps")
            if st.button("Start the 5-step tour", key="tour_start", type="primary", icon=":material/play_arrow:",
                         width="stretch"):
                _go(0)
        else:
            with st.container(key="tour_steps"):
                for i, s in enumerate(tour):
                    if st.button(f"{i + 1}. {s['title']}", key=f"tour_jump_{i}", width="stretch",
                                 type="primary" if i == current else "tertiary"):
                        _go(i)
            if st.button("Exit tour", key="tour_exit", icon=":material/close:"):
                st.session_state.pop("tour_step", None)
                st.rerun()
    if current is not None:
        s = tour[current]
        box = st.container(border=True, key="tour_box")
        bars = "".join(f'<i class="{"on" if i <= current else ""}"></i>' for i in range(len(tour)))
        text_col, btn_col = box.columns([5, 1], vertical_alignment="center")
        text_col.html(f'<div class="ig-steps">{bars}</div>'
                      f'<div class="ig-tour-k">Guided tour, step {current + 1} of {len(tour)}</div>'
                      f'<div class="ig-tour-t">{esc(s["title"])}</div><div class="ig-tour-x">{esc(s["text"])}</div>')
        if current + 1 < len(tour):
            if btn_col.button("Next step", key="tour_next", type="primary", icon=":material/arrow_forward:",
                              width="stretch"):
                _go(current + 1)
        elif btn_col.button("Finish tour", key="tour_finish", icon=":material/check:", width="stretch"):
            st.session_state.pop("tour_step", None)
            st.rerun()
