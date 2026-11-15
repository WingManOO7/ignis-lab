"""The narrator's recorded voice pack: clip keys (JS == Python), what the voice says, and how the page gets the pack."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_voice  # noqa: E402

from ignis import simulation as sim  # noqa: E402

PAGE = (ROOT / "ignis" / "sim_assets" / "fire_story.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def models():
    from ignis.data import load_models
    return load_models()


def _js_function(src, head):
    """The source of a top-level `const name = ...;` / `function name(...) {...}` block from the page."""
    i = src.index(head)
    depth, j, started = 0, i, False
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1; started = True
        elif c == "}":
            depth -= 1
            if started and depth == 0:
                return src[i:j + 1] + (";" if head.startswith("const") else "")
        j += 1
    raise ValueError(head)


def _node(code):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    r = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_fnv1a_known_vectors():
    assert build_voice.fnv1a("") == "811c9dc5"
    assert build_voice.fnv1a("a") == "e40c292c"


def test_clip_keys_match_the_page():
    texts = ["Fire out.", "The model gives K equals 0.50 square millimetres per second.", "d₀ ≥ 30% · O₂ – ±"]
    js = _js_function(PAGE, "const clipKey = s =>")
    out = _node(js + f"\nconsole.log(JSON.stringify({json.dumps(texts, ensure_ascii=False)}.map(clipKey)));")
    assert out == [build_voice.fnv1a(t) for t in texts]


def test_spoken_text():
    js = _js_function(PAGE, "function speakable(t)")
    cases = {
        "Flooding with CO2.": "Flooding with carbon dioxide.",                      # not "C-oxygen"
        "CO and CO2 exceeded crew limits.": "carbon monoxide and carbon dioxide exceeded crew limits.",
        "Candles lasted up to 45 min on Mir. (NASA)": "Candles lasted up to 45 minutes on Mir, according to NASA.",
        "FLEX discovered this (Nayagam et al., 2012).": "FLEX discovered this, according to Nayagam and colleagues in 2012.",
        "The model gives K = 0.50 mm²/s.": "The model gives K equals 0.50 square millimetres per second.",
        "Every nearby NASA run broke apart (Disruption).": "Every nearby NASA run broke apart (Disruption).",
        "34% O2 at 0.56 atm": "34 percent oxygen at 0.56 atmospheres",
    }
    out = _node(js + f"\nconsole.log(JSON.stringify({json.dumps(list(cases), ensure_ascii=False)}.map(speakable)));")
    assert out == list(cases.values())


def test_build_html_inlines_the_voice_pack(models):
    payload = sim.web_model_payload(models)
    html = sim.build_html({"scenario": "x"}, payload, voice=None)
    assert "window.IGNIS_VOICE = null;" in html and sim.VOICE_PLACEHOLDER not in html
    pack = {"base": "voice/", "engine": "sapi", "label": "Zira", "match": "Zira", "quality": "basic", "clips": {"0000abcd": ["0000abcd.mp3", 1.5]}}
    html = sim.build_html({"scenario": "x"}, payload, voice=pack)
    m = re.search(r"window\.IGNIS_VOICE = (\{.*?\});</script>", html)
    assert m and json.loads(m.group(1))["clips"] == pack["clips"]


def test_voice_pack_skips_missing_files(tmp_path, monkeypatch):
    (tmp_path / "aaaa0001.mp3").write_bytes(b"ID3")
    (tmp_path / "manifest.json").write_text(json.dumps({"engine": "sapi", "quality": "basic",
        "clips": {"aaaa0001": ["aaaa0001.mp3", 1.2], "bbbb0002": ["bbbb0002.mp3", 2.0]}}), encoding="utf-8")
    monkeypatch.setattr(sim, "VOICE_DIR", tmp_path)
    monkeypatch.setattr(sim, "VOICE_MANIFEST", tmp_path / "manifest.json")
    vp = sim.voice_pack("voice/")
    assert vp["base"] == "voice/" and list(vp["clips"]) == ["aaaa0001"]
    assert sim.voice_pack(None) is None
    (tmp_path / "manifest.json").write_text("{broken", encoding="utf-8")
    assert sim.voice_pack("voice/") is None                                         # never breaks the page


def test_committed_pack_is_consistent():
    """Every clip in static/voice/manifest.json exists and is named by the hash of its sentence."""
    if not build_voice.MANIFEST.is_file():
        pytest.skip("no voice pack")
    m = json.loads(build_voice.MANIFEST.read_text(encoding="utf-8"))
    for key, (file, dur) in m["clips"].items():
        assert file == f"{key}.mp3" and (build_voice.VOICE_DIR / file).is_file() and 0.2 < dur < 20
