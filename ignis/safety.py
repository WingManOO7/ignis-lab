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

# ==================================================================================== history and practice
# Facts about extinguishers, past fires and today's fire-safety practice, each with its source (NASA unless marked).
# Every key in "src" must be in SOURCES (tested). "link" is OUR interpretation of how it relates to IGNIS LAB.
SOURCES = {
    "ops23": ("Tobias & McMillan, history of ISS, Shuttle and Orion emergency operations, SpaceOps 2023 (NASA JSC)",
              "https://ntrs.nasa.gov/api/citations/20220019247/downloads/Emergency%20Ops%20History%20for%20SpaceOps%20Conference%202023.pdf"),
    "pfe13": ("NASA (2013), water-mist portable fire extinguisher for the ISS", "https://ntrs.nasa.gov/citations/20130011664"),
    "spinoff": ("NASA Spinoff, water-mist fire extinguisher", "https://spinoff.nasa.gov/node/11065"),
    "nas_halon": ("National Academies (1996), Halon 1301 in the Space Shuttle", "https://www.nationalacademies.org/read/5435/chapter/5"),
    "shuttle_fds": ("NASA, Space Shuttle fire detection and suppression", "https://ntrs.nasa.gov/citations/19930011015"),
    "sp4009": ("NASA SP-4009, The Apollo Spacecraft: A Chronology, Vol. IV",
               "https://www.nasa.gov/wp-content/uploads/2023/03/sp-4009vol4.pdf"),
    "dsto": ("DSTO (Australian defence research, 2006), water mist on ships",
             "https://www.mobilityengineeringtech.com/component/content/article/5081-dsto-0001"),
    "epa_co2": ("US EPA, Carbon dioxide as a fire suppressant: examining the risks",
                "https://19january2025snapshot.epa.gov/snap/carbon-dioxide-fire-suppressant-examining-risks/index.html"),
    "epa_halon": ("US EPA, Halons program", "https://www.epa.gov/ozone-layer-protection/halons-program"),
    "csacp": ("NASA, Compound Specific Analyzer-Combustion Products (CSA-CP)", "https://ntrs.nasa.gov/citations/20050217459"),
    "apollo1": ("NASA, Apollo 1 mission page", "https://www.nasa.gov/mission/apollo-1/"),
    "sp350": ("NASA SP-350, Apollo Expeditions to the Moon, ch. 4.4",
              "https://www.nasa.gov/wp-content/uploads/static/history/SP-350/ch-4-4.html"),
    "apollo_atm": ("NASA, 50th anniversary of the mixed-gas atmosphere for Apollo",
                   "https://www.nasa.gov/feature/50th-anniversary-of-nasa-deciding-on-a-mixed-gas-atmosphere-for-apollo-a-direct-result-of"),
    "apollo13": ("NASA, 50 years ago: the Apollo 13 Review Board report",
                 "https://www.nasa.gov/history/50-years-ago-apollo-13-review-board-report"),
    "mir": ("NASA, 25 years ago: fire aboard space station Mir", "https://www.nasa.gov/feature/25-years-ago-fire-aboard-space-station-mir"),
    "elektron": ("News report (AP via NBC News), 18 Sep 2006", "https://www.nbcnews.com/news/amp/wbna14889541"),
    "test1": ("NASA, will a material that passes NASA-STD-6001 Test 1 pass in microgravity?",
              "https://ntrs.nasa.gov/api/citations/20160010292/downloads/20160010292.pdf"),
    "bass2": ("NASA, BASS-II results: oxygen margin of safety",
              "https://ntrs.nasa.gov/api/citations/20160000593/downloads/20160000593.pdf"),
    "saffire_end": ("NASA (2024), flame burns out on long-running spacecraft fire experiment",
                    "https://www.nasa.gov/humans-in-space/flame-burns-out-on-nasas-long-running-spacecraft-fire-experiment/"),
    "saffire21": ("Urban et al., Saffire IV and V, ICES 2021",
                  "https://ntrs.nasa.gov/api/citations/20210011521/downloads/ICES%202021-266%200503-2021%20final.pdf"),
    "eawg": ("NASA, choosing the 8.2 psia / 34% O2 exploration atmosphere", "https://ntrs.nasa.gov/citations/20130013505"),
    "explo26": ("NASA (2026), materials for an 8.2 psia / 34-40% O2 environment", "https://ntrs.nasa.gov/citations/20260003925"),
}

