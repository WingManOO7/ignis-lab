"""Startup self-check: before any page runs, make sure the files the app reads exist and the saved models load with
the installed scikit-learn. streamlit_app.py shows ONE st.error with what is wrong and how to fix it, then stops,
instead of a stack trace deep inside a page.

    problems = startup_problems()          # cached (st.cache_resource): runs once per server process
    if problems: st.error(problem_message(problems)); st.stop()

Pure function for tests: run_checks(root, sklearn_version) -> list[Problem].
"""
import warnings
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

PIPELINE = "python scripts/run_all.py"
PIN = "pip install -r requirements.txt"
REQUIRED = {                                    # file the app reads -> command that rebuilds it
    "data/processed/flex_clean.csv": PIPELINE,
    "data/atlas/investigations.json": PIPELINE,
    "data/docs_index/chunks.json": PIPELINE + " --docs",
    "reports/cv_folds.csv": PIPELINE,
    "models/extinction_clf.joblib": PIPELINE,
    "models/k_reg.joblib": PIPELINE,
    "models/k_interval.joblib": PIPELINE,
    "models/evidence_index.joblib": PIPELINE,
}


@dataclass(frozen=True)
class Problem:
    what: str           # one line, plain language
    fix: str            # command that fixes it
    alt: str = ""       # optional second way to fix it


def _installed_sklearn():
    import sklearn
    return sklearn.__version__


def _check_model(path, rel, installed):
    """Load one .joblib; report a load failure, or a scikit-learn version other than the one it was saved with
    (from its meta, else from scikit-learn's own InconsistentVersionWarning)."""
    import joblib
    try:
        from sklearn.exceptions import InconsistentVersionWarning
    except Exception:
        InconsistentVersionWarning = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            obj = joblib.load(path)
    except Exception as e:
        return Problem(f"`{rel}` could not be loaded ({type(e).__name__}: {e}).", PIN, alt=PIPELINE)
    meta = obj.get("meta") if isinstance(obj, dict) else None
    saved = meta.get("sklearn_version") if isinstance(meta, dict) else None
    if saved is None and InconsistentVersionWarning is not None:
        saved = next((str(w.message.original_sklearn_version) for w in caught
                      if isinstance(w.message, InconsistentVersionWarning)), None)
    if saved is not None and str(saved) != str(installed):
        return Problem(f"`{rel}` was saved with scikit-learn {saved}, but scikit-learn {installed} is installed.",
                       PIN, alt=PIPELINE)
    return None


def run_checks(root: Path = ROOT, sklearn_version: str | None = None) -> list[Problem]:
    """Every problem found (empty list = ready to start). Never raises."""
    problems = []
    try:
        root = Path(root)
        installed = sklearn_version or _installed_sklearn()
        for rel, fix in REQUIRED.items():
            if not (root / rel).is_file():
                problems.append(Problem(f"Missing `{rel}`.", fix))
        for path in sorted((root / "models").glob("*.joblib")):
            p = _check_model(path, path.relative_to(root).as_posix(), installed)
            if p is not None:
                problems.append(p)
    except Exception as e:                  # the check itself must never crash the app
        problems.append(Problem(f"The startup self-check itself failed ({type(e).__name__}: {e}).", PIN))
    return problems


@st.cache_resource(show_spinner=False)
def startup_problems() -> list[Problem]:
    """run_checks() once per server process (call startup_problems.clear() to re-check after a fix)."""
    return run_checks()


def problem_message(problems: list[Problem]) -> str:
    """One Markdown message: what is wrong, then each fixing command once."""
    n = len(problems)
    lines = [f"**IGNIS LAB cannot start: {n} problem{'' if n == 1 else 's'} with its data or model files.**", ""]
    lines += [f"- {p.what}" for p in problems]
    lines += ["", "**How to fix** (in a terminal, in the repository folder, with the app's Python environment):", ""]
    seen = set()
    for p in problems:
        if (p.fix, p.alt) in seen:
            continue
        seen.add((p.fix, p.alt))
        lines.append(f"- `{p.fix}`" + (f" (or rebuild with the installed version: `{p.alt}`)" if p.alt else ""))
    lines += ["", "Then reload this page."]
    return "\n".join(lines)
