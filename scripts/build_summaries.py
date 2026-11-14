"""
OFFLINE: generate a 2-3 sentence plain-language summary of each PSI investigation, grounded only in its NASA
metadata (title, objective, approach, platform, hardware), and save data/atlas/summaries.json.
The app never calls the LLM for this; it only reads the saved file (ignis.data.load_summaries: {} if absent).

Every sentence goes through the same checker as the Ask page (ignis.rag.verify_report, with the NASA metadata as
the only source, counted as cited): no link/image/URL/HTML, every number (digits or words such as 'twelve';
percentages as percentages) must appear in the metadata, >= 50% of its keywords must appear in it, and a
not/never/no only if the metadata says so too. Failing sentences are dropped and listed. This is an automatic
citation, number and keyword check - not a guarantee: review every summary by hand before committing.
Each entry is labelled "AI-generated offline, reviewed by the team".

Needs GEMINI_API_KEY or GROQ_API_KEY (environment variable or .streamlit/secrets.toml); without a key nothing is
written. Run from the repository root (after build_atlas.py):
    python scripts/build_summaries.py                 # all investigations
    python scripts/build_summaries.py --only PSI-69   # just one (or several)
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ignis.rag import OFFLINE_LABEL, LLMUnavailable, call_llm, llm_provider, verify_report  # noqa: E402

ATLAS = ROOT / "data/atlas/investigations.json"
OUT = ROOT / "data/atlas/summaries.json"
PROMPT = ("Write a 2-3 sentence plain-language summary of this NASA investigation for university students. "
          "Use ONLY the NASA metadata below and reuse its own words. Do not add facts, numbers, dates or claims "
          "that are not in it. Plain text only: no citations, links, bullet points or formatting.\n\n"
          "NASA metadata:\n{meta}\n\nSummary:")


def metadata_text(r):
    return "\n".join(f"{k}: {r.get(k) or ''}" for k in ["title", "platform", "hardware", "objective", "approach"])


def check_summary(raw, meta):
    """(kept_text, [[sentence, reason], ...]) - the Ask page's verifier with the metadata as the only source."""
    report = verify_report(raw, [{"text": meta}], require_citation=False)
    return " ".join(s for s, r in report if r is None), [[s, r] for s, r in report if r]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", nargs="*", help="accession numbers to (re)generate, e.g. PSI-69")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between LLM calls (free-tier rate limits)")
    args = ap.parse_args(argv)
    if not llm_provider():
        print("No GEMINI_API_KEY or GROQ_API_KEY configured - nothing generated (the app shows NASA's text).")
        return 0
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    records = [r for r in json.loads(ATLAS.read_text(encoding="utf-8"))
               if not args.only or r["accession"] in args.only]
    for i, r in enumerate(records):
        if i:
            time.sleep(args.pause)
        meta = metadata_text(r)
        try:
            raw, model = call_llm(PROMPT.format(meta=meta))
        except LLMUnavailable as err:
            print(f"{r['accession']}: skipped ({err})")
            continue
        kept, dropped = check_summary(raw, meta)
        if not kept:
            print(f"{r['accession']}: every sentence failed the check - not saved ({len(dropped)} dropped)")
            continue
        out[r["accession"]] = {"summary": kept, "dropped": dropped, "model": model, "label": OFFLINE_LABEL,
                               "generated": date.today().isoformat()}
        print(f"{r['accession']}: saved, {len(dropped)} sentence(s) dropped by the check")
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {OUT.relative_to(ROOT)} ({len(out)} summaries) - review every summary by hand before committing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
