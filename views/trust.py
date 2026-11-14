import plotly.express as px
import streamlit as st

from ignis.data import load_cv, load_models

st.title("Can you trust this? - model card")
cv = load_cv()
st.markdown("**Validation:** 5-fold *grouped* cross-validation - every repeat of the same test "
            "condition stays on the same side of the split. Every model is compared with baselines.")
for task, metric in [("A extinction", "balanced_acc"), ("B burning-rate K", "MAE")]:
    sub = cv[cv["task"] == task]
    st.plotly_chart(px.strip(sub, x="model", y=metric, title=f"{task}: {metric} per fold"))
    st.dataframe(sub.groupby("model")[metric].agg(["mean", "min", "max"]).round(3))
cov = [r for r in load_models()["k"]["coverage_check"] if r["level"] == "80%"]
st.metric("Measured coverage of the '80%' K interval on unseen conditions",
          f"{sum(r['coverage'] for r in cov) / len(cov):.0%}")
st.markdown("**Limits:** 274 tabulated tests, 2 fuels, pressure 0.69-3.05 atm, O2 0.12-0.34; "
            "pressure above 1 atm only occurs together with ~70% CO2; no partial-gravity data exist in PSI; "
            "Disruption labels may reflect needle contamination.")
