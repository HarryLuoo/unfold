"""Source-anchored HTML notes: citation registry, PDF cropping, page assembly, single-file packaging.

A note directory holds two authored files:
  cites.py      - `from notelib import *`, then config(...), source(...), pdf(...), link(...)
  content.html  - the note body with [[key]] / [[key|label]] citations, <sn>sidenote</sn>, <en>margin note</en>
Build with:  python build.py NOTE_DIR [--standalone] [--share]
"""
import base64, html, io, json, logging, os, re, shutil, subprocess, sys, urllib.parse, urllib.request
logging.getLogger("fontTools").setLevel(logging.ERROR)

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CACHE = os.path.expanduser("~/.cache/html-notes")

CONFIG, SRC, C = {}, {}, {}

# ----------------------------------------------------------------- registry API (used by cites.py)

def config(root, name, title, lang="en", out=None):
    """root: folder that source paths and PDF links are relative to; name: output basename.
    out: folder for the reader's file. When set (repository layout), the build writes one self-contained
    <out>/<name>.html and keeps every intermediate (crops, plain page, share build) in <note_dir>/_build/.
    When unset (legacy layout), all outputs go to root."""
    CONFIG.update(root=root, name=name, title=title, lang=lang, out=out)

def source(key, file, short, abbr, offset=None, cols=1, share=None, share_dpi=None):
    """offset: int (printed page = PDF page - offset), a format string such as "144412-{p}", or None.
    cols: 2 for two-column journals (crops follow the matched column).
    share: what --share builds link to instead of the local PDF: a public URL (DOI, repository), or a
    relative path such as "literature/x.pdf#page={page}" for a copy of the PDF attached to the share build
    (written to _build/share/). "{page}" becomes the cited page.
    share_dpi: downsample the attached copy's images to this resolution, for PDFs too large to publish."""
    SRC[key] = dict(file=file, short=short, abbr=abbr, offset=offset, cols=cols, share=share,
                    share_dpi=share_dpi)

def pdf(key, src, page, where, start=None, end=None, mode="crop", pad=(6, 6), frac=None, printed=None):
    """Crop from the first match of `start` to the first later match of `end` on 1-based PDF `page`.
    start=None -> top of the text; end=None -> bottom of the text; mode="page" -> whole page.
    frac=(top, bottom) as fractions of the page height -> that horizontal band of the page
    (for handwritten or scanned pages whose text layer cannot be searched).
    printed: the printed page number, when the source's PDF-to-printed offset is not constant."""
    if frac is not None:
        mode = "region"
    C[key] = dict(kind="pdf", src=src, page=page, where=where, start=start, end=end, mode=mode, pad=pad,
                  frac=frac, printed=printed)

def link(key, label, href, text, where, private=True):
    """Text-only preview (emails, local notes, web pages). private links lose their href in --share builds."""
    C[key] = dict(kind="link", label=label, href=href, text=text, where=where, private=private)

# ----------------------------------------------------------------- cropping

def _find(page, s, after=None):
    hits = page.search_for(s)
    if after is not None:
        hits = [h for h in hits if h.y0 >= after - 2]
    return hits[0] if hits else None

def _column(page, rect):
    xs = [(b[0], b[2]) for b in page.get_text("blocks")
          if b[1] <= rect.y1 and b[3] >= rect.y0 and b[0] <= rect.x1 and b[2] >= rect.x0]
    return (min(x[0] for x in xs), max(x[1] for x in xs)) if xs else (rect.x0, rect.x1)

def _clip(page, c, pymupdf):
    if c["mode"] == "page":
        return page.rect
    if c["mode"] == "region":
        r, (t, b) = page.rect, c["frac"]
        return pymupdf.Rect(r.x0, r.y0 + t * r.height, r.x1, r.y0 + b * r.height)
    bs = page.get_text("blocks")
    tx0, tx1 = min(b[0] for b in bs), max(b[2] for b in bs)
    ty0, ty1 = min(b[1] for b in bs), max(b[3] for b in bs)
    s = _find(page, c["start"]) if c["start"] else None
    if c["start"] and s is None:
        raise ValueError(f"start anchor not found: {c['start']!r}")
    y0 = s.y0 if s else ty0
    e = _find(page, c["end"], after=y0) if c["end"] else None
    if c["end"] and e is None:
        raise ValueError(f"end anchor not found: {c['end']!r}")
    y1 = e.y1 if e else ty1
    x0, x1 = tx0, tx1
    if s and e and SRC[c["src"]]["cols"] == 2:
        a, b = _column(page, s), _column(page, e)
        x0, x1 = min(a[0], b[0]), max(a[1], b[1])
        if x1 - x0 < 0.3 * page.rect.width:
            x0, x1 = tx0, tx1
    pt, pb = c["pad"]
    return pymupdf.Rect(x0 - 6, y0 - pt, x1 + 6, y1 + pb) & page.rect

