import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis import ui
from ignis.data import ROOT, load_cv, load_models
from ignis.glossary import glossary_list

ui.page_header("Can you trust this?",
               "How the models were tested, how honest their numbers are, and where they stop working.",
               "NASA PSI-69 FLEX, grouped 5-fold cross-validation")
cv = load_cv()
models = load_models()
meta = models["clf"]["meta"]
a = cv[cv["task"] == "A extinction"]
b = cv[cv["task"] == "B burning-rate K"]
shown = a[a["model"] == meta["classifier"]]
brier = a.groupby("model")["brier"].mean()
k_name = meta.get("regressor")          # name of the SHIPPED K model's cross-validation row (set by train.py)
mae = b.groupby("model")["MAE"].mean()
cov = [r for r in models["k"]["coverage_check"] if r["level"] == "80%"]
n_ext = round(meta["base_rate_extinction"] * meta["n_rows_clf"])

# ---------------------------------------------------------------- hero: four honest numbers
cells = [{"v": f"{brier.get(meta['classifier'], float('nan')):.3f}",
          "l": "Brier score: probability error (lower is better)",
          "s": f"Base-rate baseline: {brier.get('Dummy (base rate)', float('nan')):.3f}"},
         {"v": f"{shown['balanced_acc'].mean():.2f}", "tone": "flame",
          "l": "Balanced accuracy: flame goes out or not",
          "s": f"Ranges {shown['balanced_acc'].min():.2f}-{shown['balanced_acc'].max():.2f} over {len(shown)} folds"}]
baseline_k = [m for m in mae.index if m.startswith("Per-fuel mean")]
if k_name in mae.index:
    cells.append({"v": f"{mae[k_name]:.3f}", "u": "mm²/s", "l": f"K error, mean absolute ({k_name})",
                  "s": (f"Per-fuel mean baseline: {mae[baseline_k[0]]:.3f}" if baseline_k else None)})
cells.append({"v": f"{sum(r['coverage'] for r in cov) / len(cov):.0%}", "l": "Coverage of the '80%' K interval",
              "s": "Measured on test conditions the model never saw"})
ui.readouts(cells)
ui.note(f"<b>Unstable on small data: read the spread, not just the mean.</b> Across {len(shown)} held-out folds the "
        f"shown model's balanced accuracy ranges <b>{shown['balanced_acc'].min():.2f}-"
        f"{shown['balanced_acc'].max():.2f}</b> (mean {shown['balanced_acc'].mean():.2f}). It rests on only "
        f"{meta['n_rows_clf'] - n_ext} 'Completion' runs against {n_ext} 'Extinction' runs, so one fold's mix of "
        "conditions can move the score a lot.", tone="caution")

left, right = st.columns([1.55, 1], gap="large")
with left:
    rel_path = ROOT / "reports/reliability_oof.csv"
    if rel_path.exists():
        rel = pd.read_csv(rel_path)
        rel["bin"] = pd.cut(rel["p_extinction"], [0, 0.5, 0.7, 0.8, 0.9, 1.0], include_lowest=True)
        t = rel.groupby("bin", observed=True).agg(predicted=("p_extinction", "mean"),
                                                  observed=("extinguished", "mean"), n=("extinguished", "size"))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration",
                                 line=dict(dash="dash", color=ui.DIM)))
        fig.add_trace(go.Scatter(x=t["predicted"], y=t["observed"], mode="markers+lines+text", name="our model",
                                 text=[f"n={n}" for n in t["n"]], textposition="top left",
                                 textfont=dict(color=ui.DIM), line=dict(color=ui.DATA, width=3),
                                 marker=dict(size=11, color=ui.DATA, line=dict(width=1.5, color=ui.SPACE))))
        fig.update_layout(title="When the model says X%, how often did NASA's flame really go out?",
                          xaxis_title="predicted probability (out-of-fold)", yaxis_title="observed share", height=420)
        ui.chart(fig)
        st.caption("We first trained with balanced class weights. That inflated the rare outcome: when it said "
                   "0-20%, flames actually went out 55% of the time. Switching to plain logistic regression fixed "
                   "the probabilities without losing accuracy.")
