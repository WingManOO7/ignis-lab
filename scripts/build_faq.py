"""
OFFLINE: build data/docs_index/faq.json - example questions with LLM answers over the NASA document index, shown
on the Ask page as "Example questions - AI-generated offline, reviewed by the team".

Questions: the team-written QUESTIONS list below (14; edit freely). For each one this runs exactly what the Ask
page runs: the same BM25 retrieval (top 5 passages), the same fixed prompt (ignis.rag.build_prompt) and
ignis.rag.verify() - the automatic citation, number and keyword check (not a guarantee). Only sentences that pass
are stored; a question whose answer is "not found" or loses every sentence is left out. The app re-checks each
stored answer when it shows it, and hides it if its passages no longer match (index rebuilt).
Review every answer by hand before committing.

Needs GEMINI_API_KEY or GROQ_API_KEY (environment variable or .streamlit/secrets.toml); without a key nothing is
written (faq.json stays as it is; [] or absent = the page shows no examples).
Run from the repository root (after build_doc_index.py):   python scripts/build_faq.py [--pause 6]
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ignis.rag import (FAQ_PATH, OFFLINE_LABEL, LLMUnavailable, build_prompt, call_llm, clean_question,  # noqa: E402
                       llm_provider, load_index, search, verify)

QUESTIONS = [
    "Why does a droplet flame go out at a large diameter?",
    "What is a cool flame?",
    "What happens after the visible flame goes out?",
    "What did FLEX measure?",
    "How does helium dilution change droplet burning?",
    "How does carbon dioxide affect droplet flame extinction?",
    "How is smoke detected on the ISS?",
    "What did the Saffire experiments burn?",
    "How large can a fire grow on a spacecraft?",
    "How does air flow speed affect flame spread over solid materials?",
    "What did BASS-II study?",
    "What does ACME study?",
    "How does partial gravity affect the flammability of solid fuels?",
    "What is the limiting oxygen concentration for burning solids in microgravity?",
]


def faq_entry(question, hits, raw, model):
    """The stored FAQ record, or None if no sentence passes verify() (a bare 'not found' reply has no [n], so it
    never passes)."""
    kept, dropped = verify(raw, hits)
    if not kept:
        return None
    return {"question": question, "answer": kept, "passage_ids": [h["id"] for h in hits],
            "sources": [{"n": i, "title": h["title"], "page": h["page"], "url": h["url"]}
                        for i, h in enumerate(hits, start=1)],
            "dropped": len(dropped), "model": model, "label": OFFLINE_LABEL, "generated": date.today().isoformat()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between LLM calls (free-tier rate limits)")
    args = ap.parse_args(argv)
    if not llm_provider():
        print("No GEMINI_API_KEY or GROQ_API_KEY configured - nothing generated (the Ask page shows no examples).")
        return 0
    chunks, bm25 = load_index()
    out = []
    for i, q in enumerate(QUESTIONS):
        if i:
            time.sleep(args.pause)
        q = clean_question(q)
        hits = search(q, chunks, bm25, k=5)
        if not hits:
            print(f"- {q}: no passages")
            continue
        try:
            raw, model = call_llm(build_prompt(q, hits))
        except LLMUnavailable as err:
            print(f"- {q}: skipped ({err})")
            continue
        entry = faq_entry(q, hits, raw, model)
        print(f"- {q}: {'kept' if entry else 'left out (nothing passed the check)'}")
        if entry:
            out.append(entry)
    if not out:
        print("no answer passed the check - faq.json left unchanged")
        return 1
    FAQ_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {FAQ_PATH.relative_to(ROOT)} ({len(out)} Q&A) - review every answer by hand before committing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
