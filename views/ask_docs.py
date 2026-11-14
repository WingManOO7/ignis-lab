"""Ask the NASA documents: BM25 search over 8 NASA reports.
Default answer: 2-3 sentences extracted verbatim from the retrieved passages (no LLM, works without any key).
Optional AI answer: only with a key, only on a click, capped per session and per day, then an automatic citation,
number and keyword check - not a guarantee; read the passages. All answers are shown as plain text (st.text), so
they cannot render links, images or HTML."""
import time
from datetime import date

import streamlit as st

from ignis import rag, ui

DEFAULT_Q = "Why does a droplet flame go out at a large diameter?"
RULES = ("Kept sentences must: contain no link, image, URL or HTML; cite a passage [n]; have every number (digits or "
         "words; percentages as percentages) in that passage; share at least half of their keywords with it; and "
         "say not/never/no only if the passage does. It checks words and numbers, not meaning: "
         f"{rag.CHECK_WORDING}.")

ui.page_header("Ask the NASA documents",
               "Search NASA's reports. Answers cite numbered passages.",
               "8 NASA technical reports (NTRS)")
chunks, bm25 = rag.load_index()
faq = rag.load_faq()

st.session_state.setdefault("ask_q", DEFAULT_Q)


def _use_example():
    if st.session_state.get("ask_example"):
        st.session_state["ask_q"] = st.session_state["ask_example"]


st.text_input("Your question", key="ask_q", max_chars=rag.MAX_QUESTION_CHARS,
              help="Searches FLEX, cool flames, BASS-II, Saffire IV-VI, SAME, ACME and the partial-gravity white "
                   "paper (max 300 characters).")
if faq:
    st.pills(f"Example questions - {rag.OFFLINE_LABEL}", [e["question"] for e in faq], key="ask_example",
             on_change=_use_example,
             help="Answers were generated offline by an LLM from these passages (scripts/build_faq.py), passed the "
                  f"{rag.CHECK_WORDING}, and were reviewed by the team.")
question = rag.clean_question(st.session_state.get("ask_q", ""))
hits = rag.search(question, chunks, bm25, k=5) if question else []

# ---------------------------------------------------------------- pre-generated answer (only if faq.json has one)
entry = rag.faq_answer_for(question, hits, faq) if faq and hits else None
if entry:
    with st.container(border=True, key="ask_faq"):
        ui.section("Team-reviewed answer")
        st.text(entry["answer"])
        st.caption(f"{rag.OFFLINE_LABEL}.",
                   help=f"Generated offline by {entry.get('model', 'an LLM')} from the passages below, kept only "
                        f"where it passed the {rag.CHECK_WORDING}; re-checked now and reviewed by the team.")

# ---------------------------------------------------------------- extracted answer (default, no LLM)
if hits:
    picks = rag.extract_answer(question, hits)
    with st.container(border=True, key="ask_answer"):
        ui.section("Extracted answer")
        for line in (rag.format_extract(picks).splitlines() if picks
                     else ["No single sentence matches well - read the passages below."]):
            st.text(line)
        st.caption(f"{rag.EXTRACT_LABEL}.",
                   help="The 2-3 sentences of the passages below that best match your question (BM25 keyword "
                        "score), copied word for word; [n] is the passage number. Picked by keyword match only, "
                        "so read them in context.")

# ---------------------------------------------------------------- optional AI answer (key + click + caps)
provider = rag.llm_provider()
today = date.today().isoformat()
daily, limit = rag.daily_counts(), rag.daily_limit()
block = rag.llm_block(st.session_state, daily, time.time(), today, limit) if provider else None
capped = bool(block) and block[0] != "cooldown"
c1, c2 = st.columns([1, 2.6], vertical_alignment="center")
clicked = c1.button("Generate cited answer", type="primary", key="ask_generate", icon=":material/auto_awesome:",
                    width="stretch", disabled=not (provider and hits) or capped)
if not provider:
    c2.caption("Retrieval only: no LLM key set.",
               help="No GEMINI_API_KEY or GROQ_API_KEY is configured, so no AI is called. The answer above is "
                    "extracted from NASA text. Add a key to Streamlit secrets to enable the optional AI answer.")
elif capped:
    c2.caption(f"AI limit reached ({block[1]}): extracted answer only.",
               help=f"Cost and abuse control: {rag.SESSION_MAX} AI answers per session, {rag.COOLDOWN_S} s apart, "
                    f"{limit} per day for the whole app.")
else:
    left = max(0, rag.SESSION_MAX - st.session_state.get("llm_calls", 0))
    c2.caption(f"Optional AI answer ({provider}), only when you click.",
               help=f"Sends your question and the passages below to {provider}. The answer is AI-generated, then "
                    f"gets an {rag.CHECK_WORDING}. {left} of {rag.SESSION_MAX} AI answers left in this session, "
                    f"{rag.COOLDOWN_S} s apart.")

res = st.session_state.get("ask_result")
if clicked and provider and hits and not (res and res.get("q") == question and not res.get("error")):
    with st.spinner("Asking the AI..."):
        out = rag.ai_answer(question, hits, st.session_state, daily, time.time(), today, limit)
    if out.get("blocked"):
        ui.note(f"AI not called: {out['blocked'][1]}. The extracted answer is shown instead.", "quiet")
    else:
        st.session_state["ask_result"] = res = out

if res and res.get("q") == question:
    if res.get("error"):
        ui.note("AI answer unavailable: extracted answer only.", "quiet", details=res["error"])
    elif not res["kept"]:
        ui.note("The AI found no answer in these passages." if res["not_found"]
                else "No AI sentence passed the check, so none is shown.", "quiet", details=RULES)
    else:
        with st.container(border=True, key="ask_ai"):
            ui.section("AI answer, checked")
            st.text(res["kept"])
            st.caption(f"AI-generated by {res['model']}: {rag.CHECK_WORDING}.", help=RULES)
    if res.get("dropped"):
        with st.expander(f"{len(res['dropped'])} AI sentence(s) removed by the check"):
            for s, reason in res["dropped"]:
                st.text(f"- {s}  ({reason})")

# ---------------------------------------------------------------- the NASA passages themselves
if hits:
    ui.section("NASA source passages", f"top {len(hits)} matches")
for i, hit in enumerate(hits, start=1):
    with st.expander(f"[{i}] {hit['title']} - page {hit['page']} (match score {hit['score']:.1f})"):
        st.text(hit["text"])
        st.markdown(f"[Open source document]({hit['url']})")
if question and not hits:
    st.info("No match. Try 'extinction', 'cool flame' or 'smoke detector'.")
