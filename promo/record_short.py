"""Record a ~27-second promo of the unfold demo as MP4 with sound, vertical 3:4 (1080x1440) and landscape (1920x1080).

It opens on a chat (chat.html): three PDFs dragged in, "help me learn this", Claude works through four steps,
and the cursor opens the note it returns. Then the title card, the demo, and the end card.

  python record_short.py [--format vertical|landscape|both] [--lang en|zh]

Needs playwright (drives the installed Chrome; no browser download), pillow, numpy, and ffmpeg on PATH.

1. Capture: plays the demo in headless Chrome at high resolution and grabs every painted frame through
   the screencast, logging where the action is (camera targets) and when things happen (sound cues).
2. Compose: an "unfold" title card opens; a virtual camera then pushes in on the board and the citation
   and pulls back for the fold levels; captions animate in where the camera leaves room; an end card closes.
3. Sound: soft whooshes, clicks, pops and a chime, plus a music bed (pad, plucked arpeggio, then kick and bass at
   96 BPM, timed so the title and the end card land on bar lines), all synthesized with numpy."""
import argparse, asyncio, base64, io, math, os, re, subprocess, time, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(os.path.dirname(HERE), "examples", "quantum-geometry", "quantum-geometry.html")
OUT = os.path.join(HERE, "out")
CHAT_PAGE = os.path.join(HERE, "chat.html")
FPS, SR = 30, 48000
CHAT = 6.3           # the chat scene: drop PDFs, ask, Claude works, open the note
INTRO = 2.5          # then the title card, then the note capture starts
CARD_CT = 16.5       # capture time at which the end card fades in (the last fold level holds ~2.8 s)
P0 = CHAT + INTRO    # video time of capture time 0
TOTAL = P0 + CARD_CT + 2.4
DOWN = CHAT + 0.42   # the music's first downbeat: the title opens
URL = "github.com/HarryLuoo/unfold"
FONTS = r"C:\Windows\Fonts"
INK, MUTED, PAPER, LASER = (22, 22, 22), (95, 95, 95), (255, 255, 255), (224, 50, 45)

# captions in capture time: (start, end, text, where)
# every word the video adds, per language (the note itself stays as written)
TEXT = {
    "en": {"captions": ["Study notes that play like a lecture", "Hover a citation: the exact PDF passage",
                        "Fold to 4 depths, keys 1\u20134"],
           "tagline": "Notes that cite, fold and lecture", "end": "Single offline HTML \u00b7 Built with Claude Code"},
    "zh": {"captions": ["像讲课一样播放的\n学习笔记", "悬停引用\n直达 PDF 原文段落", "四级折叠\n按 1\u20134 切换"],
           "tagline": "会引用、能折叠、可讲课的笔记", "end": "单个离线 HTML \u00b7 用 Claude Code 构建"},
}
LANG = "en"
L = lambda key: TEXT[LANG][key]
CAPTION_TIMES = [(0.0, 5.4, "high", "left"), (5.7, 10.3, "high", "right"), (10.4, CARD_CT, "low", "right")]

PAGE_JS = """
localStorage.setItem('lv-guide', '1');
localStorage.setItem('lv:' + location.pathname, '10');
addEventListener('DOMContentLoaded', () => {
  const st = document.createElement('style');  // the page's floating buttons stay out of the promo
  st.textContent = '.theme-toggle,.nav-toggle,.lv-toggle,.foldbar,.lv-ctl{display:none!important} main.page{padding-top:28px!important}';
  document.head.append(st);
  const c = document.createElement('div');     // headless Chrome draws no cursor
  c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:99999;pointer-events:none;display:none;'
    + 'background:no-repeat center/contain url("data:image/svg+xml,' + encodeURIComponent(
      '<svg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 16 16\\'><path d=\\'M1 1l5 14 2-6 6-2z\\' fill=\\'#161616\\' stroke=\\'#fff\\' stroke-width=\\'1.2\\'/></svg>') + '")';
  document.body.append(c);
  addEventListener('mousemove', e => { c.style.display = 'block'; c.style.transform = `translate(${e.clientX - 2}px, ${e.clientY - 2}px)`; });
});
window.__rect = sels => {  // union of the visible boxes of some selectors, in CSS px
  let a = null;
  for (const s of sels) for (const e of document.querySelectorAll(s)) {
    const r = e.getBoundingClientRect(); if (!r.width || !r.height || !e.isConnected) continue;
    a = a ? [Math.min(a[0], r.left), Math.min(a[1], r.top), Math.max(a[2], r.right), Math.max(a[3], r.bottom)] : [r.left, r.top, r.right, r.bottom];
  }
  return a;
};
"""


