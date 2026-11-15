"""Shared look of IGNIS LAB: injected CSS, page header, provenance badge, notes, readouts, the evidence lamp,
and one Plotly template used by every chart.

Visual language (matches the 3D fire story): deep navy "mission control" background, flame orange = act here /
research gap, cool blue = NASA data, green / amber / red only for the evidence light."""
import hashlib
import re
from html import escape

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------- tokens
SPACE = "#081226"      # page background (deep navy)
HULL = "#0F1B33"       # cards, inputs
HULL_HI = "#16243F"    # raised surfaces
RULE = "#243756"       # borders
GRID = "#1B2B47"       # chart grid
INK = "#E6ECF5"        # text
DIM = "#8FA0BA"        # secondary text
FLAME = "#FF7A1A"      # primary accent
EMBER = "#FFB27A"      # light flame (text on dark)
DATA = "#5CB3FF"       # NASA data
GO, HOLD, STOP = "#3DDC84", "#FFC233", "#FF5468"   # evidence light ONLY

DISPLAY = "'Chakra Petch', 'Segoe UI', sans-serif"
BODY = "'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', 'Segoe UI', system-ui, sans-serif"
FONTS_URL = ("https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;500;700"
             "&family=Chakra+Petch:wght@500;600;700&display=swap")

# chart series colours: data blue first, flame second, then quiet companions (never green/amber/red)
SERIES = [DATA, FLAME, "#B39DFF", "#3FD6C5", "#E8C872", "#FF8FB8", "#9FB3D1"]
OUTCOME_COLORS = {"Extinction": DATA, "Completion": FLAME, "Disruption": "#B39DFF"}
LIGHT_COLORS = {"GREEN": GO, "AMBER": HOLD, "RED": STOP}

# ---------------------------------------------------------------- Plotly template
PLOT_BG = "#0C172D"     # opaque plot area (looks like the old 55% navy on the page) so nothing behind it can tint it
_axis = dict(gridcolor=GRID, zerolinecolor=RULE, linecolor=RULE, tickcolor=RULE, ticks="outside", ticklen=4,
             title=dict(font=dict(color=DIM, size=13)), tickfont=dict(color=DIM, size=12), automargin=True)
TEMPLATE = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG,
    font=dict(family=BODY, color=INK, size=13),
    title=dict(font=dict(family=DISPLAY, size=16, color=INK), x=0, xanchor="left", y=0.98),
    colorway=SERIES, xaxis=_axis, yaxis=_axis,
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK, size=12), orientation="h", y=-0.18, x=0,
                title=dict(font=dict(color=DIM))),
    hoverlabel=dict(bgcolor=HULL_HI, bordercolor=RULE, font=dict(family=BODY, color=INK, size=13)),
    margin=dict(l=8, r=8, t=44, b=8),
    colorscale=dict(sequential=[[0, "#0F1B33"], [0.5, "#2F6FB8"], [1, DATA]]),
    annotationdefaults=dict(font=dict(color=DIM, size=12)),
    shapedefaults=dict(line=dict(color=DIM)),
))
pio.templates["ignis"] = TEMPLATE
pio.templates.default = "ignis"
try:                                   # plotly express figures pick up the same template
    import plotly.express as px
    px.defaults.template = "ignis"
except Exception:                      # pragma: no cover
    pass


def chart(fig, **kwargs):
    """st.plotly_chart with the shared template and no Streamlit re-theming (same look on every page)."""
    fig.update_layout(template=TEMPLATE)
    # plotly express facet titles read "fuel=Heptane"; show just "Heptane"
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=", 1)[1])
                            if a.text and re.match(r"^[A-Za-z_]+=", a.text) else None)
    kwargs.setdefault("width", "stretch")
    return st.plotly_chart(fig, theme=None, **kwargs)


