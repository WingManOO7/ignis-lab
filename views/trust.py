import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ignis.data import ROOT, load_cv, load_models

st.title("Can you trust this? - model card")
cv = load_cv()
meta = load_models()["clf"]["meta"]
st.markdown("**Validation:** 5-fold *grouped* cross-validation, repeated 5 times. Every repeat of the same test "
            "condition stays on the same side of the split (257 of 274 FLEX runs share their conditions with "
            "another run, so a random split would leak). Every model is compared with a dumb baseline.")

# ---------------------------------------------------------------- Task A
st.subheader("A. Will the visible flame go out before the droplet burns out?")
st.caption(f"{meta['n_rows_clf']} runs (Extinction vs Completion; Disruption excluded). "
           f"Shown in the app: **{meta['classifier']}**.")
a = cv[cv["task"] == "A extinction"]
summary = a.groupby("model")[["balanced_acc", "recall_completion", "roc_auc", "brier"]].mean().round(3)
summary.columns = ["balanced accuracy (higher better)", "catches 'burns to completion'",
                   "ROC-AUC (higher better)", "Brier: probability error (lower better)"]
st.dataframe(summary.sort_values("ROC-AUC (higher better)", ascending=False))
st.plotly_chart(px.strip(a, x="model", y="balanced_acc", title="Balanced accuracy per fold (spread = honesty)"))

rel_path = ROOT / "reports/reliability_oof.csv"
if rel_path.exists():
    rel = pd.read_csv(rel_path)
    rel["bin"] = pd.cut(rel["p_extinction"], [0, 0.5, 0.7, 0.8, 0.9, 1.0], include_lowest=True)
    t = rel.groupby("bin", observed=True).agg(predicted=("p_extinction", "mean"),
                                              observed=("extinguished", "mean"), n=("extinguished", "size"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration",
                             line=dict(dash="dash", color="gray")))
    fig.add_trace(go.Scatter(x=t["predicted"], y=t["observed"], mode="markers+lines+text", name="our model",
                             text=[f"n={n}" for n in t["n"]], textposition="top left", marker=dict(size=10)))
    fig.update_layout(title="Reliability: when the model says X%, how often did NASA's flame really go out?",
                      xaxis_title="predicted probability (out-of-fold)", yaxis_title="observed share", height=420)
    st.plotly_chart(fig)
    st.caption("We first trained with balanced class weights. That inflated the rare outcome: when it said "
               "0-20%, flames actually went out 55% of the time. Switching to plain logistic regression fixed "
               "the probabilities without losing accuracy.")

# ---------------------------------------------------------------- Task B
st.subheader("B. Burning-rate constant K (mm²/s)")
b = cv[cv["task"] == "B burning-rate K"]
st.dataframe(b.groupby("model")[["MAE", "R2"]].agg(["mean", "min", "max"]).round(3))
st.plotly_chart(px.strip(b, x="model", y="MAE", title="Mean absolute error per fold (lower is better)"))
cov = [r for r in load_models()["k"]["coverage_check"] if r["level"] == "80%"]
st.metric("Measured coverage of the '80%' K interval on unseen conditions",
          f"{sum(r['coverage'] for r in cov) / len(cov):.0%}")

st.subheader("Limits")
st.markdown("- 274 tabulated tests, 2 fuels, pressure 0.69-3.05 atm, O2 0.12-0.34. Pressures above 1 atm only "
            "occur together with ~70% CO2, so the app flags other high-pressure mixes RED.\n"
            "- No FLEX test exists at NASA's exploration atmosphere (8.2 psia, 34% O2); the only microgravity "
            "flame tests there are 20 ACME CFI-G gas-flame tests (see the Atlas).\n"
            "- 'Disruption' outcomes may reflect fuel-needle contamination (NASA/TP-2015-216046 sec. 5.2) and are "
            "not used as labels; the Predict page warns when nearby runs disrupted.\n"
            "- No partial-gravity (Moon/Mars) combustion data exist in PSI. Models learn correlations, not physics.")
