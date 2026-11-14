# Fire story scene (`fire_story.html`)

A five-scene 3D story rendered with three.js 0.160.0 (loaded from `cdn.jsdelivr.net`, pinned) inside
Streamlit's components iframe. `ignis/simulation.py` injects one JSON object (see the params contract in
its docstring); everything else is in this single HTML file.

| Scene | What it shows | Source |
|---|---|---|
| 1 Earth lab | Teardrop candle flame, buoyant plume, smoke, hot-gas / fresh-air arrows | Illustrative |
| 2 Into orbit | Generic module (no logos or markings) over a procedural Earth | Illustrative |
| 3 Inside the cabin | Panels, handrails, fan, smoke detector, combustion chamber box | Illustrative |
| 4 Droplet flame | d(t)² = d0² − K·t with K from the model; flame goes out at the median extinction diameter of the nearest NASA runs when P(extinction) ≥ 0.5; "not simulated" when the light is RED; cool-flame glow for heptane after extinction | **Data**: burn timing, K ± 80% interval, P(extinction), extinction diameter. Illustrative: flame shape, colour, size, needles, igniters, diffusion particles, droplet shrinking after extinction |
| 5 Spark in the cabin | Arc, material ignition, fan ON (fed, stretched flame) vs OFF (small, nearly spherical), smoke cloud that does not rise | Illustrative and qualitative (O2 only scales size and brightness) |

Screen time: the visible burn plays in 10–20 s (real time when it lasts 10–20 s, otherwise slowed down or sped
up); the HUD always shows real seconds and the playback factor.

Testing options (open the rendered HTML directly): `?scene=1..5`, `&t=<seconds into the scene>` (pauses
there), `&fan=off`, `&play=1`. Without WebGL or without internet, the page shows a message and keeps the captions,
data panel and the d² plot working.
