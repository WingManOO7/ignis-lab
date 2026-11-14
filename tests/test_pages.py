"""Smoke test: every page renders without an exception, run through the real entry point
(streamlit_app.py + st.navigation), so page links, switch_page and the sidebar work as in the app.
Run:  python tests/test_pages.py      (or: python -m pytest -q)"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PAGES = ["home", "atlas", "explorer", "d2law", "predict", "simulate", "trust", "ask_docs"]
# Extra states worth rendering: (page, session_state overrides)
STATES = [("predict", {"preset": "Exploration atmosphere (8.2 psia, 34% O2)"}),   # RED path
          ("atlas", {"atlas_scenario": "exploration"}),
          ("explorer", {"explorer_pick": "248F001"}),                             # run with a d2 recording
          ("explorer", {"explorer_pick": "C11M201"}),                             # run without one
          ("simulate", {"sim_query": {"fuel": "Heptane", "p_atm": 0.56, "x_o2": 0.34, "d0_mm": 3.0,  # RED story
                                      "x_co2": 0.0, "x_he": 0.0,
                                      "preset": "Exploration atmosphere (8.2 psia, 34% O2)"}}),
          ("simulate", {"sim_query": {"fuel": "Methanol", "p_atm": 1.0, "x_o2": 0.21, "d0_mm": 2.5,
                                      "x_co2": 0.2, "x_he": 0.0, "diluent": "CO2"}})]


def run_page(name, state=None):
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=180)
    for k, v in (state or {}).items():
        at.session_state[k] = v
    at.run()
    if name != "home" and not at.exception:
        at.switch_page(f"views/{name}.py").run()
    return at


def cases():
    return [(p, None) for p in PAGES] + STATES


def test_pages():
    for name, state in cases():
        at = run_page(name, state)
        assert not at.exception, f"{name} {state}: {[e.message for e in at.exception]}"


if __name__ == "__main__":
    failed = 0
    for name, state in cases():
        at = run_page(name, state)
        tag = f"{name}{' ' + str(state) if state else ''}"
        if at.exception:
            failed += 1
            print(f"FAIL {tag}:")
            for e in at.exception:
                print("   ", e.message)
        else:
            print(f"OK   {tag}  ({len(at.markdown)} markdown, {len(at.dataframe)} tables, "
                  f"{len(at.get('plotly_chart'))} charts)")
    sys.exit(1 if failed else 0)
