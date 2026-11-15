# IGNIS LAB — microgravity fire-safety insights from NASA data

NASA Space Apps Challenge 2026 · **Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data**
([challenge page](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/)) · Lahore (UMT) local event

**Live app:** https://ignis-lab.streamlit.app · Team **Chann De Yaar**: M. Mohid Shafiq, Syed Fawad Hassan, Amna Naseer

In 1967 a fire in a pure-oxygen cabin killed the three Apollo 1 astronauts during a ground test. Crews still live in a
small sealed cabin with their wiring and their air, and NASA plans oxygen-rich air (34% O2) again for exploration
habitats. FLEX, NASA's droplet-fire experiment on the ISS, has no tests near that atmosphere. We wanted to know what
NASA's microgravity fire data can tell the next crew, and to be honest about where it runs out.

IGNIS LAB is an interactive web dashboard that **summarizes, ranks and interprets** NASA's microgravity combustion
investigations from the Physical Sciences Informatics (PSI) repository for crew-habitat fire safety:

| Page | What it does | Challenge verb |
|---|---|---|
| **Mission brief** | The question, headline numbers, why FLEX matters and its scope | — |
| **Investigation atlas** | All 24 PSI Combustion Science investigations from NASA metadata; **relevance** to an ISS, lunar or exploration atmosphere kept separate from **evidence completeness** (uncurated = "not enough data", never a low score); real test counts near each habitat; tested-envelope chart; side-by-side comparison; jump to Predict; CSV download | Summarize, rank |
| **Safety controls** | Evidence-linked cards for fire detection & smoke monitoring, suppression, and material screening & prevention: the PSI investigation (linked), what NASA measured, any NASA-reported result (cited), and the safety question it may inform, labelled as our interpretation, not a NASA finding or recommendation | Interpret |
| **FLEX run explorer** | All 274 FLEX droplet burns; fuel / diluent / outcome / pressure filters; click a point to inspect the run and its d² recording; CSV download | Interpret |
| **d² law check** | Refits K from NASA's raw diameter-vs-time recordings and compares it with NASA's tabulated K | Interpret |
| **Predict** | Calibrated chance the flame goes out early and K with an 80% interval; GREEN / AMBER / RED check (RED withholds numbers and lists the investigations that did test there); what NASA saw at the 5 closest runs; risk map over O2 × pressure (never-tested cells grey); one-variable sweep; JSON download | Interpret (ML) |
| **Fire story (3D)** | Interactive three.js Fire lab: Earth lab (gravity-off toggle) → orbit → cabin → FLEX chamber → wiring & fan, in cinema mode with an optional guided story (about 4 minutes, paced by the narrator, covering every place) and full screen. In the chamber every slider runs our trained models in the browser (same numbers as Predict): K, chance of early extinction, GREEN/AMBER/RED and the nearest NASA runs; RED = not simulated. Cabin wiring fire (spark, fan, flash, CO2) is illustrative; everything is tagged DATA or ILLUSTRATIVE. Nova, an original astronaut-cat mascot, floats in the cabin and reacts to sparks, the fan and CO2 (decoration only) | Interpret |
| **Can you trust this?** | Grouped CV vs baselines, fold-to-fold spread, reliability chart, permutation importance, measured interval coverage, limits | — |
| **Ask the NASA documents** | BM25 search over 8 NASA reports; a no-AI extracted answer (verbatim NASA sentences) by default; optional LLM answer (button, key needed) with an automatic citation, number and keyword check - not a guarantee; rate-limited | Interpret (SI) |

A sidebar **guided tour** walks through the story in 5 steps (Atlas lunar → research gap → Predict GREEN → RED → Trust).

## Quick start