# ---------------------------------------------------------------- CSS
CSS = f"""
@import url('{FONTS_URL}');
:root {{
  color-scheme: dark;
  --ig-space:{SPACE}; --ig-hull:{HULL}; --ig-hull-hi:{HULL_HI}; --ig-rule:{RULE}; --ig-ink:{INK}; --ig-dim:{DIM};
  --ig-flame:{FLAME}; --ig-ember:{EMBER}; --ig-data:{DATA}; --ig-go:{GO}; --ig-hold:{HOLD}; --ig-stop:{STOP};
  --ig-display:{DISPLAY}; --ig-body:{BODY};
}}
/* the page itself is dark too (dark-mode extensions check html/body before recolouring a site) */
html, body {{ background-color: {SPACE} !important; }}
/* ---------- canvas */
[data-testid="stApp"] {{
  background:
    radial-gradient(1200px 520px at 78% -12%, rgba(92,179,255,.10), transparent 60%),
    radial-gradient(900px 480px at -10% 110%, rgba(255,122,26,.06), transparent 60%),
    {SPACE};
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stDecoration"], [data-testid="stAppDeployButton"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1240px; }}
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3 {{ letter-spacing: -.01em; }}

/* ---------- sidebar */
[data-testid="stSidebar"] {{ border-right: 1px solid var(--ig-rule); }}
[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"] {{ border-radius: .5rem; }}
[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: rgba(255,122,26,.13); box-shadow: inset 3px 0 0 var(--ig-flame);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: #FFE3CC; }}
[data-testid="stNavSectionHeader"] {{ color: var(--ig-dim); font-size: .8rem; margin-top: .4rem; }}

/* ---------- widgets */
[data-testid="stBaseButton-primary"] {{ border: 0; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p {{ color: #1A0B00 !important; font-weight: 700; }}
[data-testid="stBaseButton-primary"]:hover {{ background: #FF8E3C; }}
[data-baseweb="tag"] {{ background: rgba(255,122,26,.16) !important; border: 1px solid rgba(255,122,26,.4); }}
[data-baseweb="tag"] span {{ color: #FFD9BC !important; }}
[data-testid="stMetricValue"] {{ font-family: var(--ig-display); letter-spacing: -.01em; }}
[data-testid="stMetricLabel"] p {{ color: var(--ig-dim); }}
[data-testid="stTabs"] button[role="tab"] p {{ font-family: var(--ig-display); font-size: 1rem; font-weight: 600; }}
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ gap: 1.4rem; }}
[data-testid="stExpander"] summary p {{ font-weight: 700; }}
[data-testid="stExpander"] details {{ background: rgba(15,27,51,.45); }}
[data-testid="stPageLink"] a p {{ font-weight: 700; color: var(--ig-ember); }}
[data-testid="stCaptionContainer"] {{ color: var(--ig-dim); }}

/* ---------- page header */
.ig-head {{ margin: 0 0 .9rem 0; }}
.ig-head-row {{ display: flex; flex-wrap: wrap; align-items: center; gap: .55rem 1rem; }}
.ig-head h1 {{ font-family: var(--ig-display); font-weight: 600; font-size: 2.15rem; line-height: 1.1; margin: 0;
  padding: 0; color: var(--ig-ink); letter-spacing: -.01em; }}
.ig-head p {{ margin: .35rem 0 0; color: var(--ig-dim); font-size: 1.06rem; line-height: 1.45; max-width: 72ch; }}
.ig-src {{ display: inline-flex; align-items: center; gap: .45rem; padding: .28rem .7rem .28rem .55rem;
  border: 1px solid rgba(92,179,255,.38); background: rgba(92,179,255,.09); border-radius: 999px;
  color: #CFE6FF; font-size: .84rem; line-height: 1.2; white-space: nowrap; }}
.ig-src b {{ color: #fff; font-weight: 700; }}
.ig-src i {{ width: .5rem; height: .5rem; border-radius: 50%; background: var(--ig-data);
  box-shadow: 0 0 0 3px rgba(92,179,255,.18); flex: none; }}

/* ---------- notes */
[class*="st-key-ignote_"] {{ border-left: 3px solid var(--ig-data); background: rgba(92,179,255,.07);
  border-radius: 0 .55rem .55rem 0; padding: .45rem .8rem; height: auto !important; flex: 0 0 auto !important;
  margin-bottom: .35rem; }}
[class*="st-key-ignote_"] > div {{ flex-shrink: 0; height: auto !important; }}
[class*="st-key-ignote_"] [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
[class*="st-key-ignote_"] [data-testid="stMarkdownContainer"] p {{ margin-bottom: 0 !important; }}
abbr.ig-tip {{ font-family: var(--ig-body); font-weight: 400; font-size: .85rem; color: var(--ig-dim); cursor: help;
  text-decoration: none; margin-left: .35rem; vertical-align: .1em; }}
[class*="st-key-ignote_"] p {{ color: #D5DFEE; font-size: .95rem; line-height: 1.4; margin: 0; }}
[class*="st-key-ignote_"] strong {{ color: #fff; }}
[class*="st-key-ignote_caution"] {{ border-left-color: var(--ig-flame); background: rgba(255,122,26,.08); }}
[class*="st-key-ignote_quiet"] {{ border-left-color: var(--ig-rule); background: transparent; }}
[class*="st-key-ignote_quiet"] p {{ color: var(--ig-dim); }}
.ig-ro[title] {{ cursor: help; }}
.ig-note {{ border-left: 3px solid var(--ig-data); background: rgba(92,179,255,.07); border-radius: 0 .55rem .55rem 0;
  padding: .55rem .85rem; color: #D5DFEE; font-size: .95rem; line-height: 1.45; margin: .25rem 0 .6rem; }}
.ig-note b {{ color: #fff; }}
.ig-note.caution {{ border-left-color: var(--ig-flame); background: rgba(255,122,26,.08); }}
.ig-note.quiet {{ border-left-color: var(--ig-rule); background: transparent; color: var(--ig-dim); }}

/* ---------- readouts (big instrument numbers) */
.ig-readouts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1.1rem 1.6rem;
  margin: .2rem 0 .4rem; }}
.ig-ro {{ border-top: 2px solid var(--ig-data); padding-top: .55rem; min-width: 0; }}
.ig-ro.flame {{ border-top-color: var(--ig-flame); }}
.ig-ro.ink {{ border-top-color: var(--ig-rule); }}
.ig-ro .v {{ font-family: var(--ig-display); font-weight: 600; font-size: 2.35rem; line-height: 1.05; color: #fff;
  letter-spacing: -.01em; white-space: nowrap; }}
.ig-ro .v small {{ font-size: .5em; font-weight: 500; color: var(--ig-dim); margin-left: .2rem; }}
.ig-ro.flame .v {{ color: #FFC59A; }}
.ig-readouts.md .v {{ font-size: 2.05rem; }}
.ig-readouts.sm {{ grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: .9rem 1.2rem; }}
.ig-readouts.sm .v {{ font-size: 1.7rem; }}
.ig-readouts.sm .l {{ font-size: .88rem; }}
.ig-ro .l {{ margin-top: .3rem; color: var(--ig-ink); font-size: .95rem; line-height: 1.35; }}
.ig-ro .s {{ margin-top: .2rem; color: var(--ig-dim); font-size: .84rem; line-height: 1.35; }}

/* ---------- evidence lamp */
.ig-lamp {{ display: flex; gap: 1.1rem; align-items: center; padding: 1rem 1.15rem; border-radius: .9rem;
  border: 1px solid var(--lamp-edge); background: var(--lamp-bg); }}
.ig-lamp .bulb {{ flex: none; width: 3.4rem; height: 3.4rem; border-radius: 50%;
  background: radial-gradient(circle at 38% 34%, #fff 0 8%, var(--lamp) 34%, var(--lamp-deep) 100%);
  box-shadow: 0 0 0 5px var(--lamp-ring), 0 0 34px var(--lamp-glow); }}
.ig-lamp .word {{ font-family: var(--ig-display); font-weight: 700; font-size: 1.7rem; line-height: 1; color: var(--lamp); }}
.ig-lamp .txt {{ color: var(--ig-ink); font-size: 1.05rem; margin-top: .25rem; }}
.ig-lamp ul {{ margin: .4rem 0 0; padding-left: 1.1rem; color: var(--ig-dim); font-size: .9rem; line-height: 1.4; }}
.ig-lamp.GREEN {{ --lamp:{GO}; --lamp-deep:#0E6B3B; --lamp-ring:rgba(61,220,132,.16); --lamp-glow:rgba(61,220,132,.45);
  --lamp-edge:rgba(61,220,132,.35); --lamp-bg:rgba(61,220,132,.06); }}
.ig-lamp.AMBER {{ --lamp:{HOLD}; --lamp-deep:#7A5600; --lamp-ring:rgba(255,194,51,.16); --lamp-glow:rgba(255,194,51,.45);
  --lamp-edge:rgba(255,194,51,.38); --lamp-bg:rgba(255,194,51,.06); }}
.ig-lamp.RED {{ --lamp:{STOP}; --lamp-deep:#7A1424; --lamp-ring:rgba(255,84,104,.16); --lamp-glow:rgba(255,84,104,.45);
  --lamp-edge:rgba(255,84,104,.42); --lamp-bg:rgba(255,84,104,.07); }}
.ig-lamps {{ display: inline-flex; gap: .35rem; vertical-align: middle; }}
.ig-lamps i {{ width: .8rem; height: .8rem; border-radius: 50%; display: inline-block; }}

/* ---------- chips (what NASA saw) */
.ig-chips {{ display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; margin: .2rem 0; }}
.ig-chips .lab {{ color: var(--ig-dim); font-size: .92rem; margin-right: .2rem; }}
.ig-chip {{ display: inline-flex; align-items: baseline; gap: .35rem; padding: .25rem .65rem; border-radius: 999px;
  background: var(--ig-hull-hi); border: 1px solid var(--ig-rule); font-size: .92rem; color: var(--ig-ink); }}
.ig-chip b {{ font-family: var(--ig-display); font-size: 1.05rem; color: #fff; }}

/* ---------- home */
.ig-hero {{ display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); gap: 2rem; align-items: center;
  margin: .4rem 0 1.4rem; }}
.ig-hero h1 {{ font-family: var(--ig-display); font-weight: 700; font-size: clamp(2.8rem, 5.4vw, 4.4rem); line-height: .95;
  margin: 0; padding: 0; color: #fff; letter-spacing: -.02em; }}
.ig-hero .promise {{ font-family: var(--ig-display); font-weight: 500; font-size: clamp(1.2rem, 1.9vw, 1.45rem);
  line-height: 1.28; color: var(--ig-ink); margin: .8rem 0 .55rem; max-width: 36ch; }}
.ig-hero .sub {{ color: var(--ig-dim); font-size: 1.02rem; line-height: 1.5; max-width: 56ch; margin: 0; }}
.ig-orb-wrap {{ display: flex; flex-direction: column; align-items: center; gap: .8rem; }}
.ig-orb {{ width: min(230px, 28vw); aspect-ratio: 1; border-radius: 50%; position: relative;
  background:
    radial-gradient(circle at 47% 46%, rgba(255,255,255,.55) 0 1.3%, rgba(255,255,255,0) 2.4%),
    radial-gradient(circle, #1B2C4D 0 7.5%, rgba(27,44,77,0) 8.5%),
    radial-gradient(circle, rgba(92,179,255,.07) 0 30%, rgba(92,179,255,.16) 44%, rgba(255,226,180,.98) 51%,
                    rgba(255,160,70,.9) 55%, rgba(255,122,26,.42) 61%, rgba(255,122,26,.12) 69%, rgba(255,122,26,0) 75%);
  filter: drop-shadow(0 0 38px rgba(255,122,26,.32)); animation: ig-breathe 5.5s ease-in-out infinite; }}
.ig-orb-cap {{ color: var(--ig-dim); font-size: .84rem; text-align: center; max-width: 30ch; line-height: 1.4; }}
@keyframes ig-breathe {{ 0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 30px rgba(255,122,26,.28)); }}
                         50% {{ transform: scale(1.025); filter: drop-shadow(0 0 46px rgba(255,122,26,.42)); }} }}
@media (prefers-reduced-motion: reduce) {{ .ig-orb {{ animation: none; }} }}
.ig-card-t {{ font-family: var(--ig-display); font-weight: 600; font-size: 1.35rem; color: #fff; margin: 0; }}
.ig-card-d {{ color: var(--ig-dim); font-size: .97rem; line-height: 1.45; margin: .35rem 0 .2rem; min-height: 1.4em; }}
.ig-card-k {{ font-family: var(--ig-display); font-weight: 600; font-size: 2.1rem; line-height: 1; color: var(--ig-data);
  margin-bottom: .55rem; height: 2.2rem; display: flex; align-items: center; gap: .5rem; }}
.ig-card-k small {{ font-family: var(--ig-body); font-size: .9rem; font-weight: 400; color: var(--ig-dim); }}
.ig-sec {{ font-family: var(--ig-display); font-weight: 600; font-size: 1.2rem; color: var(--ig-ink); margin: 1.2rem 0 .5rem; }}
.ig-sec span {{ display: block; font-family: var(--ig-body); font-weight: 400; font-size: .9rem; color: var(--ig-dim);
  margin-top: .15rem; line-height: 1.4; }}

/* ---------- keyed containers */
.st-key-tour_box {{ border-left: 3px solid var(--ig-flame) !important; background: rgba(255,122,26,.06); }}
.st-key-pred_inputs {{ background: rgba(15,27,51,.55); }}
.st-key-limits p, .st-key-limits li {{ font-size: .94rem; line-height: 1.45; color: #CBD6E6; }}
.st-key-ask_answer {{ border-left: 3px solid var(--ig-data) !important; }}
.st-key-tour_steps {{ gap: .2rem; }}
.st-key-tour_steps button {{ justify-content: flex-start; text-align: left; min-height: 2.3rem; padding: .3rem .7rem; }}
.st-key-tour_steps button p, .st-key-tour_steps button div {{ text-align: left; justify-content: flex-start; }}
.st-key-tour_steps button > div {{ width: 100%; }}
.st-key-tour_steps [data-testid="stBaseButton-tertiary"] {{ color: var(--ig-dim); }}
.st-key-tour_steps [data-testid="stBaseButton-tertiary"]:hover {{ color: var(--ig-ink); background: var(--ig-hull); }}
.ig-steps {{ display: flex; gap: .3rem; margin: .1rem 0 .45rem; }}
.ig-steps i {{ height: 4px; flex: 1; border-radius: 2px; background: var(--ig-rule); }}
.ig-steps i.on {{ background: var(--ig-flame); }}
.ig-tour-k {{ color: var(--ig-ember); font-size: .86rem; }}
.ig-tour-t {{ font-family: var(--ig-display); font-weight: 600; font-size: 1.15rem; color: #fff; margin: .1rem 0 .2rem; }}
.ig-tour-x {{ color: #D5DFEE; font-size: .96rem; line-height: 1.45; }}

@media (max-width: 760px) {{
  .ig-hero {{ grid-template-columns: 1fr; }}
  .ig-orb {{ width: 170px; }}
  .ig-head h1 {{ font-size: 1.7rem; }}
  .ig-src {{ white-space: normal; }}
}}
"""


