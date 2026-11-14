"""Honesty checks for the d² page (sample size, worst gap, low-R² flag) and the Atlas (phenomenon tag,
'what is missing').  Run:  python -m pytest -q"""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ignis.droplets import LOW_R2, d2_summary, droplet_index, k_comparison, r2_flag, sample_counts, sample_line, \
    worst_gap

ROOT = Path(__file__).resolve().parents[1]


def atlas_helpers():
    """views/atlas.py is a Streamlit page (importing it renders the page), so compile only its pure top-level
    helpers (functions and constants named below) into a fresh namespace."""
    names = {"PHENOMENON_RULES", "PHENOMENA", "phenomenon", "COMPLETENESS_WORDS", "_blank", "missing_fields"}
    tree = ast.parse((ROOT / "views/atlas.py").read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns = {"pd": pd}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(ROOT / "views/atlas.py"), "exec"), ns)
    assert names <= set(ns), f"missing helpers in views/atlas.py: {names - set(ns)}"
    return ns


def investigations():
    return json.loads((ROOT / "data/atlas/investigations.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- Atlas
def test_phenomenon_tag_covers_all_24_investigations():
    h, rows = atlas_helpers(), investigations()
    tags = {r["acronym"]: h["phenomenon"](r) for r in rows}
    assert len(rows) == 24 and set(tags.values()) <= set(h["PHENOMENA"]), tags
    assert all(h["phenomenon"](r) == tags[r["acronym"]] for _, r in pd.DataFrame(rows).iterrows())  # rows as Series
    expected = {"FLEX": "droplet", "FLEX-2": "droplet", "CFI": "droplet", "ACME CFI-G": "gas flame",
                "ACME BRE": "gas flame", "SPICE": "gas flame", "SLICE": "gas flame", "BASS-II": "solid fuel",
                "BASS": "solid fuel", "SAFFIRE-II": "solid fuel", "SAME": "smoke/aerosol",
                "DAFT / DAFT-2": "smoke/aerosol"}
    assert {a: tags[a] for a in expected} == expected
    ground = [r["acronym"] for r in rows if r["project_type"].startswith("Ground")]
    assert ground and all(tags[a] == "modelling/ground" for a in ground)
    assert h["phenomenon"]({"family": "something new", "fuel_type": None}) == "unclassified"   # never guessed


def test_what_is_missing_lists_exactly_the_empty_fields():
    h = atlas_helpers()
    row = {"tested_o2_min": 0.17, "tested_o2_max": None, "tested_p_min_atm": float("nan"), "tested_p_max_atm": 3.0,
           "rows": np.nan, "outcomes": "Test end (Extinction)", "phase_source": "metadata"}
    assert h["missing_fields"](row) == ["O2 max", "P min", "table rows", "phase tag"]
    assert h["missing_fields"](pd.Series(row)) == ["O2 max", "P min", "table rows", "phase tag"]
    full = {**row, "tested_o2_max": 0.3, "tested_p_min_atm": 0.5, "rows": 87, "phase_source": "curated"}
    assert h["missing_fields"](full) == []
    assert h["missing_fields"]({**full, "outcomes": "  "}) == ["outcomes"]                # blank text is empty


def test_completeness_is_seven_minus_what_is_missing_on_real_atlas():
    h = atlas_helpers()
    fields = list(h["COMPLETENESS_WORDS"])
    for r in investigations():
        filled = sum(r.get(f) is not None for f in fields) + (r.get("phase_source") == "curated")
        assert 7 - len(h["missing_fields"](r)) == filled, r["acronym"]


# ---------------------------------------------------------------- d² law
def synthetic_comparison():
    return pd.DataFrame([
        {"flex_id": "A", "fuel": "Heptane", "test_end": "Extinction", "k_fit": 0.55, "k_nasa": 0.50, "r2": 0.99},
        {"flex_id": "B", "fuel": "Methanol", "test_end": "Disruption", "k_fit": 0.44, "k_nasa": 0.50, "r2": 0.79},
        {"flex_id": "C", "fuel": "Methanol", "test_end": "Completion", "k_fit": 0.51, "k_nasa": 0.50, "r2": LOW_R2},
        {"flex_id": "D", "fuel": "Heptane", "test_end": "Disruption", "k_fit": 0.90, "k_nasa": np.nan, "r2": 0.10},
        {"flex_id": "E", "fuel": "Heptane", "test_end": "Extinction", "k_fit": np.nan, "k_nasa": 0.50,
         "r2": np.nan}]).assign(diff_pct=lambda d: 100 * (d["k_fit"] - d["k_nasa"]) / d["k_nasa"])


def synthetic_index(on_disk):
    return pd.DataFrame({"file_name": [f"FLEX-{n:03d}_DropletData.txt" for n in (1, 2, 5, 9)],
                         "flex_number": [1, 2, 5, 9], "on_disk": on_disk})


def test_d2_summary_worst_gap_and_low_r2_flags():
    comp = synthetic_comparison()
    s = d2_summary(comp, synthetic_index([True, True, False, False]))
    assert s["worst"]["flex_id"] == "B" and s["worst"]["diff_pct"] == pytest.approx(-12.0)   # D has no NASA K
    assert s["n_comparable"] == 3 and s["median_gap_pct"] == pytest.approx(10.0)
    assert s["low_r2"] == ["B", "D"] and s["low_r2_comparable"] == 1           # 0.8 itself and no fit: no flag
    assert [r2_flag(v) for v in comp["r2"]] == ["", "low R²", "", "low R²", ""]
    assert worst_gap(comp.iloc[3:]) is None


def test_d2_sample_counts_and_line():
    earliest = sample_counts(synthetic_index([True, True, False, False]))
    assert (earliest["on_disk"], earliest["total"], earliest["earliest"]) == (2, 4, True)
    assert sample_line(earliest) == "2 of 4 recordings, the earliest runs - not a random sample"
    picked = sample_counts(synthetic_index([True, False, True, False]))
    assert not picked["earliest"] and "earliest" not in sample_line(picked)
    assert sample_line(sample_counts(synthetic_index([True] * 4))) == "All 4 recordings"


def test_d2_summary_on_real_recordings_is_computed_live():
    idx, comp = droplet_index(), k_comparison()
    if comp.empty:
        pytest.skip("no droplet recordings on disk")
    s = d2_summary(comp, idx)
    ok = comp.dropna(subset=["k_fit", "k_nasa"])
    brute = ok.iloc[int(np.argmax(ok["diff_pct"].abs().to_numpy()))]
    assert s["worst"]["flex_id"] == brute["flex_id"] and s["worst"]["diff_pct"] == pytest.approx(brute["diff_pct"])
    assert (comp["flag"] == np.where(comp["r2"] < LOW_R2, "low R²", "")).all()
    on_disk = {p.name for p in (ROOT / "data/raw/droplet_histories").glob("FLEX-*_DropletData.txt")}
    listed = json.loads((ROOT / "data/raw/droplet_histories/index.json").read_text(encoding="utf-8"))
    assert (s["sample"]["on_disk"], s["sample"]["total"]) == (len(on_disk & set(idx["file_name"])), len(listed))


# ---------------------------------------------------------------- the pages really show it
def test_pages_show_the_new_columns_and_lines():
    from streamlit.testing.v1 import AppTest
    for page, checks in [("atlas", ("phenomenon", "missing_txt")), ("d2law", ("flag",))]:
        at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=180)
        at.run()
        at.switch_page(f"views/{page}.py").run()
        assert not at.exception, [e.message for e in at.exception]
        cols = {c for df in at.dataframe for c in df.value.columns}
        assert set(checks) <= cols, (page, cols)
        text = " ".join(m.value for m in at.markdown)
        if page == "atlas":
            assert "read the **phenomenon** tag" in text
        else:
            assert "not a random sample" in text or "All " in text
