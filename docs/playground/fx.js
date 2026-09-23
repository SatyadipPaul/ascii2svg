// Motion for the playground, with GSAP: an intro, scroll reveals, magnetic buttons, and responses
// to what the tool does (a render lands, a fix is applied, something is copied). The tool itself
// never waits on any of this; without GSAP, or with reduced motion, everything is simply there.
const gsap = window.gsap, ST = window.ScrollTrigger;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];

// Spotlight tiles and the nav work without GSAP (CSS variables and a class).
$$(".spot").forEach((el) => el.addEventListener("pointermove", (e) => {
  const r = el.getBoundingClientRect();
  el.style.setProperty("--mx", `${e.clientX - r.left}px`);
  el.style.setProperty("--my", `${e.clientY - r.top}px`);
}));
const bar = $("#topbar");
const onScroll = () => bar && bar.classList.toggle("scrolled", scrollY > 24);
addEventListener("scroll", onScroll, { passive: true });
onScroll();

if (gsap) gsap.config({ nullTargetWarn: false });   // responses fire on whatever the render produced
if (gsap && !reduce) {
  if (ST) gsap.registerPlugin(ST);
  document.documentElement.classList.add("fx");

  // ── intro: the headline rises word by word, then the rest follows ────────
  $$(".hero-title .line").forEach((line) => {
    line.innerHTML = line.textContent.split(" ").map((w) => `<span class="w"><span>${w}</span></span>`).join(" ");
  });
  gsap.timeline({ defaults: { ease: "power3.out" } })
    .from(".topbar", { y: -30, opacity: 0, duration: 0.6 })
    .from(".hero-title .w > span", { yPercent: 115, duration: 0.9, stagger: 0.06 }, "-=0.3")
    .from([".eyebrow", ".hero-sub", ".hero-cta > *", ".hero-stats li", "#hero-steps"],
          { y: 18, opacity: 0, duration: 0.6, stagger: 0.07 }, "-=0.55")
    .from(".scroll-cue", { opacity: 0, duration: 0.6 }, "-=0.2");

  // count the stats up
  $$(".hero-stats b[data-to]").forEach((b) => {
    const to = +b.dataset.to, o = { v: 0 };
    gsap.to(o, { v: to, duration: 1.4, delay: 0.9, ease: "power2.out",
                 onUpdate: () => { b.textContent = Math.round(o.v) + (b.dataset.suffix || ""); } });
  });

  // ── scroll: sections and cards rise into place ──────────────────────────
  if (ST) {
    $$("[data-reveal]").forEach((el) => gsap.from(el, {
      y: 40, opacity: 0, duration: 0.9, ease: "power3.out",
      scrollTrigger: { trigger: el, start: "top 88%", once: true },
    }));
    $$("[data-stagger]").forEach((wrap) => gsap.from(wrap.children, {
      y: 30, opacity: 0, duration: 0.7, ease: "power3.out", stagger: 0.08,
      scrollTrigger: { trigger: wrap, start: "top 85%", once: true },
    }));
    gsap.from("#tool .panel", {
      y: 50, opacity: 0, rotateX: 6, transformOrigin: "50% 0%", duration: 1, ease: "power3.out", stagger: 0.12,
      scrollTrigger: { trigger: "#tool .grid", start: "top 90%", once: true },
    });
    gsap.to(".scroll-cue", { opacity: 0, scrollTrigger: { trigger: "#hero", start: "top top", end: "+=200", scrub: true } });
  }

  // ── magnetic buttons ─────────────────────────────────────────────────────
  $$(".magnetic").forEach((el) => {
    const x = gsap.quickTo(el, "x", { duration: 0.4, ease: "power3" });
    const y = gsap.quickTo(el, "y", { duration: 0.4, ease: "power3" });
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      x((e.clientX - r.left - r.width / 2) * 0.28);
      y((e.clientY - r.top - r.height / 2) * 0.35);
    });
    el.addEventListener("pointerleave", () => { x(0); y(0); });
  });

  // every button gives a little under the finger
  document.addEventListener("pointerdown", (e) => {
    const b = e.target.closest("button, .btn");
    if (b && !b.disabled) gsap.fromTo(b, { scale: 0.95 }, { scale: 1, duration: 0.5, ease: "elastic.out(1, 0.45)" });
  });

  // an option changes: its control nods
  $$(".toolbar select, .toolbar input").forEach((el) => el.addEventListener("change", () => {
    gsap.fromTo(el.closest("label"), { y: -3 }, { y: 0, duration: 0.5, ease: "bounce.out" });
  }));
}

