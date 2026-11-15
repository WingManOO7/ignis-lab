"""Make the narrated demo video of the Fire lab's "Play the story" (full HD, AI-generated narrator voice).

    python scripts/make_story_video.py [--engine auto|edge|sapi] [--voice NAME] [--fps 30] [--out DIR]

1. serves static/ on 127.0.0.1 and rebuilds static/fire_lab.html (ignis.simulation.ensure_fire_lab_page)
2. harvest: plays the story on a virtual clock (scripts/record_story.mjs --harvest) to list every narrator sentence
3. voice: makes the missing clips (scripts/build_voice.py; neural with edge-tts if installed, else the Windows voice)
   and repeats 2-3 until every sentence has a clip (the story waits for each clip, so durations shape the timing)
4. render: films the story frame by frame (record_story.mjs), then lays the clips on the soundtrack at the logged
   times, adds a quiet ambient bed and a few sound effects (spark, flash, CO2, camera moves), and muxes the MP4
   plus an .srt subtitle file. Needs Node 18+, ffmpeg and Microsoft Edge or Chrome. Rendering takes ~10 min/minute.
"""
import argparse
import http.server
import json
import shutil
import subprocess
import sys
import threading
from functools import partial
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import build_voice  # noqa: E402

SR = 48000
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
        ".mp3": "audio/mpeg", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".wasm": "application/wasm"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        return MIME.get(Path(str(path)).suffix.lower(), "application/octet-stream")

    def log_message(self, *a):
        pass


def serve_static():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT / "static")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/fire_lab.html"


def rebuild_page():
    from ignis.simulation import ensure_fire_lab_page
    ensure_fire_lab_page()


