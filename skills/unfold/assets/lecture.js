/* ---- live lecture mode ----
   Markup (all optional; a note without it still plays, with whole paragraphs as narration):
     <header class="titleblock" data-live>     start in live mode when the page opens
     <k>…</k>, <p class="key">                 written on the board
     <say>…</say>                              one narration sentence; loose text in a paragraph is wrapped
     at="id id" ink="dot|line|box|hl" keep     on a <say>, <k> or board element: where the pointer goes,
                                               what it draws, and whether the mark stays in the note
     \htmlId{id}{…}                            a pointer target inside an equation
     <div class="check predict|ask">           a question on the board; removed when the board is finished */
const LV = {beats: [], secs: [], marks: [], cur: null, pos: 0, run: 0, on: false, ready: false};
const lvStore = "lv:" + location.pathname;
const lvSleep = ms => new Promise(r => setTimeout(r, ms));
const lvCalm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const SVGNS = "http://www.w3.org/2000/svg";

function lvBoot() {
  try {
    const page = document.querySelector("main.page");
    const btn = document.querySelector(".lv-toggle");
    btn.hidden = false;
    btn.addEventListener("click", () => { if (LV.on) lvFinish(); else lvStart(1); });
    lvPrepare();
    let saved = null; try { saved = localStorage.getItem(lvStore); } catch (e) {}
    const at = parseInt(saved, 10) || 1;  // a finished lecture saved its last beat: a section added since then plays next
    if (page.querySelector("[data-live]") && at < LV.beats.length) lvStart(at, true);
    else { lvFinish(); lvFold("read"); }
    let seen = null; try { seen = localStorage.getItem("lv-guide"); } catch (e) {}
    if (page.querySelector("[data-live]") && !seen) lvGuide(true);
  } finally { document.body.classList.add("lv-ready"); }
}