def inject_css():
    # CSS declares color-scheme: dark, so browsers' automatic dark mode leaves this already-dark page (and its charts) alone
    st.html(f"<style>{CSS}</style>")
    # Dark Reader's opt-out tag (rendered in the body; the extension looks for it anywhere in the document)
    st.markdown('<meta name="darkreader-lock">', unsafe_allow_html=True)


# ---------------------------------------------------------------- building blocks
def esc(text):
    return escape(str(text), quote=True)


def page_header(title, purpose, source):
    """Title + provenance badge (which NASA dataset this page uses) + one-line purpose."""
    st.html(f'<div class="ig-head"><div class="ig-head-row"><h1>{esc(title)}</h1>'
            f'<span class="ig-src"><i></i><span>Data: <b>{esc(source)}</b></span></span></div>'
            f'<p>{esc(purpose)}</p></div>')


def _key(prefix, text):
    return f"{prefix}_{hashlib.md5(str(text).encode('utf-8')).hexdigest()[:10]}"


def note(text, tone="info", details=None):
    """One-line callout (markdown). tone: 'info' (data blue), 'caution' (flame orange), 'quiet'.
    details: the full wording, shown in a tooltip (?) right next to the line."""
    with st.container(key=_key(f"ignote_{tone}", text)):
        st.markdown(text, help=details)


