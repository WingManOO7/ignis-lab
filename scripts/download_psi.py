"""
STARTER CODE - a learning reference. Rewrite/adapt it yourselves during the event.

Downloads small NASA PSI files through the JSON API that psi.nasa.gov itself uses.
VERIFIED to work without any login on 2026-11-13, but the API is UNDOCUMENTED:
if it breaks, download the same files from the website instead
(https://psi.nasa.gov/physci/repo/data/investigations/PSI-69).

Run from the repository root:   python scripts/download_psi.py
Optional d^2(t) histories:      python scripts/download_psi.py --droplets 20
"""
import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://psi.nasa.gov/geode-py/ws"
RAW_DIR = Path("data/raw")
HEADERS = {"Accept": "application-json", "user_token": ""}  # what the website sends

# (PSI accession, exact file name, file version seen on 2026-11-13)
TABLES = [
    ("PSI-69", "PSI-69_Experimental table_FLEX.csv", 4),                    # FLEX: 274 rows
    ("PSI-68", "PSI-68_Experimental table_Flex2.csv", 6),                   # FLEX-2: 8-row design ranges
    ("PSI-39", "PSI-39_Experimental table_CFI.csv", 4),                     # CFI droplets: inputs only
    ("PSI-159", "PSI-159_Experimental table_CFI-G_Normal Flames.csv", 1),   # ACME CFI-G
    ("PSI-159", "PSI-159_Experimental table_CFI-G_Inverse Flames.csv", 1),
    ("PSI-101", "PSI-101_Experimental table_SAME-R.csv", 1),                # SAME-R
    ("PSI-25", "PSI-25_Experimental table_BASS-II.csv", 1),                 # BASS-II
]


def get_json(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def signed_url(psi_id, file_name, version):
    """Ask PSI for a short-lived pre-signed S3 link (plain text body)."""
    query = urllib.parse.urlencode({"file": file_name, "version": version, "redirect": "false"})
    req = urllib.request.Request(f"{API}/studies/{psi_id}/download?{query}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode().strip().strip('"')


def download(psi_id, file_name, version, out_dir=RAW_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / file_name
    if target.exists():
        print(f"skip (already downloaded): {target}")
        return target
    # Try the verified version first, then other version numbers (versions can change).
    for v in [version] + [x for x in range(1, 9) if x != version]:
        try:
            link = signed_url(psi_id, file_name, v)      # links expire: never store them
            with urllib.request.urlopen(link, timeout=300) as resp:
                target.write_bytes(resp.read())
            print(f"OK   {psi_id} v{v}  {file_name}  ({target.stat().st_size:,} bytes)")
            return target
        except urllib.error.HTTPError as err:
            print(f"     {psi_id} v{v} failed (HTTP {err.code}), trying another version")
            time.sleep(0.5)
    raise RuntimeError(f"Could not download {file_name}. Use the PSI website instead.")


def flex_droplet_histories(limit):
    """OPTIONAL Tier-2 data: FLEX-###_DropletData.txt files (tab-separated d(t) series).
    They are named by the OFFICIAL FLEX number, so we read each file's folder name
    (e.g. 'FLEX 018_01_Jul_2009_Hep_248F001' or 'FLEX_020_24_Oct_2009_MeOH_192F001')
    to recover the 7-character FLEX Identifier join key. The earliest folders end in
    '_Air' instead: take their identifier from FLEX-###_TestSheet.txt ('CIR Test Number')."""
    listing = get_json(f"{API}/repo/investigations/PSI-69/versions")   # ~6.5 MB JSON
    records = [r for v in listing.get("versions", []) for r in v.get("added", [])]
    found = {}
    for r in records:
        name = r.get("file_name", "")
        if not name.endswith("_DropletData.txt"):
            continue
        folder = html.unescape(r.get("subcategory") or "").rstrip("/").split("/")[-1]
        m = re.match(r"FLEX[ _](\d+)_.*_([0-9A-Za-z]{7})$", folder)
        found[name] = {"file_name": name, "folder": folder,
                       "flex_number": int(name.split("-")[1].split("_")[0]),
                       "flex_id": m.group(2) if m else None,      # None -> look it up in the TestSheet
                       "version": r.get("version", 5)}
    index = sorted(found.values(), key=lambda d: d["flex_number"])
    out_dir = RAW_DIR / "droplet_histories"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"{len(index)} DropletData files found; downloading {limit}")
    for item in index[:limit]:
        download("PSI-69", item["file_name"], item["version"], out_dir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--droplets", type=int, default=0, help="also fetch N d(t) histories")
    args = ap.parse_args()
    for psi_id, name, version in TABLES:
        download(psi_id, name, version)
    meta = get_json(f"{API}/repo/investigations/PSI-69")
    (RAW_DIR / "PSI-69_metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("Saved PSI-69 metadata JSON (title, DOI, licence, file list for the experimental table).")
    if args.droplets:
        flex_droplet_histories(args.droplets)