function lvPrepare() {
  if (LV.ready) return;
  LV.ready = true;
  const page = LV.page = document.querySelector("main.page");
  LV.layer = el("div", "lv-ink"); LV.dot = el("div", "lv-dot"); LV.layer.append(LV.dot); page.append(LV.layer);
  LV.ctl = document.querySelector(".lv-ctl"); LV.count = LV.ctl.querySelector(".lv-count");
  LV.say = el("div", "lv-say");
  const isWS = n => n.nodeType === 3 && !n.data.trim();
  const hold = e => e.classList.add("lv-el");

  function paragraph(p, sec, pre) {
    const first = [...p.childNodes].find(x => !isWS(x));
    let run = null;
    [...p.childNodes].forEach(n => {
      const tag = n.nodeType === 1 ? n.tagName : "";
      if (tag === "K" || tag === "SAY" || (n === first && tag === "B")) { run = null; return; }
      if (isWS(n) && !run) return;
      if (!run) { run = document.createElement("say"); p.insertBefore(run, n); }
      run.appendChild(n);
    });
    p.querySelectorAll(":scope > say").forEach(s => { if (!s.textContent.trim()) s.remove(); });
    const hasKey = !!p.querySelector(":scope > k");
    p.classList.add(hasKey ? "lv-haskey" : "lv-narr");
    if (p.querySelector(":scope > say")) p.classList.add("lv-more");
    hold(p);
    let shown = false;
    [...p.children].forEach(c => {
      if (c.tagName !== "K" && c.tagName !== "SAY") return;
      hold(c);
      LV.beats.push({type: c.tagName === "K" ? "board" : "narr", sec, src: c, els: shown ? [c] : [...pre.splice(0), p, c]});
      shown = true;
    });
  }

  [...page.querySelectorAll(":scope > header, :scope > section:not(.sources), :scope > .part")].forEach(sec => {
    LV.secs.push(sec); sec.classList.add("lv-b");
    if (sec.matches(".part")) { sec.classList.add("lv-sec"); LV.beats.push({type: "board", sec, src: sec, els: []}); return; }
    const head = sec.matches("header");
    if (!head) sec.classList.add("lv-sec");
    const kids = head ? [...(sec.querySelector(".abstract") || sec).children].filter(c => !c.matches("h1, .subtitle")) : [...sec.children];
    const pre = [], n0 = LV.beats.length;
    kids.forEach(c => {
      hold(c);
      if (c.matches("h2, h3, .marginnote")) pre.push(c);
      else if (c.matches("details")) { const last = LV.beats[LV.beats.length - 1]; if (LV.beats.length > n0) last.els.push(c); else pre.push(c); }
      else if (c.matches(".check")) LV.beats.push({type: "check", sec, src: c, els: [...pre.splice(0), c]});
      else if (c.matches("p") && !c.matches(".key, .disp") && !c.querySelector(".katex-display")) { c.classList.remove("lv-el"); paragraph(c, sec, pre); }
      else LV.beats.push({type: "board", sec, src: c, els: [...pre.splice(0), c]});
    });
    if (pre.length && LV.beats.length > n0) LV.beats[LV.beats.length - 1].els.push(...pre);
  });

  // the narration of each beat goes under the last block written so far in its section
  let last = null, lastSec = null;
  LV.beats.forEach(b => {
    if (b.sec !== lastSec) { last = null; lastSec = b.sec; }
    b.els.forEach(e => { last = e.matches("k, say") ? e.parentElement : e; });
    b.after = last;
  });

  LV.missing = [];
  LV.beats.forEach(b => (b.src.getAttribute("at") || "").split(/\s+/).forEach(id => { if (id && !document.getElementById(id)) LV.missing.push(id); }));
  if (LV.missing.length) console.warn("live mode: no element with id " + LV.missing.join(", "));

  // fold levels
  const bar = document.querySelector(".foldbar"), names = ["full", "read", "points", "statements"];
  names.filter(l => l !== "points" || page.querySelector("k, p.key")).forEach(l => {
    const b = el("button"); b.type = "button"; b.dataset.l = l;
    b.append(el("kbd", "", String(names.indexOf(l) + 1)), l[0].toUpperCase() + l.slice(1));
    b.addEventListener("click", () => { lvFold(l, true); b.blur(); }); bar.append(b);
  });

  // check questions
  page.querySelectorAll(".check.predict li").forEach(li => li.addEventListener("click", () => {
    li.parentElement.querySelectorAll("li").forEach(x => x.classList.remove("chosen"));
    li.classList.add("chosen"); lvRelayoutSoon();
    if (LV.on) lvIntoView(li.closest(".check"), false, true);
  }));
  page.querySelectorAll(".check.ask").forEach(c => {
    const ta = el("textarea"); ta.placeholder = "Your answer, and one line of reasoning";
    const row = el("div", "row"), conf = el("input"), copy = el("button", "", "Copy for chat");
    conf.type = "number"; conf.min = 0; conf.max = 100; conf.placeholder = "%"; copy.type = "button";
    row.append("Confidence", conf, copy); c.append(ta, row);
    copy.addEventListener("click", async () => {
      const q = plainText(c.querySelector("p")).replace(/\s+/g, " ");
      const msg = "Check question: " + q + "\nMy answer: " + ta.value.trim() + "\nConfidence: " + (conf.value || "?") + "%";
      try { await navigator.clipboard.writeText(msg); copy.textContent = "Copied. Paste it in chat"; }
      catch (e) { ta.value = msg; ta.select(); copy.textContent = "Select all and copy"; }
    });
  });

  // controls
  LV.ctl.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (!b) return;
    b.blur();
    ({restart: () => lvGoto(1, true), back: lvBack, next: lvNext, end: lvFinish})[b.dataset.a]();
  });
  document.addEventListener("click", e => {
    const t = e.target;
    const p = t.closest("p.lv-more"), sec = t.closest(".lv-b"), h = t.closest("h2");
    // unfold in place: any board of a note, and in a lecture every board except the one being written
    if (sec && (h || p) && document.body.classList.contains("lv-folded") && !t.closest("a, summary, button")
        && !(LV.on && sec.classList.contains("lv-cur"))) {
      if (h) sec.classList.toggle("lv-open");
      else if (!sec.classList.contains("lv-open")) p.classList.toggle("fopen");
      lvRelayoutSoon(); return;
    }
    if (!LV.on || t.closest("a, button, summary, input, textarea, select, label, .check, .toc, .preview, .lv-ctl, .foldbar, .lv-guide")) return;
    if (String(window.getSelection())) return;
    lvNext();
  });
  document.addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]"))) return;
    const lv = ["full", "read", "points", "statements"]["1234".indexOf(e.key)];
    if (lv && document.querySelector('.foldbar button[data-l="' + lv + '"]')) return lvFold(lv, true);
    if (e.key === "?") return lvGuide(!document.querySelector(".lv-guide"));
    if (e.key === "Escape" && document.querySelector(".lv-guide")) return lvGuide(false);
    if (!LV.on) return;
    if ([" ", "ArrowRight", "Enter", "PageDown"].includes(e.key)) { e.preventDefault(); lvNext(); }
    else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); lvBack(); }
  });
  window.addEventListener("resize", lvRelayoutSoon);
  page.addEventListener("toggle", lvRelayoutSoon, true);
  if (window.ResizeObserver) new ResizeObserver(lvRelayoutSoon).observe(page);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(lvRelayoutSoon);
}

