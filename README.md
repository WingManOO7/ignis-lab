# IGNIS LAB — microgravity fire-safety insights from NASA data

NASA Space Apps Challenge 2026 · **Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data**
([challenge page](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/)) · Lahore (UMT) local event

IGNIS LAB is an interactive web dashboard that **summarizes, ranks and interprets** NASA's microgravity combustion
investigations from the Physical Sciences Informatics (PSI) repository for crew-habitat fire safety:

| Page | What it does | Challenge verb |
|---|---|---|
| **Mission brief** | The question, headline numbers, NASA's prevent / detect / suppress framework | — |
| **Investigation atlas** | All 24 PSI Combustion Science investigations, summarized from NASA metadata; ranked for an ISS, lunar or exploration atmosphere with a transparent, adjustable score; tested-envelope chart; side-by-side comparison | Summarize, rank |
| **FLEX run explorer** | Every one of the 274 FLEX droplet burns on the ISS, by fuel, oxygen, diluent and outcome | Interpret |
| **Predict + NASA evidence** | Extinction probability and burning-rate constant K with an interval, the 5 nearest real NASA runs, and a GREEN / AMBER / RED out-of-range light | Interpret (ML) |
| **Can you trust this?** | Model card: grouped cross-validation per fold vs. baselines, measured interval coverage, limits | — |
| **Ask the NASA documents** | Keyword (BM25) search over 8 public NASA reports; every answer is a quoted, linked passage | Interpret (SI) |

## Quick start

Python **3.12 or 3.13** is required.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py            # data, atlas and models are already in the repo
```

To rebuild everything from NASA (no login needed, ~1 minute; add `--docs` for the ~100 MB of PDFs):

```bash
python scripts/run_all.py --docs
python tests/test_pages.py                # renders every page headlessly; must print OK x6
```

## Pipeline

```
NASA PSI API ──► scripts/download_psi.py ──► data/raw/  (7 experimental tables, FLEX metadata, droplet d(t) files)
                 scripts/clean_flex.py   ──► data/processed/flex_clean.csv + flex_data_issues.csv (72 logged issues)
                 scripts/train.py        ──► models/extinction_clf.joblib, k_reg.joblib, reports/cv_folds.csv
                 scripts/calibrate_and_evidence.py ──► models/k_interval.joblib, evidence_index.joblib
                 scripts/build_atlas.py  ──► data/atlas/investigations.json (PSI metadata + data/atlas/curation.json)
