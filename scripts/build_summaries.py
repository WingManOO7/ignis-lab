"""
OFFLINE: generate a 2-3 sentence plain-language summary of each PSI investigation, grounded only in
its NASA metadata (title, objective, approach, platform, hardware), and save data/atlas/summaries.json.
The app never calls the LLM for this; it only reads the saved file.

Every sentence is number-checked: a sentence is dropped if it contains a number that does not appear
literally in the NASA metadata text. Review the output by hand before committing it.

Needs GEMINI_API_KEY or GROQ_API_KEY (environment variable or .streamlit/secrets.toml).
Run from the repository root (after build_atlas.py):   python scripts/build_summaries.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ignis.rag import LLMUnavailable, call_llm, llm_provider, number_supported, numbers_in, split_sentences  # noqa: E402

ATLAS = Path("data/atlas/investigations.json")
OUT = Path("data/atlas/summaries.json")
PROMPT = ("Write a 2-3 sentence plain-language summary of this NASA investigation for university students. "
          "Use ONLY the NASA metadata below. Do not add facts, numbers, dates or claims that are not in it. "
          "No citations, no bullet points.\n\nNASA metadata:\n{meta}\n\nSummary:")


def metadata_text(r):
    return "\n".join(f"{k}: {r.get(k) or ''}" for k in ["title", "platform", "hardware", "objective", "approach"])


def main():
    if not llm_provider():
        print("No GEMINI_API_KEY or GROQ_API_KEY configured - nothing generated (the app shows NASA's text).")
        return
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for r in json.loads(ATLAS.read_text(encoding="utf-8")):
        meta = metadata_text(r)
        try:
            raw, model = call_llm(PROMPT.format(meta=meta))
        except LLMUnavailable as err:
            print(f"{r['accession']}: skipped ({err})")
            continue
        kept, dropped = [], []
        for s in split_sentences(raw):
            (kept if all(number_supported(n, [meta]) for n in numbers_in(s)) else dropped).append(s)
        out[r["accession"]] = {"summary": " ".join(kept), "dropped": dropped, "model": model}
        print(f"{r['accession']}: {len(kept)} sentences kept, {len(dropped)} dropped")
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {OUT} - review every summary by hand before committing")


if __name__ == "__main__":
    main()