/* A small card that says how to read the page: on the first visit to a note that opens in a lecture,
   and whenever the reader presses "?". */
function lvGuide(show) {
  const old = document.querySelector(".lv-guide");
  if (old) old.remove();
  if (!show) { try { localStorage.setItem("lv-guide", "1"); } catch (e) {} return; }
  const card = el("div", "lv-guide"); card.setAttribute("role", "dialog"); card.setAttribute("aria-label", "How to read this page");
  card.append(el("b", "", "How to read this page"));
  const ul = el("ul");
  [["Space / → / click", "next step of the lecture; ← goes back"],
   ["1 2 3 4", "fold: Full, Read, Points (key sentences), Statements"],
   ["hover a chip", "see the cited passage in its PDF; click to open it"],
   ["⏭ or ■ Lecture", "show the whole note; ▶ Lecture plays it again"],
   ["?", "show this card again"]].forEach(([k, t]) => {
    const li = el("li"); li.append(el("kbd", "", k), " " + t); ul.append(li);
  });
  const ok = el("button", "", "Got it"); ok.type = "button";
  ok.addEventListener("click", () => lvGuide(false));
  card.append(ul, ok); document.body.append(card); ok.focus({preventScroll: true});
}

let lvOpened = [];
function lvFold(level, byUser) {
  const body = document.body;
  if (byUser) LV.userFold = true;
  body.dataset.fold = level;
  body.classList.toggle("lv-folded", level === "points" || level === "statements");
  body.classList.toggle("lv-st", level === "statements");
  lvOpened.forEach(d => (d.open = false)); lvOpened = [];
  if (level === "full") LV.page.querySelectorAll("details:not([open])").forEach(d => { d.open = true; lvOpened.push(d); });
  LV.page.querySelectorAll(".lv-open, .fopen").forEach(e => e.classList.remove("lv-open", "fopen"));
  document.querySelectorAll(".foldbar button").forEach(b => b.classList.toggle("on", b.dataset.l === level));
  if (LV.on && LV.pos) lvVoice(LV.beats[LV.pos - 1]);
  lvRelayoutSoon();
}
/* The beat being played is always readable: in its own place when the fold level keeps it,
   otherwise in the narration block under the last block written. */
function lvVoice(b, anim) {
  LV.say.replaceChildren(); LV.say.remove();
  if (b.type === "check" || b.src.getClientRects().length) return;
  const c = b.src.cloneNode(true);
  c.querySelectorAll("[id]").forEach(x => x.removeAttribute("id")); c.removeAttribute("id");
  if (c.matches("k, say")) LV.say.append(...c.childNodes); else LV.say.append(c);
  if (b.after) b.after.after(LV.say); else (b.sec.querySelector(".abstract") || b.sec).prepend(LV.say);
  if (anim) { LV.say.classList.remove("lv-fade"); void LV.say.offsetWidth; LV.say.classList.add("lv-fade"); }
}