Python **3.12 or 3.13** is required (checked 14 Nov: fresh installs of `requirements.txt` on Python 3.12.16 and
3.13.5 both succeed and load the saved models).

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py            # data, atlas and models are already in the repo
```

Rebuild everything from NASA (no login needed; add `--docs` for the ~100 MB of PDFs), then test:

```bash
python scripts/run_all.py --docs
pip install -r requirements-dev.txt       # pytest
python -m pytest -q                       # unit tests + every page rendered through the real navigation
```

**Optional LLM key** (Ask page, offline summaries): put `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`) or
`GROQ_API_KEY` (optionally `GROQ_MODEL`) in `.streamlit/secrets.toml` or Streamlit Cloud secrets. Without a key the
app runs in retrieval-only mode. Check model names in the provider console; defaults are `gemini-flash-latest` and
`openai/gpt-oss-20b`.

## Pipeline

```
NASA PSI API ──► scripts/download_psi.py ──► data/raw/  (7 experimental tables, FLEX metadata, droplet d(t) files)
                 scripts/clean_flex.py   ──► data/processed/flex_clean.csv + flex_data_issues.csv (72 logged issues)
                 scripts/train.py        ──► models/extinction_clf.joblib, k_reg.joblib, reports/ (CV folds,
                                             reliability, permutation importance)
                 scripts/calibrate_and_evidence.py ──► models/k_interval.joblib, evidence_index.joblib
                 scripts/build_atlas.py  ──► data/atlas/investigations.json (PSI metadata + curation.json + real
                                             test counts near each habitat)
