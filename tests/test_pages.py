"""Smoke test: every page renders without an exception.  Run:  python -m pytest -q  (or python tests/test_pages.py)"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PAGES = ["home", "atlas", "explorer", "predict", "trust", "ask_docs"]


def run_page(name):
    at = AppTest.from_file(str(ROOT / "views" / f"{name}.py"), default_timeout=120).run()
    return at


def test_pages():
    for name in PAGES:
        at = run_page(name)
        assert not at.exception, f"{name}: {[e.message for e in at.exception]}"


if __name__ == "__main__":
    failed = 0
    for name in PAGES:
        at = run_page(name)
        if at.exception:
            failed += 1
            print(f"FAIL {name}:")
            for e in at.exception:
                print("   ", e.message, "\n", "".join(e.stack_trace[-6:]) if e.stack_trace else "")
        else:
            warn = [w.body for w in at.warning] + [w.body for w in at.error]
            print(f"OK   {name}  ({len(at.markdown)} markdown, {len(at.dataframe)} tables, "
                  f"{len(at.get('plotly_chart'))} charts){'  messages: ' + str(warn)[:200] if warn else ''}")
    sys.exit(1 if failed else 0)
