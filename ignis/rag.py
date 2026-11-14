"""STARTER CODE - keyword (BM25) retrieval over NASA passages; no LLM needed.
Optional upgrade: pass the top passages to an LLM with the instruction
'Answer only from the numbered excerpts, cite [n] after each claim, otherwise say
"not found in the provided NASA documents"', and still show the passages.

Added during the event: the optional grounded LLM answer (call_llm, only on a button click) and
verify(), which keeps a sentence only if it cites a passage and every number in it appears
literally in a cited passage."""
import http.client
import json
import os
import re
import urllib.request
from pathlib import Path

import streamlit as st
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]
NOT_FOUND = "not found in the provided NASA documents"
INSTRUCTION = ("Answer only from the numbered excerpts, cite [n] after every sentence, copy numbers exactly, "
               f"otherwise reply: {NOT_FOUND}")


# ---------------------------------------------------------------- retrieval (no LLM)
def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())   # keeps 'flex-2', 'n-heptane'


@st.cache_resource
def load_index():
    chunks = json.loads((ROOT / "data/docs_index/chunks.json").read_text(encoding="utf-8"))
    return chunks, BM25Okapi([tokenize(c["text"]) for c in chunks])


def search(question, chunks, bm25, k=5):
    scores = bm25.get_scores(tokenize(question))
    best = scores.argsort()[::-1][:k]
    return [{**chunks[i], "score": float(scores[i])} for i in best if scores[i] > 0]


# ---------------------------------------------------------------- LLM call (provider-agnostic)
class LLMUnavailable(RuntimeError):
    """No key configured, or the provider failed - callers fall back to retrieval only."""


def _setting(name, default=None):
    try:
        value = st.secrets.get(name)          # .streamlit/secrets.toml or Streamlit Cloud secrets
    except Exception:                          # no secrets file at all
        value = None
    return value or os.environ.get(name) or default


def llm_provider():
    """Which provider is configured: 'gemini', 'groq' or None (no key -> retrieval only)."""
    if _setting("GEMINI_API_KEY"):
        return "gemini"
    if _setting("GROQ_API_KEY"):
        return "groq"
    return None


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def call_llm(prompt, timeout=45):
    """Return (text, provider_and_model). Raises LLMUnavailable on missing key or any API error.
    Model names are settings (GEMINI_MODEL / GROQ_MODEL) - check them in the provider console."""
    provider = llm_provider()
    try:
        if provider == "gemini":
            model = _setting("GEMINI_MODEL", "gemini-flash-latest")
            data = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                         {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}},
                         {"x-goog-api-key": _setting("GEMINI_API_KEY")}, timeout)
            return data["candidates"][0]["content"]["parts"][0]["text"], f"gemini/{model}"
        if provider == "groq":
            model = _setting("GROQ_MODEL", "openai/gpt-oss-20b")
            data = _post("https://api.groq.com/openai/v1/chat/completions",
                         {"model": model, "temperature": 0.1, "messages": [{"role": "user", "content": prompt}]},
                         {"Authorization": f"Bearer {_setting('GROQ_API_KEY')}"}, timeout)
            return data["choices"][0]["message"]["content"], f"groq/{model}"
    except (OSError, http.client.HTTPException, KeyError, IndexError, TypeError, ValueError) as err:
        # OSError covers URLError, timeouts, connection resets; HTTPException covers IncompleteRead
        raise LLMUnavailable(f"{provider} request failed: {type(err).__name__}") from err
    raise LLMUnavailable("no API key configured (GEMINI_API_KEY or GROQ_API_KEY)")


def build_prompt(question, passages):
    excerpts = "\n\n".join(f"[{i}] ({p['title']}, page {p['page']}) {p['text']}"
                           for i, p in enumerate(passages, start=1))
    return f"{INSTRUCTION}\n\nNumbered excerpts:\n{excerpts}\n\nQuestion: {question}\nAnswer:"


# ---------------------------------------------------------------- verifier
_ABBREV = ("et al.", "e.g.", "i.e.", "fig.", "figs.", "eq.", "approx.", "vs.", "no.", "ref.", "sec.", "ca.")
_CITE = re.compile(r"\[(\d+(?:\s*[,;\-–]\s*\d+)*)\]")                  # [1]  [1, 3]  [1-2]  [1–2]
_CITE_ONLY = re.compile(r"^(\[\d+(?:\s*[,;\-–]\s*\d+)*\]\s*)+[.!?]?$")   # a part that is only citations
_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*")


def split_sentences(text):
    """Sentences, without splitting decimals (0.25) or abbreviations (et al., e.g.); a trailing
    citation written after the full stop ('... mm2/s. [1]') stays with its sentence."""
    out = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        for part in re.split(r"(?<=[.!?])\s+", line):
            if not part:
                continue
            if out and (out[-1].lower().endswith(_ABBREV) or _CITE_ONLY.match(part)):
                out[-1] += " " + part
            else:
                out.append(part)
    return [s for s in out if s.strip()]


def cited_numbers(sentence):
    """Passage numbers cited in a sentence; ranges like [1-3] are expanded."""
    cited = set()
    for grp in _CITE.findall(sentence):
        for item in re.split(r"\s*[,;]\s*", grp):
            bounds = [int(x) for x in re.split(r"\s*[\-–]\s*", item) if x]
            cited.update(range(min(bounds), max(bounds) + 1) if len(bounds) == 2 else bounds)
    return cited


def numbers_in(text):
    return [n.rstrip(".,") for n in _NUMBER.findall(_CITE.sub(" ", text))]


def number_supported(num, sources):
    """True if num appears as a whole number in a source ('5' is NOT supported by '0.25');
    thousands separators are ignored ('1,200' == '1200')."""
    plain = num.replace(",", "")
    return any(plain in {n.replace(",", "") for n in numbers_in(s)} for s in sources)


def verify(answer, passages):
    """Keep a sentence only if it cites >= 1 valid passage [n] AND every number in it appears
    literally in one of the cited passages. Returns (kept_text, dropped_sentences)."""
    kept, dropped = [], []
    for sent in split_sentences(answer):
        valid = sorted(n for n in cited_numbers(sent) if 1 <= n <= len(passages))
        sources = [passages[n - 1]["text"] for n in valid]
        has_text = re.search(r"[A-Za-z]", _CITE.sub(" ", sent)) is not None     # not just '[1]'
        if valid and has_text and all(number_supported(num, sources) for num in numbers_in(sent)):
            kept.append(sent)
        else:
            dropped.append(sent)
    return " ".join(kept), dropped
