// Film the Fire lab's "Play the story" frame by frame (Node 18+, no packages; Microsoft Edge or Chrome; ffmpeg on PATH).
//
//   node scripts/record_story.mjs --url http://127.0.0.1:8765/fire_lab.html --out <dir> [--fps 30] [--size 1920x1080]
//   node scripts/record_story.mjs --url ... --out <dir> --harvest       (no frames: only the narration log, fast)
//
// The page runs on a virtual clock (setTimeout / requestAnimationFrame / performance.now / CSS animations are all
// advanced by exactly 1/fps per frame), so the video is smooth however slowly this computer renders. In ?record=1 mode
// the page plays no audio: it logs each narrator sentence (with its recorded clip and duration) and sound-effect marks
// to window.__ignisRec; scripts/make_story_video.py turns that log into the soundtrack.
// Writes <out>/video.mp4 (no audio) and <out>/rec.json.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? (process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[i + 1] : true) : d; };
const URL0 = arg("url", "http://127.0.0.1:8765/fire_lab.html"), OUT = arg("out", "story_out"), FPS = +arg("fps", 30);
const [W, H] = String(arg("size", "1920x1080")).split("x").map(Number), HARVEST = !!arg("harvest", false);
const MAX_S = +arg("max", 420), TAIL_S = +arg("tail", 1.5), QUALITY = +arg("quality", 92);
const BROWSERS = [arg("browser"), "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].filter(Boolean);
const BROWSER = BROWSERS.find(p => p && existsSync(p));
if (!BROWSER) { console.error("No Edge/Chrome found; pass --browser <path>"); process.exit(2); }
mkdirSync(OUT, { recursive: true });

// Installed before any page script: a virtual clock driven by window.__vt.step(ms) from this recorder.
const FAKE_CLOCK = `(() => {
  if (!/[?&]record=1\\b/.test(location.search)) return;
  const realST = window.setTimeout.bind(window), ch = new MessageChannel(); let wake = null; ch.port1.onmessage = () => { const w = wake; wake = null; w && w(); };
  const flush = () => new Promise(r => { wake = r; ch.port2.postMessage(0); });            // a real macrotask: drains microtasks
  let now = 0, seq = 0; const timers = new Map(); let rafs = [];
  const t0 = Date.now(); performance.now = () => now; Date.now = () => t0 + now;
  window.setTimeout = (fn, ms, ...a) => { const id = ++seq; timers.set(id, { at: now + Math.max(0, +ms || 0), fn, a, every: 0 }); return id; };
  window.setInterval = (fn, ms, ...a) => { const id = ++seq, e = Math.max(1, +ms || 0); timers.set(id, { at: now + e, fn, a, every: e }); return id; };
  window.clearTimeout = window.clearInterval = id => { timers.delete(id); };
  window.requestAnimationFrame = fn => { const id = ++seq; rafs.push([id, fn]); return id; };
  window.cancelAnimationFrame = id => { rafs = rafs.filter(r => r[0] !== id); };
  const call = (fn, a) => { try { typeof fn === "function" ? fn(...a) : (0, eval)(String(fn)); } catch (e) { console.error(e); } };
  window.__vt = {
    now: () => now,
    async step(ms) {
      const to = now + ms;
      for (let guard = 0; guard < 20000; guard++) {                                          // timers due in this frame, in order
        let best = null; for (const [id, t] of timers) if (t.at <= to && (!best || t.at < best[1].at || (t.at === best[1].at && id < best[0]))) best = [id, t];
        if (!best) break;
        const [id, t] = best; now = Math.max(now, t.at);
        if (t.every) t.at = now + t.every; else timers.delete(id);
        call(t.fn, t.a); await flush();
      }
      now = to;
      for (const a of document.getAnimations()) {                                            // CSS transitions/animations on the same clock
        try { if (!a.__vt) { a.__vt = 1; a.pause(); a.currentTime = 0; } else a.currentTime = (+a.currentTime || 0) + ms; } catch (e) {}
      }
      const list = rafs; rafs = []; for (const [, fn] of list) call(fn, [now]);               // one animation frame
      await flush();
      return now;
    },
  };
})();`;

const prof = mkdtempSync(join(tmpdir(), "ignis-rec-"));
const port = 9400 + Math.floor(Math.random() * 400);
const br = spawn(BROWSER, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, `--window-size=${W},${H}`,
  "--hide-scrollbars", "--mute-audio", "--no-first-run", "--no-default-browser-check", "--use-angle=d3d11", "--enable-gpu",
  "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader", "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
  "about:blank"], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let wsUrl = null;
for (let i = 0; i < 100 && !wsUrl; i++) { try { const j = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const pg = j.find(t => t.type === "page"); if (pg) wsUrl = pg.webSocketDebuggerUrl; } catch {} if (!wsUrl) await sleep(200); }
if (!wsUrl) { console.error("browser did not start"); br.kill(); process.exit(3); }
const ws = new WebSocket(wsUrl); await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let mid = 0; const pend = new Map(), logs = [];
ws.onmessage = m => { const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) { const { res, rej } = pend.get(d.id); pend.delete(d.id); d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result); }
  else if (d.method === "Runtime.consoleAPICalled" && /error|warn/.test(d.params.type)) logs.push(d.params.type + ": " + d.params.args.map(a => a.value ?? a.description ?? "").join(" "));
  else if (d.method === "Runtime.exceptionThrown") logs.push("exception: " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text)); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++mid; pend.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expression, awaitPromise = false) => { const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };

