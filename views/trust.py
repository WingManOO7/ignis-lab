import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis import ui
from ignis.data import ROOT, load_atlas, load_cv, load_flex, load_models
from ignis.glossary import glossary_list

ui.page_header("Can you trust this?",
               "How we tried to break our own models, and where they stop working.",
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
cells = [{"v": f"{brier.get(meta['classifier'], float('nan')):.3f}", "l": "Brier score",
          "s": f"baseline {brier.get('Dummy (base rate)', float('nan')):.3f}",
          "t": "Probability error of the flame-out model (lower is better), vs a base-rate baseline."},
         {"v": f"{shown['balanced_acc'].mean():.2f}", "tone": "flame", "l": "balanced accuracy",
          "s": f"range {shown['balanced_acc'].min():.2f}-{shown['balanced_acc'].max():.2f}, {len(shown)} folds",
          "t": "Does the visible flame go out before burnout? Mean over held-out grouped folds."}]
baseline_k = [m for m in mae.index if m.startswith("Per-fuel mean")]
if k_name in mae.index:
    cells.append({"v": f"{mae[k_name]:.3f}", "u": "mm²/s", "l": "K error (MAE)",
                  "s": (f"baseline {mae[baseline_k[0]]:.3f}" if baseline_k else None),
                  "t": f"Mean absolute error of the burning-rate model ({k_name}) vs the per-fuel mean baseline."})
cells.append({"v": f"{sum(r['coverage'] for r in cov) / len(cov):.0%}", "l": "'80%' interval coverage",
              "s": "unseen conditions", "t": "Measured on test conditions the model never saw."})
ui.readouts(cells)
ui.note(f"**Unstable on small data:** read the spread ({shown['balanced_acc'].min():.2f}-"
        f"{shown['balanced_acc'].max():.2f}), not the mean.", tone="caution",
        details=f"Across {len(shown)} held-out folds the shown model's balanced accuracy ranges "
                f"{shown['balanced_acc'].min():.2f}-{shown['balanced_acc'].max():.2f} (mean "
                f"{shown['balanced_acc'].mean():.2f}). It rests on only {meta['n_rows_clf'] - n_ext} 'Completion' "
                f"runs against {n_ext} 'Extinction' runs, so one fold's mix of conditions can move the score a lot.")

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
        fig.update_layout(title="Predicted vs real flame-out rate",
                          xaxis_title="predicted probability (out-of-fold)", yaxis_title="observed share", height=420)
        ui.chart(fig)
        st.caption("How we fixed the calibration",
                   help="When the model says X%, how often did NASA's flame really go out? We first trained with "
                        "balanced class weights. That inflated the rare outcome, so its percentages could not be taken at face "
                        "value (Brier 0.177, worse than always guessing the base rate, 0.115). Switching to plain "
                        "logistic regression fixed the probabilities "
                        "without losing accuracy.")
flex = load_flex()
near = {r["acronym"]: r["tests_near"] for r in load_atlas() if isinstance(r.get("tests_near"), dict)}
flex_expl, cfig_expl = near.get("FLEX", {}).get("exploration", "?"), near.get("ACME CFI-G", {}).get("exploration", "?")
with right.container(key="limits"):
    ui.section("Limits")
    st.markdown(f"- {flex['fuel'].nunique()} liquid fuels, droplets only\n"
                "- Pressure tied to CO2 above 1 atm\n"
                f"- {flex_expl} FLEX tests at the exploration atmosphere\n"
                "- Disruption runs not used as labels\n"
                "- No Moon/Mars data; correlations, not physics")
    with st.expander("Details"):
        st.markdown(f"- {len(flex)} tabulated tests, {flex['fuel'].nunique()} fuels, pressure "
                    f"{flex['p_atm'].min():.2f}-{flex['p_atm'].max():.2f} atm, O2 {flex['x_o2'].min():.2f}-"
                    f"{flex['x_o2'].max():.2f}. Pressures above 1 atm only occur together with ~70% CO2, so the app "
                    "flags other high-pressure mixes RED.\n"
                    f"- FLEX has {flex_expl} tests at NASA's exploration atmosphere (8.2 psia, 34% O2). Counted from "
                    f"NASA's per-test tables, ACME CFI-G has {cfig_expl} gas-flame tests there; ACME BRE also ran "
                    "that atmosphere but publishes only a day-level log (see the Atlas).\n"
                    "- 'Disruption' outcomes may reflect fuel-needle contamination (NASA/TP-2015-216046 sec. 5.2) "
                    "and are not used as labels; the Predict page warns when nearby runs disrupted.\n"
                    "- No partial-gravity (Moon/Mars) combustion data exist in PSI. Models learn correlations, "
                    "not physics.")

tab_a, tab_b, tab_pi, tab_how = st.tabs(["Flame goes out? (model A)", "Burning rate K (model B)",
                                         "What the models rely on", "How we tested"])
with tab_a:
    st.caption(f"{meta['n_rows_clf']} runs. Shown in the app: **{meta['classifier']}**.",
               help="Extinction vs Completion; Disruption runs excluded.")
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
        st.caption("What the models rely on, **not** cause and effect.",
                   help="Permutation importance on held-out grouped folds: shuffle one input on condition groups the "
                        "model never saw and measure how much worse it gets (bar = mean over 5 folds, line = spread). "
                        "Correlated inputs share credit: in FLEX, high pressure only occurs with ~70% CO2, so the "
                        "model cannot separate those two.")
with tab_how:
    shared = int((flex.groupby("condition_id")["condition_id"].transform("size") > 1).sum())
    st.markdown("**Validation:** 5-fold *grouped* cross-validation (repeated with 5 shuffles for the flame-out model, "
                "once for K). Every repeat of the same test "
                f"condition stays on the same side of the split ({shared} of {len(flex)} FLEX runs share their "
                "conditions with another run, so a random split would leak). Every model is compared with a dumb "
                "baseline.")
    glossary_list(["grouped cv", "calibration", "conformal", "light", "outcomes"])