NASA NTRS PDFs ► scripts/build_doc_index.py ──► data/docs_index/chunks.json (894 passages)
                                                    │
                                     streamlit_app.py + views/*.py  (never retrains; loads cached files)
```

## Results (grouped 5-fold cross-validation, run 2026-11-14)

Repeats of the same test condition always stay on the same side of the split (`GroupKFold` /
`StratifiedGroupKFold` by `condition_id`): 257 of 274 FLEX rows share their exact conditions with another run,
so a random split would leak. Only pre-ignition inputs are used: fuel, pressure, O2, CO2, He, initial diameter.

| Task | Rows | Model | Score (mean, fold range) | Baseline |
|---|---|---|---|---|
| A: visible flame goes out before burnout? (Extinction vs Completion) | 204 (177 vs 27) | Logistic regression (calibrated) | balanced accuracy **0.754** (0.60–0.91), ROC-AUC **0.82**, Brier **0.089** | base rate: 0.50, Brier 0.115 |
| B: burning-rate constant K (mm²/s) | 255 | Ridge | MAE **0.047**, R² **0.72** | per-fuel mean: MAE 0.103 |
| K interval (split conformal, calibrated on held-out condition groups) | 255 | — | "80%" interval covers **80.8%**, "90%" covers **89.8%** of unseen conditions | — |

**Calibration fix.** Our first classifier used balanced class weights. A reliability check showed its
probabilities were wrong: when it said 0–20%, flames actually went out 55% of the time (Brier 0.177, worse than
the 0.115 baseline). Plain logistic regression, flagging "burns to completion" when P(extinction) falls below the
87% base rate, fixed the probabilities and improved every metric. The Trust page shows the reliability chart.

**Evidence checks on the Predict page.** A query is RED, and its numbers are withheld, if any input is outside the
tested range or the nearest real run is more than 2× the usual neighbour distance (each value tested, but never
together, e.g. 2.5 atm without CO2). The page always shows what NASA actually observed at the 5 closest runs and
warns when most of them ended in Disruption, an outcome the model was not trained on.

**Real tests near each habitat** (counted from the tables, ±0.1 atm, O2 at least the target's): FLEX has 36 near the
ISS cabin, 17 near the lunar-habitat case and **0** at the exploration atmosphere (8.2 psia, 34% O2). ACME CFI-G has
**20** there, so CFI-G gas flames are the only microgravity flame data for that atmosphere.

## Data sources (NASA, CC0)

| Dataset | PSI ID / DOI | Used for |
|---|---|---|
| FLEX — Flame Extinguishment Experiment | [PSI-69](https://psi.nasa.gov/physci/repo/data/investigations/PSI-69) · 10.60555/mbq8-0451 | Explorer, models, evidence (= NASA/TP-2015-216046 Table IX) |
| ACME CFI-G — Cool Flames Investigation with Gases | [PSI-159](https://psi.nasa.gov/physci/repo/data/investigations/PSI-159) | Atlas envelope (chamber O2 0.18–0.40, 0.49–3.27 atm) |
| BASS-II — Burning and Suppression of Solids II | [PSI-25](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25) | Atlas envelope (initial O2 13.6–22.2%) |
| FLEX-2, CFI, SAME-R | [PSI-68](https://psi.nasa.gov/physci/repo/data/investigations/PSI-68), [PSI-39](https://psi.nasa.gov/physci/repo/data/investigations/PSI-39), [PSI-101](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101) | Atlas facts |
| All 24 Combustion Science investigations | [PSI search](https://psi.nasa.gov/physci/repo/search?q=combustion) | Atlas summaries (objective, approach, platform, dates, publications) |
| NASA technical reports (FLEX TP-2015-216046, cool-flame paper, BASS-II TM, Saffire IV–VI, SAME, ACME, partial-gravity white paper) | listed in `scripts/build_doc_index.py` | Document search |

Downloads use the JSON API that psi.nasa.gov itself calls. It is undocumented and could change; if it breaks,
download the same files from the PSI web pages above.

## Limits (shown in the app too)

- FLEX covers 2 fuels, 0.69–3.05 atm and O2 0.12–0.34; pressures above 1 atm only occur with ~70% CO2.
- NASA's exploration atmosphere (8.2 psia ≈ 0.56 atm, 34% O2) is **outside** FLEX's tested pressures: the app flags it RED instead of guessing.
- "Disruption" outcomes may be caused by fuel-needle contamination (NASA/TP-2015-216046 sec. 5.2), so they are not used as labels.
- PSI has no partial-gravity (Moon/Mars) combustion data. The atlas ranking is our heuristic, not a NASA ranking.
- Atlas envelope fields come from `data/atlas/curation.json`; entries marked "not curated" have not been checked yet.

## Project structure

```
streamlit_app.py        entry point (st.navigation)
views/                  one file per page
ignis/                  shared helpers: data loaders, evidence lookup, document search
scripts/                pipeline steps (see above) + run_all.py
data/raw/               NASA files as downloaded (data/docs/ PDFs are git-ignored)
data/processed/         cleaned FLEX table + issue log
data/atlas/             curation.json (team-verified facts) + generated investigations.json
models/, reports/       trained models and cross-validation results
tests/test_pages.py     headless smoke test of every page
```

## Team workflow

- `main` must always run. Work on a branch per person (`git switch -c yourname/feature`), open small pull requests.
- One owner per file to avoid conflicts: data/pipeline (`scripts/`, `data/`), models (`train.py`, `calibrate_and_evidence.py`),
  pages (`views/*.py`, one owner each), pitch and README.
- Before merging: `python tests/test_pages.py` must print OK for every page.
- Deploy: push to GitHub → [Streamlit Community Cloud](https://share.streamlit.io) → main file `streamlit_app.py`.
  In **Advanced settings choose Python 3.12 or 3.13** (numpy 2.5.4 does not install on older Python).
  Open the app once before judging (free apps sleep after inactivity). Never commit API keys (`.streamlit/secrets.toml` is ignored).

## Use of Super Intelligence (SI) / AI — disclosure

Space Apps 2026 requires SI use to be disclosed inside the project.

- **AI-assisted research and code.** Background research and an initial code scaffold were produced with an AI coding
  assistant. Files whose header says `STARTER CODE` came from that scaffold. `scripts/build_atlas.py`,
  `ignis/scenarios.py`, `ignis/evidence.py`, `views/atlas.py`, `views/predict.py`, `views/trust.py`, the classifier
  calibration change in `scripts/train.py` and `tests/test_pages.py` were also written or revised with AI assistance. The team reviews, adapts and is
  responsible for all code; changes made during the event are recorded in the git history.
- **SI inside the product.** The dashboard's SI layer is classical machine learning (scikit-learn logistic regression and
  ridge regression with conformal intervals and nearest-neighbour evidence) plus BM25 keyword retrieval. No generative
  model writes any number or answer shown in the app.
- No AI-generated images, video or audio are used, and no NASA logos or insignia appear in the project.

## Credits and licence

Data: NASA Physical Sciences Informatics (CC0) and NASA Technical Reports Server. This project is not affiliated with or
endorsed by NASA. Open-source libraries: pandas, NumPy, scikit-learn, Streamlit, Plotly, joblib, pypdf, rank-bm25.
Original content is released under Apache-2.0 (the Space Apps default) unless the team chooses another OSI licence.