def section(title, sub=None, help=None):
    """Small display-font heading; optional short sub line and a tooltip with the details."""
    tip = f'<abbr class="ig-tip" title="{esc(help)}">&#9432;</abbr>' if help else ""
    st.html(f'<div class="ig-sec">{esc(title)}{tip}{f"<span>{esc(sub)}</span>" if sub else ""}</div>')


def readouts_html(items, size="", cols=None):
    """items: dicts with v (value, str), l (label), optional s (small line), u (unit), t (hover tooltip),
    tone ('data'|'flame'|'ink').
    size: '' (big), 'md' or 'sm'; cols: optional CSS grid-template-columns, e.g. '1fr 1.4fr 1fr'."""
    cells = []
    for it in items:
        unit = f"<small>{esc(it['u'])}</small>" if it.get("u") else ""
        sub = f'<div class="s">{esc(it["s"])}</div>' if it.get("s") else ""
        tip = f' title="{esc(it["t"])}"' if it.get("t") else ""
        cells.append(f'<div class="ig-ro {it.get("tone", "data")}"{tip}><div class="v">{esc(it["v"])}{unit}</div>'
                     f'<div class="l">{esc(it["l"])}{" &#9432;" if tip else ""}</div>{sub}</div>')
    style = f' style="grid-template-columns:{esc(cols)}"' if cols else ""
    return f'<div class="ig-readouts {size}"{style}>{"".join(cells)}</div>'


