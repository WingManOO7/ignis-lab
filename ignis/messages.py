"""Shared wording shown on several pages, so every page tells the same, honest story."""
import streamlit as st

WHY_FLEX = ("**Why this matters.** FLEX is a controlled NASA dataset on how oxygen level, pressure and suppressant "
            "gases (CO2, helium) decide whether a flame survives in microgravity - the question behind choosing "
            "cabin atmospheres and fire-extinguishing gases for spacecraft and future habitats.")
SCOPE_FLEX = ("**Scope.** FLEX covers two liquid fuels (n-heptane and methanol) burned as isolated droplets. It is "
              "not a model of solid spacecraft materials such as fabrics or plastics - those were studied in BASS, "
              "BASS-II and Saffire (see the Investigation atlas). No Moon or Mars (partial-gravity) fire data exist "
              "in NASA PSI yet.")


def why_and_scope():
    st.markdown(WHY_FLEX)
    st.info(SCOPE_FLEX)
