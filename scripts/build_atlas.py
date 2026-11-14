"""
Builds data/atlas/investigations.json - one record per NASA PSI "Combustion Science"
investigation (24 on 2026-11-14) - for the Investigation Atlas page.

* Narrative fields (objective, approach, platform, hardware, dates, publications, DOI,
  licence, data size, table files) come LIVE from the PSI JSON API, the same API that
  psi.nasa.gov uses (undocumented, no login needed).
* Test-envelope fields (O2 / pressure tested, outcome table, phase) come from
  data/atlas/curation.json, which holds only facts the team has verified and cited.
* Where possible, envelopes are recomputed from the downloaded experimental tables.

Raw API responses are cached in data/raw/psi_api/ so later runs work offline.
Run from the repository root (after download_psi.py):   python scripts/build_atlas.py
Add --refresh to ignore the cache and re-query NASA.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # so 'ignis' imports from scripts/
from ignis.scenarios import P_TOL, SCENARIOS, near_mask         # noqa: E402

API = "https://psi.nasa.gov/geode-py/ws"
CACHE = Path("data/raw/psi_api")
CURATION = Path("data/atlas/curation.json")
OUT = Path("data/atlas/investigations.json")
PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{}"

# Hardware families, as grouped in the challenge brief (plus smoke and ground studies).
FAMILIES = {
    "ACME gas flames (CIR)": ["PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
    "Droplet combustion (MDCA in CIR)": ["PSI-69", "PSI-68", "PSI-39"],
    "Solids & gas jets (MSG flow duct)": ["PSI-25", "PSI-26", "PSI-106", "PSI-107"],
    "Large-scale fires (Saffire, Cygnus)": ["PSI-98", "PSI-99", "PSI-100"],
    "Smoke & aerosol detection": ["PSI-101", "PSI-102", "PSI-47"],
}
# Fallback when an investigation is not curated: tag the fire-safety phase from its text.
PHASE_KEYWORDS = {
    "detection": r"smoke|aerosol|dust|detect|soot|particulate",
    "suppression": r"extinguish|suppress|extinction|inert|diluent",
    "prevention": r"flammab|ignit|burn|flame spread|fire safety|material",
}


DETAIL_KEEP = ["accession", "title", "doi", "licenseName", "totalFileSize", "objective", "approach",
               "hypothesis", "researchImpacts", "experimentHardware"]   # what the atlas uses


def slim_detail(d):
    """Detail responses can be 8 MB (huge file lists); cache only the fields we use."""
    out = {k: d.get(k) for k in DETAIL_KEEP}
    out["publications"] = [{"title": p.get("title")} for p in d.get("publications", [])]
    out["experimentalTable"] = [{"file_name": t.get("file_name")} for t in d.get("experimentalTable", [])]
    return out


def get_json(url, cache_file, refresh=False, slim=None):
    if cache_file.exists() and not refresh:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"Accept": "application-json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    if slim:
        data = slim(data)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def tidy(text):
    """PSI text sometimes contains U+FFFD where an apostrophe was; squeeze whitespace."""
    text = (text or "").replace("�", "'")
    return " ".join(text.split())


def family_of(acc, project_type):
    for fam, members in FAMILIES.items():
        if acc in members:
            return fam
    return "Ground / modelling studies" if "Ground" in (project_type or "") else "Other"


def keyword_phase(*texts):
    blob = " ".join(texts).lower()
    return [ph for ph, pat in PHASE_KEYWORDS.items() if re.search(pat, blob)]


def read_table(path):
    """PSI CSVs mix encodings, BOMs, double spaces and trailing spaces in headers."""
    df = pd.read_csv(path, encoding="cp1252", dtype=str).dropna(how="all")
    df.columns = [" ".join(c.replace("﻿", "").replace("ï»¿", "").split()) for c in df.columns]
    return df


def num(series):
    return pd.to_numeric(series.str.strip(), errors="coerce").dropna()


def envelopes_from_tables(raw_dir=Path("data/raw")):
    """Recompute tested O2 / pressure envelopes from downloaded tables (beats hand-typing)."""
    found = {}
    bass2 = raw_dir / "PSI-25_Experimental table_BASS-II.csv"
    if bass2.exists():
        df = read_table(bass2)
        col = "Calibrated initial O2 % by vol"
        o2 = num(df[col]) / 100.0 if col in df.columns else pd.Series(dtype=float)
        if len(o2):
            found["PSI-25"] = {"tested_o2_min": round(float(o2.min()), 3),
                               "tested_o2_max": round(float(o2.max()), 3),
                               "envelope_source": f"O2 computed from '{col}' ({len(o2)} tests)"}
    normal = raw_dir / "PSI-159_Experimental table_CFI-G_Normal Flames.csv"
    inverse = raw_dir / "PSI-159_Experimental table_CFI-G_Inverse Flames.csv"
    if normal.exists() and inverse.exists():
        n, i = read_table(normal), read_table(inverse)
        o2 = num(n["XO2 before test"])                        # chamber (ambient) O2, normal flames
        p_atm = pd.concat([num(n["approx p (bar)"]), num(i["approx p (bar)"])]) * 0.98692
        found["PSI-159"] = {"tested_o2_min": round(float(o2.min()), 3),
                            "tested_o2_max": round(float(o2.max()), 3),
                            "tested_p_min_atm": round(float(p_atm.min()), 2),
                            "tested_p_max_atm": round(float(p_atm.max()), 2),
                            "envelope_source": "chamber O2 from 'XO2 before test' (normal flames); "
                                               "pressure from 'approx p (bar)' in both tables, x0.98692"}
    return found


def real_test_points(raw_dir=Path("data/raw")):
    """(O2 mole fraction, pressure atm) of every real test comparable with an O2/N2 habitat atmosphere,
    from the per-test tables. Lets the app count real tests near ANY atmosphere, not just presets."""
    pts = {}
    flex = Path("data/processed/flex_clean.csv")
    if flex.exists():
        f = pd.read_csv(flex)
        f = f[(f["x_co2"] == 0) & (f["x_he"] == 0)]          # habitats are O2/N2: skip suppressant mixes
        pts["PSI-69"] = f[["x_o2", "p_atm"]].dropna().round(4).values.tolist()
    normal = raw_dir / "PSI-159_Experimental table_CFI-G_Normal Flames.csv"
    if normal.exists():
        n = read_table(normal)
        both = pd.DataFrame({"o2": pd.to_numeric(n["XO2 before test"], errors="coerce"),
                             "p": pd.to_numeric(n["approx p (bar)"], errors="coerce") * 0.98692}).dropna()
        pts["PSI-159"] = both.round(4).values.tolist()
    return pts


def tests_near_scenarios(points):
    """Count REAL tests near each habitat atmosphere (joint O2 + pressure, not separate ranges)."""
    out = {}
    for acc, xy in points.items():
        d = pd.DataFrame(xy, columns=["o2", "p"])
        out[acc] = {k: int(near_mask(d["o2"], d["p"], o2, p).sum()) for k, (_, o2, p, _) in SCENARIOS.items()}
    return out


def main(refresh=False):
    search = get_json(f"{API}/repo/search?source=psi&type=investigation&size=200",
                      CACHE / "search_investigations.json", refresh)
    hits = [h["_source"] for h in search["hits"]["hits"]]
    combustion = [h for h in hits if h.get("Research Area") == "Combustion Science"]
    combustion.sort(key=lambda h: int(h["Accession"].split("-")[1]))
    curation = json.loads(CURATION.read_text(encoding="utf-8"))
    computed = envelopes_from_tables()
    points = real_test_points()
    near = tests_near_scenarios(points)

    records = []
    for h in combustion:
        acc = h["Accession"]
        d = get_json(f"{API}/repo/investigations/{acc}", CACHE / f"{acc}.json", refresh, slim=slim_detail)
        cur = {**curation.get(acc, {}), **computed.get(acc, {})}
        pubs = [tidy(p.get("title")) for p in d.get("publications", []) if p.get("title")]
        size = d.get("totalFileSize")
        rec = {
            "accession": acc,
            "acronym": tidy(h.get("Acronym")) or tidy(h.get("Title"))[:40],
            "title": tidy(h.get("Title")),
            "family": family_of(acc, h.get("Project Type")),
            "project_type": tidy(h.get("Project Type")),
            "platform": tidy(h.get("Flight Platform")) or "n/a (ground study)",
            "hardware": tidy(d.get("experimentHardware")) or tidy((h.get("Experiment Hardware") or {}).get("Name")),
            "sub_area": tidy(h.get("SubResearch Area")),
            "start": tidy(h.get("Investigation Start Date")),
            "end": tidy(h.get("Investigation End Date")),
            "objective": tidy(d.get("objective") or h.get("Objectives")),
            "approach": tidy(d.get("approach") or h.get("Approach")),
            "hypothesis": tidy(d.get("hypothesis") or h.get("Hypothesis")),
            "impacts": tidy(d.get("researchImpacts") or h.get("Research Impacts/Earth Benefits")),
            "keywords": tidy(h.get("Keywords")),
            "n_publications": len(pubs),
            "publications": pubs[:8],
            "doi": tidy(d.get("doi")) or None,
            "license": tidy(d.get("licenseName")) or None,
            "data_size_gb": round(size / 1e9, 1) if isinstance(size, (int, float)) else None,
            "table_files": [t.get("file_name") for t in d.get("experimentalTable", []) if t.get("file_name")],
            "page": PAGE.format(acc),
            # ---- curated (verified) fields; None = not curated yet ----
            "phase": cur.get("phase") or keyword_phase(h.get("Title", ""), h.get("SubResearch Area", ""),
                                                      h.get("Objectives", "")),
            "phase_source": "curated" if cur.get("phase") else "keyword guess",
            "fuel_type": cur.get("fuel_type") or tidy(h.get("SubResearch Area")),
            "tested_o2_min": cur.get("tested_o2_min"),
            "tested_o2_max": cur.get("tested_o2_max"),
            "tested_p_min_atm": cur.get("tested_p_min_atm"),
            "tested_p_max_atm": cur.get("tested_p_max_atm"),
            "rows": cur.get("rows"),
            "has_outcome_table": bool(cur.get("has_outcome_table", False)),
            "outcomes": cur.get("outcomes"),
            "notes": cur.get("notes"),
            "tests_near": near.get(acc),   # {scenario key: number of real tests}, None = not computed
            "test_points": points.get(acc),   # [[O2, p_atm], ...] of real O2/N2 tests, None = no per-test table
            "tests_near_rule": (f"real tests within +/-{P_TOL} atm of the target pressure with O2 >= target"
                                if acc in near else None),
            "curation_source": "; ".join(s for s in [cur.get("source"), cur.get("envelope_source")] if s) or None,
        }
        records.append(rec)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
    n_cur = sum(r["accession"] in curation for r in records)
    print(f"{len(records)} combustion investigations -> {OUT}  ({n_cur} with curated facts)")
    for r in records:
        print(f"  {r['accession']:8} {r['acronym'][:28]:28} {r['family'][:34]:34} pubs={r['n_publications']:3}"
              f"  O2max={r['tested_o2_max']}  Pmin={r['tested_p_min_atm']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="ignore cache and re-query PSI")
    main(ap.parse_args().refresh)
