// The playground's hero: what ascii2svg does, in three.js. Characters drift in space, scroll pulls
// them onto the grid, then the box characters give way to drawn lines, arrowheads and tinted boxes.
// Scroll drives it through GSAP ScrollTrigger when present; without it (or with reduced motion,
// or without WebGL) the finished drawing shows and the page works exactly the same.
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.186.0/build/three.module.min.js";

const DIAGRAM = [
  "┌───────────────┐       ┌───────────────┐       ┌───────────────┐",
  "│  plain text   ├──────▶│   ascii2svg   ├──────▶│   crisp SVG   │",
  "└───────┬───────┘       └───────┬───────┘       └───────┬───────┘",
  "        │                       │                       │",
  "        ▼                       ▼                       ▼",
  " ┌─────────────┐         ┌─────────────┐         ┌─────────────┐",
  " │   repair    │         │ self-check  │         │   animate   │",
  " └─────────────┘         └─────────────┘         └─────────────┘",
];
const ARMS = { "─": "LR", "│": "UD", "┌": "RD", "┐": "LD", "└": "UR", "┘": "UL", "├": "UDR", "┤": "UDL",
               "┬": "LRD", "┴": "LRU", "┼": "UDLR" };
const HEADS = { "▶": "R", "▼": "D", "◀": "L", "▲": "U" };
const CW = 1, CH = 2;                                   // a character cell is twice as tall as it is wide

const canvas = document.getElementById("hero-gl");
const hero = document.getElementById("hero");
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

function fail() { hero.classList.add("no-gl"); }

try { init(); } catch (e) { console.warn("hero: falling back to the static banner", e); fail(); }

