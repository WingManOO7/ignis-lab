"""Build the recorded narrator voice pack (static/voice) from the sentences the Fire lab speaks.

AI-generated narration audio (the team has permission to use AI-generated audio). Engines:
  edge - neural voices (needs `pip install edge-tts` and internet)  -> quality "neural": the page uses it by default
  sapi - Windows built-in voices (System.Speech, offline)            -> quality "basic": the page offers it in the menu
Input: rec.json files written by scripts/record_story.mjs (their narrator sentences), or --text "One sentence."
Each clip is named by the FNV-1a hash of the exact spoken sentence, the same key the page computes (clipKey in
ignis/sim_assets/fire_story.html), so a sentence whose wording or numbers change simply falls back to the browser voice.

    python scripts/build_voice.py work/harvest/rec.json [--engine auto|edge|sapi] [--voice NAME] [--fresh]
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "static" / "voice"
MANIFEST = VOICE_DIR / "manifest.json"
DEFAULTS = {"edge": ("en-US-AndrewNeural", "Andrew, neural", "Andrew", "neural"),
            "sapi": ("Microsoft Zira Desktop", "Zira, Windows voice", "Zira", "basic")}
RATE = {"edge": "-3%", "sapi": 1}        # speaking rate: edge-tts percentage, System.Speech -10..10

SAPI_PS1 = r"""
param([string]$Jobs, [string]$Voice, [int]$Rate)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate = $Rate
$items = Get-Content -Raw -Encoding UTF8 $Jobs | ConvertFrom-Json
foreach ($it in $items) { $s.SetOutputToWaveFile($it.wav); $s.Speak([string]$it.text) }
$s.SetOutputToNull(); $s.Dispose()
"""


def fnv1a(text: str) -> str:
    h = 0x811C9DC5
    for b in text.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def edge_available() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


def synth_sapi(items, voice, tmp: Path, rate: int = RATE["sapi"]):
    """Windows System.Speech -> one WAV per sentence (a single PowerShell process for all of them)."""
    ps1, jobs = tmp / "sapi.ps1", tmp / "jobs.json"
    ps1.write_text(SAPI_PS1, encoding="utf-8")
    todo = [{"wav": str(tmp / f"{k}.wav"), "text": t} for k, t in items]
    jobs.write_text(json.dumps(todo, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                    "-Jobs", str(jobs), "-Voice", voice, "-Rate", str(rate)], check=True)
    return {k: tmp / f"{k}.wav" for k, _ in items}


def synth_edge(items, voice, tmp: Path, rate: str = RATE["edge"]):
    import edge_tts

    async def run():
        for k, t in items:
            await edge_tts.Communicate(t, voice, rate=rate).save(str(tmp / f"{k}.mp3"))
    asyncio.run(run())
    return {k: tmp / f"{k}.mp3" for k, _ in items}


def to_clip(src: Path, dst: Path) -> float:
    """Trim leading/trailing silence, mono 24 kHz MP3; returns the duration in seconds."""
    trim = ("silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04,areverse,"
            "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.10,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", trim, "-ac", "1", "-ar", "24000",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(dst)], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


def sentences_from(paths, texts):
    """(key, text) pairs from rec.json logs (keys checked against our own hash) and --text arguments."""
    seen = {}
    for p in paths:
        rec = json.loads(Path(p).read_text(encoding="utf-8"))
        for e in rec.get("log", []) + rec.get("missing", []):
            if e.get("stop") or not e.get("text"):
                continue
            k = fnv1a(e["text"])
            if e.get("key") and e["key"] != k:
                sys.exit(f"hash mismatch for {e['text']!r}: page {e['key']} vs python {k}")
            seen[k] = e["text"]
    for t in texts or []:
        seen[fnv1a(t)] = t
    return seen


def build(sentences: dict, engine: str = "auto", voice: str | None = None, fresh: bool = False) -> dict:
    if engine == "auto":
        engine = "edge" if edge_available() else "sapi"
    vname, label, match, quality = DEFAULTS[engine]
    if voice:
        vname, label, match = voice, voice, voice.split("-")[-1].replace("Neural", "").split()[0]
    m = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    if fresh or m.get("engine") != engine or m.get("voice") != vname or m.get("rate") != RATE[engine]:
        m = {"clips": {}}
        if VOICE_DIR.is_dir():
            for f in VOICE_DIR.glob("*.mp3"):
                f.unlink()
    m.update({"engine": engine, "voice": vname, "rate": RATE[engine], "label": label, "match": match, "quality": quality,
              "note": "AI-generated narration of the Fire lab's narrator sentences (scripts/build_voice.py)."})
    clips = m.setdefault("clips", {})
    todo = [(k, t) for k, t in sentences.items() if k not in clips or not (VOICE_DIR / clips[k][0]).is_file()]
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    if todo:
        print(f"voice: {len(todo)} new clip(s) with {engine} ({vname})")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            raw = synth_edge(todo, vname, tmp) if engine == "edge" else synth_sapi(todo, vname, tmp)
            for k, _ in todo:
                clips[k] = [f"{k}.mp3", to_clip(raw[k], VOICE_DIR / f"{k}.mp3")]
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rec", nargs="*", help="rec.json file(s) from scripts/record_story.mjs")
    ap.add_argument("--text", action="append", help="an extra sentence (exactly as the page speaks it)")
    ap.add_argument("--engine", default="auto", choices=["auto", "edge", "sapi"])
    ap.add_argument("--voice", help="voice name (edge: e.g. en-US-AndrewNeural; sapi: e.g. Microsoft Zira Desktop)")
    ap.add_argument("--fresh", action="store_true", help="drop the existing clips first")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed on PATH")
    m = build(sentences_from(a.rec, a.text), a.engine, a.voice, a.fresh)
    print(f"voice pack: {len(m['clips'])} clips, {m['engine']} ({m['voice']}) -> {MANIFEST}")


if __name__ == "__main__":
    main()
