import plotly.express as px
import streamlit as st

from ignis.data import load_flex

st.title("FLEX run explorer - 274 real ISS droplet burns")
df = load_flex()
fuels = st.multiselect("Fuel", sorted(df["fuel"].unique()), default=sorted(df["fuel"].unique()))
dil = st.multiselect("Diluent", ["N2", "CO2", "He"], default=["N2", "CO2", "He"])
view = df[df["fuel"].isin(fuels) & df["diluent"].isin(dil)]

fig = px.scatter(view, x="x_o2", y="d0_mm", color="test_end", symbol="diluent", facet_col="fuel",
                 hover_data=["flex_id", "test_date", "p_atm", "x_co2", "x_he", "k_mm2_s", "dext_mm"],
                 labels={"x_o2": "O2 mole fraction", "d0_mm": "initial droplet diameter (mm)"},
                 title="Outcome of every run by oxygen level and droplet size")
st.plotly_chart(fig)
fig2 = px.scatter(view.dropna(subset=["k_mm2_s"]), x="x_o2", y="k_mm2_s", color="diluent",
                  facet_col="fuel", hover_data=["flex_id"],
                  labels={"k_mm2_s": "burning-rate constant K (mm²/s)", "x_o2": "O2 mole fraction"})
st.plotly_chart(fig2)
st.caption("Disruption outcomes may be caused by needle-coating contamination (NASA/TP-2015-216046, sec. 5.2).")
st.dataframe(view, hide_index=True)