with right.container(key="limits"):
    ui.section("Limits")
    st.markdown("- 274 tabulated tests, 2 fuels, pressure 0.69-3.05 atm, O2 0.12-0.34. Pressures above 1 atm only "
                "occur together with ~70% CO2, so the app flags other high-pressure mixes RED.\n"
                "- No FLEX test exists at NASA's exploration atmosphere (8.2 psia, 34% O2). Counted from NASA's "
                "per-test tables, ACME CFI-G has 20 gas-flame tests there; ACME BRE also ran that atmosphere but "
                "publishes only a day-level log (see the Atlas).\n"
                "- 'Disruption' outcomes may reflect fuel-needle contamination (NASA/TP-2015-216046 sec. 5.2) and are "
                "not used as labels; the Predict page warns when nearby runs disrupted.\n"
                "- No partial-gravity (Moon/Mars) combustion data exist in PSI. Models learn correlations, not physics.")

tab_a, tab_b, tab_pi, tab_how = st.tabs(["Flame goes out? (model A)", "Burning rate K (model B)",
                                         "What the models rely on", "How we tested"])
with tab_a:
    st.caption(f"{meta['n_rows_clf']} runs (Extinction vs Completion; Disruption excluded). "
               f"Shown in the app: **{meta['classifier']}**.")
    summary = a.groupby("model")[["balanced_acc", "recall_completion", "roc_auc", "brier"]].mean().round(3)
    summary.columns = ["balanced accuracy (higher better)", "catches 'burns to completion'",
                       "ROC-AUC (higher better)", "Brier: probability error (lower better)"]
    st.dataframe(summary.sort_values("ROC-AUC (higher better)", ascending=False), width="stretch")
    fig = px.strip(a, x="model", y="balanced_acc", title="Balanced accuracy per fold (spread = honesty)",
                   color_discrete_sequence=[ui.DATA])
    fig.update_layout(height=380, xaxis_title="")
    ui.chart(fig)
with tab_b:
    st.dataframe(b.groupby("model")[["MAE", "R2"]].agg(["mean", "min", "max"]).round(3), width="stretch")
    fig = px.strip(b, x="model", y="MAE", title="Mean absolute error per fold (lower is better)",
                   color_discrete_sequence=[ui.FLAME])
    fig.update_layout(height=380, xaxis_title="")
    ui.chart(fig)
    st.metric("Measured coverage of the '80%' K interval on unseen conditions",
              f"{sum(r['coverage'] for r in cov) / len(cov):.0%}")
with tab_pi:
    pi_path = ROOT / "reports/permutation_importance.csv"
    if pi_path.exists():
        pi = pd.read_csv(pi_path)
        agg = pi.groupby(["task", "feature"])["importance"].agg(["mean", "std"]).reset_index()
        names = {"x_o2": "oxygen (O2)", "p_atm": "pressure", "x_co2": "CO2", "x_he": "helium",
                 "d0_mm": "droplet size", "fuel": "fuel type"}
        agg["input"] = agg["feature"].map(names)
        c1, c2 = st.columns(2)
        for col, task, unit, color in [(c1, "A extinction", "drop in ROC-AUC", ui.DATA),
                                       (c2, "B burning-rate K", "rise in error (mm²/s)", ui.FLAME)]:
            sub = agg[agg["task"] == task].sort_values("mean")
            fig = px.bar(sub, x="mean", y="input", error_x="std", orientation="h",
                         title=f"{'Flame goes out early?' if task.startswith('A') else 'Burning rate K'}",
                         labels={"mean": unit, "input": ""}, color_discrete_sequence=[color])
            fig.update_layout(height=340)
            with col:
                ui.chart(fig)
        st.caption("Permutation importance on held-out grouped folds: shuffle one input on condition groups the model "
                   "never saw and measure how much worse it gets (bar = mean over 5 folds, line = spread). It shows "
                   "what the model relies on - **not** physical cause and effect. Correlated inputs share credit: in "
                   "FLEX, high pressure only occurs with ~70% CO2, so the model cannot separate those two.")
with tab_how:
    st.markdown("**Validation:** 5-fold *grouped* cross-validation, repeated 5 times. Every repeat of the same test "
                "condition stays on the same side of the split (257 of 274 FLEX runs share their conditions with "
                "another run, so a random split would leak). Every model is compared with a dumb baseline.")
    glossary_list(["grouped cv", "calibration", "conformal", "light", "outcomes"])