# ------------------------------------------------------------------ 1. capture

async def capture(view_w, view_h, scale):
    """Returns frames [(t, Image)], camera targets [(t, rect in device px)], sound cues [(t, kind)]."""
    from playwright.async_api import async_playwright
    frames, marks, cues, t0 = [], [], [], [None]
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True,  # without the flag the screencast sends CSS pixels
                                          args=[f"--force-device-scale-factor={scale}"])
        ctx = await browser.new_context(viewport={"width": view_w, "height": view_h}, device_scale_factor=scale)
        await ctx.add_init_script(PAGE_JS)
        page = await ctx.new_page()
        await page.goto("file:///" + DEMO.replace("\\", "/"))
        await page.wait_for_function("document.body.classList.contains('lv-ready')")
        await page.wait_for_timeout(1500)
        cdp = await ctx.new_cdp_session(page)

        async def on_frame(ev):
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            if t0[0] is not None:
                frames.append((ev["metadata"]["timestamp"] - t0[0], ev["data"]))
        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92,
                                                 "maxWidth": int(view_w * scale), "maxHeight": int(view_h * scale)})
        t0[0] = time.time()
        now = lambda: time.time() - t0[0]
        await page.evaluate("document.body.style.outline = '0px solid transparent'")

        async def at(t):
            d = t - now()
            if d > 0:
                await page.wait_for_timeout(d * 1000)

        async def mark(sels, label):
            r = await page.evaluate(f"window.__rect({sels!r})")
            if r:
                marks.append((now(), label, [v * scale for v in r]))

        await mark(["main.page p", "main.page h1", "main.page .env", "main.page .katex-display"], "column")  # the text column

        async def glide(x, y, ms):
            x0, y0 = await page.evaluate("[window.__cx || innerWidth * 0.75, window.__cy || innerHeight * 0.8]")
            start = time.time()
            while True:
                s = min(1.0, (time.time() - start) * 1000 / ms); e = s * s * (3 - 2 * s)
                await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
                if s >= 1.0:
                    break
            await page.evaluate(f"window.__cx = {x}; window.__cy = {y}")

        eq = ["section .env.def .katex-display .base"]  # the glyphs, not the full-width display box
        # beat 1: the board writes Definition 1.1; the pointer goes to d(theta), then 2 pi, then x^2 + y^2
        for i, t in enumerate((0.5, 1.8, 3.1, 4.4)):
            await at(t); cues.append((now(), "key")); await page.keyboard.press("Space")
            cues.append((now() + (0.05 if i == 0 else 0.18), "write" if i == 0 else "whoosh"))
            await at(t + 0.9); await mark(eq, f"eq{i}"); await mark([".lv-say"], f"say{i}")
        await at(5.5); cues.append((now(), "settle")); await page.evaluate("lvFinish()")
        # beat 2: scroll to the Peotta & Toermae chip and open its preview
        await at(6.0); cues.append((now(), "scroll"))
        await page.evaluate("""setTimeout(() => { const r = document.querySelector('a.cite[data-k="pt-tensor"]').getBoundingClientRect();
            scrollBy({top: r.top - innerHeight * 0.42, behavior: 'smooth'}); }, 0)""")
        await at(6.9)
        await page.evaluate("""new Promise(done => { let y = -1; const f = () => {  // wait for the scroll to settle
            if (Math.abs(scrollY - y) < 1) done(); else { y = scrollY; setTimeout(f, 80); } }; f(); })""")
        r = await page.evaluate("""(() => { const r = document.querySelector('a.cite[data-k="pt-tensor"]').getBoundingClientRect();
            return [r.left + r.width * 0.5, r.top + r.height * 0.55]; })()""")
        cues.append((now(), "glide")); await glide(r[0], r[1], 650)
        cues.append((now(), "pop")); await page.evaluate("show(document.querySelector('a.cite[data-k=\"pt-tensor\"]'))")
        await page.wait_for_timeout(350); await mark(["a.cite[data-k='pt-tensor']", ".preview"], "preview")
        # beat 3: back to the top, fold levels
        await at(10.4); cues.append((now(), "scroll"))
        await page.evaluate("hideSoon(); setTimeout(() => scrollTo({top: 0, behavior: 'smooth'}), 0)")
        await glide(view_w * 0.93, view_h * 0.6, 300)
        for key, t in (("3", 12.4), ("4", 13.0), ("1", 13.7)):
            await at(t); cues.append((now(), "key")); cues.append((now() + 0.04, "fold")); await page.keyboard.press(key)
        await at(CARD_CT + 0.1)
        await cdp.send("Page.stopScreencast")
        await browser.close()
    shots = [(t, Image.open(io.BytesIO(base64.b64decode(d))).convert("RGB")) for t, d in frames]
    print(f"{len(shots)} frames; marks {[(round(t, 1), l) for t, l, _ in marks]}")
    return shots, marks, cues


