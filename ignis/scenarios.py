"""Crew-habitat atmospheres and coverage logic shared by every page (single source of truth).
SCENARIOS key: (label, O2 mole fraction, pressure in atm, where the numbers come from)"""
import pandas as pd

SCENARIOS = {
    "iss": ("ISS cabin (14.7 psia, 21% O2)", 0.21, 1.00, "ISS normal atmosphere"),
    "lunar": ("Lunar habitat per challenge brief (<=10.2 psi, >=30% O2)", 0.30, 0.69, "challenge brief"),
    "exploration": ("Exploration atmosphere (8.2 psia, 34% O2)", 0.34, 0.56, "NASA exploration atmosphere"),
}
LABEL_TO_KEY = {v[0]: k for k, v in SCENARIOS.items()}

# A real test counts as "near" a scenario if its pressure is within +/-P_TOL atm and its
# oxygen is at least the scenario's (more O2 = harder fire-safety case, so it still informs it).
P_TOL, O2_TOL = 0.10, 0.01


def near_mask(o2_series, p_series, o2_target, p_target):
    return (o2_series >= o2_target - O2_TOL) & ((p_series - p_target).abs() <= P_TOL)


def scenario_key_for(o2, p):
    """Return the scenario key if (o2, p) is exactly a preset, else None."""
    for key, (_, o2_t, p_t, _) in SCENARIOS.items():
        if abs(o2 - o2_t) < 1e-9 and abs(p - p_t) < 1e-9:
            return key
    return None


def coverage(row, o2_t, p_t, skey=None):
    """How well one investigation (atlas row) covers an atmosphere -> (status, detail).
    status: 'yes' | 'likely' | 'partial' | 'no' | 'unknown'.
    Uses real-test counts from the experimental tables when they exist for this scenario,
    otherwise the curated tested ranges (which do not prove the combination was run)."""
    points = row.get("test_points")
    if isinstance(points, list) and points:                # per-test table: count real tests, any atmosphere
        d = pd.DataFrame(points, columns=["o2", "p"])
        n = int(near_mask(d["o2"], d["p"], o2_t, p_t).sum())
        return ("yes", f"YES - {n} real tests near target") if n else ("no", "NO - 0 real tests near target")
    o2_max, p_min, p_max = row.get("tested_o2_max"), row.get("tested_p_min_atm"), row.get("tested_p_max_atm")
    if pd.isna(o2_max) and pd.isna(p_min):
        return "unknown", "? envelope not curated yet"
    o2_ok = pd.notna(o2_max) and o2_max >= o2_t - O2_TOL
    # an unknown upper pressure is NOT 'unbounded': only accept targets at the known minimum
    p_top_ok = (p_max >= p_t - 0.05) if pd.notna(p_max) else (p_t <= p_min + 0.05 if pd.notna(p_min) else False)
    p_ok = pd.notna(p_min) and p_min <= p_t + 0.05 and p_top_ok
    if o2_ok and p_ok:
        return "likely", "LIKELY - O2 and pressure ranges include target"
    if o2_ok or p_ok:
        return "partial", "PARTIAL - only the " + ("O2" if o2_ok else "pressure") + " range includes target"
    return "no", "NO - outside the tested envelope"


def covering_investigations(atlas, o2, p):
    """Atlas rows (DataFrame) that tested at or near (o2, p), strongest evidence first."""
    skey = scenario_key_for(o2, p)
    rows = []
    for _, r in atlas.iterrows():
        status, detail = coverage(r, o2, p, skey)
        if status in ("yes", "likely"):
            rows.append({"acronym": r["acronym"], "evidence": detail, "fuel / sample": r["fuel_type"],
                         "title": r["title"], "page": r["page"], "_rank": 0 if status == "yes" else 1})
    out = pd.DataFrame(rows)
    return out.sort_values("_rank").drop(columns="_rank") if len(out) else out
