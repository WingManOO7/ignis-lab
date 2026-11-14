"""
STARTER CODE - a learning reference. Rewrite/adapt it yourselves during the event.

Turns the NASA PSI-69 FLEX experimental table (274 rows x 15 columns, cp1252 text)
into an ML-ready table plus a log of every data issue we handled.
Column names below are the VERIFIED raw headers (2026-11-13).

Run from the repository root:   python scripts/clean_flex.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/PSI-69_Experimental table_FLEX.csv")
OUT_DIR = Path("data/processed")

RENAME = {
    "FLEX Test #": "row_no",          # re-sequenced 1..274 - NOT the official FLEX number
    "FLEX Identifier": "flex_id",     # the real join key (e.g. 248F001, C11M201)
    "Test Date": "test_date",
    "Test GMT": "test_gmt",
    "Fuel": "fuel",                   # Methanol / Heptane
    "Ambient pressure; mmHg": "p_mmhg",
    "O initial ambient composition; mole fraction": "x_o2",    # 'O' means O2 (subscript lost)
    "N initial ambient composition; mole fraction": "x_n2",    # 'N' means N2
    "CO initial ambient composition; mole fraction": "x_co2",  # 'CO' means CO2
    "He initial ambient composition; mole fraction": "x_he",
    "Droplet initial diameter; mm": "d0_mm",
    "Visible flame extinction diameter; mm": "dext_mm",
    "Burning rate; mm": "k_mm2_s",    # burning-rate constant K, really mm^2/s
    "Burn time; s": "burn_time_s",
    "Test end": "test_end",           # Extinction / Disruption / Completion
}
NUMERIC = ["p_mmhg", "x_o2", "x_n2", "x_co2", "x_he", "d0_mm", "dext_mm", "k_mm2_s", "burn_time_s"]
NOMINAL_ATM = np.array([0.7, 1.0, 2.0, 2.7, 3.0])   # pressure levels seen in the table


def load_raw(path=RAW):
    df = pd.read_csv(path, encoding="cp1252", dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    missing = set(RENAME) - set(df.columns)
    if missing:
        raise ValueError(f"Unexpected header - PSI file changed? Missing: {missing}")
    df = df.rename(columns=RENAME)
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df


def clean(df):
    issues = []

    def log(mask, text):
        for fid in df.loc[mask, "flex_id"]:
            issues.append({"flex_id": fid, "issue": text})

    # 1) Approximate values such as "~6" -> keep a flag, then treat as missing.
    df["burn_time_approx"] = df["burn_time_s"].str.startswith("~")
    log(df["burn_time_approx"], "burn time given as approximate (~); set to NaN")

    # 2) Text -> numbers. The en dash (cp1252 byte 0x96) and blanks become NaN.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col].str.replace("~", "", regex=False), errors="coerce")
    df.loc[df["burn_time_approx"], "burn_time_s"] = np.nan

    # 3) Pressure of 0 mmHg (C11M201) is a transcription error -> NaN.
    zero_p = df["p_mmhg"] == 0
    log(zero_p, "pressure recorded as 0 mmHg; set to NaN")
    df.loc[zero_p, "p_mmhg"] = np.nan
    df["p_atm"] = df["p_mmhg"] / 760.0
    nearest = np.abs(df["p_atm"].to_numpy()[:, None] - NOMINAL_ATM[None, :]).argmin(axis=1)
    df["p_nominal_atm"] = np.where(df["p_atm"].notna(), NOMINAL_ATM[nearest], np.nan)

    # 4) Dates come in two formats (3/5/2009 and 12/14/10).
    df["test_date"] = pd.to_datetime(df["test_date"], format="mixed", errors="coerce")

    # 5) Duplicate identifier 193F001 (two rows, different K) -> keep for display, exclude from ML.
    df["dup_id"] = df["flex_id"].duplicated(keep=False)
    log(df["dup_id"], "duplicate FLEX Identifier; excluded from model training")

    # 6) Gas fractions should sum to ~1 (six rows sum to 0.98 by rounding).
    comp = df[["x_o2", "x_n2", "x_co2", "x_he"]].sum(axis=1)
    log((comp - 1).abs() > 0.015, "gas mole fractions do not sum to 1 (rounding)")

    # 7) Zero extinction diameters are not physical diameters -> NaN for regression.
    df["dext_target_mm"] = df["dext_mm"].where((df["test_end"] == "Extinction") & (df["dext_mm"] > 0))

    # 8) Disruption may be caused by needle-coating contamination (NASA/TP-2015-216046 sec. 5.2).
    log(df["test_end"] == "Disruption", "Disruption: possible needle contamination; not a clean label")

    # Derived columns (all known BEFORE ignition, so legal model inputs)
    df["diluent"] = np.select([df["x_co2"] > 0, df["x_he"] > 0], ["CO2", "He"], default="N2")
    df["p_o2_atm"] = df["x_o2"] * df["p_atm"]          # oxygen partial pressure
    df["campaign_id"] = df["flex_id"].str[:3]           # e.g. C11, 193, H19 (same fill/day series)
    key = ["p_nominal_atm", "x_o2", "x_n2", "x_co2", "x_he"]   # repeats of one condition share this id
    df["condition_id"] = df["fuel"] + "|" + df[key].apply(
        lambda row: "|".join(f"{v:.2f}" for v in row), axis=1)   # f-string keeps 'nan' visible

    # Targets (NaN = not usable for that task)
    df["y_extinction"] = df["test_end"].map({"Extinction": 1.0, "Completion": 0.0})  # Disruption -> NaN
    df["k_target"] = df["k_mm2_s"].where(df["k_mm2_s"] > 0)
    return df, pd.DataFrame(issues)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_df, issues_df = clean(load_raw())
    clean_df.to_csv(OUT_DIR / "flex_clean.csv", index=False)
    issues_df.to_csv(OUT_DIR / "flex_data_issues.csv", index=False)
    feats = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
    complete = clean_df[feats].notna().all(axis=1) & ~clean_df["dup_id"]
    print("rows:", len(clean_df), "| outcome counts:", clean_df["test_end"].value_counts().to_dict())
    print("condition groups:", clean_df["condition_id"].nunique(),
          "| campaign groups:", clean_df["campaign_id"].nunique())
    print("usable rows - extinction vs completion:", int((complete & clean_df["y_extinction"].notna()).sum()),
          "| K:", int((complete & clean_df["k_target"].notna()).sum()),
          "| extinction diameter:", int((complete & clean_df["dext_target_mm"].notna()).sum()))
    print("logged issues:", len(issues_df))
