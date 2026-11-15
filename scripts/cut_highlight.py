"""Cut a short highlight (about 30 s) from the full story video, using whole narrator sentences.

    python scripts/cut_highlight.py [--video ../submission/video/IGNIS-LAB-fire-story.mp4] [--rec .video_work/render/rec.json]

Each segment is one or more consecutive narrator sentences, found by their text in the recorder's log, so no word is
cut. Segments are joined with short fades. Run scripts/make_story_video.py first.
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# (first sentence starts with, last sentence starts with); None = the title card at the start
SEGMENTS = [
    None,
    ("The flame turns small", "The flame turns small"),
    ("Meet Nova", "Meet Nova"),
    ("Chance the flame goes out early: 9", "It should go out near"),
    ("FLEX never ran near", "Instead of guessing"),
    ("Flash ignition", "At "),
    ("Fire out.", "The smoke stays"),
    ("Real NASA data where it exists", "Real NASA data where it exists"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", default=str(ROOT.parent / "submission" / "video" / "IGNIS-LAB-fire-story.mp4"))
    ap.add_argument("--rec", default=str(ROOT / ".video_work" / "render" / "rec.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", type=float, default=3.4, help="seconds of the opening title card")
    a = ap.parse_args()
    rec = json.loads(Path(a.rec).read_text(encoding="utf-8"))
    t0, dt = rec["t0"], 1.0 / rec["fps"]
    lines = [e for e in rec["log"] if not e.get("stop") and e.get("text")]
    spans = []
    for seg in SEGMENTS:
        if seg is None:
            spans.append((0.0, a.title)); continue
        first, last = seg
        i = next(k for k, e in enumerate(lines) if e["text"].startswith(first))
        j = next(k for k in range(i, len(lines)) if lines[k]["text"].startswith(last))
        start = lines[i]["t"] - t0 - dt - 0.15
        end = lines[j]["t"] - t0 - dt + (lines[j]["dur"] or 2.0) + 0.35
        spans.append((max(0.0, start), end))
    total = sum(b - a_ for a_, b in spans)
    f, parts = 0.18, []
    for n, (s, e) in enumerate(spans):
        d = e - s
        parts.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS,fade=t=in:st=0:d={f},fade=t=out:st={d - f:.3f}:d={f}[v{n}];"
                     f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={f},afade=t=out:st={d - f:.3f}:d={f}[a{n}];")
    graph = "".join(parts) + "".join(f"[v{n}][a{n}]" for n in range(len(spans))) + f"concat=n={len(spans)}:v=1:a=1[v][a]"
    out = Path(a.out) if a.out else Path(a.video).with_name(Path(a.video).stem + "-30s.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(out)], check=True)
    print(f"highlight: {out} ({total:.1f} s, {len(spans)} segments)")


if __name__ == "__main__":
    main()
