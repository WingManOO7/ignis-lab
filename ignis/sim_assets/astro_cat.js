/* IGNIS LAB mascot "Nova": an original chibi astronaut cat for the three.js fire lab (three.js 0.160.0).
   DECORATION ONLY: it shows no data, numbers or claims. Hover label: "Nova, our mascot (just for fun)".
   Classic script (no import / export), safe to inline in a normal script tag. Defines:
     window.IgnisCat = { create(THREE, opts) }
       opts: { scene, camera, name: "Nova", scenes?: { cabin, wiring, chamber }, places?: {...overrides}, seed?, focus?: () => Vector3|null }
     create() returns { group, update(dt, t), react(event), setPlace(place, scene?), onPointer(raycaster) -> bool,
                        setVisible(bool), dispose(), hitTest(raycaster) -> bool, label, play(name), setFocus(v3|null) }
   react() events: enter spark flash fan_on fan_off co2 reset green amber red click
   Places: earth / orbit = hidden; cabin = floats near the viewer (lower right of the view, follows the camera);
           chamber = peeks in from the lower right edge (camera-anchored, unit-agnostic, works in the mm scene);
           wiring = floats in the world beside the fan, clear of the fire.
   Cost: about 4.9k triangles (~70 small meshes), unlit MeshMatcapMaterial (one procedural matcap) + two tiny shaders, no lights, no shadows.
   Bloom: everything stays below the place's bloom threshold (tone per place) except the tiny backpack status light.
   Transparent parts (blush, helmet glass, hearts, bubbles) use renderOrder 1-3 so they draw after the scene's
   own transparent effects (renderOrder 0). */
