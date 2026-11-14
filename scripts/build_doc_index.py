"""
STARTER CODE - a learning reference. Rewrite/adapt it yourselves during the event.

Builds a small, citable passage index over public NASA documents (retrieval only, no LLM).
Run from the repository root:   python scripts/build_doc_index.py
"""
import json
import unicodedata
import urllib.request
from pathlib import Path

from pypdf import PdfReader

DOCS, OUT = Path("data/docs"), Path("data/docs_index")
SOURCES = [  # (local file, citation title, public URL) - all public NASA documents
    ("flex_tp_2015.pdf", "Dietrich et al., FLEX detailed results, NASA/TP-2015-216046",
     "https://ntrs.nasa.gov/api/citations/20150023456/downloads/20150023456.pdf"),
    ("flex_coolflame_2014.pdf", "Nayagam et al., Cool-flame extinction of n-alkane droplets (2014)",
     "https://ntrs.nasa.gov/api/citations/20140006750/downloads/20140006750.pdf"),
    ("bass2_tm_2021.pdf", "Olson et al., BASS-II summary report, NASA/TM-20210011385",
     "https://ntrs.nasa.gov/api/citations/20210011385/downloads/TM-20210011385.pdf"),
    ("saffire_ices_2021.pdf", "Urban et al., Saffire IV and V, ICES 2021",
     "https://ntrs.nasa.gov/api/citations/20210011521/downloads/ICES%202021-266%200503-2021%20final.pdf"),
    ("saffire6_ices_2024.pdf", "Urban et al., Saffire VI, ICES 2024",
     "https://ntrs.nasa.gov/api/citations/20240002981/downloads/Saffire-ICES-2024-ICES-365-accepted%20final.pdf"),
    ("same_factsheet.pdf", "NASA SAME fact sheet",
     "https://www.nasa.gov/wp-content/uploads/2025/07/smoke-aerosol-measurement-experiment-same.pdf"),
    ("acme_overview_2021.pdf", "Stocker, ACME overview (2021)",
     "https://ntrs.nasa.gov/api/citations/20210022542/downloads/ACME%20JASMAC-33%2020211007.pdf"),
    ("gollner_2021.pdf", "Gollner et al., Solid fuel combustion in partial and micro-gravity (2021)",
     "https://ntrs.nasa.gov/api/citations/20210022402/downloads/217-_GollnerMichaelJ.pdf"),
]
WORDS, OVERLAP = 180, 30   # all-MiniLM-L6-v2 truncates at 256 word pieces, so stay below ~200 words


def clean(text):
    text = unicodedata.normalize("NFKC", text)            # fixes ligatures such as 'ﬂ'
    keep = [ln for ln in text.splitlines()
            if sum(ch.isalpha() for ch in ln) >= 0.4 * max(1, len(ln.replace(" ", "")))]
    return " ".join(" ".join(keep).split())               # drop axis-number noise, squeeze spaces


def chunk_pdf(path, title, url):
    chunks = []
    for page_no, page in enumerate(PdfReader(path).pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as err:   # some scanned/figure-heavy pages fail to decode: skip them
            print(f"  skipped {path.name} page {page_no}: {type(err).__name__}")
            continue
        words = clean(raw).split()
        for start in range(0, len(words), WORDS - OVERLAP):
            piece = words[start:start + WORDS]
            if len(piece) >= 25:
                chunks.append({"title": title, "url": url, "page": page_no, "text": " ".join(piece)})
    return chunks


if __name__ == "__main__":
    DOCS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    for name, title, url in SOURCES:
        path = DOCS / name
        if not path.exists():
            print("downloading", name)
            with urllib.request.urlopen(url, timeout=300) as resp:
                path.write_bytes(resp.read())
        part = chunk_pdf(path, title, url)
        print(f"{name}: {len(part)} chunks")
        all_chunks += part
    for i, c in enumerate(all_chunks):
        c["id"] = i
    (OUT / "chunks.json").write_text(json.dumps(all_chunks, ensure_ascii=False), encoding="utf-8")
    print("total chunks:", len(all_chunks))