async def capture_chat(view_w, view_h, scale):
    """The chat scene (chat.html plays itself); returns frames, camera targets and sound cues like capture()."""
    from playwright.async_api import async_playwright
    frames, t0 = [], [None]
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=[f"--force-device-scale-factor={scale}"])
        ctx = await browser.new_context(viewport={"width": view_w, "height": view_h}, device_scale_factor=scale)
        page = await ctx.new_page()
        await page.goto("file:///" + CHAT_PAGE.replace("\\", "/") + f"?lang={LANG}")
        await page.wait_for_timeout(800)
        cdp = await ctx.new_cdp_session(page)

        async def on_frame(ev):
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            frames.append((ev["metadata"]["timestamp"] - t0[0] if t0[0] else -1.0, ev["data"]))
        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92,
                                                 "maxWidth": int(view_w * scale), "maxHeight": int(view_h * scale)})
        await page.wait_for_timeout(300)
        t0[0] = time.time()
        await page.evaluate("window.__play(); 0")
        await page.wait_for_timeout((CHAT + 0.2) * 1000)
        cues = await page.evaluate("window.__cues")
        marks = await page.evaluate("window.__marks")
        await cdp.send("Page.stopScreencast")
        await browser.close()
    shots = [(t, Image.open(io.BytesIO(base64.b64decode(d))).convert("RGB")) for t, d in frames]
    pre = [x for x in shots if x[0] < 0]  # keep only the last frame painted before the scene starts
    shots = ([(0.0, pre[-1][1])] if pre else []) + [x for x in shots if x[0] >= 0]
    marks = [(t, l, [v * scale for v in r]) for t, l, r in marks]
    print(f"chat: {len(shots)} frames; marks {[(round(t, 1), l) for t, l, _ in marks]}")
    return shots, marks, [(t, k) for t, k in cues]


# ------------------------------------------------------------------ 2. compose

def font(name, size, latin=False):
    """Georgia for English; in Chinese the serif roles go to Noto Serif SC (bold or regular)."""
    if LANG == "zh" and name.startswith("georgia") and not latin:
        f = ImageFont.truetype(os.path.join(FONTS, "NotoSerifSC-VF.ttf"), size)
        f.set_variation_by_axes([800 if name == "georgiab.ttf" else 500])
        return f
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def tokens(line):
    """Words with their trailing space; in Chinese each character is a token and Latin runs stay whole."""
    return re.findall(r"[A-Za-z0-9\u2013\-]+\s*|[^\x00-\x7f]\s*|\S+\s*" if LANG == "zh" else r"\S+\s*", line)


def ease(s):
    s = min(1.0, max(0.0, s)); return s * s * (3 - 2 * s)


def camera_keys(marks, W, H):
    """Camera keyframes (ct, cx, cy, zoom): establish, push in on the board, follow it, pull back, push in on
    the citation, pull back for the folds with a slow push. Zoom 1 shows the whole captured page."""
    full = (W / 2, H / 2, 1.0)
    def fit(rect, pad=1.3, zmax=2.3, bias=0.0):
        x0, y0, x1, y1 = rect
        z = min(W / ((x1 - x0) * pad), H / ((y1 - y0) * pad), zmax)
        return ((x0 + x1) / 2, (y0 + y1) / 2 + bias * H / z, max(1.0, z))
    m = {l: r for _, l, r in marks}
    zmax = 1.5 if H > W else 1.6
    k = [(0.0, *full), (0.7, *full)]
    for i, t in enumerate((1.6, 2.9, 4.2, 5.2)):
        e = m.get(f"eq{min(i + 1, 3)}") or m.get("eq0")
        if not e:
            continue
        sy = m.get(f"say{min(i + 1, 3)}")
        z = min(W / ((e[2] - e[0]) * 1.5), zmax) * (1 + 0.03 * i)        # a slow push while the board holds
        cy = (e[1] + (sy[3] if sy else e[3])) / 2                          # equation and narration both in frame
        k.append((t, (e[0] + e[2]) / 2, cy, max(1.0, z)))
    k += [(6.0, *full), (7.2, *full)]
    if "preview" in m:
        cx, cy, z = fit(m["preview"], pad=1.15, zmax=1.5 if H > W else 1.7)
        k += [(8.1, cx, cy, z), (10.3, cx, cy, z * 1.04)]
    k += [(10.9, W / 2, H / 2, 1.0), (CARD_CT, W / 2, H * 0.47, 1.06)]
    return k