/* ---- geometry: where a target sits, in the ink layer's coordinates ---- */
function lvLeaves(root) {
  let a = null;
  const add = e => {
    if (e.closest(".tag, .katex-mathml") || e.matches(".strut, .pstrut, .vlist-s")) return;
    const leaf = (!e.children.length && e.textContent.replace(/[\s​]/g, "")) || e.tagName.toLowerCase() === "svg" || e.matches(".frac-line, .overline-line, .underline-line");
    if (!leaf) return;
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) return;
    a = a ? {l: Math.min(a.l, r.left), t: Math.min(a.t, r.top), r: Math.max(a.r, r.right), b: Math.max(a.b, r.bottom)}
          : {l: r.left, t: r.top, r: r.right, b: r.bottom};
  };
  add(root); root.querySelectorAll("*").forEach(add);
  return a ? [{left: a.l, top: a.t, width: a.r - a.l, height: a.b - a.t}] : [];
}
function lvRects(t) {
  if (!t || !t.isConnected) return [];
  let rs;
  const disp = !t.closest(".katex") && t.matches("p, span, .katex-display") && t.querySelector(".katex-display .katex-html");
  if (t.closest(".katex")) rs = lvLeaves(t);
  else if (disp) rs = lvLeaves(disp);
  else if (getComputedStyle(t).display === "inline") rs = [...t.getClientRects()];
  else rs = [t.getBoundingClientRect()];
  const L = LV.layer.getBoundingClientRect();
  return rs.filter(r => r.width > 0 && r.height > 0).map(r => ({x: r.left - L.left, y: r.top - L.top, w: r.width, h: r.height}));
}