// ── responses to the tool (from the page script's events) ─────────────────────
addEventListener("a2s:ready", () => {
  const o = $("#overlay");
  if (!o) return;
  if (gsap && !reduce) gsap.to(o, { opacity: 0, duration: 0.4, onComplete: () => { o.style.display = "none"; } });
});

let lastMs = 0;
addEventListener("a2s:rendered", ({ detail }) => {
  if (!gsap || reduce) return;
  const media = $("#preview img, #preview iframe");
  if (media) gsap.fromTo(media, { opacity: 0, y: 10, scale: 0.985 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power3.out" });
  const pill = $("#report .pill");
  if (pill) gsap.from(pill, { scale: 0.3, opacity: 0, duration: 0.6, ease: "back.out(3)" });
  if ($("#report li")) gsap.from("#report li", { x: -8, opacity: 0, duration: 0.35, stagger: 0.03, ease: "power2.out" });
  const fix = $("#fix-btn");
  if (fix) gsap.from(fix, { scale: 0.6, opacity: 0, duration: 0.6, ease: "back.out(2.5)", delay: 0.15 });
  if (detail && detail.ms != null) {                    // the timing counts to its new value
    const t = $("#timing"), o = { v: lastMs };
    gsap.to(o, { v: detail.ms, duration: 0.6, ease: "power2.out",
                 onUpdate: () => { t.textContent = `rendered in ${Math.round(o.v)} ms`; } });
    lastMs = detail.ms;
  }
});

addEventListener("a2s:fixed", ({ detail }) => {
  const src = $("#src");
  if (gsap && !reduce) {
    gsap.fromTo(src, { boxShadow: "inset 0 0 0 2px rgba(63,185,80,.9)" },
                { boxShadow: "inset 0 0 0 2px rgba(63,185,80,0)", duration: 1.4, ease: "power2.out" });
    burst(detail && detail.from, detail && detail.count);
  }
});

function burst(from, count = 6) {
  // a small spray of box characters from the button that fixed them
  const r = from ? from.getBoundingClientRect() : { left: innerWidth / 2, top: innerHeight / 2, width: 0, height: 0 };
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const glyphs = "┌┐└┘─│├┤┬┴▶▼";
  for (let i = 0; i < Math.min(28, 10 + count * 3); i++) {
    const s = document.createElement("span");
    s.className = "spark";
    s.textContent = glyphs[i % glyphs.length];
    s.style.left = cx + "px";
    s.style.top = cy + "px";
    document.body.appendChild(s);
    const a = Math.random() * Math.PI * 2, d = 50 + Math.random() * 90;
    gsap.to(s, { x: Math.cos(a) * d, y: Math.sin(a) * d - 30, rotation: (Math.random() - 0.5) * 240, opacity: 0,
                 duration: 0.9 + Math.random() * 0.5, ease: "power3.out", onComplete: () => s.remove() });
  }
}

addEventListener("a2s:toast", () => {
  if (gsap && !reduce) gsap.fromTo("#toast", { y: 16 }, { y: 0, duration: 0.45, ease: "back.out(2)" });
});

addEventListener("a2s:copied", ({ detail }) => {
  const b = detail && detail.button;
  if (!b) return;
  const label = b.dataset.label || b.textContent;
  b.dataset.label = label;
  b.textContent = "Copied ✓";
  b.classList.add("done");
  if (gsap && !reduce) gsap.fromTo(b, { scale: 0.9 }, { scale: 1, duration: 0.5, ease: "back.out(3)" });
  setTimeout(() => { b.textContent = label; b.classList.remove("done"); }, 1400);
});