def record(url, out: Path, harvest: bool, fps: int) -> dict:
    cmd = ["node", str(ROOT / "scripts" / "record_story.mjs"), "--url", url, "--out", str(out), "--fps", str(fps)]
    if harvest:
        cmd.append("--harvest")
    subprocess.run(cmd, check=True)
    return json.loads((out / "rec.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------- soundtrack
def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def _env(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def _bandnoise(n, lo, hi, rng):
    from scipy.signal import butter, sosfilt
    sos = butter(4, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, rng.standard_normal(n)).astype(np.float32)


def sfx_sound(kind: str, rng) -> np.ndarray:
    from scipy.signal import butter, sosfilt
    if kind == "spark":          # electric arcing: crackles + a gated buzz, 1.7 s
        n = int(1.8 * SR); x = np.zeros(n, np.float32)
        for t in rng.uniform(0, 1.7, 110):
            i = int(t * SR); m = int(rng.uniform(0.002, 0.009) * SR)
            x[i:i + m] += (rng.standard_normal(m) * np.exp(-np.linspace(0, 6, m)) * rng.uniform(0.3, 1)).astype(np.float32)[: n - i]
        x = sosfilt(butter(2, [1500, 7000], btype="band", fs=SR, output="sos"), x).astype(np.float32)
        tt = np.arange(n) / SR
        gate = (rng.random(int(1.8 * 40) + 1) > 0.45).astype(np.float32).repeat(SR // 40)[:n]
        buzz = 0.25 * np.sign(np.sin(2 * np.pi * 120 * tt)) * gate
        buzz = sosfilt(butter(2, 900, fs=SR, output="sos"), buzz).astype(np.float32)
        return 0.32 * (x / (np.abs(x).max() + 1e-9) + buzz) * _env(n, 0.01, 0.25)
    if kind == "flash":          # a low whoomp
        n = int(2.2 * SR); tt = np.arange(n) / SR
        boom = np.sin(2 * np.pi * (85 * tt - 22 * tt ** 2)) * np.exp(-tt * 2.2)
        rush = sosfilt(butter(2, 700, fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-tt * 1.6)
        rush /= np.abs(rush).max() + 1e-9
        return (0.55 * boom + 0.35 * rush).astype(np.float32) * _env(n, 0.02, 0.6)
    if kind == "co2":            # extinguisher hiss
        n = int(2.8 * SR)
        h = _bandnoise(n, 2500, 11000, rng)
        return 0.2 * h / (np.abs(h).max() + 1e-9) * _env(n, 0.08, 1.2)
    if kind == "whoosh":         # camera move
        n = int(1.6 * SR); tt = np.arange(n) / SR
        w = _bandnoise(n, 250, 1400, rng)
        return (0.10 * w / (np.abs(w).max() + 1e-9) * np.sin(np.pi * tt / 1.6) ** 2).astype(np.float32)
    return np.zeros(1, np.float32)


def ambient(n, rng) -> np.ndarray:
    """A quiet, slowly breathing pad (A minor), plus soft low noise."""
    from scipy.signal import butter, sosfilt
    tt = np.arange(n) / SR; x = np.zeros(n, np.float64)
    for f, a, lfo in [(55, 0.30, 0.031), (82.41, 0.22, 0.023), (110, 0.18, 0.041), (130.81, 0.10, 0.017), (164.81, 0.08, 0.029)]:
        for det in (-0.25, 0.25):
            x += a * np.sin(2 * np.pi * (f + det) * tt + rng.uniform(0, 6)) * (0.65 + 0.35 * np.sin(2 * np.pi * lfo * tt + rng.uniform(0, 6)))
    x += 0.15 * sosfilt(butter(2, 320, fs=SR, output="sos"), rng.standard_normal(n)) * 4
    x = x / (np.abs(x).max() + 1e-9)
    return (0.075 * x).astype(np.float32)


def soundtrack(rec: dict, out_wav: Path, voice_dir: Path):
    rng = np.random.default_rng(7)
    dur, t0, dt = rec["duration"], rec["t0"], 1.0 / rec["fps"]
    n = int((dur + 0.5) * SR)
    voice = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    log = rec["log"]
    stops = sorted(e["t"] for e in log if e.get("stop"))
    cues = []
    for e in log:
        if e.get("stop") or not e.get("file"):
            continue
        start = e["t"] - t0 - dt
        clip = decode(voice_dir / e["file"])
        cut = next((s for s in stops if s - t0 - dt > start + 0.05), None)     # a newer narration stopped this clip
        if cut is not None:
            clip = clip[: max(0, int((cut - t0 - dt - start) * SR))]
        i = int(max(0, start) * SR); j = min(n, i + len(clip))
        if j > i:
            voice[i:j] += clip[: j - i]
            cues.append((start, start + len(clip) / SR, e["text"]))
    for e in rec.get("sfx", []):
        s = sfx_sound(e["k"], rng); i = int(max(0, e["t"] - t0 - dt) * SR); j = min(n, i + len(s))
        if j > i:
            fx[i:j] += s[: j - i]
    peak = np.abs(voice).max() or 1.0
    voice *= 0.82 / peak
    # duck the ambient bed under the narrator
    act = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(int(0.25 * SR), np.float32) / int(0.25 * SR), mode="same")
    bed = ambient(n, rng) * (1.0 - 0.55 * np.clip(act * 3, 0, 1)) * _env(n, 2.5, 3.5)
    mix = voice + fx + bed
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    import wave
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return cues


def write_srt(cues, path: Path):
    def ts(x):
        x = max(0.0, x); h, r = divmod(x, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"
    lines = []
    for i, (a, b, t) in enumerate(cues, 1):
        nxt = cues[i][0] if i < len(cues) else b + 1
        lines += [str(i), f"{ts(a)} --> {ts(min(b + 0.25, nxt - 0.02))}", t, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", default="auto", choices=["auto", "edge", "sapi"])
    ap.add_argument("--voice", help="voice name for the engine")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default=str(ROOT.parent / "submission" / "video"))
    ap.add_argument("--name", default="IGNIS-LAB-fire-story")
    ap.add_argument("--work", default=str(ROOT / ".video_work"))
    ap.add_argument("--harvest-only", action="store_true", help="only build the voice pack")
    a = ap.parse_args()
    for tool in ("node", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is needed on PATH")
    work, out = Path(a.work), Path(a.out); work.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    srv, url = serve_static()
    try:
        rebuild_page()
        for rnd in range(1, 6):                                   # every sentence needs its clip (they set the pace)
            rec = record(url, work / "harvest", harvest=True, fps=a.fps)
            missing = {build_voice.fnv1a(e["text"]): e["text"] for e in rec["missing"]}
            print(f"harvest {rnd}: {len([e for e in rec['log'] if not e.get('stop')])} sentences, {len(missing)} without a clip")
            if not missing:
                break
            build_voice.build(missing, a.engine, a.voice)
            rebuild_page()
        else:
            print("warning: some sentences still have no clip; their timing is estimated")
        if a.harvest_only:
            return
        rec = record(url, work / "render", harvest=False, fps=a.fps)
        if rec["missing"]:
            print(f"warning: {len(rec['missing'])} sentence(s) had no clip in the render: {[m['text'] for m in rec['missing']][:5]}")
        wav = work / "soundtrack.wav"
        cues = soundtrack(rec, wav, build_voice.VOICE_DIR)
        final = out / f"{a.name}.mp4"
        d = rec["duration"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "render" / "video.mp4"), "-i", str(wav),
                        "-vf", f"fade=t=in:st=0:d=0.8,fade=t=out:st={max(0, d - 1.2):.2f}:d=1.2",
                        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,afade=t=in:st=0:d=0.5,afade=t=out:st={max(0, d - 1.4):.2f}:d=1.4",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", str(final)], check=True)
        write_srt(cues, out / f"{a.name}.srt")
        m = json.loads(build_voice.MANIFEST.read_text(encoding="utf-8"))
        print(f"video: {final} ({d:.1f} s, {final.stat().st_size / 1e6:.1f} MB), voice {m['engine']} ({m['voice']}), "
              f"{len(cues)} narrated sentences; subtitles: {out / (a.name + '.srt')}")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