/* ---- ink ---- */
function lvInk(ink, r) {
  let e;
  if (ink === "box") {
    const p = 5, w = r.w + 2 * p, h = r.h + 2 * p;
    e = document.createElementNS(SVGNS, "svg"); e.setAttribute("class", "lv-mark lv-box");
    e.setAttribute("width", w); e.setAttribute("height", h);
    e.style.left = (r.x - p) + "px"; e.style.top = (r.y - p) + "px";
    const rc = document.createElementNS(SVGNS, "rect");
    Object.entries({x: 1, y: 1, width: w - 2, height: h - 2, rx: 4, pathLength: 1}).forEach(([k, v]) => rc.setAttribute(k, v));
    e.append(rc);
    return e;
  }
  e = el("div", "lv-mark lv-" + (ink === "dot" ? "spot" : ink));
  const g = ink === "line" ? [r.x, r.y + r.h + 1, r.w, null] : ink === "hl" ? [r.x - 2, r.y, r.w + 4, r.h] : [r.x - 4, r.y - 3, r.w + 8, r.h + 6];
  e.style.left = g[0] + "px"; e.style.top = g[1] + "px"; e.style.width = g[2] + "px";
  if (g[3] !== null) e.style.height = g[3] + "px";
  return e;
}
function lvStatic(m) {  // draw a mark in its final state
  m.els.forEach(e => e.remove()); m.els = [];
  m.targets.forEach(t => lvRects(t).forEach(r => {
    const e = lvInk(m.ink, r); if (m.keep) e.classList.add("kept");
    LV.layer.append(e); m.els.push(e);
  }));
}
function lvMove(x, y, ms) {
  LV.dot.style.transitionDuration = ms + "ms, .3s";
  LV.dot.style.transform = `translate(${x}px, ${y}px)`;
  return lvSleep(ms);
}
async function lvPoint(m, tok) {  // the pointer travels to each target and draws
  m.busy = true;
  const live = () => tok === LV.run;
  LV.dot.style.opacity = 1;
  outer: for (const t of m.targets) for (const r of lvRects(t)) {
    const start = m.ink === "box" ? [r.x - 5, r.y - 5] : m.ink === "line" ? [r.x, r.y + r.h + 2] : m.ink === "hl" ? [r.x, r.y + r.h / 2] : [r.x + r.w / 2, r.y + r.h + 5];
    await lvMove(start[0], start[1], 420);
    if (!live()) break outer;
    const e = lvInk(m.ink, r); LV.layer.append(e); m.els.push(e);
    const d = m.ink === "dot" ? 280 : Math.round(Math.min(950, 360 + (m.ink === "box" ? 2 * (r.w + r.h) : r.w) * 1.5));
    const opt = {duration: d, easing: "ease-in-out"};
    if (m.ink === "box") {
      e.firstChild.animate([{strokeDashoffset: 1}, {strokeDashoffset: 0}], opt);
      const x0 = r.x - 5, y0 = r.y - 5, x1 = r.x + r.w + 5, y1 = r.y + r.h + 5, per = 2 * (r.w + r.h + 20);
      const tr = (x, y) => `translate(${x}px, ${y}px)`;
      LV.dot.animate([{transform: tr(x0, y0), offset: 0}, {transform: tr(x1, y0), offset: (r.w + 10) / per},
        {transform: tr(x1, y1), offset: .5}, {transform: tr(x0, y1), offset: .5 + (r.w + 10) / per}, {transform: tr(x0, y0), offset: 1}], opt);
    } else if (m.ink === "dot") e.animate([{opacity: 0}, {opacity: 1}], opt);
    else {
      e.animate([{transform: "scaleX(0)"}, {transform: "scaleX(1)"}], opt);
      lvMove(r.x + r.w, start[1], d);
    }
    await lvSleep(d + 80);
    if (!live()) break outer;
  }
  m.busy = false;
  if (m.keep) lvStatic(m);
  else if (!live()) { m.els.forEach(e => e.remove()); m.els = []; }
}
function lvClearCur() {
  const m = LV.cur; LV.cur = null;
  if (!m || m.keep) return;
  const els = m.els; m.els = [];
  els.forEach(e => e.classList.add("out"));
  setTimeout(() => els.forEach(e => e.remove()), 320);
}
let lvPending = false;
function lvRelayoutSoon() {
  if (lvPending || !LV.ready) return;
  lvPending = true;
  requestAnimationFrame(() => {
    lvPending = false;
    LV.marks.forEach(m => { if (!m.busy) lvStatic(m); });
    if (LV.cur && !LV.cur.busy && !LV.cur.keep) lvStatic(LV.cur);
  });
}

