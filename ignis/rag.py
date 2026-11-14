"""STARTER CODE - keyword (BM25) retrieval over NASA passages; no LLM needed.
Optional upgrade: pass the top passages to an LLM with the instruction
'Answer only from the numbered excerpts, cite [n] after each claim, otherwise say
"not found in the provided NASA documents"', and still show the passages."""
import json
import re
from pathlib import Path

import streamlit as st
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]


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
