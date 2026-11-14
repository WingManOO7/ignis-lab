"""Run the whole data pipeline in order (from the repository root):

    python scripts/run_all.py            # tables + atlas + models (+ doc index if --docs)
    python scripts/run_all.py --docs     # also download NASA PDFs and build the search index

Each step can also be run on its own; see README.md.
"""
import subprocess
import sys

STEPS = [
    ["scripts/download_psi.py", "--droplets", "30"],   # NASA PSI tables + 30 droplet histories
    ["scripts/clean_flex.py"],                          # -> data/processed/flex_clean.csv
    ["scripts/train.py"],                               # grouped CV + models/*.joblib
    ["scripts/calibrate_and_evidence.py"],              # conformal intervals + evidence index
    ["scripts/build_atlas.py"],                         # -> data/atlas/investigations.json
]

if "--docs" in sys.argv:
    STEPS.append(["scripts/build_doc_index.py"])        # -> data/docs_index/chunks.json

for step in STEPS:
    print(f"\n=== {' '.join(step)}")
    if subprocess.run([sys.executable, *step]).returncode != 0:
        sys.exit(f"step failed: {step[0]}")
print("\nPipeline finished. Start the app with:  streamlit run streamlit_app.py")