def fit(rect, W, H, pad=1.3, zmax=2.3):
    x0, y0, x1, y1 = rect
    z = min(W / ((x1 - x0) * pad), H / ((y1 - y0) * pad), zmax)
    return ((x0 + x1) / 2, (y0 + y1) / 2, max(1.0, z))


def chat_camera_keys(marks, W, H):
    """Hold wide while the PDFs come in, push in on the composer during the typing, ride up with the reply,
    then rush into the note's card as the cursor opens it."""
    m = {l: r for _, l, r in marks}
    full = (W / 2, H / 2, 1.0)
    k = [(0.0, *full), (1.0, *full)]
    if "composer" in m:
        cx, cy, z = fit(m["composer"], W, H, 1.25, 1.5)
        k += [(1.9, cx, cy, z), (2.6, cx, cy, z * 1.03)]
    if "convo" in m:
        k.append((3.3, *fit(m["convo"], W, H, 1.2, 1.3)))
    if "reply" in m:
        k.append((5.3, *fit(m["reply"], W, H, 1.12, 1.4)))
    if "card" in m:
        cx, cy, z = fit(m["card"], W, H, 1.5, 1.9)
        k += [(5.95, cx, cy, z), (CHAT, cx, cy, fit(m["card"], W, H, 1.0, 2.6)[2])]
    return k


def keep_column(cam, marks, W, H, margin):
    """On a narrow (vertical) page, the camera may crop the margins but never the text column."""
    col = next((r for _, l, r in marks if l == "column"), None)
    if not col or W > H:
        return cam
    cx, cy, z = cam
    x0, x1 = max(0, col[0] - margin), min(W, col[2] + margin)
    z = max(1.0, min(z, W / (x1 - x0)))
    half = W / z / 2
    return (min(max(cx, x1 - half), x0 + half), cy, z)


def camera_at(keys, ct):
    if ct <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= ct <= b[0]:
            s = ease((ct - a[0]) / (b[0] - a[0]))
            return tuple(a[i] + (b[i] - a[i]) * s for i in (1, 2, 3))
    return keys[-1][1:]