function init() {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  if (!renderer.getContext()) throw new Error("no WebGL");
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 400);
  camera.position.set(0, 0, 90);
  const group = new THREE.Group();
  scene.add(group);

  const rows = DIAGRAM.length, cols = Math.max(...DIAGRAM.map((l) => [...l].length));
  const cell = (r, c) => new THREE.Vector3((c - (cols - 1) / 2) * CW, -(r - (rows - 1) / 2) * CH, 0);
  const at = (r, c) => (r >= 0 && r < rows ? [...DIAGRAM[r]][c] || " " : " ");

  // ── glyph atlas: every character drawn once into a texture ────────────────
  const chars = [...new Set(DIAGRAM.join("").replace(/ /g, ""))];
  const SCATTER = "+-|<>v^/\\#*=~:.";                   // extra drifting characters that never land
  const all = [...new Set([...chars, ...SCATTER])];
  const TILE = 64, ACOLS = Math.ceil(Math.sqrt(all.length));
  const atlas = document.createElement("canvas");
  atlas.width = atlas.height = TILE * ACOLS;
  const g2 = atlas.getContext("2d");
  g2.fillStyle = "#fff";
  g2.textAlign = "center";
  g2.textBaseline = "middle";
  g2.font = `500 ${TILE * 0.82}px ui-monospace, "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace`;
  all.forEach((ch, i) => g2.fillText(ch, (i % ACOLS + 0.5) * TILE, (Math.floor(i / ACOLS) + 0.53) * TILE));
  const tex = new THREE.CanvasTexture(atlas);
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.anisotropy = 4;

  // ── points: one per character, flying from chaos to its cell ──────────────
  const start = [], target = [], glyph = [], rand = [], isLine = [], lands = [];
  const rnd = (a, b) => a + Math.random() * (b - a);
  const scatterPos = () => new THREE.Vector3(rnd(-70, 70), rnd(-40, 40), rnd(-60, 30));
  for (let r = 0; r < rows; r++) {
    [...DIAGRAM[r]].forEach((ch, c) => {
      if (ch === " ") return;
      start.push(...scatterPos().toArray());
      target.push(...cell(r, c).toArray());
      glyph.push(all.indexOf(ch));
      rand.push(Math.random());
      isLine.push(ARMS[ch] || HEADS[ch] ? 1 : 0);
      lands.push(1);
    });
  }
  for (let i = 0; i < 260; i++) {                        // background dust: drifts, then fades away
    const p = scatterPos().multiplyScalar(1.3);
    start.push(...p.toArray());
    target.push(p.x * 1.6, p.y * 1.6, p.z - 40);
    glyph.push(all.indexOf(SCATTER[i % SCATTER.length]));
    rand.push(Math.random());
    isLine.push(0);
    lands.push(0);
  }
  const pg = new THREE.BufferGeometry();
  pg.setAttribute("position", new THREE.Float32BufferAttribute(start, 3));
  pg.setAttribute("aTarget", new THREE.Float32BufferAttribute(target, 3));
  pg.setAttribute("aGlyph", new THREE.Float32BufferAttribute(glyph, 1));
  pg.setAttribute("aRand", new THREE.Float32BufferAttribute(rand, 1));
  pg.setAttribute("aLine", new THREE.Float32BufferAttribute(isLine, 1));
  pg.setAttribute("aLands", new THREE.Float32BufferAttribute(lands, 1));
  const uniforms = {
    uProgress: { value: 0 }, uDraw: { value: 0 }, uTime: { value: 0 }, uPx: { value: 1 },
    uAtlas: { value: tex }, uCols: { value: ACOLS },
    uCold: { value: new THREE.Color("#7d8cff") }, uWarm: { value: new THREE.Color("#e6edf3") },
  };
  const points = new THREE.Points(pg, new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */`
      attribute vec3 aTarget; attribute float aGlyph, aRand, aLine, aLands;
      uniform float uProgress, uDraw, uTime, uPx;
      varying float vGlyph, vAlpha, vT;
      void main() {
        float t = smoothstep(0.0, 1.0, clamp(uProgress * 1.5 - aRand * 0.5, 0.0, 1.0));
        vec3 p = mix(position, aTarget, t);
        float drift = 1.0 - t * aLands;
        p += drift * vec3(sin(uTime * .35 + aRand * 40.), cos(uTime * .3 + aRand * 31.), sin(uTime * .25 + aRand * 23.)) * 1.6;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = 2.0 * uPx / -mv.z;
        vGlyph = aGlyph; vT = t * aLands;
        float dust = aLands > .5 ? 1.0 : (1.0 - uProgress) * .55;
        vAlpha = dust * mix(.55, 1.0, vT) * (1.0 - aLine * smoothstep(.15, .7, uDraw));
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uAtlas; uniform float uCols; uniform vec3 uCold, uWarm;
      varying float vGlyph, vAlpha, vT;
      void main() {
        vec2 pc = gl_PointCoord;
        float col = mod(vGlyph, uCols), row = floor(vGlyph / uCols);
        float a = texture2D(uAtlas, vec2((col + pc.x) / uCols, 1.0 - (row + pc.y) / uCols)).a;
        gl_FragColor = vec4(mix(uCold, uWarm, vT), a * vAlpha);
        if (gl_FragColor.a < .01) discard;
      }`,
  }));
  group.add(points);

  // ── drawn lines: each arm of each box character becomes a thin quad ──────
  const quad = [], order = [];
  const W = 0.13;
  const addSeg = (a, b, o) => {
    const d = new THREE.Vector3().subVectors(b, a).normalize(), n = new THREE.Vector3(-d.y, d.x, 0).multiplyScalar(W);
    const e = d.clone().multiplyScalar(W);                // overlap the ends so joins are seamless
    const a2 = a.clone().sub(e), b2 = b.clone().add(e);
    const v = [a2.clone().add(n), a2.clone().sub(n), b2.clone().add(n), b2.clone().sub(n)];
    for (const i of [0, 1, 2, 2, 1, 3]) { quad.push(...v[i].toArray()); order.push(o); }
  };
  const addTri = (p1, p2, p3, o) => { for (const p of [p1, p2, p3]) { quad.push(...p.toArray()); order.push(o); } };
  const DIR = { L: [-1, 0], R: [1, 0], U: [0, 1], D: [0, -1] };
  for (let r = 0; r < rows; r++) {
    [...DIAGRAM[r]].forEach((ch, c) => {
      const o = c / cols * 0.75 + r / rows * 0.25;      // draw sweeps left to right, a little top to bottom
      const p = cell(r, c);
      for (const a of ARMS[ch] || "") {
        const [dx, dy] = DIR[a];
        addSeg(p, p.clone().add(new THREE.Vector3(dx * CW / 2, dy * CH / 2, 0)), o);
      }
      if (HEADS[ch]) {
        const [dx, dy] = DIR[HEADS[ch]];
        const tip = p.clone().add(new THREE.Vector3(dx * CW / 2, dy * CH / 2, 0));
        const back = p.clone().add(new THREE.Vector3(-dx * CW / 2, -dy * CH / 2, 0));
        const base = tip.clone().add(new THREE.Vector3(-dx * 0.9, -dy * 0.9, 0));
        const side = new THREE.Vector3(-dy * 0.45, dx * 0.45, 0);
        addSeg(back, base, o);
        addTri(tip, base.clone().add(side), base.clone().sub(side), o + 0.02);
      }
    });
  }
  const lg = new THREE.BufferGeometry();
  lg.setAttribute("position", new THREE.Float32BufferAttribute(quad, 3));
  lg.setAttribute("aOrder", new THREE.Float32BufferAttribute(order, 1));
  const lineMat = new THREE.ShaderMaterial({
    uniforms: { uDraw: uniforms.uDraw, uA: { value: new THREE.Color("#58a6ff") }, uB: { value: new THREE.Color("#bc8cff") } },
    transparent: true, depthWrite: false,
    vertexShader: `attribute float aOrder; varying float vO; varying float vX;
      void main() { vO = aOrder; vX = position.x; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform float uDraw; uniform vec3 uA, uB; varying float vO; varying float vX;
      void main() { float on = smoothstep(vO - .02, vO, uDraw * 1.08 - .04);
        if (on < .01) discard; gl_FragColor = vec4(mix(uA, uB, clamp((vX + 32.) / 64., 0., 1.)), on); }`,
  });
  group.add(new THREE.Mesh(lg, lineMat));

  // ── box fills, tinted like --color, fading in last ─────────────────────────
  const HUES = ["#1f6feb", "#2ea043", "#8957e5", "#1f6feb", "#2ea043", "#8957e5"];
  const fills = [];
  let k = 0;
  for (let r = 0; r < rows; r++) {
    [...DIAGRAM[r]].forEach((ch, c) => {
      if (ch !== "┌") return;
      let c2 = c + 1;
      while (c2 < cols && at(r, c2) !== "┐") c2++;
      let r2 = r + 1;
      while (r2 < rows && at(r2, c) !== "└") r2++;
      if (c2 >= cols || r2 >= rows) return;
      const a = cell(r, c), b = cell(r2, c2);
      const m = new THREE.Mesh(new THREE.PlaneGeometry(b.x - a.x, a.y - b.y),
        new THREE.MeshBasicMaterial({ color: HUES[k++ % HUES.length], transparent: true, opacity: 0, depthWrite: false }));
      m.position.set((a.x + b.x) / 2, (a.y + b.y) / 2, -0.3);
      fills.push(m);
      group.add(m);
    });
  }

  // ── layout, scroll, pointer, loop ─────────────────────────────────────────
  let wide = true;
  function resize() {
    const w = hero.clientWidth, h = hero.clientHeight;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    wide = w > 900;
    // fit the diagram's width into the part of the screen the copy leaves free
    const visibleW = wide ? 0.54 : 0.94;
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const needH = (cols * CW / visibleW) / camera.aspect;
    camera.position.z = Math.max(needH / (2 * Math.tan(halfFov)) * 1.04, rows * CH * 2.2);
    camera.updateProjectionMatrix();
    const viewH = 2 * Math.tan(halfFov) * camera.position.z, viewW = viewH * camera.aspect;
    // wide: to the right of the copy; narrow: in the free space under it, 80% of the way down
    group.position.set(wide ? viewW * 0.2 : 0, wide ? 0 : -viewH * 0.3, 0);
    uniforms.uPx.value = (h * dpr) / (2 * Math.tan(halfFov));
  }
  resize();
  addEventListener("resize", resize);

  const state = { progress: reduce ? 1 : 0, draw: reduce ? 1 : 0 };
  const caption = document.querySelectorAll("#hero-steps li");
  function apply(p) {                                     // p: 0..1 across the pinned scroll
    state.progress = Math.min(p / 0.5, 1);
    state.draw = Math.max(0, Math.min((p - 0.5) / 0.4, 1));
    const step = p < 0.22 ? 0 : p < 0.62 ? 1 : 2;
    caption.forEach((li, i) => li.classList.toggle("on", i === step));
  }
  const gsap = window.gsap, ST = window.ScrollTrigger;
  if (gsap && ST && !reduce) {
    gsap.registerPlugin(ST);
    ST.create({ trigger: hero, start: "top top", end: "+=150%", pin: true, scrub: 0.8,
                onUpdate: (self) => apply(self.progress) });
    apply(0);
  } else {
    apply(1);
  }

  const pointer = { x: 0, y: 0 }, tilt = { x: 0, y: 0 };
  hero.addEventListener("pointermove", (e) => {
    const r = hero.getBoundingClientRect();
    pointer.x = (e.clientX - r.left) / r.width - 0.5;
    pointer.y = (e.clientY - r.top) / r.height - 0.5;
  });

  let visible = true, raf = 0;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) loop(); }).observe(hero);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loop(); });
  const smooth = { p: state.progress, d: state.draw };
  function frame() {
    const t = performance.now() / 1000;
    smooth.p += (state.progress - smooth.p) * 0.12;
    smooth.d += (state.draw - smooth.d) * 0.12;
    uniforms.uTime.value = reduce ? 0 : t;
    uniforms.uProgress.value = smooth.p;
    uniforms.uDraw.value = smooth.d;
    fills.forEach((m, i) => { m.material.opacity = 0.34 * Math.max(0, Math.min((smooth.d - 0.55 - i * 0.04) / 0.3, 1)); });
    if (!reduce) {
      tilt.x += (pointer.y * 0.18 - tilt.x) * 0.05;
      tilt.y += (pointer.x * 0.28 - tilt.y) * 0.05;
      const settle = 1 - smooth.p * 0.6;                  // chaos sways more than the finished drawing
      group.rotation.set(tilt.x * settle + Math.sin(t * 0.3) * 0.04 * (1 - smooth.p), tilt.y * settle, 0);
    }
    renderer.render(scene, camera);
  }
  function loop() {
    cancelAnimationFrame(raf);
    const tick = () => {
      frame();
      if (visible && !document.hidden && !reduce) raf = requestAnimationFrame(tick);
    };
    tick();
  }
  loop();
  hero.classList.add("gl-on");
}
