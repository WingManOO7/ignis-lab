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
SCOPE_SHORT = ("**Model scope:** isolated FLEX fuel droplets (n-heptane, methanol), inside NASA's tested conditions "
               "only.")
MODEL_SCOPE = ("The models were trained only on NASA FLEX (PSI-69): isolated n-heptane and methanol droplets burned on "
               "the ISS. For such a droplet they estimate two things: whether its visible flame goes out early, and its "
               "burning-rate constant K. They do NOT predict whole spacecraft fires, the flammability of solid "
               "materials (fabrics, plastics - studied in BASS, BASS-II and Saffire), smoke behaviour or detection, or "
               "partial-gravity (Moon/Mars) outcomes. Outside NASA's tested conditions the app shows RED and withholds "
               "the numbers: the models are not validated there.")
SCOPE_DETAILS = MODEL_SCOPE
CHART_SCOPE = "FLEX isolated droplets only; no prediction outside NASA's tested conditions."
# Machine-readable scope attached to every downloaded prediction
SCOPE_RECORD = {
    "applies_to": "isolated fuel droplets (n-heptane, methanol) as burned in NASA FLEX (PSI-69), inside the tested "
                  "conditions (traffic light GREEN or AMBER)",
    "does_not_predict": ["whole spacecraft fires", "solid-material flammability", "smoke behaviour or detection",
                         "partial-gravity (Moon/Mars) outcomes"],
    "outside_tested_conditions": "traffic light RED; numbers withheld; not validated",
}


def scope_note():
    """One-line scope banner (always visible on pages that use the FLEX models); full text in the tooltip."""
    ui.note(SCOPE_SHORT, tone="quiet", details=SCOPE_DETAILS)


def why_and_scope():
    """Full 'why FLEX matters' + scope text (used inside expanders and 'How to read' tabs)."""
    st.markdown(WHY_FLEX)
    st.info(SCOPE_FLEX)