def shoot(img, cam, out_w, out_h, center=False):
    """Crop the camera's view. With center, the view stays centred on its target even past the top or bottom
    of the captured page; the missing strip is filled with the page's own background."""
    cx, cy, z = cam
    W, H = img.size
    cw, ch = W / z, H / z
    x0 = min(max(cx - cw / 2, 0), W - cw)
    y0 = cy - ch / 2 if center else min(max(cy - ch / 2, 0), H - ch)
    if 0 <= y0 and y0 + ch <= H:
        return img.resize((out_w, out_h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    m = int(max(-y0, y0 + ch - H)) + 8
    canvas = Image.new("RGB", (W, H + 2 * m), img.getpixel((W - 4, 4)))
    canvas.paste(img, (0, m))
    return canvas.resize((out_w, out_h), Image.BICUBIC, box=(x0, y0 + m, x0 + cw, y0 + m + ch))


HERO, RETREAT = 1.8, 0.5   # a caption holds the screen, then flies into its card


def caption_layer(size, text, where, side, age, left, vertical):
    """First a full-screen title over a paper veil (words appear one by one), then it shrinks and flies
    into a corner card that stays while the shot plays."""
    w, h = size
    fh = font("georgiab.ttf", (96 if LANG == "zh" else 112) if vertical else 96)
    k = (62 if vertical else 50) / fh.size                       # card scale
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    maxw = w * ((0.88 if LANG == "zh" else 0.8) if vertical else 0.6)
    lines = []
    for para in text.split("\n"):
        cur = ""
        for tk in tokens(para):
            if cur and d.textlength((cur + tk).rstrip(), font=fh) > maxw and tk.strip() not in "，。：、":
                lines.append(cur.rstrip()); cur = ""
            cur += tk
        lines.append(cur.rstrip())
    lh = fh.size * (1.3 if LANG == "zh" else 1.2)
    tw, th = max(d.textlength(l, font=fh) for l in lines), lh * len(lines)
    T = Image.new("RGBA", (int(tw) + 8, int(th + fh.size * 0.35)), (0, 0, 0, 0)); dt = ImageDraw.Draw(T)
    n, ty = 0, 0
    for l in lines:
        tx = 0
        for wd in tokens(l + " "):
            wa = ease((age - 0.1 - (0.05 if LANG == "zh" else 0.08) * n) / 0.25)
            dt.text((tx, ty + (1 - wa) * 18), wd.rstrip(), font=fh, fill=INK + (int(255 * wa),))
            tx += dt.textlength(wd, font=fh); n += 1
        ty += lh
    pad = fh.size * k * 0.75
    bw, bh = tw * k + 2 * pad, th * k + fh.size * k * 0.75
    bx = w * 0.06 if side == "left" else w * 0.94 - bw
    by = (h * (0.80 if vertical else 0.78) - bh) if where == "low" else h * (0.07 if vertical else 0.08)
    hero = ((w - tw) / 2 + 14, h * 0.46 - th / 2)
    card = (bx + pad, by + fh.size * k * 0.32)
    r = ease((age - HERO) / RETREAT)
    sc = 1 + (k - 1) * r
    px, py = hero[0] + (card[0] - hero[0]) * r, hero[1] + (card[1] - hero[1]) * r
    out = ease(left / 0.3)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    veil = 0.86 * ease(age / 0.3) * (1 - r) * out
    if veil > 0:
        layer.paste(PAPER + (int(255 * veil),), (0, 0, w, h))
    if r > 0:                                                    # the card grows in behind the arriving words
        ca = ease((r - 0.45) / 0.55) * out
        shadow = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([bx + 6, by + 10, bx + bw + 6, by + bh + 10], 18, fill=(0, 0, 0, int(60 * ca)))
        ImageDraw.Draw(shadow := shadow.filter(ImageFilter.GaussianBlur(14))).rounded_rectangle(
            [bx, by, bx + bw, by + bh], 18, fill=PAPER + (int(250 * ca),))  # drawn on its own layer: drawing on the veil would punch a hole
        layer = Image.alpha_composite(layer, shadow)
    dl = ImageDraw.Draw(layer)                                   # the red bar rides with the words
    barx = px - (30 + (pad - 30) * r)
    dl.rounded_rectangle([barx, py - 4 * sc, barx + max(8, 12 * sc), py + th * sc * ease(age / 0.5)], 4,
                         fill=LASER + (int(255 * out),))
    if sc != 1:
        T = T.resize((max(1, int(T.width * sc)), max(1, int(T.height * sc))), Image.LANCZOS)
    if out < 1:
        T.putalpha(T.getchannel("A").point(lambda x: int(x * out)))
    layer.alpha_composite(T, (int(px), int(py)))
    return layer


def title_card(size, v, vertical):
    """'unfold' opens out vertically like paper, a red rule draws, the tagline fades in."""
    w, h = size
    im = Image.new("RGB", size, PAPER)
    big = font("georgiab.ttf", 190 if vertical else 170, latin=True)  # the wordmark stays Georgia
    word = Image.new("RGBA", (int(big.getlength("unfold")) + 40, big.size + 60), (0, 0, 0, 0))
    ImageDraw.Draw(word).text((20, 10), "unfold", font=big, fill=INK)
    s = ease((v - 0.15) / 0.55)
    if s > 0.01:
        k = s + 0.06 * math.sin(math.pi * s)  # a little overshoot as it opens
        ww, wh = word.size; nh = max(1, int(wh * k))
        im.paste(word.resize((ww, nh), Image.BICUBIC), ((w - ww) // 2, int(h * 0.42 - nh / 2)), word.resize((ww, nh), Image.BICUBIC))
    d = ImageDraw.Draw(im)
    r = ease((v - 0.35) / 0.5) * w * 0.22
    yl = h * 0.42 + big.size * 0.62
    d.line([(w / 2 - r, yl), (w / 2 + r, yl)], fill=LASER, width=6)
    tag = font("georgia.ttf", 52 if vertical else 46)
    ta = ease((v - 0.75) / 0.4)
    t = L("tagline")
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(((w - tag.getlength(t)) / 2, yl + 40 + (1 - ta) * 14), t, font=tag, fill=MUTED + (int(255 * ta),))
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def end_card(size, vertical):
    w, h = size
    im = Image.new("RGB", size, PAPER); d = ImageDraw.Draw(im)
    big, mid, small = (font("georgiab.ttf", 170 if vertical else 140, latin=True), font("georgia.ttf", 48 if vertical else 42),
                       font("consola.ttf", 44 if vertical else 38))
    y = h * 0.34
    d.text(((w - d.textlength("unfold", font=big)) / 2, y), "unfold", font=big, fill=INK)
    y += big.size * 1.28
    d.line([(w * 0.42, y), (w * 0.58, y)], fill=LASER, width=5)
    y += 48
    sub = L("end")
    d.text(((w - d.textlength(sub, font=mid)) / 2, y), sub, font=mid, fill=MUTED)
    y += mid.size * 2.0
    d.text(((w - d.textlength(URL, font=small)) / 2, y), URL, font=small, fill=LASER)
    return im


def compose(chat, page, fmt):
    tag = fmt + ("" if LANG == "en" else "-" + LANG)
    (cshots, cmarks, ccues), (shots, marks, cues) = chat, page
    vertical = fmt == "vertical"
    w, h = (1080, 1440) if vertical else (1920, 1080)
    W, H = shots[0][1].size
    keys, ckeys = camera_keys(marks, W, H), chat_camera_keys(cmarks, *cshots[0][1].size)
    os.makedirs(OUT, exist_ok=True)
    silent = os.path.join(OUT, f"_video-{tag}.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                            "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    card = end_card((w, h), vertical)
    blank = title_card((w, h), 0.0, vertical)
    mark_f = font("consola.ttf", 30 if vertical else 26)
    k = kc = 0
    checks = [round(x * FPS) for x in (1.0, 2.2, 4.4, 6.0, 9.4, 10.6, 11.8, 12.6, 15.6, 16.6, 17.6, 21.0, 23.0)]
    for n in range(int(TOTAL * FPS)):
        v = n / FPS; ct = v - P0; u = v - CHAT
        if v < CHAT:  # the chat scene, then a white-out into the title
            while kc + 1 < len(cshots) and cshots[kc + 1][0] <= v:
                kc += 1
            frame = shoot(cshots[kc][1], camera_at(ckeys, v), w, h)
            s = ease((v - (CHAT - 0.22)) / 0.22)
            if s > 0:
                frame = Image.blend(frame, blank, s)
        else:
            while k + 1 < len(shots) and shots[k + 1][0] <= max(ct, 0):
                k += 1
            frame = shoot(shots[k][1], keep_column(camera_at(keys, max(ct, 0)), marks, W, H, 10 * W / 720), w, h, center=vertical)
            d = ImageDraw.Draw(frame)
            d.text((w - d.textlength(URL, font=mark_f) - 28, h - 56), URL, font=mark_f, fill=(150, 150, 150))
            for (a, b, where, side), text in zip(CAPTION_TIMES, L("captions")):
                if a <= ct < b:
                    frame = Image.alpha_composite(frame.convert("RGBA"),
                                                  caption_layer((w, h), text, where, side, ct - a, b - ct, vertical)).convert("RGB")
            if u < INTRO + 0.45:  # title card, then a zoom-through into the page
                tc = title_card((w, h), u, vertical)
                s = ease((u - (INTRO - 0.35)) / 0.8)
                if s > 0:
                    zoom = 1 + 0.25 * s
                    tw, th = int(w * zoom), int(h * zoom)
                    tc = tc.resize((tw, th), Image.BICUBIC).crop(((tw - w) // 2, (th - h) // 2, (tw - w) // 2 + w, (th - h) // 2 + h))
                frame = Image.blend(tc, frame, s)
            if ct >= CARD_CT:
                frame = Image.blend(frame, card, ease((ct - CARD_CT) / 0.5))
        enc.stdin.write(frame.tobytes())
        if n in checks:
            frame.save(os.path.join(OUT, f"key-{tag}-{n * 10 // FPS:03d}.png"))
    enc.stdin.close(); enc.wait()
    wav = os.path.join(OUT, f"_audio-{tag}.wav")
    write_audio(wav, ccues, cues)
    out = os.path.join(OUT, f"unfold-short-{tag}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent); os.remove(wav)
    print(out, os.path.getsize(out) // 1024, "KB")


# ------------------------------------------------------------------ 3. sound

RNG = np.random.default_rng(7)


def env(n, attack, release):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1); r = np.clip((n / SR - t) / release, 0, 1)
    return np.minimum(a, r) ** 1.5


def lowpass(x, cut):  # one-pole, cut may vary per sample
    y = np.empty_like(x); a = 1 - np.exp(-2 * np.pi * np.asarray(cut) / SR) * np.ones_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y


def whoosh(dur=0.45, lo=300, hi=2600, gain=0.16):
    n = int(dur * SR); s = np.linspace(0, 1, n)
    cut = lo + (hi - lo) * np.sin(np.pi * s) ** 2           # the sweep up and back down is the "air"
    x = RNG.standard_normal(n)
    y = lowpass(x, cut) - lowpass(x, cut * 0.25)             # band-pass
    y *= np.sin(np.pi * s) ** 2
    return gain * y / (np.abs(y).max() + 1e-9)


def click(gain=0.10):
    n = int(0.045 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 140) + 0.4 * RNG.standard_normal(n) * np.exp(-t * 600)
    return gain * y / np.abs(y).max()


def pop(gain=0.13):
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 620 + 520 * (1 - np.exp(-t * 40))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)
    return gain * y


def thump(gain=0.30):
    n = int(0.45 * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (52 + 40 * np.exp(-t * 18)) * t) * np.exp(-t * 9)
    return gain * y


def chime(gain=0.11):
    n = int(1.8 * SR); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * dcy) for f, a, dcy in ((880, 1, 2.6), (1320, .55, 3.2), (1760, .25, 4.0)))
    return gain * y * env(n, 0.005, 0.4)


def tick(gain=0.035):  # one keystroke
    n = int(0.02 * SR); t = np.arange(n) / SR
    y = np.diff(RNG.standard_normal(n + 1)) * np.exp(-t * 400) + 0.5 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 300)
    return gain * y / np.abs(y).max()


# ---- music: a soft pad, a plucked arpeggio, then kick, bass and shaker from the title on.
# The tempo is chosen so that the title opening (DOWN) and the end card fall exactly on bar lines.

BAR = (P0 + CARD_CT - DOWN) / 7
BEAT = BAR / 4
mf = lambda m: 440.0 * 2 ** ((m - 69) / 12)
AM7, FMAJ7, G6, EM7, CMAJ9 = [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [48, 55, 59, 62, 64]
DM7 = [50, 53, 57, 60]
INTRO_BARS = [AM7, FMAJ7, G6]          # under the chat scene, the last one leads into the title
MAIN_BARS = [FMAJ7, G6, EM7, AM7, DM7, FMAJ7, G6]


def tone(f, dur, harm, decay=0.0, attack=0.005, release=0.05, detune=0.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * k * (1 + detune) * t) * np.exp(-t * decay * k) for k, a in harm)
    return y * env(n, attack, release)


def music(n_total):
    L, R = np.zeros(n_total), np.zeros(n_total)
    def put(t, y, pan=0.0, g=1.0):
        i = int(round(t * SR)); y = y * g
        if i < 0: y, i = y[-i:], 0
        j = min(n_total, i + len(y))
        if j > i:
            L[i:j] += y[:j - i] * (1 - pan) ** 0.5; R[i:j] += y[:j - i] * (1 + pan) ** 0.5
    pad_h = [(1, 1), (2, .35), (3, .12), (4, .05)]
    bars = [(DOWN - BAR * (len(INTRO_BARS) - i), c, False) for i, c in enumerate(INTRO_BARS)]
    bars += [(DOWN + BAR * i, c, True) for i, c in enumerate(MAIN_BARS)]
    for t, chord, full in bars:
        for m in chord:  # pad: slow swell, a hair detuned left and right
            for pan, dt in ((-0.6, -0.0015), (0.6, 0.0015)):
                put(t, tone(mf(m), BAR + 0.6, pad_h, attack=0.5, release=0.7, detune=dt), pan, 0.016 if full else 0.013)
        tones = chord[:4] + [chord[0] + 12]
        steps = 8 if full else 4
        for e in range(steps):  # plucked arpeggio: eighths once the title opens, quarters before
            m = tones[[0, 2, 1, 3, 4, 3, 1, 2][e] if full else [0, 2, 4, 2][e]] + 12
            harm = [(1, 1), (2, .5), (3, .3), (4, .15)] if full else [(1, 1), (2, .3)]
            put(t + e * BAR / steps, tone(mf(m), 0.6, harm, decay=7, release=0.2), 0.35 if e % 2 else -0.35, 0.045 if full else 0.035)
        if full:
            root = mf(chord[0] - 12)
            for b0, d in ((0, 1.4), (2.5, 1.4)):  # bass
                put(t + b0 * BEAT, tone(root, d * BEAT, [(1, 1), (2, .25)], attack=0.01, release=0.08), 0, 0.075)
            for b0 in (0, 2):                     # kick
                n = int(0.35 * SR); tt = np.arange(n) / SR
                put(t + b0 * BEAT, np.sin(2 * np.pi * np.cumsum(48 + 70 * np.exp(-tt * 32)) / SR) * np.exp(-tt * 9), 0, 0.17)
            for e in range(8):                    # shaker on the off-eighths
                if e % 2:
                    n = int(0.06 * SR); tt = np.arange(n) / SR
                    put(t + e * BAR / 8, np.diff(RNG.standard_normal(n + 1)) * np.exp(-tt * 70), 0.2, 0.012)
    # riser while Claude works, cut by the title's downbeat
    n = int(1.9 * SR); sw = np.linspace(0, 1, n)
    x = RNG.standard_normal(n); cut = 300 + 5000 * sw ** 2
    y = (lowpass(x, cut) - lowpass(x, cut * 0.3)) * sw ** 2
    y = y / (np.abs(y).max() + 1e-9) + 0.25 * np.sin(2 * np.pi * np.cumsum(220 + 660 * sw ** 2) / SR) * sw ** 2
    put(DOWN - 1.9, y, 0, 0.05)
    # the end card: a Cmaj9 strum that rings out
    end = P0 + CARD_CT
    for i, m in enumerate(CMAJ9 + [CMAJ9[1] + 12, CMAJ9[2] + 12]):
        put(end + 0.035 * i, tone(mf(m + 12), 2.4, [(1, 1), (2, .4), (3, .15)], decay=1.6, release=0.5), (i - 3) * 0.12, 0.04)
    for m in CMAJ9:
        put(end, tone(mf(m), 2.6, pad_h, attack=0.2, release=1.2), 0, 0.02)
    put(end, tone(mf(36), 2.0, [(1, 1), (2, .3)], decay=1.2, release=0.6), 0, 0.09)
    fade = np.clip(np.arange(n_total) / SR / 0.8, 0, 1) * np.clip((TOTAL - np.arange(n_total) / SR) / 0.6, 0, 1)
    return L * fade, R * fade


def write_audio(path, chat_cues, cues):
    n_total = int(TOTAL * SR) + SR
    track = np.zeros(n_total)
    def put(t, snd):
        i = int(max(t, 0) * SR); j = min(len(track), i + len(snd)); track[i:j] += snd[:j - i]
    for t, kind in chat_cues:  # the chat scene
        if kind == "drag": put(t, whoosh(0.9, 250, 1600, 0.07))
        elif kind == "drop": put(t, thump(0.12)); put(t, pop(0.08))
        elif kind == "chip": put(t, pop(0.06))
        elif kind == "type": put(t, tick())
        elif kind == "key": put(t, click(0.09))
        elif kind == "send": put(t, whoosh(0.4, 600, 3600, 0.09))
        elif kind == "step": put(t, pop(0.045))
        elif kind == "card": put(t, pop(0.12))
    put(CHAT - 0.25, whoosh(0.5, 500, 3800, 0.10))                      # white-out into the title
    put(CHAT + 0.12, whoosh(0.7, 200, 1400, 0.08)); put(DOWN, thump())  # the title opens
    put(P0 - 0.3, whoosh(0.6, 400, 3200, 0.12))                         # zoom-through into the page
    for t, kind in cues:
        v = t + P0
        if kind == "key": put(v, click())
        elif kind == "whoosh": put(v, whoosh(0.42, 500, 3400, 0.12))     # the laser pointer moves
        elif kind == "write": put(v, whoosh(0.55, 250, 1800, 0.08))
        elif kind == "settle": put(v, whoosh(0.6, 200, 1200, 0.09))
        elif kind == "scroll": put(v, whoosh(0.7, 300, 2200, 0.10))
        elif kind == "glide": put(v, whoosh(0.5, 600, 4000, 0.07))
        elif kind == "pop": put(v, pop())
        elif kind == "fold": put(v, whoosh(0.3, 800, 3800, 0.07))
    put(P0 + CARD_CT + 0.05, chime(0.08))
    # the music ducks a little under each sound effect
    e = np.abs(track); c = np.cumsum(e); win = int(0.04 * SR)
    sm = np.concatenate([c[:win] / np.arange(1, win + 1), (c[win:] - c[:-win]) / win])
    duck = 1 - 0.45 * np.clip(sm / 0.03, 0, 1)
    ml, mr = music(n_total)
    left, right = track + ml * duck, track + mr * duck
    out = []
    for ch in (left, right):
        ch = np.tanh(ch * 1.4) / 1.4                                      # gentle limiter
        out.append((np.clip(ch * 1.5, -1, 1) * 32767 * 0.9).astype(np.int16))
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes(np.column_stack(out).ravel().tobytes())


def main():
    global LANG
    ap = argparse.ArgumentParser(); ap.add_argument("--format", default="both", choices=["vertical", "landscape", "both"])
    ap.add_argument("--lang", default="en", choices=sorted(TEXT))
    a = ap.parse_args(); fmt, LANG = a.format, a.lang
    if fmt in ("vertical", "both"):   # a 3:4 page, 720 x 960 CSS px at 2x
        compose(asyncio.run(capture_chat(720, 960, 2.0)), asyncio.run(capture(720, 960, 2.0)), "vertical")
    if fmt in ("landscape", "both"):  # 1024 x 576 CSS px at 2x
        compose(asyncio.run(capture_chat(1024, 576, 2.0)), asyncio.run(capture(1024, 576, 2.0)), "landscape")


if __name__ == "__main__":
    main()
