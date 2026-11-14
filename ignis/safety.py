"""Evidence-linked safety-control cards: which NASA investigations could inform fire detection, suppression and
material screening / prevention.

Each card separates three things on purpose:
  measured  - what the investigation actually measured or studied (PSI record + team-verified curation.json facts)
  reported  - optional NASA-reported result, quoted closely with its NASA source link
  question  - the safety question it MAY help inform: OUR INTERPRETATION, phrased as a question - never a NASA finding
              or an engineering recommendation.
Nothing here is computed by the models. Accessions must exist in data/atlas/investigations.json (tested)."""

NTRS = {
    "flex_tp": ("NASA/TP-2015-216046, FLEX detailed results", "https://ntrs.nasa.gov/citations/20150023456"),
    "detect_wp": ("NASA fire-detection white paper (Fortenberry et al., 2021)",
                  "https://ntrs.nasa.gov/api/citations/20210022143/downloads/Fire%20detection%20white%20paper%20final%20211031.pdf"),
    "saffire21": ("Urban et al., Saffire IV and V, ICES 2021",
                  "https://ntrs.nasa.gov/api/citations/20210011521/downloads/ICES%202021-266%200503-2021%20final.pdf"),
    "saffire24": ("Urban et al., Saffire VI, ICES 2024",
                  "https://ntrs.nasa.gov/api/citations/20240002981/downloads/Saffire-ICES-2024-ICES-365-accepted%20final.pdf"),
    "bass2_tm": ("Olson et al., BASS-II summary report, NASA/TM-20210011385", "https://ntrs.nasa.gov/citations/20210011385"),
    "same_fs": ("NASA SAME fact sheet",
                "https://www.nasa.gov/wp-content/uploads/2025/07/smoke-aerosol-measurement-experiment-same.pdf"),
    "acme": ("Stocker, ACME overview (2021)",
             "https://ntrs.nasa.gov/api/citations/20210022542/downloads/ACME%20JASMAC-33%2020211007.pdf"),
}

PILLARS = {
    "detection": ("Fire detection & smoke monitoring", "Noticing a fire early, in air where smoke does not rise."),
    "suppression": ("Fire suppression", "Making a flame go out: diluent gases, oxygen and airflow."),
    "prevention": ("Material screening & fire prevention", "Which materials and atmospheres can sustain a flame."),
}