EXTINGUISHERS = [
    {"name": "Water mist", "space": "ISS (US segment, open cabin); Orion carries a similar water-spray extinguisher",
     "earth": "Ships, as a replacement for Halon 1301 flooding",
     "how": "A tank of water and nitrogen in separate bladders (6 lb and 1.2 lb) mixes on discharge into a very fine "
            "mist. The droplets take the fire's heat as they turn to steam.",
     "cabin": "The air stays breathable, unlike with CO2. It was chosen with lithium-ion battery fires in mind, which can "
              "keep burning with very little oxygen. Nine units were built; the last reached the ISS in 2016.",
     "src": ["spinoff", "pfe13", "ops23", "dsto"]},
    {"name": "Carbon dioxide (CO2)", "space": "ISS (US segment), for fires inside equipment racks",
     "earth": "Portable extinguishers and room-flooding systems",
     "how": "About 2.7 kg of CO2 pushes the oxygen away from the flame.",
     "cabin": "The crew's filter masks cannot remove CO2, so they must wear oxygen masks to use it, and NASA notes that it "
              "creates an unsafe breathing environment. On Earth, the CO2 level that puts out a fire is many times the "
              "lethal level: the US EPA counted 62 incidents and 119 deaths.",
     "src": ["ops23", "pfe13", "epa_co2"]},
    {"name": "Water-based foam / gel", "space": "ISS Russian segment; Mir (1997); the Apollo command module after Apollo 1",
     "earth": "Common portable extinguishers",
     "how": "A water-based foam or gel, sprayed onto the fire.",
     "cabin": "After the Apollo 1 fire, NASA chose an aqueous gel (foam) extinguisher for the command module (Sep 1967). "
              "The Mir crew used three foam extinguishers on the 1997 fire.",
     "src": ["pfe13", "sp4009", "mir"]},
    {"name": "Halon 1301", "space": "Space Shuttle: 3 fixed bottles in the avionics bays and 3 portable ones in the crew cabin",
     "earth": "Aircraft (recycled halon only); new production ended in the US in 1994 under the Montreal Protocol",
     "how": "A gas released from bottles; the three fixed Shuttle bottles together would give about 1% (10,000 ppm) in the cabin.",
     "cabin": "Not used on the ISS: at high temperature it breaks down into toxic gases.",
     "src": ["nas_halon", "shuttle_fds", "ops23", "epa_halon"]},
]

ISS_RESPONSE = [
    ("Detect", "Photoelectric and ionisation smoke detectors in the cabin, in air ducts and inside racks; or a crew "
               "member calls it."),
    ("Automatic response", "Fans, gas feeds and oxygen generation switch off. A rack alarm also cuts that rack's power."),
    ("Protect the crew", "Gather and put on masks: oxygen breathing apparatus (aboard since 2000) or respirators with "
                         "fire cartridges (since 2011)."),
    ("Find the source", "Sample the air through fireports with a handheld analyser (CSA-CP), which measures CO, HCl, HCN "
                        "and O2."),
    ("Put it out", "Remove power first, then use an extinguisher; power down and leave the module if needed."),
    ("Clean the air", "Filter canisters clean the cabin afterwards. Crews never let a fire block the way to their return "
                      "vehicle."),
]
ISS_RESPONSE_SRC = ["ops23", "csacp"]