NASA NTRS PDFs ► scripts/build_doc_index.py ──► data/docs_index/chunks.json (894 passages)
LLM (optional) ► scripts/build_summaries.py ──► data/atlas/summaries.json (offline, number-checked, review by hand)
                                                    │
                                     streamlit_app.py + views/*.py  (never retrains; loads cached files)
```

## Results (grouped 5-fold cross-validation, run 2026-11-14)

Repeats of the same test condition always stay on the same side of the split (`GroupKFold` /
`StratifiedGroupKFold` by `condition_id`): 257 of 274 FLEX rows share their exact conditions with another run,
so a random split would leak. Only pre-ignition inputs are used: fuel, pressure, O2, CO2, He, initial diameter.

| Task | Rows | Model | Score (mean, fold range) | Baseline |
|---|---|---|---|---|
| A: visible flame goes out before burnout? (Extinction vs Completion) | 204 (177 vs 27) | Logistic regression, fuel-specific slopes | ROC-AUC **0.89**, Brier **0.074**, balanced accuracy 0.78 (range **0.60–0.93** over 25 folds) | base rate: AUC 0.50, Brier 0.115 |
| B: burning-rate constant K (mm²/s) | 255 | Ridge, fuel-specific slopes | MAE **0.045**, R² 0.715 | per-fuel mean: MAE 0.103 |
| K interval (split conformal, calibrated on held-out condition groups) | 255 | — | "80%" interval covers **80.8%**, "90%" covers **91.0%** of unseen conditions | — |

Task A rests on only 27 "Completion" runs, so the fold-to-fold spread matters more than the mean.

**Model search (pre-registered, `reports/model_search.md`).** Six shippable candidates per task were compared with
the previous models on identical folds (10 shuffles) and on a leave-one-campaign-out test. Only "fuel-specific
slopes" (each input also gets a heptane-only copy, so the two fuels can respond differently) passed the rule we set
in advance (wins ≥ 70% of paired folds and gains more than half the fold spread): extinction ROC-AUC 0.82 → 0.89
(wins 88% of folds), Brier 0.087 → 0.073 (86%); K MAE 0.049 → 0.044 (82%, a modest margin). The balanced-accuracy
gain did not pass the rule, so we do not claim it. Physics transforms, splines, tuned regularisation, Gaussian
processes and tree ensembles did not beat the linear models. Both shipped models stay linear, so the 3D lab
evaluates them exactly in the browser (`ignis/sim_assets/ignis_model.js`, checked against scikit-learn to 1e-9).

**Calibration fix.** Our first classifier used balanced class weights. A reliability check showed its
probabilities could not be taken at face value: balanced weights inflate the rare outcome (Brier 0.177, worse than
the 0.115 baseline). Plain logistic regression, flagging "burns to completion" when P(extinction) falls below the
87% base rate, fixed the probabilities and improved every metric. The Trust page shows the reliability chart.

**Which inputs matter** (permutation importance on held-out grouped folds): oxygen matters most in both models;
fuel, droplet size and CO2 also matter for extinction; helium and droplet size for K. This shows what the models rely on, not cause and
effect, and pressure cannot be separated from CO2 in FLEX.

**Independent d² check.** Refitting K from NASA's raw diameter-vs-time recordings (fit window fixed in advance:
20–100% of NASA's burn time) reproduces NASA's tabulated K with a median difference of **2.3%** (14 of 15 comparable
droplets within 10%). The page states its sample (30 of 260 recordings, the earliest FLEX runs, not a random sample), shows the worst gap (196F002, -11.8%) next to the median and flags fits with R² < 0.8.

**Evidence checks on the Predict page.** A query is RED, and its numbers are withheld, if any input is outside the
tested range or the nearest real run is more than 2× the usual neighbour distance (each value tested, but never
together, e.g. 2.5 atm without CO2). The page always shows what NASA actually observed at the 5 closest runs and
applies a **Disruption rule**: if 3 or more of the 5 closest runs ended in Disruption (an outcome the model was not trained on) the light is at most AMBER, and RED if all 5 did (lunar heptane, 5 of 5 Disruption, is RED). The same rules run in the 3D lab's browser model (parity test). A 'close to a coin flip' note appears for P between 35 and 65%.

**Real tests near each habitat** (counted from the tables, ±0.1 atm, O2 at least the target's): FLEX has 36 near the
ISS cabin, 17 near the lunar-habitat case and **0** at the exploration atmosphere (8.2 psia, 34% O2). ACME CFI-G has
**20** there, so CFI-G gas flames are the only per-test microgravity flame data for that atmosphere (ACME BRE also ran
it, but publishes only a day-level log).

## Data sources (NASA, CC0)

| Dataset | PSI ID / DOI | Used for |
|---|---|---|
| FLEX — Flame Extinguishment Experiment | [PSI-69](https://psi.nasa.gov/physci/repo/data/investigations/PSI-69) · 10.60555/mbq8-0451 | Explorer, models, evidence, d² recordings (= NASA/TP-2015-216046 Table IX) |
| ACME CFI-G — Cool Flames Investigation with Gases | [PSI-159](https://psi.nasa.gov/physci/repo/data/investigations/PSI-159) | Atlas envelope (chamber O2 0.18–0.40, 0.49–3.27 atm) and real test counts |
| BASS-II — Burning and Suppression of Solids II | [PSI-25](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25) | Atlas envelope (initial O2 13.6–22.2%) |
| FLEX-2, CFI, SAME-R | [PSI-68](https://psi.nasa.gov/physci/repo/data/investigations/PSI-68), [PSI-39](https://psi.nasa.gov/physci/repo/data/investigations/PSI-39), [PSI-101](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101) | Atlas facts |
| All 24 Combustion Science investigations | [PSI search](https://psi.nasa.gov/physci/repo/search?q=combustion) | Atlas summaries (objective, approach, platform, dates, publications) |
| NASA technical reports (FLEX TP-2015-216046, cool-flame paper, BASS-II TM, Saffire IV–VI, SAME, ACME, partial-gravity white paper) | listed in `scripts/build_doc_index.py` | Document search |

Downloads use the JSON API that psi.nasa.gov itself calls. It is undocumented and could change; if it breaks,
download the same files from the PSI web pages above.

## Limits (shown in the app too)

- FLEX covers 2 liquid fuels as isolated droplets, 0.69–3.05 atm and O2 0.12–0.34; pressures above 1 atm only occur with ~70% CO2, so pressure and CO2 effects cannot be separated.
- FLEX is not a model of solid spacecraft materials (fabrics, plastics); those are BASS, BASS-II and Saffire (Atlas).
- NASA's exploration atmosphere (8.2 psia ≈ 0.56 atm, 34% O2) is **outside** FLEX's tested pressures: the app flags it RED instead of guessing.
- "Disruption" outcomes may be caused by fuel-needle contamination (NASA/TP-2015-216046 sec. 5.2), so they are not used as labels.
- PSI has no partial-gravity (Moon/Mars) combustion data. The atlas ranking is our heuristic, not a NASA ranking, and only investigations with a verified envelope are ranked.
- The extinction model is unstable across folds (balanced accuracy 0.60–0.93) because only 27 runs burned to completion.

## Project structure

```
streamlit_app.py        entry point (st.navigation + guided tour)
views/                  one file per page
ignis/                  shared logic: data loaders, scenarios + coverage, evidence (traffic light), explore (risk
                        map/sweeps), droplets (d² fits), rag (retrieval, LLM call, verifier), glossary, messages, tour
scripts/                pipeline steps (see above) + run_all.py; build_voice.py (recorded narrator voice),
                        record_story.mjs + make_story_video.py (the narrated demo video of "Play the story")
data/raw/               NASA files as downloaded (data/docs/ PDFs are git-ignored)
data/processed/         cleaned FLEX table + issue log
data/atlas/             curation.json (team-verified facts) + generated investigations.json
models/, reports/       trained models, CV results, reliability, permutation importance
static/                 bundled three.js (vendor/), generated standalone Fire lab page (fire_lab.html),
                        recorded narrator clips (voice/, AI-generated)
tests/                  unit tests (test_core, test_rag, test_honesty, test_selfcheck) + test_pages.py (every page)
```

## Before judging

1. Streamlit Cloud: **Advanced settings → Python 3.12 or 3.13**; do not upgrade Streamlit (pinned 1.67.0).
2. Open the app once to wake it; open the Fire lab once and check the 3D footer says **"three.js: bundled"**.
3. On the presenting laptop test WebGL, **F** (full screen) and the voice (off by default; Microsoft Edge has the most natural voices, which need internet;
   the voice menu also offers "Recorded AI voice", which works offline). "Play the story" (about 4 minutes) waits for each line to finish.
   Demo video: `python scripts/make_story_video.py` films the story in full HD with the narration (needs Node and ffmpeg).
4. Test the venue network. Backup: run locally with `streamlit run streamlit_app.py` (the 3D lab works offline).
5. Ask page: it shows which mode is active ("Retrieval only: no LLM key set" or the provider). The key lives in a
   git-ignored `.env` locally (copy `.env.example`) and in Streamlit Cloud under App settings → Secrets
   (`GEMINI_API_KEY`; model `gemini-3.5-flash-lite` by default). With a key, set `DAILY_LLM_LIMIT` if needed (default 150 calls per day).
6. `python -m pytest -q` must pass before the final push.

## Team workflow

- `main` must always run. Work on a branch per person (`git switch -c yourname/feature`), open small pull requests.
- One owner per file to avoid conflicts: data/pipeline (`scripts/`, `data/`), models (`train.py`, `calibrate_and_evidence.py`),
  pages (`views/*.py`, one owner each), pitch and README.
- Before merging: `python -m pytest -q` must pass.
- Deploy: push to GitHub → [Streamlit Community Cloud](https://share.streamlit.io) → main file `streamlit_app.py`.
  In **Advanced settings choose Python 3.12 or 3.13** (numpy 2.5.4 does not install on older Python).
  Open the app once before judging (free apps sleep after inactivity). Never commit API keys (`.streamlit/secrets.toml` is ignored).

## Use of Super Intelligence (SI) / AI

Our project uses AI (SI) in two ways: inside the app, in clearly limited and checked roles, and as a tool that helped
us build it faster.

### In the app

- **Machine learning makes every prediction.** Two scikit-learn models (logistic regression and ridge regression with
  fuel-specific slopes) are trained on 274 NASA FLEX droplet fires. They give a calibrated chance that a flame goes out
  early and a burning rate with a conformal 80% interval, and a nearest-run evidence check (GREEN / AMBER / RED)
  withholds the numbers outside NASA's tested data. The 3D Fire lab runs the same two models in the browser, checked
  against scikit-learn to 1e-9. No generative model produces any prediction or data value.
- **Ask the NASA documents.** The default answer is copied word for word from NASA passages (keyword search, no AI).
  An optional answer from Google Gemini (`gemini-3.5-flash-lite`) is generated only when the user clicks. Every
  sentence must cite a passage, and its numbers and key words must appear there; otherwise it is removed and listed.
  The answer is labelled AI-generated. Limits: 300-character questions, 20 s between calls, 5 per session, a daily cap
  (`DAILY_LLM_LIMIT`, default 150).
- **Narrator voice.** The narration text is fixed in the app. Its optional voice is the browser's text-to-speech or
  pre-recorded clips of the same sentences made with a text-to-speech engine (`scripts/build_voice.py`, Windows
  "Zira" voice; `static/voice/manifest.json` names it). This is SI-generated audio, labelled on screen
  ("Narration: AI-generated voice"). A demo video recorded from the app (`scripts/make_story_video.py`) uses the same
  narration.
- **Optional offline text.** `scripts/build_summaries.py` and `scripts/build_faq.py` can draft Atlas summaries and
  example Q&A with an LLM; they pass the same check and must be reviewed by the team before use. None are in the app.

### In our development process

- We used an AI coding assistant for background research, an initial code scaffold, writing and revising code (data
  pipeline, models, every page, the 3D Fire lab and its mascot Nova, tests), finding and checking sources for the
  Safety page, and drafting documentation, the presentation scripts and slides. Files whose header says
  `STARTER CODE` came from that scaffold. These files were written or substantially revised with AI assistance:
  `scripts/build_atlas.py`, `scripts/build_summaries.py`, `scripts/build_faq.py`, `scripts/train.py`,
  `scripts/build_voice.py`, `scripts/record_story.mjs`, `scripts/make_story_video.py`, `scripts/cut_highlight.py`,
  every module in `ignis/` (including `ignis/sim_assets/`, the 3D Fire lab), `streamlit_app.py`, every file in
  `views/`, and `tests/`.
- The team decided what to build and what to change, reviewed and tested every AI-assisted change (122 automated
  tests, plus every page rendered through the real navigation), and checked facts against the NASA sources linked in
  the app. The git history records every change.
- No AI-generated images or video are used in the app: the 3D scenes, the spacecraft and Nova are drawn in code
  (three.js), and every 3D element is tagged DATA or ILLUSTRATIVE on screen. The presentation slides carry a visible
  "SI-assisted" watermark. No NASA logos, insignia or branding appear anywhere.

### In short

AI predicts nothing without the NASA data behind it, the generative parts are optional and checked, and AI was a tool
that helped us move faster. The team chose what to build, checked it, and is responsible for all of it.

## Credits and licence

Data: NASA Physical Sciences Informatics (CC0) and NASA Technical Reports Server. This project is not affiliated with or
endorsed by NASA. Open-source libraries: pandas, NumPy, scikit-learn, Streamlit, Plotly, joblib, pypdf, rank-bm25
(pytest for tests), and three.js 0.160.0 (MIT, © 2010-2023 three.js authors), bundled in `static/vendor/three-0.160.0/` with its
LICENSE and served by Streamlit static file serving, so the Fire lab works offline (WebGL needed); if the bundled files
cannot be served it falls back to the same pinned files on jsDelivr, checked with SRI hashes. On start the app checks
its data files and models (`ignis/selfcheck.py`) and shows one clear message with the fix instead of a stack trace. Original content is released under Apache-2.0 (the Space Apps default) unless the team chooses
another OSI licence.