CARDS = [
    # ---------------------------------------------------------------- detection
    {"pillar": "detection", "accessions": ["PSI-102", "PSI-101"], "title": "SAME and SAME-R: smoke from spacecraft materials",
     "measured": "Smoke made by overheating spacecraft materials in microgravity (5 materials in SAME-R). Smoke-particle "
                 "sizes, plus the signals of ISS-type, shuttle-type and ionisation smoke detectors and particle counters "
                 "for each test.",
     "reported": "The ISS smoke detector failed to alarm for Kapton smoke in half the tests and for Teflon smoke in "
                 "two-thirds of them.", "reported_src": "detect_wp",
     "question": "Would a smoke detector tuned on Earth smoke reliably notice smoke from the materials inside a "
                 "spacecraft or habitat?", "explore": None},
    {"pillar": "detection", "accessions": ["PSI-47"], "title": "DAFT / DAFT-2: dust vs smoke instruments",
     "measured": "No fire: test dust was released and sampled at several ISS cabin locations with the particle "
                 "instruments used for SAME, to check how those instruments behave in orbit.",
     "reported": None, "reported_src": None,
     "question": "Could the same instruments tell ordinary cabin dust from smoke, to avoid false alarms?",
     "explore": None},
    {"pillar": "detection", "accessions": ["PSI-98", "PSI-99", "PSI-100"], "title": "Saffire I-III: large fires in a cargo ship",
     "measured": "Large solid samples burned inside a departing Cygnus cargo vehicle: fire growth, burn time and spread, "
                 "with cabin sensor and gas telemetry.",
     "reported": "In the later Saffire VI tests, CO and CO2 passed crew exposure limits while the temperature rose only "
                 "near the fire, and a typical smoke-alarm threshold was reached only after most of the hazardous gas "
                 "had been released.", "reported_src": "saffire24",
     "question": "Should spacecraft fire detection watch toxic gases as well as smoke and heat?", "explore": None},
    # ---------------------------------------------------------------- suppression
    {"pillar": "suppression", "accessions": ["PSI-69"], "title": "FLEX: gases that put droplet flames out",
     "measured": "274 isolated n-heptane and methanol droplets burned on the ISS in O2/N2 with CO2 (up to 70%) or "
                 "helium (up to 45%) added: whether the flame went out early, the burning rate K and the extinction "
                 "diameter.",
     "reported": "In O2/N2 the limiting oxygen level, below which the droplet flames could not be sustained, was about "
                 "12% for methanol and 15% for heptane.", "reported_src": "flex_tp",
     "question": "How much diluent gas, or how little oxygen, makes a small liquid-fuel flame go out early?",
     "explore": ("views/predict.py", "Explore it in Predict (FLEX droplets only)")},
    {"pillar": "suppression", "accessions": ["PSI-68"], "title": "FLEX-2: more realistic fuels",
     "measured": "Follow-up droplet tests with fuels and blends that mimic real combustor fuels, in O2/N2 or O2/He "
                 "(design ranges 0.5-3 atm, 17-30% O2). No per-test results table is published in PSI.",
     "reported": None, "reported_src": None,
     "question": "Do the FLEX suppression trends still hold for more realistic fuel blends?", "explore": None},
    {"pillar": "suppression", "accessions": ["PSI-26", "PSI-25"], "title": "BASS and BASS-II: burning and suppression of solids",
     "measured": "Ignition, flame growth, spread and extinction of solid materials (e.g. PMMA, SIBAL fabric) in a "
                 "controlled airflow, with chamber O2 lowered to as little as 13.6% in BASS-II.",
     "reported": None, "reported_src": None,
     "question": "Which combinations of airflow and reduced oxygen make a burning solid stop spreading?",
     "explore": None},
    {"pillar": "suppression", "accessions": ["PSI-39"], "title": "CFI: helium and cool flames",
     "measured": "n-dodecane droplets and blends at 0.5-5 atm, including tests with helium added, to study cool flames "
                 "(a low-temperature flame that can continue after the visible flame is out). Conditions only; "
                 "no outcome table in PSI.",
     "reported": None, "reported_src": None,
     "question": "Can a fuel keep reacting invisibly after a fire looks extinguished, and does the diluent gas matter?",
     "explore": None},
    # ---------------------------------------------------------------- prevention
    {"pillar": "prevention", "accessions": ["PSI-26"], "title": "BASS: Earth screening test vs microgravity",
     "measured": "Designed to bridge NASA's Earth-gravity material screening test (NASA-STD-6001 Test 1) and actual "
                 "material flammability in microgravity, by burning the same materials in airflow on the ISS.",
     "reported": "Passing NASA-STD-6001 Test 1 cannot be assumed to mean that a material will not burn in low "
                 "gravity.", "reported_src": "saffire21",
     "question": "Is the Earth-gravity screening test enough to clear a cabin material for microgravity use?",
     "explore": None},
    {"pillar": "prevention", "accessions": ["PSI-98", "PSI-99", "PSI-100"], "title": "Saffire I-III: how big can a fire grow?",
     "measured": "How rapidly a large-scale fire grows in low gravity, and low-gravity flammability limits compared with "
                 "NASA's normal-gravity screening test (the investigation's stated objectives).",
     "reported": None, "reported_src": None,
     "question": "How large and how fast can a fire on real spacecraft materials grow, compared with what screening "
                 "tests suggest?", "explore": None},
    {"pillar": "prevention", "accessions": ["PSI-20"], "title": "ACME BRE: burning in exploration-like air",
     "measured": "A gas burner that emulates burning solids, run in ISS-like air, 10.2 psia / 26.5% O2 and "
                 "exploration-like 8.2 psia / 34% O2 atmospheres (the table lists up to 40% O2). Day-level log only.",
     "reported": None, "reported_src": None,
     "question": "Could the oxygen-rich, low-pressure air planned for exploration let more materials sustain a flame?",
     "explore": ("views/atlas.py", "See the exploration atmosphere in the Atlas")},
    {"pillar": "prevention", "accessions": ["PSI-159"], "title": "ACME CFI-G: ignition in oxygen-enriched air",
     "measured": "Gaseous fuels from a spherical burner in chamber O2 of 18-40% at 0.49-3.27 atm (normal flames), and "
                 "up to 85% O2 flowing from the burner (inverse flames). Per test: hot ignition yes/no, burn time, and "
                 "whether the flame self-extinguished.",
     "reported": None, "reported_src": None,
     "question": "Under oxygen-enriched cabin air, when do flames ignite and keep burning?",
     "explore": ("views/atlas.py", "See its tests near each habitat in the Atlas")},
]