def render_crops(outdir):
    """Render every pdf() citation to outdir/<key>.png. Returns a list of anchor errors."""
    import pymupdf
    os.makedirs(outdir, exist_ok=True)
    docs, errors = {}, []
    for k, c in C.items():
        if c["kind"] != "pdf":
            continue
        f = SRC[c["src"]]["file"]
        d = docs.setdefault(f, pymupdf.open(os.path.join(CONFIG["root"], f)))
        page = d[c["page"] - 1]
        try:
            clip = _clip(page, c, pymupdf)
        except ValueError as ex:
            errors.append(f"{k} (PDF {c['page']} of {f}): {ex}")
            continue
        dpi = 160
        if c["mode"] == "page":
            dpi = 80 if page.rect.height > page.rect.width else 110
        elif c["mode"] == "region":
            dpi = int(round(640 / (page.rect.width / 72)))  # about 640 px wide, the width of the preview window
        pix = page.get_pixmap(dpi=dpi, clip=clip)
        pix.save(os.path.join(outdir, f"{k}.png"))
        c["img"], c["w"], c["h"] = f"{k}.png", pix.width, pix.height
    return errors

# ----------------------------------------------------------------- page assembly

def printed(c):
    if c.get("printed") is not None:
        return str(c["printed"])
    off, p = SRC[c["src"]]["offset"], c["page"]
    if off is None:
        return None
    return str(p - off) if isinstance(off, int) else off.format(p=p)

def default_label(c):
    if c["kind"] == "link":
        return c["label"]
    pp = printed(c)
    s = SRC[c["src"]]
    return f"{s['abbr']} p. {pp}" if pp else f"{s['abbr']} {c['page']}"

def _meta(k, assets, share):
    c = C[k]
    if c["kind"] == "link":
        href = None if (share and c["private"]) else c["href"]
        return dict(title=c["label"], where=c["where"], text=c["text"], href=href, loc="")
    s = SRC[c["src"]]
    pp = printed(c)
    loc = f"PDF {c['page']}" + (f", p. {pp}" if pp else "")
    href = _share_href(s, c["page"]) if share else f"{urllib.parse.quote(s['file'])}#page={c['page']}"
    return dict(title=s["short"], where=c["where"], loc=loc, img=f"{assets}/{c['img']}",
                w=c["w"], h=c["h"], href=href)

def _share_href(s, page):
    return s["share"] and s["share"].replace("{page}", str(page))

def attach(dest):
    """Copy the PDFs that --share builds link to by relative path into dest (downsampled to share_dpi,
    if set). Returns the paths written, relative to dest."""
    import pymupdf
    shutil.rmtree(dest, ignore_errors=True)
    done = []
    for s in SRC.values():
        rel = (s["share"] or "").split("#")[0]
        if not rel or "://" in rel or rel in done:
            continue
        out = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        src = os.path.join(CONFIG["root"], s["file"])
        if s["share_dpi"]:
            doc = pymupdf.open(src)
            doc.rewrite_images(dpi_threshold=round(s["share_dpi"] * 1.1), dpi_target=s["share_dpi"], quality=85)
            doc.save(out, garbage=4, deflate=True)
        else:
            shutil.copyfile(src, out)
        done.append(rel)
    return done

def _stamp():
    """The commit a share build was made from, for its footer."""
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=CONFIG["note_dir"], capture_output=True, text=True,
                                  encoding="utf-8").stdout.strip()
        except OSError:  # no git on PATH
            return ""
    commit = git("log", "-1", "--format=%h (%cs)")
    if not commit:
        return ""
    dirty = " plus uncommitted changes" if git("status", "--porcelain", "--", ".", SKILL) else ""
    return f'<p class="build-stamp">Snapshot of commit {commit}{dirty}. The repository holds the current version.</p>'

