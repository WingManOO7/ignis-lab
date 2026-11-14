"""Shared wording shown on several pages, so every page tells the same, honest story."""
import streamlit as st

from ignis import ui

WHY_FLEX = ("**Why this matters.** FLEX is a controlled NASA dataset on how oxygen level, pressure and suppressant "
            "gases (CO2, helium) decide whether a flame survives in microgravity - the question behind choosing "
            "cabin atmospheres and fire-extinguishing gases for spacecraft and future habitats.")
SCOPE_FLEX = ("**Scope.** FLEX covers two liquid fuels (n-heptane and methanol) burned as isolated droplets. It is "
              "not a model of solid spacecraft materials such as fabrics or plastics - those were studied in BASS, "
              "BASS-II and Saffire (see the Investigation atlas). No Moon or Mars (partial-gravity) fire data exist "
              "in NASA PSI yet.")
SCOPE_SHORT = ("<b>Scope:</b> FLEX burned two liquid fuels (n-heptane, methanol) as single droplets. It says nothing "
               "about solid materials such as fabrics or plastics (BASS, BASS-II, Saffire in the Atlas), and NASA PSI "
               "has no Moon or Mars fire data yet.")


def scope_note():
    """One-line scope banner (always visible on pages that use the FLEX models)."""
    ui.note(SCOPE_SHORT, tone="quiet")


def why_and_scope():
    """Full 'why FLEX matters' + scope text (used inside expanders and 'How to read' tabs)."""
    st.markdown(WHY_FLEX)
    st.info(SCOPE_FLEX)