def readouts(items, size="", cols=None):
    st.html(readouts_html(items, size, cols))


def split_light(light):
    """'GREEN - close to real NASA runs' -> ('GREEN', 'Close to real NASA runs')."""
    word, _, text = light.partition(" - ")
    return word.strip(), (text[:1].upper() + text[1:]) if text else ""


def evidence_lamp(light, reasons=()):
    word, text = split_light(light)
    items = "".join(f"<li>{esc(r)}</li>" for r in reasons)
    st.html(f'<div class="ig-lamp {esc(word)}" role="status" aria-label="Evidence check: {esc(word)}">'
            f'<div class="bulb"></div><div><div class="word">{esc(word)}</div><div class="txt">{esc(text)}</div>'
            f'{f"<ul>{items}</ul>" if items else ""}</div></div>')


def chips(label, counts):
    """counts: {name: n}. Renders 'label  [n name] [n name]'."""
    parts = "".join(f'<span class="ig-chip"><b>{esc(n)}</b>{esc(k)}</span>' for k, n in counts.items())
    lab = f'<span class="lab">{esc(label)}</span>' if label else ""
    st.html(f'<div class="ig-chips">{lab}{parts}</div>')


def lamps_html():
    return ('<span class="ig-lamps" aria-hidden="true">'
            f'<i style="background:{GO}"></i><i style="background:{HOLD}"></i><i style="background:{STOP}"></i></span>')