(function () {
  "use strict";

  function create(THREE, opts) {
    opts = opts || {};
    const camera = opts.camera;
    const NAME = String(opts.name || "Nova");
    const LABEL = NAME + ", our mascot (just for fun)";

    /* ------------------------------------------------------------------ helpers */
    let seed = (opts.seed >>> 0) || 0;
    const rnd = seed ? () => { seed = (seed + 0x6D2B79F5) >>> 0; let t = seed; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; } : Math.random;
    const rand = (a, b) => a + rnd() * (b - a);
    const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
    const lerp = (a, b, t) => a + (b - a) * t;
    const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
    const env = (u, a, b, c, d) => sstep(a, b, u) * (1 - sstep(c, d, u));     // rise a..b, fall c..d
    const bell = (u, c, w) => Math.exp(-((u - c) / w) * ((u - c) / w));
    const easeIO = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const easeOutBack = t => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
    const wrapPi = a => { a = (a + Math.PI) % (2 * Math.PI); if (a < 0) a += 2 * Math.PI; return a - Math.PI; };
    const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
    const GEOS = [], MATS = [], TEX = [];
    const geo = g => { GEOS.push(g); return g; };

    function canvasTex(w, h, draw) {
      const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TEX.push(t); return t;
    }

    /* ------------------------------------------------------------------ textures (procedural, tiny) */
    // soft "vinyl toy" matcap: warm key light top-left, cool rim bottom-right; peak kept low so nothing blooms
    const MATCAP = canvasTex(256, 256, (g, S) => {
      g.fillStyle = "#5d6274"; g.fillRect(0, 0, S, S);
      let gr = g.createRadialGradient(S * 0.37, S * 0.31, S * 0.02, S * 0.47, S * 0.47, S * 0.6);
      gr.addColorStop(0, "#f3efe9"); gr.addColorStop(0.32, "#e2ddd8"); gr.addColorStop(0.62, "#bcb8bc"); gr.addColorStop(0.86, "#8f8f9e"); gr.addColorStop(1, "#6c7088");
      g.fillStyle = gr; g.beginPath(); g.arc(S / 2, S / 2, S / 2, 0, 7); g.fill();
      const b = document.createElement("canvas"); b.width = b.height = S; const h = b.getContext("2d");
      gr = h.createRadialGradient(S / 2, S / 2, S * 0.36, S / 2, S / 2, S * 0.5);
      gr.addColorStop(0, "rgba(0,0,0,0)"); gr.addColorStop(0.75, "rgba(90,120,170,0.25)"); gr.addColorStop(1, "rgba(150,185,235,0.6)");
      h.fillStyle = gr; h.fillRect(0, 0, S, S);
      h.globalCompositeOperation = "destination-in";
      const lg = h.createLinearGradient(S * 0.2, S * 0.2, S * 0.95, S * 0.95); lg.addColorStop(0, "rgba(0,0,0,0.15)"); lg.addColorStop(1, "rgba(0,0,0,1)");
      h.fillStyle = lg; h.fillRect(0, 0, S, S);
      g.globalCompositeOperation = "lighter"; g.drawImage(b, 0, 0);
      gr = g.createRadialGradient(S * 0.5, S * 0.98, 0, S * 0.5, S * 0.98, S * 0.45);     // warm bounce from below
      gr.addColorStop(0, "rgba(120,70,40,0.25)"); gr.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = gr; g.fillRect(0, 0, S, S);
      gr = g.createRadialGradient(S * 0.33, S * 0.26, 0, S * 0.33, S * 0.26, S * 0.11);   // soft specular
      gr.addColorStop(0, "rgba(255,255,255,0.22)"); gr.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = gr; g.fillRect(0, 0, S, S);
    });
    // tapered stroke helper for tabby stripes
    function stroke(g, x1, y1, x2, y2, w1, w2) {
      const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
      g.beginPath(); g.moveTo(x1 + nx * w1, y1 + ny * w1); g.lineTo(x2 + nx * w2, y2 + ny * w2);
      g.arc(x2, y2, w2, Math.atan2(ny, nx), Math.atan2(-ny, -nx)); g.lineTo(x1 - nx * w1, y1 - ny * w1);
      g.arc(x1, y1, w1, Math.atan2(-ny, -nx), Math.atan2(ny, nx)); g.closePath(); g.fill();
    }
    // head fur (equirectangular): orange tabby, soft stripes, cream muzzle and chin. Face centre at u = 0.25.
    const HEAD_TEX = canvasTex(512, 256, (g, W, H) => {
      let gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, "#f39445"); gr.addColorStop(0.55, "#f7a457"); gr.addColorStop(1, "#f9b46c");
      g.fillStyle = gr; g.fillRect(0, 0, W, H);
      const fx = W * 0.25;
      g.save(); g.filter = "blur(2px)"; g.fillStyle = "rgba(190,80,26,0.92)";
      stroke(g, fx, 14, fx, 84, 7.5, 3); stroke(g, fx - 21, 20, fx - 15, 74, 6.5, 2.5); stroke(g, fx + 21, 20, fx + 15, 74, 6.5, 2.5);   // forehead
      for (const s of [-1, 1]) {                                                                                                        // cheeks
        stroke(g, fx + s * 112, 116, fx + s * 80, 122, 7, 2); stroke(g, fx + s * 114, 134, fx + s * 84, 137, 6, 2);
      }
      for (let k = -2; k <= 2; k++) stroke(g, W * 0.75 + k * 30, 6, W * 0.75 + k * 34, 110 - Math.abs(k) * 12, 9, 3);                  // back of head
      g.restore();
      g.save(); g.filter = "blur(5px)";
      gr = g.createRadialGradient(fx, H * 0.74, 4, fx, H * 0.74, 64); gr.addColorStop(0, "rgba(255,244,228,1)"); gr.addColorStop(0.6, "rgba(255,240,222,0.92)"); gr.addColorStop(1, "rgba(255,238,220,0)");
      g.fillStyle = gr; g.beginPath(); g.ellipse(fx, H * 0.74, 64, 36, 0, 0, 7); g.fill();
      g.restore();
    });
    const BADGE_TEX = canvasTex(128, 128, (g, S) => {
      g.fillStyle = "#ff7a1a"; g.beginPath(); g.arc(S / 2, S / 2, S / 2, 0, 7); g.fill();
      g.fillStyle = "#1c2742"; g.beginPath(); g.arc(S / 2, S / 2, S * 0.42, 0, 7); g.fill();
      g.fillStyle = "#ff8a2a"; g.beginPath(); g.moveTo(64, 26); g.bezierCurveTo(86, 52, 92, 70, 84, 86); g.bezierCurveTo(78, 100, 50, 100, 44, 86);
      g.bezierCurveTo(38, 72, 46, 56, 64, 26); g.fill();
      g.fillStyle = "#ffd27a"; g.beginPath(); g.moveTo(64, 54); g.bezierCurveTo(76, 68, 78, 80, 72, 88); g.bezierCurveTo(66, 94, 56, 92, 54, 84);
      g.bezierCurveTo(52, 76, 56, 68, 64, 54); g.fill();
    });
    const BLUSH_TEX = canvasTex(64, 64, (g, S) => {
      const gr = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
      gr.addColorStop(0, "rgba(255,92,140,1)"); gr.addColorStop(0.5, "rgba(255,105,150,0.6)"); gr.addColorStop(1, "rgba(255,120,160,0)");
      g.fillStyle = gr; g.fillRect(0, 0, S, S);
    });
    function heartPath(g, cx, cy, s) {
      g.beginPath(); g.moveTo(cx, cy + s * 0.9);
      g.bezierCurveTo(cx - s * 1.25, cy + s * 0.05, cx - s * 0.95, cy - s * 0.95, cx, cy - s * 0.38);
      g.bezierCurveTo(cx + s * 0.95, cy - s * 0.95, cx + s * 1.25, cy + s * 0.05, cx, cy + s * 0.9); g.closePath();
    }
    const HEART_TEX = canvasTex(64, 64, (g, S) => {
      g.fillStyle = "#ff5f8a"; heartPath(g, 32, 34, 26); g.fill();
      g.lineWidth = 3; g.strokeStyle = "rgba(160,30,70,0.5)"; g.stroke();
      g.fillStyle = "rgba(255,255,255,0.8)"; g.beginPath(); g.ellipse(22, 22, 6, 4, -0.6, 0, 7); g.fill();
    });
    function bubbleTex(glyph, color) {
      return canvasTex(128, 128, (g, S) => {
        g.fillStyle = "rgba(20,26,40,0.35)"; g.beginPath(); g.arc(66, 58, 46, 0, 7); g.fill();
        g.fillStyle = "#f0f0ee"; g.beginPath(); g.arc(64, 56, 46, 0, 7); g.fill();
        g.beginPath(); g.moveTo(38, 88); g.lineTo(26, 116); g.lineTo(58, 98); g.fill();
        g.fillStyle = color; g.font = "900 68px 'Segoe UI', Arial, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText(glyph, 64, 60);
      });
    }
    const BANG_TEX = bubbleTex("!", "#ff7a1a"), ASK_TEX = bubbleTex("?", "#3f8fe0");

    /* ------------------------------------------------------------------ materials (tone-scaled per place) */
    function track(m, kind) { MATS.push({ m, base: m.color.clone(), kind }); return m; }
    const mc = (hex, map) => track(new THREE.MeshMatcapMaterial({ matcap: MATCAP, color: new THREE.Color(hex), map: map || null }), "mc");
    const M = {
      fur: mc(0xffffff, HEAD_TEX), furO: mc(0xf59a4c), furD: mc(0xcf6a2e), cream: mc(0xfff0de), pink: mc(0xf7a3b5),
      nose: mc(0xf2879c), dark: mc(0x2e1d16), mouthIn: mc(0x8a3446), whisk: mc(0xfff7ec),
      suit: mc(0xe3e7ee), suit2: mc(0xc9d0db), acc: mc(0xff7a1a), badge: mc(0xffffff, BADGE_TEX),
    };
    const blushMat = track(new THREE.MeshBasicMaterial({ map: BLUSH_TEX, transparent: true, depthWrite: false, opacity: 0.6, color: 0xffffff }), "basic");
    const ledMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.3, 1.0, 0.6) }); MATS.push({ m: ledMat, base: ledMat.color.clone(), kind: "led" });
    const OUT = "\n#include <tonemapping_fragment>\n#include <colorspace_fragment>\n";
    const eyeMat = new THREE.ShaderMaterial({
      uniforms: { uPupil: { value: 0.6 }, uLook: { value: new THREE.Vector2() }, uTone: { value: 1 }, uOpen: { value: 1 }, uLash: { value: 1 },
        uIris: { value: new THREE.Color(0x4fd0b4) }, uIris2: { value: new THREE.Color(0x1f6890) }, uDark: { value: new THREE.Color(0x120d16) } },
      vertexShader: "varying vec3 vP; varying vec3 vN; varying vec3 vV;\n" +
        "void main(){ vP = position; vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = -mv.xyz; gl_Position = projectionMatrix * mv; }",
      fragmentShader: "uniform float uPupil, uTone, uOpen, uLash; uniform vec2 uLook; uniform vec3 uIris, uIris2, uDark; varying vec3 vP; varying vec3 vN; varying vec3 vV;\n" +
        "void main(){\n" +
        "  vec2 p = vP.xy; float rr = length(p);\n" +
        "  float lid = mix(-0.62 + 0.3 * (1.0 - p.x * p.x), 1.08, uOpen);\n" +     // upper eyelid edge; closes into a gentle content arch
        "  float below = lid - p.y;\n" +
        "  if (below < 0.0 || below > mix(0.085 * step(0.05, uLash), 3.0, smoothstep(0.0, 0.45, uOpen))) discard;\n" +
        "  vec2 q = p - uLook; float r = length(q * vec2(1.0, 0.9));\n" +
        "  vec3 col = mix(uIris, uIris2, smoothstep(-0.75, 0.5, q.y));\n" +
        "  col = mix(col, uDark, smoothstep(0.78, 0.92, r));\n" +
        "  col = mix(uDark, col, smoothstep(uPupil - 0.035, uPupil + 0.035, r));\n" +
        "  col = mix(col, uDark, smoothstep(0.84, 0.97, rr));\n" +
        "  col *= 1.0 - 0.35 * smoothstep(0.25, 0.95, p.y);\n" +
        "  float ndv = clamp(dot(normalize(vN), normalize(vV)), 0.0, 1.0);\n" +
        "  col += vec3(0.04, 0.06, 0.09) * pow(1.0 - ndv, 2.0);\n" +
        "  float h1 = 1.0 - smoothstep(0.17, 0.215, length((p - vec2(-0.30, 0.34)) * vec2(1.0, 0.92)));\n" +
        "  float h2 = 1.0 - smoothstep(0.075, 0.105, length(p - vec2(0.31, -0.30)));\n" +
        "  col = mix(col, vec3(0.78), max(h1, h2 * 0.95));\n" +
        "  float lash = (1.0 - smoothstep(0.03, 0.13, below)) * (1.0 - step(0.999, uOpen)) * uLash;\n" +   // dark lid line
        "  col = mix(col, uDark * 1.8, max(lash, 1.0 - smoothstep(0.1, 0.3, uOpen)));\n" +
        "  gl_FragColor = vec4(col * uTone, 1.0);" + OUT + "}",
    });
    const GLASS_VS = "varying vec3 vN; varying vec3 vV;\n" +
      "void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = -mv.xyz; gl_Position = projectionMatrix * mv; }";
    const GLASS_FS = "uniform float uTone, uOpacity, uHi; uniform vec3 uTint, uEdge; varying vec3 vN; varying vec3 vV;\n" +
      "void main(){\n" +
      "  vec3 n = normalize(vN), v = normalize(vV); float ndv = clamp(dot(n, v), 0.0, 1.0);\n" +
      "  float f = pow(1.0 - ndv, 2.6); vec3 col = uTint; float a = 0.035 + 0.42 * f;\n" +
      "  float e = smoothstep(0.80, 0.97, 1.0 - ndv); col = mix(col, uEdge, e * 0.7); a = max(a, e * 0.55);\n" +
      "  vec2 q = n.xy; float r = length(q); float ang = atan(q.y, q.x);\n" +
      "  float band = smoothstep(0.70, 0.75, r) * (1.0 - smoothstep(0.83, 0.88, r)) * smoothstep(1.95, 2.15, ang) * (1.0 - smoothstep(2.6, 2.85, ang));\n" +
      "  float d2 = 1.0 - smoothstep(0.045, 0.07, length(q - vec2(-0.22, 0.80)));\n" +
      "  float d3 = 1.0 - smoothstep(0.05, 0.08, length(q - vec2(0.6, -0.48)));\n" +
      "  float hl = max(band * 0.85, max(d2 * 0.85, d3 * 0.5)) * step(0.0, n.z) * uHi;\n" +
      "  col = mix(col, vec3(0.86), hl); a = max(a, hl * 0.75);\n" +
      "  gl_FragColor = vec4(col * uTone, a * uOpacity);" + OUT + "}";
    function glassMat(tint, edge, hi) {
      return new THREE.ShaderMaterial({ uniforms: { uTone: { value: 1 }, uOpacity: { value: 1 }, uHi: { value: hi },
        uTint: { value: new THREE.Color(tint) }, uEdge: { value: new THREE.Color(edge) } },
        vertexShader: GLASS_VS, fragmentShader: GLASS_FS, transparent: true, depthWrite: false });
    }
    const helmetMat = glassMat(0xcfe4ff, 0x6f86a8, 1), ballMat = glassMat(0xffd9f2, 0x9fd8ff, 0.8);
    const spriteMat = tex => track(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, color: 0xffffff }), "sprite");

    /* ------------------------------------------------------------------ geometry (shared, low poly) */
    const G = {
      sph: geo(new THREE.SphereGeometry(1, 18, 12)), sphB: geo(new THREE.SphereGeometry(1, 14, 9)), sphM: geo(new THREE.SphereGeometry(1, 9, 6)), sphS: geo(new THREE.SphereGeometry(1, 7, 5)),
      half: geo(new THREE.SphereGeometry(1, 12, 8, 0, Math.PI, 0, Math.PI)), halfS: geo(new THREE.SphereGeometry(1, 8, 5, 0, Math.PI, 0, Math.PI)), disc: geo(new THREE.CircleGeometry(1, 12)),
      discS: geo(new THREE.CircleGeometry(1, 8)),
    };
    const mesh = (g, m, x, y, z, sx, sy, sz) => { const o = new THREE.Mesh(g, m); o.position.set(x || 0, y || 0, z || 0); o.scale.set(sx || 1, sy == null ? sx || 1 : sy, sz == null ? sx || 1 : sz); return o; };
    const basis = new THREE.Matrix4(), bx = V3(), by = V3(), bz = V3();
    function orient(obj, n, up) {    // obj +Z along n, +Y as close to `up` as possible
      bz.copy(n).normalize(); bx.crossVectors(up || V3(0, 1, 0), bz); if (bx.lengthSq() < 1e-6) bx.set(1, 0, 0); bx.normalize(); by.crossVectors(bz, bx);
      basis.makeBasis(bx, by, bz); obj.quaternion.setFromRotationMatrix(basis); return obj;
    }

    /* ------------------------------------------------------------------ rig: root > pop > drift > spin > model */
    const root = new THREE.Group(); root.name = "IgnisCat:" + NAME; root.visible = false;
    root.userData.tip = LABEL; root.userData.isIgnisCat = true;
    const pop = new THREE.Group(), drift = new THREE.Group(), spin = new THREE.Group(), model = new THREE.Group();
    root.add(pop); pop.add(drift); drift.add(spin); spin.add(model);
    const CAT_H = 4.42, CENTER_Y = 0.29;          // model units: head radius ~1; visual centre sits at the root origin
    model.position.y = -CENTER_Y;

    // ---- head (pivot at the neck; turns inside the helmet)
    const HEAD_C = V3(0, 0.86, 0), HA = 1.1, HB = 0.94, HC = 1.0;
    const head = new THREE.Group(); head.position.set(0, 0.12, 0); model.add(head);
    const face = new THREE.Group(); face.position.copy(HEAD_C); head.add(face);
    const skull = mesh(G.sph, M.fur, 0, 0, 0, HA, HB, HC); face.add(skull);
    function onHead(yaw, pitch, lift) {
      const d = V3(Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
      const k = 1 / Math.sqrt((d.x / HA) ** 2 + (d.y / HB) ** 2 + (d.z / HC) ** 2), p = d.multiplyScalar(k);
      const n = V3(p.x / (HA * HA), p.y / (HB * HB), p.z / (HC * HC)).normalize(); p.addScaledVector(n, lift || 0); return { p, n };
    }
    const place = (obj, yaw, pitch, lift, up) => { const s = onHead(yaw, pitch, lift); obj.position.copy(s.p); orient(obj, s.n, up); face.add(obj); return obj; };
    // eyes: big, glossy, low on the face (baby proportions)
    const EYE_S = V3(0.255, 0.305, 0.085), eyes = [], arches = [], chevs = [];
    for (const s of [-1, 1]) {
      const holder = new THREE.Group(); place(holder, s * 0.42, -0.11, -0.035);
      const e = mesh(G.half, eyeMat, 0, 0, 0, EYE_S.x, EYE_S.y, EYE_S.z); holder.add(e); eyes.push(e);
      const ar = new THREE.Mesh(geo(new THREE.TorusGeometry(0.17, 0.034, 4, 9, Math.PI)), M.dark); ar.position.set(0, -0.06, 0.07); holder.add(ar); arches.push(ar);
      const ch = new THREE.Group(); ch.position.z = 0.07; holder.add(ch); chevs.push(ch);
      for (const k of [1, -1]) { const b = new THREE.Mesh(geo(new THREE.BoxGeometry(0.21, 0.048, 0.03)), M.dark); b.position.set(0, 0.048 * k, 0); b.rotation.z = k * s * 0.47; ch.add(b); }
    }
    // nose, muzzle, mouth
    place(mesh(G.sphS, M.nose, 0, 0, 0, 0.1, 0.068, 0.07), 0, -0.31, 0.025);
    for (const s of [-1, 1]) place(mesh(G.sphS, M.cream, 0, 0, 0, 0.145, 0.105, 0.075), s * 0.1, -0.41, -0.025);
    const mouth = new THREE.Group(); place(mouth, 0, -0.455, 0.035);
    const omega = new THREE.Group(); mouth.add(omega);
    for (const s of [-1, 1]) { const a = new THREE.Mesh(geo(new THREE.TorusGeometry(0.05, 0.014, 3, 7, Math.PI)), M.dark); a.rotation.z = Math.PI; a.position.set(s * 0.05, 0.012, 0); omega.add(a); }
    omega.add(mesh(G.sphS, M.dark, 0, 0.05, 0, 0.012, 0.04, 0.01));
    const mouthOpen = new THREE.Group(); mouthOpen.position.set(0, -0.02, 0.005); mouth.add(mouthOpen);
    mouthOpen.add(mesh(G.halfS, M.mouthIn, 0, 0, 0, 0.1, 0.1, 0.03), mesh(G.sphS, M.pink, 0, -0.045, 0.012, 0.055, 0.035, 0.02));
    const blushes = [];
    for (const s of [-1, 1]) { const b = new THREE.Mesh(G.disc, blushMat); b.scale.set(0.2, 0.12, 1); b.renderOrder = 1; place(b, s * 0.68, -0.47, 0.016); blushes.push(b); }
    // whiskers (pivot at the base so they can ruffle)
    const whiskers = [], WG = geo(new THREE.CylinderGeometry(0.006, 0.015, 0.46, 4, 1, true).translate(0, 0.23, 0));
    for (const s of [-1, 1]) for (let k = 0; k < 3; k++) {
      const base = onHead(s * 0.3, -0.45 + k * 0.03, -0.02).p, dir = V3(s, 0.16 - k * 0.17, 0.22 - k * 0.04).normalize();
      const pv = new THREE.Group(); pv.position.copy(base); pv.quaternion.setFromUnitVectors(V3(0, 1, 0), dir); pv.add(new THREE.Mesh(WG, M.whisk)); face.add(pv);
      whiskers.push({ pv, q0: pv.quaternion.clone(), k: k + (s > 0 ? 3 : 0) });
    }
    // ears: rounded lathe cones, pink inside; pivot at the base
    const earOut = geo(new THREE.LatheGeometry([[0.35, 0], [0.33, 0.14], [0.26, 0.33], [0.15, 0.5], [0.06, 0.6], [0, 0.63]].map(p => new THREE.Vector2(p[0], p[1])), 7));
    const earIn = geo(new THREE.LatheGeometry([[0.23, 0], [0.2, 0.15], [0.13, 0.33], [0.05, 0.45], [0, 0.48]].map(p => new THREE.Vector2(p[0], p[1])), 6));
    const ears = [];
    for (const s of [-1, 1]) {
      const d = V3(s * Math.sin(0.62), Math.cos(0.62), 0.12).normalize(), b = onHead(Math.atan2(d.x, d.z), Math.asin(d.y), -0.1).p;
      const pv = new THREE.Group(); pv.position.copy(b); face.add(pv);
      by.copy(d); bx.crossVectors(by, V3(0, 0, 1)).normalize(); bz.crossVectors(bx, by); basis.makeBasis(bx, by, bz); pv.quaternion.setFromRotationMatrix(basis);
      const q0 = pv.quaternion.clone(), tw = new THREE.Group(); pv.add(tw);
      tw.add(mesh(earOut, M.furO, 0, 0, 0, 1, 1, 0.55), mesh(earIn, M.pink, 0, 0.03, 0.135, 1, 1, 0.3));
      ears.push({ pv, tw, q0, s, twitch: 0, tv: 0 });
    }
    // cheek and crown tufts (they poof up when startled)
    const tufts = [], TG = geo(new THREE.ConeGeometry(0.1, 0.24, 5, 1, true).translate(0, 0.12, 0));
    for (const s of [-1, 1]) for (const [pt, dy] of [[-0.18, -0.25], [-0.4, -0.55]]) {
      const b = onHead(s * 1.32, pt, -0.06).p, t = new THREE.Mesh(TG, M.furO); t.position.copy(b);
      t.quaternion.setFromUnitVectors(V3(0, 1, 0), V3(s, dy, -0.15).normalize()); face.add(t); tufts.push(t);
    }
    for (const [x, z, a] of [[-0.08, 0.15, 0.25], [0.07, 0.2, -0.2]]) {
      const t = new THREE.Mesh(TG, M.furO); t.position.copy(onHead(x, 1.2, -0.07).p); t.scale.setScalar(0.62);
      t.quaternion.setFromUnitVectors(V3(0, 1, 0), V3(a, 1, z + 0.35).normalize()); face.add(t); tufts.push(t);
    }

    // ---- helmet bubble on the collar (does not turn with the head)
    const HELM_C = V3(0, 1.05, 0), HELM_R = 1.45, cut = Math.acos(-(HELM_C.y - 0.0) / HELM_R);
    const helmet = new THREE.Mesh(geo(new THREE.SphereGeometry(HELM_R, 22, 11, 0, Math.PI * 2, 0, cut)), helmetMat);
    helmet.position.copy(HELM_C); helmet.renderOrder = 2; model.add(helmet);
    const collar = new THREE.Mesh(geo(new THREE.TorusGeometry(0.99, 0.12, 6, 22)), M.acc); collar.rotation.x = Math.PI / 2; model.add(collar);

    // ---- body (white suit, orange bands, flame badge)
    const BODY_C = V3(0, -0.7, 0), BR = V3(0.86, 0.84, 0.78);
    model.add(mesh(G.sphB, M.suit, BODY_C.x, BODY_C.y, BODY_C.z, BR.x, BR.y, BR.z));
    const belt = new THREE.Mesh(geo(new THREE.TorusGeometry(0.86, 0.06, 3, 18)), M.acc); belt.rotation.x = Math.PI / 2; belt.position.copy(BODY_C);
    belt.scale.set(1, BR.z / BR.x, 1); model.add(belt);
    { const by0 = -0.33, dy = by0 - BODY_C.y, z = BR.z * Math.sqrt(1 - (dy / BR.y) ** 2), n = V3(0, dy / (BR.y * BR.y), z / (BR.z * BR.z)).normalize();
      const b = new THREE.Mesh(G.disc, M.badge); b.scale.setScalar(0.17); b.position.set(0, by0, z).addScaledVector(n, 0.012); orient(b, n); model.add(b); }
    // backpack with antenna and a slowly blinking status light (the only thing allowed to bloom)
    const pack = new THREE.Group(); pack.position.set(0, -0.62, -0.74); model.add(pack);
    pack.add(mesh(geo(new THREE.CapsuleGeometry(0.34, 0.38, 3, 8)), M.suit2, 0, 0, 0, 1.15, 1, 0.55));
    pack.add(mesh(geo(new THREE.BoxGeometry(0.5, 0.11, 0.06)), M.acc, 0, -0.14, -0.2));
    const led = mesh(G.sphS, ledMat, 0.22, 0.3, -0.16, 0.065); pack.add(led);

    // ---- arms: shoulder pivot, stretchy sleeve, orange cuff, cream mitten paw with pink beans on the palm (+Z)
    const ARM_LEN = 0.66, SLEEVE = geo(new THREE.CapsuleGeometry(0.165, 0.36, 2, 7).translate(0, -0.18, 0));
    const CUFF = geo(new THREE.TorusGeometry(0.165, 0.05, 4, 10)), arms = [];
    for (const s of [1, -1]) {             // s = +1: Nova's left arm (+X, viewer's right)
      const pv = new THREE.Group(); pv.position.set(s * 0.74, -0.3, 0.16); model.add(pv);
      const sleeve = new THREE.Mesh(SLEEVE, M.suit); pv.add(sleeve);
      const cuff = new THREE.Mesh(CUFF, M.acc); cuff.rotation.x = Math.PI / 2; pv.add(cuff);
      const paw = new THREE.Group(); pv.add(paw);
      paw.add(mesh(G.sphM, M.cream, 0, 0, 0, 0.21, 0.2, 0.18));
      const bean = (x, y, r, sy) => { const d = V3(x, y, 1).normalize(), b = new THREE.Mesh(G.discS, M.pink);
        b.position.set(d.x * 0.21, d.y * 0.2, d.z * 0.18 + 0.004); b.scale.set(r, r * (sy || 1), 1); orient(b, d); paw.add(b); };
      bean(0, 0.12, 0.075, 0.8); bean(-0.42, -0.36, 0.036); bean(0, -0.5, 0.038); bean(0.42, -0.36, 0.036);
      arms.push({ s, pv, sleeve, cuff, paw, q: new THREE.Quaternion() });
    }
    // ---- legs with boots
    const LEG = geo(new THREE.CapsuleGeometry(0.19, 0.18, 2, 7).translate(0, -0.12, 0)), SOLE = geo(new THREE.TorusGeometry(0.19, 0.045, 3, 10)), legs = [];
    for (const s of [1, -1]) {
      const pv = new THREE.Group(); pv.position.set(s * 0.36, -1.3, 0.1); model.add(pv);
      pv.add(new THREE.Mesh(LEG, M.suit), mesh(G.sphM, M.suit, 0, -0.42, 0.05, 0.24, 0.2, 0.3));
      const sole = new THREE.Mesh(SOLE, M.acc); sole.rotation.x = Math.PI / 2; sole.position.set(0, -0.5, 0.05); sole.scale.set(1, 1.25, 1); pv.add(sole);
      legs.push({ s, pv });
    }
    // ---- tail in a little suit sleeve: chain of segments, fur tip pokes out
    // root frame: +Y = out to Nova's left side (viewer's right), slightly down and back; +Z = "up" so curling about X lifts the tip
    const tail = [], TSEG = 0.28, tailRoot = new THREE.Group(); tailRoot.position.set(0.32, -1.18, -0.5); model.add(tailRoot);
    { const ty = V3(0.95, -0.1, -0.3).normalize(), tz = V3(0, 1, 0).addScaledVector(ty, -ty.y).normalize(), tx = V3().crossVectors(ty, tz);
      basis.makeBasis(tx, ty, tz); tailRoot.quaternion.setFromRotationMatrix(basis); }
    const TAIL_CURL = [0, 0.1, 0.35, 0.55, 0.6, 0.5];
    let parent = tailRoot;
    for (let i = 0; i < 6; i++) {
      const fur = i >= 4, r = fur ? 0.105 - (i - 4) * 0.01 : 0.125 - i * 0.006;
      const seg = new THREE.Group(); seg.position.y = i ? TSEG : 0; parent.add(seg);
      const m = new THREE.Mesh(geo(new THREE.CapsuleGeometry(r, TSEG * 0.7, 1, 6).translate(0, TSEG / 2, 0)), fur ? (i === 5 ? M.furD : M.furO) : M.suit); seg.add(m);
      if (i === 3) { const ring = new THREE.Mesh(geo(new THREE.TorusGeometry(r + 0.01, 0.045, 4, 10)), M.acc); ring.rotation.x = Math.PI / 2; ring.position.y = TSEG * 0.95; seg.add(ring); }
      tail.push({ seg, m, fur }); parent = seg;
    }
    { const tip = mesh(G.sphS, M.furD, 0, TSEG + 0.02, 0, 0.1); tail[5].seg.add(tip); tail[5].tip = tip; }

    // ---- floating extras: hearts, "!" / "?" bubble, a little soap bubble to bat at
    const hearts = [];
    for (let i = 0; i < 6; i++) { const sp = new THREE.Sprite(spriteMat(HEART_TEX)); sp.renderOrder = 3; sp.visible = false; pop.add(sp); hearts.push({ sp, life: -1, v: V3() }); }
    const bubble = new THREE.Sprite(spriteMat(BANG_TEX)); bubble.renderOrder = 3; bubble.visible = false; drift.add(bubble);
    const ball = new THREE.Mesh(geo(new THREE.SphereGeometry(0.2, 10, 6)), ballMat); ball.renderOrder = 2; ball.visible = false; model.add(ball);
    // invisible click proxy
    const hit = new THREE.Mesh(geo(new THREE.SphereGeometry(2.3, 10, 8)), new THREE.MeshBasicMaterial({ visible: false }));
    hit.position.y = 0.0; spin.add(hit); MATS.push({ m: hit.material, base: new THREE.Color(1, 1, 1), kind: "none" });

    /* ------------------------------------------------------------------ places */
    const PL = {
      earth: null, orbit: null,
      cabin:   { mode: "screen", ndc: [0.66, -0.36], h: 0.30, dist: 0.5, tone: 1.0, yaw: -0.32, roll: 0, side: -1, focus: [-1.065, -0.04, 2.56], wind: null },
      chamber: { mode: "screen", ndc: [0.93, -0.42], h: 0.29, dist: 4, tone: 0.5, yaw: -0.55, roll: 0.42, side: -1, peek: true, focus: [0, 0, 0], wind: null },
      wiring:  { mode: "world", pos: [1.0, 0.64, -3.08], height: 0.44, tone: 1.0, faceMix: 0.22, side: 1, focus: [1.22, -0.13, -0.56], wind: [-0.15, 0, 1] },
    };
    if (opts.places) for (const k in opts.places) PL[k] = opts.places[k] ? Object.assign({}, PL[k] || {}, opts.places[k]) : null;

    /* ------------------------------------------------------------------ pose system */
    const POSE0 = {
      px: 0, py: 0, pz: 0, rx: 0, ry: 0, rz: 0, sq: 1, hy: 0, hp: 0, hr: 0, hdrop: 0, look: 1,
      eL: 0, eR: 0, perk: 0, aLx: -0.28, aLy: 0, aLz: 0.52, aRx: -0.28, aRy: 0, aRz: -0.52, reachL: 0, reachR: 0,
      tLx: 0.6, tLy: 0.2, tLz: 1.1, tRx: -0.6, tRy: 0.2, tRz: 1.1, lLx: -0.22, lLz: 0.12, lRx: -0.22, lRz: -0.12,
      tAmp: 0.32, tCurl: 0, tPuff: 0, tSpd: 1.5, open: 1, wide: 0, pupil: 0.6, happy: 0, squeeze: 0, gx: 0, gy: 0,
      mouth: 0, blush: 0.35, poof: 0, ruffle: 0, bang: 0, ask: 0, rate: 7, sx: 0, sy: 0, sz: 0,
    };
    const P = Object.assign({}, POSE0), C = Object.assign({}, POSE0);
    const NOSMOOTH = { rate: 1, sx: 1, sy: 1, sz: 1, bang: 1, ask: 1 };
    const mix = (k, v, w) => { P[k] += (v - P[k]) * w; };
    let T = 0, cur = null, queued = null, lastIdle = "", nextIdle = rand(5, 8);
    const spinRes = V3();
    let fireActive = false, wind = opts.fan === false ? 0 : 1, windT = wind;
    const windLocal = V3(-1, 0, 0), fearLocal = V3(0, 0.2, -1);
    const ctx = { u: 0, pu: 0, at(x) { return ctx.pu < x && ctx.u >= x; }, heart: n => { for (let i = 0; i < (n || 1); i++) emitHeart(); }, ball: null };

    // armReach target helpers (model space)
    const EYE_GLASS_L = [0.36, 0.78, 1.5], EYE_GLASS_R = [-0.36, 0.78, 1.5];
    function reach(side, w, x, y, z) {
      const k = side > 0 ? "L" : "R";
      if (w <= 0) return; P["reach" + k] = Math.max(P["reach" + k], w);
      mix("t" + k + "x", x, w); mix("t" + k + "y", y, w); mix("t" + k + "z", z, w);
    }
    const IDLE_ACTIONS = ["slowblink", "bat", "somersault", "yawn", "chase", "wave", "knead"];
    const PEEK_OK = { slowblink: 1, bat: 1, yawn: 1, wave: 1, knead: 1 };

    const ACT = {
      /* ---- idle extras (random, 7-12 s apart, never the same twice in a row) */
      slowblink: { dur: 3.8, prio: 0, fn(u) {
        const c = Math.min(1, env(u, 0.3, 0.75, 2.0, 2.4) + env(u, 2.7, 2.95, 3.15, 3.4)), w = env(u, 0, 0.4, 3.2, 3.8);
        mix("open", 0.05, c); P.hr += 0.16 * w; P.blush += 0.45 * w; P.perk -= 0.3 * w; P.hp += 0.06 * w;
        if (ctx.at(0.95)) ctx.heart(); if (ctx.at(1.35)) ctx.heart(); if (ctx.at(1.75)) ctx.heart();
      } },
      bat: { dur: 4.2, prio: 0, fn(u) {
        const w = env(u, 0, 0.35, 3.5, 4.2), hov = V3(0.98, 0.42, 1.05);
        let bp;
        if (u < 1.48) { const a = sstep(0, 1.1, u); bp = V3(lerp(2.1, hov.x, a), lerp(1.3, hov.y, a) + 0.05 * Math.sin(u * 4), lerp(1.6, hov.z, a)); }
        else { const k = u - 1.48; bp = V3(hov.x + 1.1 * k, hov.y + 0.9 * k - 0.1 * k * k, hov.z + 0.5 * k); }
        const burst = u > 2.45 ? 0 : u > 2.3 ? 1.35 : 1, sc = sstep(0, 0.35, u) * burst;
        ctx.ball = sc > 0.01 ? { p: bp, s: sc } : null;
        const look = env(u, 0.1, 0.5, 2.4, 2.9);
        P.look *= 1 - look; P.hy += 0.42 * look; P.hp += 0.28 * look; P.gx += 0.22 * look; P.gy -= 0.2 * look;
        P.perk += 0.7 * w; mix("pupil", 0.74, env(u, 0.2, 0.5, 2.3, 2.6));
        const wig = env(u, 0.6, 0.75, 1.2, 1.32); P.rz += 0.08 * Math.sin(u * 30) * wig; P.tAmp += 0.5 * wig; P.tSpd += 5 * wig;
        const sw = env(u, 1.28, 1.42, 1.6, 1.95); P.rate = Math.max(P.rate, 7 + 10 * sw);
        reach(1, sw, hov.x + 0.05, hov.y + 0.1, hov.z + 0.1); P.rz -= 0.12 * sw; P.ry += 0.15 * sw;
        const sur = env(u, 2.3, 2.4, 2.6, 2.9); P.wide += sur; mix("pupil", 0.32, sur); P.mouth += 0.3 * sur;
        mix("happy", 1, env(u, 2.9, 3.1, 3.6, 4.0)); P.blush += 0.4 * env(u, 2.9, 3.1, 3.6, 4.0);
      } },
      somersault: { dur: 3.4, prio: 0, fn(u) {
        const e = easeIO(sstep(0.35, 2.5, u)), tuck = env(u, 0.2, 0.55, 2.3, 2.7), ta = env(u, 2.45, 2.7, 3.0, 3.4);
        P.sx = 2 * Math.PI * e; P.look *= 1 - tuck;
        P.aLx = lerp(P.aLx, -1.3, tuck); P.aRx = lerp(P.aRx, -1.3, tuck); P.aLz = lerp(P.aLz, 0.25, tuck); P.aRz = lerp(P.aRz, -0.25, tuck);
        P.lLx = lerp(P.lLx, -1.3, tuck); P.lRx = lerp(P.lRx, -1.3, tuck); P.tCurl += 1.0 * tuck;
        mix("happy", 1, tuck); P.mouth += 0.35 * tuck; P.ruffle += 0.2 * tuck;
        P.aLz += 1.2 * ta; P.aRz -= 1.2 * ta; mix("happy", 1, ta); P.py += 0.1 * ta;
      } },
      yawn: { dur: 3.9, prio: 0, fn(u) {
        const st = env(u, 0.3, 0.9, 2.0, 2.6), mo = env(u, 0.55, 1.0, 1.9, 2.35), sh = env(u, 2.6, 2.7, 3.15, 3.35);
        P.aLz = lerp(P.aLz, 2.55, st); P.aRz = lerp(P.aRz, -2.55, st); P.aLx = lerp(P.aLx, -0.15, st); P.aRx = lerp(P.aRx, -0.15, st);
        P.aLz += 0.05 * Math.sin(u * 30) * st; P.aRz -= 0.05 * Math.sin(u * 31) * st;
        P.sq += 0.08 * st; P.hp -= 0.28 * st; P.look *= 1 - st; P.lLx += 0.3 * st; P.lRx += 0.3 * st; P.lLz += 0.2 * st; P.lRz -= 0.2 * st;
        mix("open", 0.04, env(u, 0.45, 0.8, 2.1, 2.5)); P.mouth += mo; P.eL += 0.35 * st; P.eR += 0.35 * st; P.tAmp *= 1 - 0.7 * st;
        P.hy += 0.22 * Math.sin(u * 22) * sh; P.ruffle += 0.6 * sh;
      } },
      chase: { dur: 3.9, prio: 0, fn(u) {
        const e = easeIO(sstep(0.35, 3.3, u)), w = env(u, 0.1, 0.4, 3.2, 3.8);
        P.sy = 2 * Math.PI * e; P.look *= 1 - w; P.hy -= 0.55 * w; P.hr += 0.1 * w; P.gx -= 0.25 * w;
        P.tAmp += 0.5 * w; P.tSpd += 4 * w; P.perk += 0.6 * w; mix("pupil", 0.76, w);
        P.aRx = lerp(P.aRx, -0.9, w); P.aRz += -0.5 * w + 0.25 * Math.sin(u * 9) * w; P.rz += 0.12 * w; P.ry -= 0.2 * w;
        P.sq += 0.04 * Math.sin(u * 9) * w;
      } },
      wave: { dur: 2.9, prio: 0, fn(u) { waveFn(u, 0.7); } },
      knead: { dur: 3.7, prio: 0, fn(u) {
        const w = env(u, 0, 0.45, 3.1, 3.7), k = Math.sin(u * 7.5);
        P.aLx = lerp(P.aLx, -1.05 + 0.32 * k, w); P.aRx = lerp(P.aRx, -1.05 - 0.32 * k, w); P.aLz = lerp(P.aLz, 0.2, w); P.aRz = lerp(P.aRz, -0.2, w);
        mix("happy", 1, env(u, 0.25, 0.55, 3.0, 3.5)); P.blush += 0.6 * w; P.eL += 0.22 * w; P.eR += 0.22 * w;
        P.px += 0.012 * Math.sin(u * 57) * w; P.rz += 0.05 * k * w; P.hr += 0.08 * k * w; P.tAmp *= 1 - 0.4 * w; P.tSpd *= 1 - 0.4 * w;
        if (ctx.at(1.7)) ctx.heart();
      } },

      /* ---- reactions */
      hello: { dur: 3.2, prio: 3, fn(u) { waveFn(u, 1); if (ctx.at(2.2)) ctx.heart(); } },
      startle: { dur: 4.9, prio: 5, fn(u) {           // spark: poof, wide eyes, ears flat, jump back, cover eyes, peek
        const jolt = env(u, 0, 0.07, 0.45, 0.95);
        P.rate = u < 0.5 ? 24 : u < 1.0 ? 12 : 8;
        P.poof = Math.max(P.poof, env(u, 0, 0.05, 1.8, 3.2)); P.tPuff = Math.max(P.tPuff, env(u, 0, 0.06, 2.6, 3.9));
        P.wide += env(u, 0, 0.05, 0.7, 1.0); mix("pupil", 0.2, env(u, 0, 0.05, 0.8, 1.2));
        P.eL += env(u, 0, 0.07, 3.3, 4.3); P.eR += env(u, 0, 0.07, 3.5, 4.4);
        P.px += fearLocal.x * 0.75 * jolt; P.pz += fearLocal.z * 0.75 * jolt; P.py += 0.32 * jolt; P.rx -= 0.28 * jolt; P.sq += 0.1 * bell(u, 0.08, 0.06) - 0.06 * bell(u, 0.3, 0.1);
        P.aLz += 1.3 * jolt; P.aRz -= 1.3 * jolt; P.lLz += 0.5 * jolt; P.lRz -= 0.5 * jolt; P.mouth += 0.45 * env(u, 0, 0.05, 0.5, 0.8);
        P.tAmp *= 1 - 0.8 * env(u, 0, 0.1, 2.6, 3.5);
        const covL = env(u, 0.55, 0.95, 2.9, 3.45), covR = env(u, 0.55, 0.95, 3.7, 4.2), cov = Math.max(covL, covR);
        reach(1, covL, EYE_GLASS_L[0], EYE_GLASS_L[1] - 0.12 * cov, EYE_GLASS_L[2]);
        reach(-1, covR, EYE_GLASS_R[0], EYE_GLASS_R[1] - 0.12 * cov, EYE_GLASS_R[2]);
        P.hp += 0.22 * cov; P.hdrop += 0.08 * cov; P.look *= 1 - 0.8 * cov;
        P.lLx = lerp(P.lLx, -1.0, cov); P.lRx = lerp(P.lRx, -1.0, cov); P.tCurl += 0.9 * cov;
        P.px += 0.018 * Math.sin(u * 41) * env(u, 0.9, 1.1, 2.7, 3.0);
        mix("squeeze", 1, env(u, 0.6, 0.8, 2.75, 2.95));
        const peek = env(u, 2.95, 3.2, 3.9, 4.3); P.wide += 0.7 * peek; mix("pupil", 0.34, peek); P.hr -= 0.2 * peek; P.gx += 0.12 * peek;
        P.py -= 0.08 * bell(u, 4.4, 0.25);
      } },
      tumble: { dur: 4.5, prio: 6, fn(u) {              // flash: tumble away with a "!" then a trembling recovery
        const e = 1 - Math.pow(1 - sstep(0.02, 1.55, u), 3), fl = env(u, 0, 0.05, 1.3, 1.7);
        P.rate = u < 0.4 ? 22 : 9;
        P.bang = env(u, 0.0, 0.08, 1.55, 1.75);
        P.sz = -2 * Math.PI * e; P.sx = 0.5 * Math.sin(Math.PI * e);
        const away = env(u, 0, 0.35, 1.7, 3.0); P.px += (fearLocal.x * 0.95 - 0.2) * away; P.pz += fearLocal.z * 0.95 * away; P.py += 0.3 * away;
        P.poof = Math.max(P.poof, env(u, 0, 0.05, 2.2, 3.6)); P.tPuff = Math.max(P.tPuff, env(u, 0, 0.05, 2.8, 4.0));
        mix("squeeze", 1, env(u, 0.0, 0.06, 1.45, 1.7)); P.eL += env(u, 0, 0.06, 3.3, 4.2); P.eR += env(u, 0, 0.06, 3.3, 4.2);
        P.aLz += 0.9 * Math.sin(u * 15) * fl + 0.8 * fl; P.aRz -= 0.9 * Math.sin(u * 15 + 1) * fl + 0.8 * fl;
        P.lLx += 0.7 * Math.sin(u * 13) * fl; P.lRx += 0.7 * Math.sin(u * 13 + 2) * fl; P.look *= 1 - env(u, 0, 0.05, 1.5, 1.9);
        const rec = env(u, 1.6, 1.9, 3.4, 4.0), trem = env(u, 1.6, 1.75, 3.2, 3.8) * (1 - 0.6 * sstep(1.6, 3.6, u));
        P.px += 0.035 * Math.sin(u * 47) * trem; P.py += 0.02 * Math.sin(u * 39) * trem;
        P.wide += 0.85 * rec; mix("pupil", 0.2, rec); P.mouth += 0.22 * rec;
        reach(1, 0.9 * rec, 0.22, -0.2, 0.95); reach(-1, 0.9 * rec, -0.22, -0.2, 0.95);
        P.hp += 0.12 * rec; P.hr += 0.1 * Math.sin(u * 3) * rec;
      } },
      relief: { dur: 3.3, prio: 4, fn(u) {               // co2 / fan_off after a fire: happy squint, sigh, hearts
        const w = env(u, 0, 0.35, 2.7, 3.3), sigh = bell(u, 0.55, 0.32);
        P.sq -= 0.07 * sigh; P.py -= 0.16 * sigh; P.pz -= 0.05 * sigh; P.eL += 0.3 * w; P.eR += 0.3 * w;
        mix("happy", 1, env(u, 0.3, 0.6, 2.7, 3.2)); P.blush += 0.65 * w; P.mouth += 0.18 * w; P.hr += 0.16 * w;
        reach(-1, 0.85 * env(u, 0.2, 0.6, 2.4, 3.0), -0.18, -0.25, 0.92); P.tAmp += 0.2 * w; P.tSpd *= 1 - 0.4 * w;
        if (ctx.at(0.75)) ctx.heart(); if (ctx.at(1.15)) ctx.heart(); if (ctx.at(1.6)) ctx.heart();
      } },
      gust: { dur: 3.1, prio: 2, fn(u) {                 // fan_on: fur and whiskers ruffle, drift with the airflow
        const w = env(u, 0, 0.25, 2.0, 3.1), d = env(u, 0, 0.7, 1.7, 3.0);
        P.px += windLocal.x * 0.55 * d; P.py += windLocal.y * 0.55 * d; P.pz += windLocal.z * 0.55 * d;
        P.rz -= windLocal.x * 0.18 * d; P.rx += windLocal.z * 0.12 * d;
        P.ruffle += w; P.poof += 0.25 * w + 0.12 * Math.sin(u * 21) * w; mix("happy", 0.9, env(u, 0.1, 0.35, 1.9, 2.6)); P.eL += 0.55 * w; P.eR += 0.55 * w;
        P.aLz += 0.45 * w + 0.12 * Math.sin(u * 12) * w; P.aRz -= 0.45 * w + 0.12 * Math.sin(u * 12.5) * w; P.tAmp += 0.45 * w; P.tSpd += 3 * w;
      } },
      settle: { dur: 1.7, prio: 1, fn(u) { const w = env(u, 0, 0.3, 1.1, 1.7); P.perk += 0.6 * w; P.hr += 0.1 * w; mix("open", 0.3, bell(u, 0.8, 0.12)); } },
      shake: { dur: 2.1, prio: 2, fn(u) {                // reset: little shake-off, then content
        const s = env(u, 0.15, 0.25, 0.9, 1.15); P.hy += 0.3 * Math.sin(u * 19) * s; P.rz += 0.08 * Math.sin(u * 19 + 1) * s; P.ruffle += 0.7 * s; P.look *= 1 - s;
        mix("open", 0.2, s * 0.6); mix("happy", 1, env(u, 1.15, 1.35, 1.75, 2.1)); P.tAmp += 0.3 * s;
      } },
      tailflick: { dur: 2.0, prio: 1, fn(u) {            // green: happy tail flick and a tiny hop
        const w = env(u, 0, 0.15, 1.2, 1.9); P.tAmp += 0.75 * w; P.tSpd += 5.5 * w; P.py += 0.22 * bell(u, 0.45, 0.17);
        P.sq += 0.05 * bell(u, 0.4, 0.12); mix("happy", 1, env(u, 0.2, 0.4, 1.4, 1.9)); P.perk += 0.5 * w;
      } },
      hmm: { dur: 2.0, prio: 1, fn(u) {                  // amber: ears perk, small head tilt, glance
        const w = env(u, 0, 0.3, 1.4, 2.0); P.perk += 0.6 * w; P.hr -= 0.14 * w; P.gx -= 0.2 * w; P.gy += 0.16 * w; P.eL -= 0.2 * w;
      } },
      curious: { dur: 2.9, prio: 2, fn(u) {              // red: curious head tilt with a "?"
        const w = env(u, 0, 0.35, 2.3, 2.9); P.ask = env(u, 0.12, 0.25, 2.35, 2.55);
        P.hr += 0.36 * w; P.hy += 0.1 * w; mix("pupil", 0.76, w); P.perk += 0.45 * w; P.eR += 0.25 * w;
        reach(-1, 0.85 * env(u, 0.25, 0.65, 2.2, 2.75), -0.3, 0.12, 1.25); P.tCurl += 0.5 * w; P.gy += 0.1 * w;
      } },
      purr: { dur: 2.7, prio: 3, fn(u) {                 // click: boop squash, purr wiggle, hearts
        const w = env(u, 0.05, 0.25, 2.1, 2.7); P.sq -= 0.12 * bell(u, 0.08, 0.06); P.rate = u < 0.2 ? 18 : 8;
        mix("happy", 1, env(u, 0.08, 0.22, 2.1, 2.6)); P.blush += 0.75 * w; P.mouth += 0.12 * w; P.eL += 0.2 * w; P.eR += 0.2 * w;
        P.px += 0.012 * Math.sin(u * 61) * w; P.rz += 0.06 * Math.sin(u * 8.5) * w; P.hr += 0.09 * Math.sin(u * 8.5) * w;
        P.aLx += 0.25 * Math.sin(u * 7.5) * w; P.aRx -= 0.25 * Math.sin(u * 7.5) * w;
        if (ctx.at(0.25)) ctx.heart(); if (ctx.at(0.6)) ctx.heart(); if (ctx.at(1.0)) ctx.heart();
      } },
    };
    function waveFn(u, big) {                         // paw wave with Nova's right arm (viewer's left)
      const w = env(u, 0, 0.4, 2.3, 2.9);
      P.aRz = lerp(P.aRz, -1.95 + 0.38 * Math.sin(u * 10.5) * sstep(0.35, 0.6, u), w); P.aRx = lerp(P.aRx, -0.55, w); P.aRy = lerp(P.aRy, 0.3, w);
      P.hr -= 0.14 * w; P.perk += 0.6 * w; P.py += 0.06 * Math.sin(u * 5.2) * w; P.ry -= 0.12 * w;
      mix("happy", big, env(u, 0.35, 0.6, 2.2, 2.7)); P.mouth += 0.22 * big * w; P.blush += 0.3 * w;
    }

    function play(name) {
      const def = ACT[name]; if (!def) return false;
      if (cur && cur.def.prio > def.prio && cur.u < cur.def.dur - 0.5) {
        if (!queued || ACT[queued].prio <= def.prio) queued = name; return true;
      }
      if (cur) { spinRes.x = wrapPi(spinRes.x + P.sx); spinRes.y = wrapPi(spinRes.y + P.sy); spinRes.z = wrapPi(spinRes.z + P.sz); }
      cur = { name, def, u: 0, pu: -1 }; return true;
    }

    /* ------------------------------------------------------------------ hearts, bubble, soap bubble */
    function emitHeart() {
      const h = hearts.find(x => x.life < 0) || hearts[0];
      h.life = 0; h.sp.visible = true; h.sp.position.set(rand(-0.6, 0.6) + C.px, 2.3 + C.py, 0.6 + C.pz); h.v.set(rand(-0.25, 0.25), rand(0.6, 0.85), 0.1);
    }
    const bub = { s: 0, v: 0, tex: null };
    function updateFx(dt, side) {
      for (const h of hearts) {
        if (h.life < 0) continue;
        h.life += dt; const L = h.life;
        if (L > 1.9) { h.life = -1; h.sp.visible = false; continue; }
        h.sp.position.addScaledVector(h.v, dt); h.sp.position.x += Math.sin(L * 6 + h.v.x * 9) * 0.006;
        h.sp.scale.setScalar(0.42 * easeOutBack(Math.min(1, L / 0.35)) * (1 + 0.08 * Math.sin(L * 9)));
        h.sp.material.opacity = 1 - sstep(1.2, 1.9, L);
      }
      const want = Math.max(P.bang, P.ask); if (P.bang > 0.01) bub.tex = BANG_TEX; else if (P.ask > 0.01) bub.tex = ASK_TEX;
      if (bub.tex && bubble.material.map !== bub.tex) { bubble.material.map = bub.tex; bubble.material.needsUpdate = true; }
      bub.v += (-(14 * 14) * (bub.s - want) - 2 * 0.42 * 14 * bub.v) * dt; bub.s += bub.v * dt; if (want === 0 && bub.s < 0.02) { bub.s = 0; bub.v = 0; }
      bubble.visible = bub.s > 0.02; bubble.scale.setScalar(0.95 * Math.max(0, bub.s));
      bubble.position.set(side * 1.15, 2.55 + 0.04 * Math.sin(T * 3), 0.5);
      if (ctx.ball) { ball.visible = true; ball.position.copy(ctx.ball.p); ball.scale.setScalar(ctx.ball.s); } else ball.visible = false;
    }

    /* ------------------------------------------------------------------ placement (screen-anchored or world) */
    let PLACE = null, curCfg = null, fromCfg = null, blendK = 1, enabled = true;
    let popState = "hidden", popT = 0, popS = 0, popFrom = 1, pending = null, wantHello = false;
    const lag = { x: 0, y: 0, vx: 0, vy: 0 }, prevFwd = V3(), camFwd = V3(), camRight = V3(), camUp = V3(), camPos = V3(), camQ = new THREE.Quaternion();
    let hasPrev = false, focusOverride = null;
    const A1 = { p: V3(), q: new THREE.Quaternion(), s: 1 }, A2 = { p: V3(), q: new THREE.Quaternion(), s: 1 };
    const tq = new THREE.Quaternion(), te = new THREE.Euler(), tm = new THREE.Matrix4(), tv = V3(), tv2 = V3(), WUP = V3(0, 1, 0);
    function camInfo() {
      camera.updateMatrixWorld(); camera.getWorldPosition(camPos); camera.getWorldQuaternion(camQ);
      camFwd.set(0, 0, -1).applyQuaternion(camQ); camRight.set(1, 0, 0).applyQuaternion(camQ); camUp.set(0, 1, 0).applyQuaternion(camQ);
    }
    function anchor(cfg, out) {
      if (cfg.mode === "screen") {
        const d = cfg.dist || 1, hh = d * Math.tan(camera.fov * Math.PI / 360), hw = hh * camera.aspect;
        const x = (cfg.ndc[0] + lag.x) * hw, y = (cfg.ndc[1] + lag.y) * hh;
        out.p.copy(camPos).addScaledVector(camFwd, d).addScaledVector(camRight, x).addScaledVector(camUp, y);
        out.s = cfg.h * 2 * hh / CAT_H;
        tm.lookAt(camPos, out.p, camUp); out.q.setFromRotationMatrix(tm);
      } else {
        out.p.fromArray(cfg.pos); out.s = cfg.height / CAT_H;
        tv.subVectors(camPos, out.p).normalize();
        if (cfg.focus && cfg.faceMix) { tv2.fromArray(cfg.focus).sub(out.p).normalize(); tv.lerp(tv2, cfg.faceMix).normalize(); }
        tv2.copy(out.p).add(tv); tm.lookAt(tv2, out.p, WUP); out.q.setFromRotationMatrix(tm);
      }
      tq.setFromEuler(te.set(0, cfg.yaw || 0, cfg.roll || 0)); out.q.multiply(tq);
      return out;
    }
    function attach(scene) { if (scene && root.parent !== scene) { if (root.parent) root.parent.remove(root); scene.add(root); } }
    function sceneFor(place, sc) { return sc || (opts.scenes && opts.scenes[place]) || opts.scene || null; }
    function showAfter(delay) { popState = "wait"; popT = -delay; }
    function startOut() { if (popState === "in" || popState === "shown") { popFrom = popS; popState = "out"; popT = 0; } else if (popState === "wait") popState = "hidden"; }

    function setPlace(place, scene) {
      PLACE = place; const cfg = PL[place] || null;
      if (!cfg || !enabled) { pending = null; startOut(); return; }
      const target = sceneFor(place, scene);
      if (popState === "hidden" || popState === "wait") {             // not on screen yet: just move there
        attach(target); curCfg = cfg; fromCfg = null; blendK = 1; hasPrev = false; if (popState === "hidden") showAfter(0.8); return;
      }
      if (popState === "out") { pending = { cfg, target }; return; }   // finish shrinking, then appear at the new place
      if (root.parent !== target) { pending = { cfg, target }; startOut(); return; }
      if (curCfg !== cfg) { fromCfg = curCfg; curCfg = cfg; blendK = 0; }   // same scene: float over smoothly
    }
    function setVisible(v) {
      enabled = !!v;
      if (!enabled) { pending = null; startOut(); }
      else if (PLACE) setPlace(PLACE);
    }

    function updatePop(dt) {
      if (popState === "wait") { popT += dt; popS = 0; if (popT >= 0) { popState = "in"; popT = 0; } }
      else if (popState === "in") { popT += dt; popS = easeOutBack(Math.min(1, popT / 0.6)); if (popT >= 0.6) { popState = "shown"; popS = 1; if (wantHello) { wantHello = false; play("hello"); } } }
      else if (popState === "out") {
        popT += dt; const k = Math.min(1, popT / 0.28); popS = popFrom * (1 - k * k * k);
        if (k >= 1) { popS = 0; popState = "hidden"; hearts.forEach(h => { h.life = -1; h.sp.visible = false; });
          if (pending && enabled) { attach(pending.target); curCfg = pending.cfg; fromCfg = null; blendK = 1; hasPrev = false; pending = null; showAfter(0.45); } }
      }
      root.visible = popState !== "hidden" && popState !== "wait" && popS > 0.002 && !!curCfg;
      pop.scale.setScalar(Math.max(1e-3, popS));
    }

    /* ------------------------------------------------------------------ main update */
    let blinkT = rand(1.5, 3.5), blinkPh = -1, blinkTwice = false, secondBlink = false, earT = rand(2, 4), lookT = 1.5, lookAtFocus = false;
    const look = { y: 0, p: 0 }, tmpV = V3(), warmC = new THREE.Color();

    function update(dt) {
      dt = Math.min(Math.max(+dt || 0, 0), 0.05); T += dt;
      if (!camera) return;
      updatePop(dt);
      wind += (windT - wind) * (1 - Math.exp(-dt * 1.5));
      if (popState === "hidden" || !curCfg) return;
      const cfg = curCfg, side = cfg.side || 1;

      // ---- scheduler: random cute actions every 7-12 s, never the same one twice in a row
      if (cur) { cur.pu = cur.u; cur.u += dt; if (cur.u >= cur.def.dur) { const was = cur; cur = null; spinRes.set(wrapPi(spinRes.x + P.sx), wrapPi(spinRes.y + P.sy), wrapPi(spinRes.z + P.sz));
        if (queued) { const q = queued; queued = null; play(q); } if (was.def.prio === 0 || !cur) nextIdle = T + rand(4, 8.5); } }
      else if (popState === "shown" && T >= nextIdle) {
        const pool = IDLE_ACTIONS.filter(n => n !== lastIdle && (!cfg.peek || PEEK_OK[n]));
        lastIdle = pool[Math.floor(rnd() * pool.length)]; play(lastIdle);
      }

      // ---- target pose = defaults + idle float + action
      Object.assign(P, POSE0);
      P.py += 0.075 * Math.sin(T * 1.25); P.px += 0.045 * Math.sin(T * 0.53); P.pz += 0.03 * Math.sin(T * 0.71);
      P.ry += 0.2 * Math.sin(T * 0.23) + 0.07 * Math.sin(T * 0.61); P.rz += 0.05 * Math.sin(T * 0.47); P.rx += 0.04 * Math.sin(T * 0.37);
      P.hr += 0.06 * Math.sin(T * 0.41); P.sq += 0.015 * Math.sin(T * 2.1);
      P.aLz += 0.08 * Math.sin(T * 1.1); P.aRz -= 0.08 * Math.sin(T * 1.1 + 1); P.aLx += 0.1 * Math.sin(T * 0.9); P.aRx += 0.1 * Math.sin(T * 0.9 + 2);
      P.lLx += 0.12 * Math.sin(T * 0.8); P.lRx += 0.12 * Math.sin(T * 0.8 + 2.2);
      if (cfg.peek) { reach(1, 0.9, 0.5, 0.22, 1.15); reach(-1, 0.9, -0.5, 0.22, 1.15); P.perk += 0.35; P.py *= 0.4; P.ry *= 0.4; }
      const w = PLACE === "wiring" ? wind : 0;
      if (w > 0.01) { P.ruffle += 0.22 * w; P.tAmp += 0.12 * w; }
      if (fireActive) { P.perk += 0.15; P.tAmp += 0.1; }
      ctx.ball = null;
      if (cur) { ctx.u = cur.u; ctx.pu = cur.pu; cur.def.fn(cur.u); }
      P.reachL = clamp(P.reachL, 0, 1); P.reachR = clamp(P.reachR, 0, 1);

      // ---- smooth toward the target (no jerks), direct channels for big spins
      const k = 1 - Math.exp(-dt * P.rate);
      for (const key in P) if (!NOSMOOTH[key]) C[key] += (P[key] - C[key]) * k;
      spinRes.multiplyScalar(Math.exp(-dt * 3.5));

      // ---- blink / ear twitch timers
      blinkT -= dt;
      if (blinkT <= 0) { blinkPh = 0; if (secondBlink) { secondBlink = false; blinkTwice = false; } else blinkTwice = rnd() < 0.2; blinkT = rand(3, 6); }
      let blink = 1;
      if (blinkPh >= 0) { blinkPh += dt; const bp = blinkPh / 0.2; blink = 1 - Math.sin(Math.PI * Math.min(1, bp));
        if (bp >= 1) { blinkPh = -1; if (blinkTwice) { secondBlink = true; blinkT = 0.12; } } }
      earT -= dt; if (earT <= 0) { earT = rand(2, 5.5); const e = ears[rnd() < 0.5 ? 0 : 1]; e.tv += rand(7, 10) * (rnd() < 0.5 ? 1 : -1); }
      for (const e of ears) { e.tv += (-200 * e.twitch - 14 * e.tv) * dt; e.twitch += e.tv * dt; }

      // ---- body
      drift.position.set(C.px, C.py, C.pz); drift.rotation.set(C.rx, C.ry, C.rz);
      spin.rotation.set(P.sx + spinRes.x, P.sy + spinRes.y, P.sz + spinRes.z);
      const sq = clamp(C.sq, 0.75, 1.3); model.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));

      // ---- placement
      camInfo();
      if (cfg.mode === "screen") {
        if (hasPrev) {
          tmpV.subVectors(camFwd, prevFwd); const dx = tmpV.dot(camRight), dy = tmpV.dot(camUp);
          if (Math.abs(dx) < 0.3 && Math.abs(dy) < 0.3) { const th = Math.tan(camera.fov * Math.PI / 360); lag.x -= 0.45 * dx / (th * camera.aspect); lag.y -= 0.45 * dy / th; }
        }
        lag.vx += (-49 * lag.x - 14 * lag.vx) * dt; lag.vy += (-49 * lag.y - 14 * lag.vy) * dt;
        lag.x = clamp(lag.x + lag.vx * dt, -0.14, 0.14); lag.y = clamp(lag.y + lag.vy * dt, -0.14, 0.14);
      }
      prevFwd.copy(camFwd); hasPrev = true;
      anchor(cfg, A1); let tone = cfg.tone == null ? 1 : cfg.tone;
      if (fromCfg && blendK < 1) {
        blendK = Math.min(1, blendK + dt / 1.7); const e = easeIO(blendK); anchor(fromCfg, A2);
        A1.p.lerpVectors(A2.p, A1.p, e); A1.p.addScaledVector(camUp, Math.sin(Math.PI * e) * 0.6 * lerp(A2.s, A1.s, e));
        A1.q.slerpQuaternions(A2.q, A1.q, e); A1.s = lerp(A2.s, A1.s, e); tone = lerp(fromCfg.tone == null ? 1 : fromCfg.tone, tone, e);
        if (blendK >= 1) fromCfg = null;
      }
      root.position.copy(A1.p); root.quaternion.copy(A1.q); root.scale.setScalar(A1.s);
      root.updateMatrixWorld(true);
      // wind direction in Nova's frame (for the fan gust)
      if (cfg.wind) { windLocal.fromArray(cfg.wind).normalize(); tq.copy(root.quaternion).invert(); windLocal.applyQuaternion(tq); }
      else windLocal.set(-0.7 * side, 0.15, -0.5).normalize();
      // "away from the fire" in Nova's frame (world places); screen places just hop back from the viewer
      if (cfg.mode === "world" && cfg.focus) { fearLocal.fromArray(cfg.focus).sub(root.position).negate(); fearLocal.y = 0; fearLocal.normalize().applyQuaternion(tq.copy(root.quaternion).invert()); fearLocal.y = 0; fearLocal.normalize(); }
      else fearLocal.set(0, 0, -1);

      // ---- look at the camera or the focus point (flame / chamber / droplet)
      lookT -= dt; if (lookT <= 0) { lookT = rand(2.5, 6); lookAtFocus = rnd() < (fireActive ? 0.6 : 0.3); }
      const fp = focusOverride || (opts.focus && opts.focus()) || (cfg.focus ? tv2.fromArray(cfg.focus) : null);
      tmpV.copy(lookAtFocus && fp ? fp : camPos); model.worldToLocal(tmpV); tmpV.sub(HEAD_C).sub(head.position);
      let wy = Math.atan2(tmpV.x, tmpV.z), wp = Math.atan2(tmpV.y, Math.hypot(tmpV.x, tmpV.z));
      if (Math.abs(wy) > 2.2) { wy = 0; wp = 0; }
      const cy = clamp(wy, -0.7, 0.7), cp = clamp(wp, -0.45, 0.45);
      const lk = 1 - Math.exp(-dt * 5); look.y += (cy - look.y) * lk; look.p += (cp - look.p) * lk;
      const L = clamp(C.look, 0, 1);
      head.rotation.set(-look.p * L + C.hp, look.y * L + C.hy, C.hr);
      head.position.y = 0.12 - C.hdrop;
      const poof = clamp(C.poof, 0, 1.5);
      skull.scale.set(HA * (1 + 0.05 * poof), HB * (1 + 0.05 * poof), HC * (1 + 0.04 * poof));
      tufts.forEach((t, i) => t.scale.set(1 + 0.5 * poof, (i > 3 ? 0.8 : 1) * (1 + 1.1 * poof + 0.15 * C.ruffle * Math.sin(T * 25 + i)), 1 + 0.5 * poof));

      // ---- face
      const open = clamp(C.open * blink, 0, 1.2), hap = clamp(C.happy, 0, 1), sqz = clamp(C.squeeze, 0, 1);
      const eo = clamp(open * (1 - hap) * (1 - sqz), 0, 1), wide = clamp(C.wide, 0, 1.2);
      const lashV = clamp(1 - Math.max(hap, sqz) * 1.4, 0, 1);
      eyes.forEach(e => { e.visible = eo > 0.03 || lashV > 0.05; e.scale.set(EYE_S.x * (1 + 0.13 * wide), EYE_S.y * (1 + 0.13 * wide), EYE_S.z); });
      eyeMat.uniforms.uOpen.value = eo; eyeMat.uniforms.uLash.value = lashV;
      eyeMat.uniforms.uPupil.value = clamp(C.pupil, 0.15, 0.8);
      eyeMat.uniforms.uLook.value.set(clamp(C.gx + clamp((wy - cy) * 0.3, -0.12, 0.12) * L, -0.25, 0.25), clamp(C.gy + clamp((wp - cp) * 0.3, -0.1, 0.1) * L, -0.22, 0.22));
      arches.forEach(a => { const s = hap * (1 - sqz); a.visible = s > 0.02; a.scale.set(1, Math.max(0.01, s), 1); });
      chevs.forEach(c => { c.visible = sqz > 0.02; c.scale.setScalar(Math.max(0.01, sqz)); });
      const mo = clamp(C.mouth, 0, 1); mouthOpen.visible = mo > 0.03; mouthOpen.scale.set(0.6 + 0.4 * mo, Math.max(0.01, mo), 1);
      omega.scale.setScalar(Math.max(0.01, 1 - clamp(mo * 2.2, 0, 1)));
      blushMat.opacity = clamp(0.5 + 0.5 * C.blush, 0, 1);
      const ru = clamp(C.ruffle, 0, 1.5);
      whiskers.forEach(wh => { te.set(ru * 0.22 * Math.sin(T * 23 + wh.k * 1.7), 0, ru * 0.3 * Math.sin(T * 19 + wh.k * 2.3) + 0.05 * Math.sin(T * 1.3 + wh.k));
        wh.pv.quaternion.copy(wh.q0).multiply(tq.setFromEuler(te)); });
      ears.forEach(e => { const flat = clamp(e.s > 0 ? C.eL : C.eR, -0.4, 1.2);
        te.set(-0.62 * flat + 0.22 * C.perk + 0.18 * ru * Math.sin(T * 17 + e.s), e.twitch * 0.6, -e.s * 0.85 * flat + e.twitch * 0.35 * e.s);
        e.pv.quaternion.copy(e.q0).multiply(tq.setFromEuler(te)); });

      // ---- arms (euler pose blended with a reach target; sleeves stretch rubber-hose style)
      for (const a of arms) {
        const K = a.s > 0 ? "L" : "R"; a.q.setFromEuler(te.set(C["a" + K + "x"], C["a" + K + "y"], C["a" + K + "z"]));
        const rw = clamp(C["reach" + K], 0, 1); let st = 1;
        if (rw > 0.002) {
          tmpV.set(C["t" + K + "x"], C["t" + K + "y"], C["t" + K + "z"]).sub(a.pv.position); const len = tmpV.length();
          tq.setFromUnitVectors(V3(0, -1, 0), tmpV.normalize()); a.q.slerp(tq, rw); st = lerp(1, clamp(len / ARM_LEN, 0.7, 2.7), rw);
        }
        a.pv.quaternion.copy(a.q); a.sleeve.scale.set(1, st, 1); a.cuff.position.y = -0.5 * st; a.paw.position.y = -(ARM_LEN * st);
      }
      legs.forEach(l => l.pv.rotation.set(l.s > 0 ? C.lLx : C.lRx, 0, l.s > 0 ? C.lLz : C.lRz));

      // ---- tail swish
      const amp = clamp(C.tAmp, 0, 1.4), curl = C.tCurl, puff = clamp(C.tPuff, 0, 1.2);
      tail.forEach((t, i) => {
        const ph = T * C.tSpd - i * 0.62;
        t.seg.rotation.set(TAIL_CURL[i] * (1 + 0.6 * curl) + amp * 0.32 * Math.sin(ph) * (0.45 + 0.13 * i), 0, amp * 0.16 * Math.sin(ph * 0.7 + 1.3) * (i ? 1 : 0.5));
        if (t.fur) t.m.scale.set(1 + 0.8 * puff, 1, 1 + 0.8 * puff);
        if (t.tip) t.tip.scale.setScalar(0.1 * (1 + 0.8 * puff));
      });

      // ---- status light (slow soft blink) and per-place tone (keeps everything below the bloom threshold)
      const blinkLed = 0.25 + 1.35 * Math.pow(0.5 + 0.5 * Math.sin(T * 2.2), 3);
      const warm = PLACE === "wiring" && fireActive ? 0.06 + 0.03 * Math.sin(T * 13) : 0;
      for (const it of MATS) {
        if (it.kind === "mc") it.m.color.copy(it.base).multiplyScalar(tone).multiply(warmC.setRGB(1 + warm, 1, 1 - warm * 0.8));
        else if (it.kind === "sprite" || it.kind === "basic") it.m.color.copy(it.base).multiplyScalar(Math.min(1, tone * 0.95));
        else if (it.kind === "led") it.m.color.copy(it.base).multiplyScalar(blinkLed);
      }
      eyeMat.uniforms.uTone.value = tone; helmetMat.uniforms.uTone.value = tone; ballMat.uniforms.uTone.value = tone;

      updateFx(dt, side);
    }

    /* ------------------------------------------------------------------ events and pointer */
    function react(ev) {
      ev = String(ev || "").toLowerCase();
      switch (ev) {
        case "enter": if (popState === "shown") play("hello"); else wantHello = true; break;
        case "spark": fireActive = true; play("startle"); break;
        case "flash": fireActive = true; play("tumble"); break;
        case "fan_on": windT = 1; play("gust"); break;
        case "fan_off": windT = 0; play(fireActive ? "relief" : "settle"); break;
        case "co2": play(fireActive ? "relief" : "curious"); fireActive = false; break;
        case "reset": fireActive = false; play("shake"); break;
        case "green": play("tailflick"); break;
        case "amber": play("hmm"); break;
        case "red": play("curious"); break;
        case "click": play("purr"); break;
        default: return false;
      }
      return true;
    }
    function hitTest(raycaster) {
      if (!root.visible || !root.parent || popS < 0.5 || !raycaster) return false;
      return raycaster.intersectObject(hit, false).length > 0;
    }
    function onPointer(raycaster) { if (!hitTest(raycaster)) return false; react("click"); return true; }

    function dispose() {
      if (root.parent) root.parent.remove(root);
      GEOS.forEach(g => g.dispose()); TEX.forEach(t => t.dispose());
      MATS.forEach(it => it.m.dispose()); [eyeMat, helmetMat, ballMat].forEach(m => m.dispose());
    }

    const api = {
      group: root, name: NAME, label: LABEL, title: LABEL,
      update, react, setPlace, onPointer, setVisible, dispose, hitTest,
      play: n => play(n), setFocus: v => { focusOverride = v ? (focusOverride || V3()).copy(v) : null; },
      places: PL, state: () => ({ place: PLACE, action: cur ? cur.name : null, pop: popState, fire: fireActive, wind: windT }),
      triangles() { let n = 0; root.traverse(o => { if (o.isMesh && o !== hit && o.geometry) { const g = o.geometry; n += (g.index ? g.index.count : g.attributes.position.count) / 3; } else if (o.isSprite) n += 2; }); return Math.round(n); },
    };
    if (opts.scene && !opts.deferAttach) attach(opts.scene);
    window.IgnisCat.current = api;
    return api;
  }

  window.IgnisCat = { create, version: "1.0.0" };
})();