def _heading_ids(body):
    """Give parts (<div class="part" data-part="I">), <h2> and <h3> stable ids for the side navigation."""
    seen = set()
    def uid(base):
        base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "s"
        i, k = 1, base
        while k in seen:
            i += 1; k = f"{base}-{i}"
        seen.add(k)
        return k
    def tag(m):
        t = m.group(0)
        if " id=" in t:
            seen.add(re.search(r' id="([^"]+)"', t).group(1))
            return t
        num = re.search(r'data-(?:num|part)="([^"]+)"', t)
        prefix = "part-" if 'class="part' in t else "sec-"
        base = prefix + num.group(1) if num else prefix + str(len(seen) + 1)
        return t[:-1] + f' id="{uid(base)}">'
    return re.sub(r'<div class="part[^"]*"[^>]*>|<h[23](?:\s[^>]*)?>', tag, body)

def assemble(share=False):
    """Return (html_text, used_keys). Images are referenced as <name>_files/<key>.png."""
    name = CONFIG["name"]
    assets = name + "_files"
    note_dir = CONFIG["note_dir"]
    body = open(os.path.join(note_dir, "content.html"), encoding="utf-8").read()
    used, n = set(), [0]

    def sidenote(m):
        n[0] += 1
        i = n[0]
        return (f'<label class="sn-ref" for="sn{i}">{i}</label>'
                f'<input type="checkbox" id="sn{i}" class="sn-toggle">'
                f'<span class="sidenote"><span class="sn-num">{i}</span> {m.group(1)}</span>')

    def cite(m):
        k, _, label = m.group(1).partition("|")
        if k not in C:
            sys.exit(f"unknown citation key: {k}")
        used.add(k)
        href = _meta(k, assets, share)["href"]
        lab = html.escape(label or default_label(C[k]))
        if href:
            return (f'<a class="cite" data-k="{k}" href="{html.escape(href)}" target="_blank" '
                    f'rel="noopener">[{lab}]</a>')
        return f'<a class="cite" data-k="{k}" href="#" data-nolink="1">[{lab}]</a>'

    body = _heading_ids(body)
    body = re.sub(r"<sn>(.*?)</sn>", sidenote, body, flags=re.S)
    body = re.sub(r"<en>(.*?)</en>", lambda m: f'<span class="marginnote">{m.group(1)}</span>', body, flags=re.S)
    body = re.sub(r"\[\[([^\]]+)\]\]", cite, body)
    if share:  # local PDF links in the body (e.g. the source list) -> public URL or plain text
        by_file = {}
        for s in SRC.values():  # the first share of each file, without its page anchor
            if s["share"] and not by_file.get(s["file"]):
                by_file[s["file"]] = s["share"].split("#")[0]
        def relink(m):
            url = by_file.get(m.group(1))
            return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{m.group(2)}</a>' if url else m.group(2)
        body = re.sub(r'<a href="([^"#]+\.pdf)">(.*?)</a>', relink, body)
        body += _stamp()
    data = {k: _meta(k, assets, share) for k in sorted(used)}
    tpl = template()
    out = (tpl.replace("%%TITLE%%", html.escape(CONFIG["title"])).replace("%%LANG%%", CONFIG["lang"])
              .replace("%%BODY%%", body).replace("%%CITES%%", json.dumps(data, ensure_ascii=False)))
    return out, used, n[0]

def template():
    """assets/template.html with the lecture mode (assets/lecture.css, assets/lecture.js) inlined."""
    asset = lambda f: open(os.path.join(SKILL, "assets", f), encoding="utf-8").read()
    return (asset("template.html").replace("%%LECTURE_CSS%%\n", asset("lecture.css"))
                                  .replace("%%LECTURE_JS%%\n", asset("lecture.js")))

# ----------------------------------------------------------------- single-file packaging

KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/"
CMU = "https://cdn.jsdelivr.net/gh/aaaakshat/cm-web-fonts@latest/font/Serif/"
CMU_FACES = [("cmunrm", "normal", "normal"), ("cmunbx", "bold", "normal"),
             ("cmunti", "normal", "italic"), ("cmunbi", "bold", "italic")]

def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

