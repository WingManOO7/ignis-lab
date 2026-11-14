"""Plain-English definitions used across pages, plus a reusable collapsible panel."""
import streamlit as st

GLOSSARY = {
    "K": ("Burning-rate constant K (mm²/s)",
          "How fast a burning droplet shrinks: the slope of its diameter-squared against time. "
          "Bigger K = faster burning. FLEX values are mostly about 0.25-0.65 mm²/s."),
    "d2 law": ("d² law",
               "In microgravity a burning droplet's diameter squared falls in a straight line with time: "
               "d(t)² = d0² - K·t. So burnout time is about d0²/K if the flame does not go out first."),
    "outcomes": ("Extinction / Completion / Disruption",
                 "How a FLEX test ended. Extinction: the visible flame went out before the fuel was used up. "
                 "Completion: the droplet burned away completely. Disruption: the droplet broke apart; NASA "
                 "suspects fuel-needle contamination for many of these, so we do not use them as labels."),
    "cool flame": ("Cool flame",
                   "A low-temperature, invisible burning stage that FLEX discovered: heptane droplets kept "
                   "burning after the visible flame went out (Nayagam et al., 2012)."),
    "conformal": ("Conformal interval (the ± on K)",
                  "A range built from the model's real errors on test conditions it never saw. Our '80%' range "
                  "contained the true K for about 80% of such runs - we measured it, not assumed it."),
    "grouped cv": ("Grouped cross-validation",
                   "Testing a model on data it has not seen, where all repeats of the same test condition stay "
                   "together. A random split would let the model 'peek' at near-identical runs."),
    "light": ("GREEN / AMBER / RED (extrapolation check)",
              "GREEN: close to real NASA runs. AMBER: inside the tested ranges but far from any single run. "
              "RED: outside what NASA tested, or a combination never tested together - numbers are withheld."),
    "calibration": ("Calibrated probability",
                    "When the model says 80%, the event should happen about 80% of the time. We check this with "
                    "a reliability chart on the Trust page."),
    "pds": ("Prevention / Detection / Suppression",
            "NASA's fire-safety framework: stop fires starting (materials, flammability limits), notice them "
            "early (smoke detectors), and put them out (e.g. CO2 or helium dilution, water mist)."),
}


def glossary_panel(terms=None, title="Glossary - what these words mean"):
    """Collapsible list of definitions; terms = list of GLOSSARY keys (default: all)."""
    with st.expander(title):
        for key in terms or GLOSSARY:
            name, text = GLOSSARY[key]
            st.markdown(f"**{name}** - {text}")