INCIDENTS = [
    {"year": 1967, "title": "Apollo 1", "when": "27 Jan 1967, launch rehearsal at Launch Complex 34 (on the ground)",
     "what": "A fire swept through the command module in seconds. Astronauts Virgil I. \"Gus\" Grissom, Edward H. White II "
             "and Roger B. Chaffee died.",
     "why": "The cabin held 100% oxygen at 16 psi. The likely cause was a tiny spark, perhaps a short circuit in the "
            "wiring. Velcro, netting and paper were aboard, and the hatch opened inwards.",
     "changed": ["A new hatch that opens outwards with a quick-release latch.",
                 "On the pad, 60% oxygen / 40% nitrogen at 16 psi instead of pure oxygen (first flown on Apollo 7).",
                 "Metal shields over exposed wires; flammable materials replaced with fire-retardant ones.",
                 "An aqueous gel (foam) fire extinguisher for the command module.",
                 "Crews did not fly again for 21 months."],
     "link": "Oxygen-rich air plus a wiring spark is the scenario of the 3D wiring station (illustrative): raise the cabin "
             "oxygen past 30% and the fire flash-ignites. Exploration habitats plan oxygen-rich air again (34%); there "
             "our model shows RED, because FLEX never ran near it.",
     "explore": ("views/simulate.py", "Try the wiring station in the 3D Fire story"),
     "src": ["apollo1", "sp350", "apollo_atm", "sp4009"]},
    {"year": 1970, "title": "Apollo 13", "when": "13 Apr 1970, about 55 h 55 min into the flight",
     "what": "A short circuit started a fire inside oxygen tank No. 2 of the service module.",
     "why": "Heater switches rated for 28 V had been run at 65 V in ground testing. The heat very likely damaged the "
            "Teflon insulation of nearby wiring, inside pure oxygen.",
     "changed": ["A third oxygen tank, in a different bay.", "Upgraded thermostats; stirring fans removed from the tanks.",
                 "Wiring sheathed in stainless steel.", "Apollo 14 slipped to January 1971."],
     "link": "Again wiring in pure oxygen. Materials that are safe in normal air can burn in oxygen-rich gas, which is why "
             "the oxygen level matters so much in our models and in the Atlas.",
     "explore": ("views/atlas.py", "See which NASA tests ran at high oxygen in the Atlas"),
     "src": ["apollo13"]},
    {"year": 1997, "title": "Fire aboard space station Mir",
     "when": "February 1997 (NASA dates it 24 Feb), Kvant-1 module, six people aboard",
     "what": "A solid-fuel oxygen generator caught fire. The flame was about 3 ft long, with molten metal, and burned for "
             "several minutes; it blocked the way to one of the Soyuz return craft. The crew, including NASA astronaut "
             "Jerry Linenger, wore oxygen masks and used three foam extinguishers. Smoke took several hours to clear; "
             "no one was lastingly harmed. NASA calls it the worst in-orbit fire in the history of spaceflight.",
     "why": "Likely latex glove material inside the oxygen-generator canister.",
     "changed": ["Russia changed crew training and how the canisters are prepared.",
                 "The lessons carried over to the ISS, e.g. never let a fire block the way to the return vehicle."],
     "link": "The smoke lingered for hours: without gravity, smoke does not rise to a detector. The 3D story shows the "
             "smoke staying after the fire is out (illustrative), and SAME/SAME-R studied spacecraft smoke detection.",
     "explore": ("views/simulate.py", "See the smoke stay in the 3D Fire story"),
     "src": ["mir", "ops23"]},
    {"year": 2006, "title": "ISS oxygen-generator smoke (not a fire)", "when": "18 Sep 2006 (news report)",
     "what": "The Elektron oxygen generator overheated and leaked potassium hydroxide, giving a burning-rubber smell and "
             "light smoke. The crew wore masks and gloves, the ventilation was shut off and a charcoal filter cleaned "
             "the air. A NASA spokesman called it \"just an irritant issue\".",
     "why": "An overheating oxygen generator (as reported; we found no NASA report).",
     "changed": ["The standard response worked: ventilation off, masks on, air filtered."],
     "link": "Oxygen generators are a recurring hazard (Mir, 1997, too). Switching the fans off first is the same move as "
             "the fan-off button in our wiring station, which starves the flame (illustrative).",
     "explore": None, "src": ["elektron"]},
]

PRACTICE = [
    {"title": "Screening materials on the ground", "src": ["test1", "bass2"],
     "text": "Every cabin material must pass NASA-STD-6001 Test 1 (upward flame spread): the flame must go out before it "
             "spreads 15 cm. But the test relies on hot air rising, which does not happen in orbit. On the ISS (BASS-II), "
             "a PMMA rod that stopped burning at 16% oxygen on Earth kept burning at 13.6% in orbit: a negative oxygen "
             "margin of safety of 2.4% O2.",
     "link": "This is why the prevention cards ask whether the Earth test is enough."},
    {"title": "Burning real fires on purpose: Saffire", "src": ["saffire_end", "saffire21"],
     "text": "Six experiments over eight years (2016 to 9 Jan 2024) burned large samples inside empty Cygnus cargo ships "
             "after they left the ISS, more than ten times larger than earlier low-gravity fire tests. Saffire IV and V "
             "burned 40 cm-wide samples releasing up to 10 kW; the last, Saffire-VI, ran 19 tests at higher oxygen and "
             "lower pressure. NASA: flames spread quickly and reached a steady size and burn rate.",
     "link": "The 3D wiring station's flash and smoke behaviour follows Saffire reports (illustrative)."},
    {"title": "Choosing the air for exploration", "src": ["eawg", "explo26"],
     "text": "NASA's exploration atmosphere is 8.2 psia with 34% oxygen (first proposed as 8.0 psia / 32%, then enriched to "
             "reduce the risk of hypoxia). A 2026 NASA study calls material flammability \"the most critical hurdle\" at "
             "8.2 psia / 34-40% O2, with 70% of the assessed subsystems needing replacement materials.",
     "link": "This is the research gap in our Atlas: FLEX ran no tests near this atmosphere, so Predict and the 3D chamber "
             "show RED there."},
]
