# Fire lab (`fire_story.html`)

An interactive 3D experience rendered with three.js 0.160.0 (pinned, from `cdn.jsdelivr.net`; OrbitControls and
bloom from the same version) inside Streamlit's components iframe. `ignis/simulation.py` fills three placeholders:
`/*__IGNIS_PARAMS__*/null` (starting conditions and the three crew-atmosphere presets), `/*__IGNIS_MODEL_DATA__*/null`
and `/*__IGNIS_MODEL_JS__*/` (the trained FLEX models, evaluated in the browser by `ignis_model.js`).

Places (buttons, the top bar, or clicking objects): **Earth lab → Orbit → Cabin**, with two cabin stations. A narrator
explains every step (typewriter text, plus the browser's built-in text-to-speech after the first click; mute
with *Voice*).

| Place / station | What you can do | Source |
|---|---|---|
| Earth lab | Candle with buoyant teardrop flame and rising smoke; *Switch gravity off* morphs it into a dim blue sphere | Illustrative (gravity-off flame based on NASA candle observations, no data) |
| Orbit | Generic module (no logos or markings) over a procedural Earth; click it to enter | Illustrative |
| Cabin | Fan, smoke detector, FLEX chamber, wire bundle (all clickable) | Illustrative |
| FLEX chamber | Fuel, pressure, O2, suppressant + fraction, droplet size, presets. Every change calls `IGNIS.predict` and restarts a looping d² burn: d² = d0² − K·t with the model's K; the flame goes out at the nearest runs' extinction diameter when P(extinction) ≥ 0.5; cool-flame glow for heptane; RED = greyed out, "not simulated". Slider bands = tested ranges | **Data**: K ± 80% interval, P(extinction), light, nearest runs, extinction diameter, tested ranges. Illustrative: flame size/brightness (mapped from K), colours, needles, igniters, diffusion particles |
| Wiring & fan | Spark the wires, fan ON/OFF, cabin O2 (shared slider), flash ignition at O2 ≥ 0.30 with the fan on, CO2 flooding, reset | Illustrative and qualitative, with NASA findings quoted (Urban et al. ICES 2021 / 2024, NASA Saffire, NASA History) |

Testing options (open a rendered HTML file directly): `?place=earth|orbit|cabin|chamber|wiring`, `&gravity=off`,
`&preset=iss|lunar|exploration`, `&fuel=`, `&o2=`, `&p=`, `&d0=`, `&fan=on|off`, `&spark=1`, `&suppress=<s>`,
`&t=<s>` (simulate that many seconds, then hold the moment), `&voice=0`. Without WebGL or internet the page shows a
message and the chamber controls, live numbers, d² plot and narrator still work.