LOGO_SVG = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 40" width="220" height="40">'
            f'<defs><radialGradient id="g" cx="50%" cy="50%" r="50%">'
            f'<stop offset="0" stop-color="{SPACE}"/><stop offset=".38" stop-color="{SPACE}"/>'
            f'<stop offset=".52" stop-color="#5CB3FF" stop-opacity=".55"/><stop offset=".66" stop-color="#FFD696"/>'
            f'<stop offset=".8" stop-color="{FLAME}"/><stop offset="1" stop-color="{FLAME}" stop-opacity="0"/>'
            f'</radialGradient></defs><circle cx="20" cy="20" r="17" fill="url(#g)"/>'
            f'<text x="46" y="27" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="700" '
            f'fill="{INK}" letter-spacing="1.5">IGNIS<tspan fill="{FLAME}" font-weight="600"> LAB</tspan></text></svg>')
LOGO_ICON = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40">'
             f'<defs><radialGradient id="g" cx="50%" cy="50%" r="50%">'
             f'<stop offset="0" stop-color="{SPACE}"/><stop offset=".38" stop-color="{SPACE}"/>'
             f'<stop offset=".52" stop-color="#5CB3FF" stop-opacity=".55"/><stop offset=".66" stop-color="#FFD696"/>'
             f'<stop offset=".8" stop-color="{FLAME}"/><stop offset="1" stop-color="{FLAME}" stop-opacity="0"/>'
             f'</radialGradient></defs><circle cx="20" cy="20" r="18" fill="url(#g)"/></svg>')


def logo():
    try:
        st.logo(LOGO_SVG, icon_image=LOGO_ICON, size="large")
    except Exception:          # logo is decoration; never break a page over it
        pass
