# IGNIS LAB — team tasks (Sat 14 → Sun 15 Nov)

**Rule for everyone:** one owner per file (listed below), one branch per person (`git switch -c name/task`), small pull
requests, and `python tests/test_pages.py` must print OK for every page before you merge. If you need to change a
file you don't own, ask its owner in the group chat.

**Space Apps rule:** SI/AI may help build, but the solution idea must be ours. Review the design together and change
anything you would do differently. Note any AI help in the README's disclosure section.

## Milestones (Pakistan time)

| When | Milestone | Who |
|---|---|---|
| Sat 15:00 | Repo on GitHub, v0 deployed on Streamlit Community Cloud | T3 |
| Sat 19:00 | **End-to-end v1 deployed**: curated atlas + model explanations + assistant draft merged | all |
| Sat night | d² page, UI polish, pitch v1 | all |
| Sun 10:30 | Feature freeze; record ≤30 s video OR ≤7 slides | T4 (+all) |
| Sun 12:30 | Project page **submitted** (editable until 23:59) | T4 |
| Sun 13:00 | Local judging: 2:30 pitch + 0:30 Q&A | all |

---

## T1 — Data & Atlas ("summarize + rank" is the core of the challenge)

**Owns:** `data/atlas/curation.json`, `scripts/build_atlas.py`, `scripts/download_psi.py`, `scripts/clean_flex.py`, `data/`

- [ ] Curate the 3 investigations with no facts yet: PSI-60, PSI-62, PSI-115 (phase, fuel/sample, outcomes, source).
- [ ] Fill missing tested O2 / pressure ranges where a PSI table or NASA paper states them (BASS PSI-26, SAME-R, Saffire, ACME CLD / E-FIELD / s-Flame). Every value needs a `source`. If you can't verify it, leave it `null`.
- [ ] Check every curated fact against its source, especially the phase tags (prevention / detection / suppression).
- [ ] Optional: compute envelopes from tables (like BASS-II and CFI-G in `envelopes_from_tables()`) for Flame Design (PSI-10) and SPICE (PSI-107).
- [ ] After each change: `python scripts/build_atlas.py`, then check the Atlas page.

**Done when:** no "not curated" rows remain, and every number in the atlas has a source.

## T2 — ML & Science (Validity score, and judges' science questions)

**Owns:** `scripts/train.py`, `scripts/calibrate_and_evidence.py`, `views/trust.py`, new `views/d2law.py`

- [ ] Learn the models well enough to explain them in 30 s: inputs, targets, grouped CV, baselines, conformal interval.
- [ ] Add **permutation importance** (on held-out folds) to the Trust page: which inputs drive extinction and K.
- [ ] Build **`views/d2law.py`**: plot d² against time for the droplet files in `data/raw/droplet_histories/`, fit a line, and compare the fitted K with NASA's K for the same test. Join via `index.json` → `flex_id`; the earliest `_Air` folders need the test sheet. Ask T3 to add the page to `streamlit_app.py`.
- [ ] Optional: extinction-diameter model (156 usable rows); treat "Disruption" as its own hazard class with a caveat.

**Done when:** the Trust page shows importances and the d² page shows at least 5 real NASA droplets with fitted vs. NASA K.

## T3 — App, UX & Deployment (Presentation + usability)

**Owns:** `streamlit_app.py`, `views/home.py`, `views/predict.py`, `views/explorer.py`, `ignis/evidence.py`, `.streamlit/config.toml`

- [ ] **First:** create the GitHub repo, push, and deploy on Streamlit Community Cloud (main file `streamlit_app.py`). Test the public link in an incognito window.
- [ ] Predict page: plain-language help for the results. Explain K, "P(flame goes out)" and the GREEN/AMBER/RED light. When the light is RED, point to the Atlas for investigations that *did* test there (e.g. ACME CFI-G for the exploration atmosphere).
- [ ] Explorer: add a pressure filter, and a short "how to read this chart" caption per chart.
- [ ] Consistent source captions on every page (PSI ID, DOI, NASA/TP-2015-216046).
- [ ] Check the app on a projector-sized screen and a phone; fix anything cut off.

**Done when:** a stranger can open the public link and understand every page without us talking.

## T4 — SI Assistant, Story & Submission (SI-powered + Presentation)

**Owns:** `views/ask_docs.py`, `ignis/rag.py`, `scripts/build_doc_index.py`, `README.md`, pitch, video/slides, project page

- [ ] Optional LLM layer on the Ask page: send the top-5 retrieved passages to a free LLM (Gemini via AI Studio key in `.streamlit/secrets.toml`, never in git). Use the instruction "answer only from these numbered excerpts, cite [n], else say not found". Always show the passages, and fall back to retrieval-only if there is no key or the API fails.
- [ ] Pitch script (2:30), built around the demo: Atlas (pick lunar) → envelope chart → Predict (ISS GREEN → exploration RED) → nearest NASA runs → Trust page. Rehearse 3× with a timer.
- [ ] Demo: **≤30 s video OR ≤7 slides** (over the limit = no global judging). No NASA logos; watermark any AI-made image.
- [ ] Project page fields: summary, demo link, final project link, description, SI use, NASA data (PSI IDs + DOIs), references (all libraries and documents). Submit by Sun 12:30.
- [ ] Ask the Lahore Local Lead: venue hours tonight, and whether preparation done before the event is OK.

**Done when:** the project page is submitted and the pitch fits in 2:30.
