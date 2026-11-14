"""STARTER CODE - cached loaders shared by all pages (adapt during the event)."""
import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data
def load_flex():
    return pd.read_csv(ROOT / "data/processed/flex_clean.csv")


@st.cache_data
def load_atlas():
    return json.loads((ROOT / "data/atlas/investigations.json").read_text(encoding="utf-8"))


@st.cache_data
def load_summaries():
    """Offline AI summaries (scripts/build_summaries.py); {} if not generated yet."""
    path = ROOT / "data/atlas/summaries.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def load_cv():
    return pd.read_csv(ROOT / "reports/cv_folds.csv")


@st.cache_resource   # models are loaded once and shared; never retrain inside the app
def load_models():
    return {"clf": joblib.load(ROOT / "models/extinction_clf.joblib"),
            "k": joblib.load(ROOT / "models/k_interval.joblib"),
            "evidence": joblib.load(ROOT / "models/evidence_index.joblib")}