/* ---- the lecture ---- */
function lvIntoView(e, top, smooth) {
  const rs = e.closest(".katex") ? lvLeaves(e) : [e.getBoundingClientRect()];
  if (!rs.length || !rs[0].height) return;
  const r = rs[0], lo = 64, hi = window.innerHeight - 70;
  let dy = 0;
  if (top) dy = r.top - 26;
  else if (r.top + r.height > hi) dy = Math.min(r.top + r.height - hi, r.top - lo);
  else if (r.top < lo) dy = r.top - lo;
  if (Math.abs(dy) > 2) window.scrollBy({top: dy, behavior: smooth && !lvCalm ? "smooth" : "auto"});
}
function lvApply(i, anim, cur) {  // cur: this beat is the one on screen (the last one applied)
  const b = LV.beats[i], prev = LV.beats[i - 1], tok = ++LV.run;
  lvClearCur();
  if (prev && prev.sec !== b.sec) prev.sec.classList.remove("lv-cur");
  const fresh = !b.sec.classList.contains("lv-started");
  b.sec.classList.add("lv-started", "lv-cur");
  b.els.forEach(e => {
    e.classList.add("lv-shown");
    if (anim && !lvCalm) { e.classList.remove("lv-in"); void e.offsetWidth; e.classList.add("lv-in"); }
  });
  if (cur) lvVoice(b, anim);
  LV.count.textContent = (i + 1) + " / " + LV.beats.length;
  const at = b.src.getAttribute("at"), ink = b.src.getAttribute("ink");
  let m = null;
  if (at || ink) {
    m = {ink: ink || "dot", keep: b.src.hasAttribute("keep"), els: [],
         targets: at ? at.trim().split(/\s+/).map(id => document.getElementById(id)).filter(Boolean) : [b.src]};
    if (m.keep) LV.marks.push(m);
  }
  if (!anim) { if (m && m.keep) lvStatic(m); return; }
  LV.cur = m;
  if (m && !lvCalm) m.busy = true;
  const head = fresh && b.sec.matches("section") && b.sec.querySelector(":scope > h2");
  if (head) lvIntoView(head, true, true);
  else if (LV.say.isConnected) lvIntoView(LV.say, false, true);
  else if (b.type === "narr") lvIntoView(b.src, false, true);
  else if (b.els.length) lvIntoView(b.els[b.els.length - 1].matches("details") ? b.src : b.els[b.els.length - 1], false, true);
  if (m) {
    if (lvCalm) lvStatic(m);
    else setTimeout(() => { if (tok === LV.run) lvPoint(m, tok); else { m.busy = false; if (m.keep) lvStatic(m); } }, b.type === "narr" ? (head ? 500 : 150) : 620);
  } else LV.dot.style.opacity = 0;
}
function lvReset() {
  LV.run++;
  LV.marks.concat(LV.cur ? [LV.cur] : []).forEach(m => m.els.forEach(e => e.remove()));
  LV.marks = []; LV.cur = null; LV.dot.style.opacity = 0; LV.say.remove();
  LV.secs.forEach(s => s.classList.remove("lv-started", "lv-cur", "lv-open"));
  LV.page.querySelectorAll(".lv-shown, .fopen, .lv-in").forEach(e => e.classList.remove("lv-shown", "fopen", "lv-in"));
}
function lvSave(v) { try { localStorage.setItem(lvStore, v); } catch (e) {} }
function lvGoto(n, anim) {
  lvReset();
  n = Math.max(1, Math.min(n, LV.beats.length));
  for (let i = 0; i < n; i++) lvApply(i, anim && i === n - 1, i === n - 1);
  LV.pos = n; lvSave(n); lvRelayoutSoon();
  if (!anim) { const b = LV.beats[n - 1]; const e = b.els[b.els.length - 1] || b.src; requestAnimationFrame(() => lvIntoView(e, false, false)); }
}
function lvStart(n, quiet) {
  lvPrepare();
  LV.on = true;
  document.body.classList.add("lv-on"); document.body.classList.remove("nav-open");
  document.querySelector(".lv-toggle").textContent = "■ Lecture";
  LV.ctl.hidden = false;
  if (!LV.userFold) lvFold(LV.page.querySelector("k, p.key") ? "points" : "read");  // no key sentences: no Points level
  lvGoto(n, !quiet);
  if (n === 1) window.scrollTo(0, 0);
}
function lvNext() {
  if (document.querySelector(".lv-guide")) lvGuide(false);  // moving on dismisses the guide
  if (!LV.on) return;
  if (LV.pos >= LV.beats.length) return lvFinish();
  lvApply(LV.pos, true, true); LV.pos++; lvSave(LV.pos);
}
function lvBack() {
  if (document.querySelector(".lv-guide")) lvGuide(false);
  if (LV.on && LV.pos > 1) lvGoto(LV.pos - 1, true);
}
function lvFinish() {  // the whole note, every board finished and folded
  lvPrepare();
  const was = LV.on;
  lvReset();
  for (let i = 0; i < LV.beats.length; i++) lvApply(i, false, false);
  LV.secs.forEach(s => { s.classList.remove("lv-cur"); s.classList.add("lv-started"); });
  LV.on = false; LV.pos = LV.beats.length;
  document.body.classList.remove("lv-on");
  document.querySelector(".lv-toggle").textContent = "▶ Lecture";
  LV.ctl.hidden = true; LV.dot.style.opacity = 0;
  if (was) { lvSave(LV.beats.length); if (!LV.userFold) lvFold("read"); }
  lvRelayoutSoon();
}