KATEX_NPM = "https://registry.npmjs.org/katex/-/katex-0.16.9.tgz"
CMU_RAW = "https://raw.githubusercontent.com/aaaakshat/cm-web-fonts/master/font/Serif/"

def _seed_katex_from_npm():
    """Fallback when the KaTeX CDN is blocked: unpack the npm tarball into the cache under the CDN names."""
    import tarfile
    tgz = io.BytesIO(_download(KATEX_NPM))
    with tarfile.open(fileobj=tgz) as t:
        for m in t.getmembers():
            if m.isfile() and m.name.startswith("package/dist/"):
                rel = m.name[len("package/dist/"):]
                dest = _cached(KATEX + rel)
                with open(dest, "wb") as f:
                    f.write(t.extractfile(m).read())

def _cached(url):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", url))

def fetch(url):
    """Download once into ~/.cache/html-notes. Falls back to npm (KaTeX) and raw GitHub (fonts)
    when the CDNs are blocked."""
    os.makedirs(CACHE, exist_ok=True)
    path = _cached(url)
    if not os.path.exists(path):
        try:
            data = _download(url)
        except Exception:
            if url.startswith(KATEX):
                _seed_katex_from_npm()
                if os.path.exists(path):
                    return open(path, "rb").read()
                raise
            if url.startswith(CMU):
                data = _download(CMU_RAW + url[len(CMU):])
            else:
                raise
        with open(path, "wb") as f:
            f.write(data)
    return open(path, "rb").read()

def b64(data, mime):
    return f"data:{mime};base64," + base64.b64encode(data).decode()

def _katex_css():
    css = fetch(KATEX + "katex.min.css").decode()
    def font(m):
        name = m.group(1)
        return f'url({b64(fetch(KATEX + "fonts/" + name + ".woff2"), "font/woff2")}) format("woff2")'
    # keep only the woff2 source of each @font-face
    css = re.sub(r'url\(fonts/(KaTeX_[A-Za-z0-9-]+)\.woff2\) format\("woff2"\)(,url\([^)]*\) format\("[a-z]+"\))*', font, css)
    return css

def _cmu_css(text):
    """Computer Modern Serif, subset to the characters of the page when fontTools is available."""
    faces = []
    for fn, weight, style in CMU_FACES:
        data, mime, fmt = fetch(CMU + fn + ".woff"), "font/woff", "woff"
        try:
            from fontTools import subset
            from fontTools.ttLib import TTFont
            font = TTFont(io.BytesIO(data))
            opts = subset.Options()
            opts.flavor, opts.layout_features = "woff2", ["*"]
            sub = subset.Subsetter(opts)
            sub.populate(text=text + "".join(chr(i) for i in range(32, 127)))
            sub.subset(font)
            buf = io.BytesIO(); font.flavor = "woff2"; font.save(buf)
            data, mime, fmt = buf.getvalue(), "font/woff2", "woff2"
        except Exception:
            pass
        faces.append(f"@font-face{{font-family:'Computer Modern Serif';font-weight:{weight};font-style:{style};"
                     f"src:url({b64(data, mime)}) format('{fmt}');}}")
    return "\n".join(faces)

def _image_uri(path):
    data = open(path, "rb").read()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=82, method=6)
        if buf.tell() < len(data):
            return b64(buf.getvalue(), "image/webp")
    except Exception:
        pass
    return b64(data, "image/png")

def standalone(page_html, assets_dir):
    """Inline images, KaTeX (JS, CSS, fonts) and Computer Modern into one HTML string."""
    def img(m):
        return '"img": "' + _image_uri(os.path.join(assets_dir, m.group(1))) + '"'
    out = re.sub(r'"img": "[^"/]+_files/([^"]+)"', img, page_html)
    def fig(m):  # figures drawn for the note: <img src="figures/..."> (note dir) or "<name>_figures/..." (root)
        for base in (CONFIG.get("note_dir", ""), CONFIG["root"]):
            path = os.path.join(base, m.group(1))
            if base and os.path.exists(path):
                return 'src="' + _image_uri(path) + '"'
        return m.group(0)
    out = re.sub(r'src="((?:[^"]*/)?(?:figures|[^"/]+_figures)/[^"]+)"', fig, out)
    visible = re.sub(r"<[^>]+>", " ", out)
    out = prerender_math(out)
    head_inline = ("<style>\n" + _cmu_css(visible) + "\n" + _katex_css() + "\n</style>\n"
                   "<script>" + fetch(KATEX + "katex.min.js").decode().replace("</script", "<\\/script") + "</script>\n"
                   "<script>" + fetch(KATEX + "contrib/auto-render.min.js").decode().replace("</script", "<\\/script") + "</script>")
    out = re.sub(r"<!-- EXTERNAL -->.*?<!-- /EXTERNAL -->", lambda m: head_inline, out, flags=re.S)
    return out