let ff = null, ffDone = null;
const cleanup = () => { try { ws.close(); } catch {} try { br.kill(); } catch {} try { rmSync(prof, { recursive: true, force: true }); } catch {} };
try {
  await send("Page.enable"); await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send("Page.addScriptToEvaluateOnNewDocument", { source: FAKE_CLOCK });
  const url = URL0 + (URL0.includes("?") ? "&" : "?") + "record=1&story=1&voice=1&place=earth";
  await send("Page.navigate", { url });
  // boot: three.js loads over the network (real time); keep the virtual clock ticking slowly until the story starts
  let started = false;
  for (let i = 0; i < 600 && !started; i++) {
    await sleep(100);
    try { if (await ev("!!window.__vt")) { await ev("__vt.step(20)", true); started = !!(await ev("!!(window.__ignis && window.__ignis.STORY.on)")); } } catch {}
  }
  if (!started) throw new Error("the story did not start (is the page served, with three.js?) " + logs.slice(-5).join(" | "));
  if (!HARVEST) {
    ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
      "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", join(OUT, "video.mp4")], { stdio: ["pipe", "inherit", "inherit"] });
    ffDone = new Promise(r => ff.on("close", r));
  }
  const dt = HARVEST ? 50 : 1000 / FPS; let frames = 0, endAt = null, tStart = await ev("__vt.now()"), wall = Date.now();
  for (;;) {
    const t = await ev(`__vt.step(${dt})`, true);
    const vs = (t - tStart) / 1000;
    if (!HARVEST) {
      const shot = await send("Page.captureScreenshot", { format: "jpeg", quality: QUALITY, optimizeForSpeed: true, captureBeyondViewport: false });
      const buf = Buffer.from(shot.data, "base64");
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    }
    frames++;
    if (endAt === null && !(await ev("window.__ignis.STORY.on"))) endAt = vs;
    if (endAt !== null && vs >= endAt + TAIL_S) break;
    if (vs > MAX_S) { console.warn("max length reached"); break; }
    if (frames % (HARVEST ? 200 : 150) === 0) {
      const pl = await ev("window.__ignis.STATE.place");
      console.log(`${HARVEST ? "harvest" : "frame"} ${frames}  t=${vs.toFixed(1)} s  place=${pl}  ${((Date.now() - wall) / frames).toFixed(0)} ms/frame`);
    }
  }
  const rec = await ev("JSON.stringify(window.__ignisRec)");
  const data = JSON.parse(rec); data.t0 = tStart / 1000; data.duration = frames * dt / 1000; data.fps = FPS; data.frames = frames;
  data.storyEnd = endAt; data.size = [W, H]; data.console = logs.slice(0, 50);
  writeFileSync(join(OUT, "rec.json"), JSON.stringify(data, null, 1));
  if (ff) { ff.stdin.end(); await ffDone; }
  console.log(`done: ${frames} frames, ${data.duration.toFixed(1)} s, ${data.log.filter(x => !x.stop).length} sentences, ${data.missing.length} without a clip` +
              (logs.length ? `, ${logs.length} console warnings/errors (see rec.json)` : ""));
} catch (e) {
  console.error("recording failed:", e.message);
  if (ff) { try { ff.stdin.end(); } catch {} }
  process.exitCode = 1;
} finally { cleanup(); }