# ----------------------------------------------------------------- math drawn at build time

# Must match renderMathInElement in assets/template.html.
MATH_DELIMS = [("\\[", "\\]", True), ("\\(", "\\)", False)]
_TOKENS = re.compile(r"(<(script|style|textarea)\b.*?</\2\s*>|<!--.*?-->|<[A-Za-z/!](?:\"[^\"]*\"|'[^']*'|[^'\">])*>)",
                     re.S | re.I)
_NO_MATH = ("pre", "code", "noscript", "option")  # auto-render's ignoredTags (script, style, textarea above)
_KATEX_NODE = ("const katex = require(process.argv[1]); let s = '';"
               "process.stdin.on('data', d => s += d).on('end', () => process.stdout.write(JSON.stringify("
               "JSON.parse(s).map(([tex, display]) => katex.renderToString(tex, {displayMode: display, throwOnError: false, trust: true, strict: 'ignore'})))));")

def _end_of_math(right, text, start):
    """auto-render's findEndOfMath: the right delimiter at brace level 0, skipping escaped characters."""
    i, level = start, 0
    while i < len(text):
        if level <= 0 and text.startswith(right, i):
            return i
        if text[i] == "\\":
            i += 1
        elif text[i] == "{":
            level += 1
        elif text[i] == "}":
            level -= 1
        i += 1
    return -1

def _split_math(text):
    """auto-render's splitAtDelimiters: a list of (is_math, text, display)."""
    out, left = [], re.compile("|".join(re.escape(l) for l, _, _ in MATH_DELIMS))
    while True:
        m = left.search(text)
        if not m:
            break
        if m.start() > 0:
            out.append((False, text[:m.start()], False))
            text = text[m.start():]
        l, r, display = next(d for d in MATH_DELIMS if text.startswith(d[0]))
        end = _end_of_math(r, text, len(l))
        if end == -1:
            break
        out.append((True, text[len(l):end], display))
        text = text[end + len(r):]
    if text:
        out.append((False, text, False))
    return out

def prerender_math(page):
    """Draw the page's math with KaTeX now, as renderMathInElement would when the page opens, so the math
    also shows in viewers that don't run scripts. Needs node; without it the page draws its math on load."""
    node = shutil.which("node")
    if not node:
        print("node not found: math is drawn when the page opens")
        return page
    fetch(KATEX + "katex.min.js")
    parts, skip, jobs, out = _TOKENS.split(page), 0, [], []
    # parts: text, token, raw-text tag name (or None), text, token, ..., text
    for i in range(0, len(parts), 3):
        text = parts[i]
        segs = _split_math(html.unescape(text)) if skip == 0 and ("\\(" in text or "\\[" in text) else []
        if any(is_math for is_math, _, _ in segs):
            jobs += [[t, display] for is_math, t, display in segs if is_math]
            out.append(segs)  # a text node holding math
        else:
            out.append(text)
        if i + 1 < len(parts):
            tok = parts[i + 1]
            out.append(tok)
            m = re.match(r"<(/?)([A-Za-z]+)", tok)
            if m and m.group(2).lower() in _NO_MATH:
                skip = max(0, skip + (-1 if m.group(1) else 1))
    if not jobs:
        return page
    run = subprocess.run([node, "-e", _KATEX_NODE, _cached(KATEX + "katex.min.js")], input=json.dumps(jobs),
                         capture_output=True, text=True, encoding="utf-8", check=True)
    rendered = iter(json.loads(run.stdout))
    def text_node(segs):
        return "".join(f"<span>{next(rendered)}</span>" if is_math else html.escape(t, quote=False)
                       for is_math, t, _ in segs)
    return "".join(p if isinstance(p, str) else text_node(p) for p in out)
