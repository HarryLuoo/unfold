#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pymupdf", "pillow", "fonttools", "brotli"]
# ///
"""unfold commands. Run with uv (it installs the dependencies above on first use) or with a Python
that has them (pip install -r requirements.txt).

  uv run note.py doctor                         what this computer has and lacks, with the fix for each; installs nothing
  uv run note.py new NOTE_DIR NAME [--title T] [--pdf FILE ...]
                                                start a note: cites.py, content.html, calibration.md, figures/
  uv run note.py find "PHRASE" FILE.pdf [...]   pages that hold PHRASE, and whether it works as a crop anchor
  uv run note.py build NOTE_DIR [--share]       build the reader's file (the same as build.py NOTE_DIR)
  uv run note.py map NOTE_DIR                   render NOTE_DIR/map.mmd to NOTE_DIR/figures/map.svg in the browser
  uv run note.py check NOTE_DIR                 check the reader's file in the browser and save screenshots
"""
import argparse, html, importlib.util, json, os, platform, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import notelib as N

CHECK = os.path.join(N.CACHE, "check")
MERMAID = ["https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
           "https://unpkg.com/mermaid@11.4.1/dist/mermaid.min.js"]


def have(module):
    return importlib.util.find_spec(module) is not None


def find_browser():
    """An installed Chrome, Edge or Chromium; HTMLNOTES_BROWSER names another."""
    named = os.environ.get("HTMLNOTES_BROWSER")
    if named and os.path.exists(named):
        return named
    candidates = []
    if platform.system() == "Windows":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                               os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    elif platform.system() == "Darwin":
        for base in ("/Applications", os.path.expanduser("~/Applications")):
            candidates += [f"{base}/Google Chrome.app/Contents/MacOS/Google Chrome",
                           f"{base}/Chromium.app/Contents/MacOS/Chromium",
                           f"{base}/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for path in candidates:
        if os.path.exists(path):
            return path
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome", "msedge"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def need_browser():
    browser = find_browser()
    if not browser:
        sys.exit("unfold: map and check need Chrome, Edge or Chromium; set HTMLNOTES_BROWSER to the browser's path")
    return browser


def need_pymupdf():
    if not have("pymupdf"):
        sys.exit("unfold: PyMuPDF is missing from " + sys.executable + "; run note.py doctor for the fix")


def load(folder):
    """Run NOTE_DIR/cites.py; return (note folder, config, folder of the reader's file)."""
    note = os.path.abspath(folder)
    cites = os.path.join(note, "cites.py")
    if not os.path.exists(cites):
        sys.exit(f"unfold: no cites.py in {note}")
    spec = importlib.util.spec_from_file_location("cites", cites)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
    config = dict(N.CONFIG)
    return note, config, config.get("out") or config["root"]


def run_browser(browser, url, extra, timeout=120):
    """Headless run in a throwaway profile, so that the user's own browser profile stays untouched."""
    os.makedirs(CHECK, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="profile-", dir=CHECK)
    try:
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={profile}",
               "--virtual-time-budget=15000", *extra, url]
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


# ---------------------------------------------------------------- doctor

def cmd_doctor(args):
    rows, ok = [("Python", "ok", f"{sys.version.split()[0]} at {sys.executable}")], True
    if have("pymupdf"):
        import pymupdf
        rows.append(("PyMuPDF", "ok", f"{pymupdf.VersionBind}; crops the cited PDF passages"))
    else:
        ok = False
        rows.append(("PyMuPDF", "MISSING", "required. Fix: run the scripts with uv run, which installs it, or "
                     "pip install -r requirements.txt (PyMuPDF is a 20-60 MB download)"))
    for module, pip_name, use in (("PIL", "pillow", "shrinks images"), ("fontTools", "fonttools", "subsets fonts"),
                                  ("brotli", "brotli", "compresses the subset fonts"),
                                  ("matplotlib", "matplotlib", "draws figures"), ("numpy", "numpy", "draws figures")):
        found = have(module)
        rows.append((module, "ok" if found else "missing", use + ("" if found else f"; optional, pip install {pip_name}")))
    node = shutil.which("node")
    rows.append(("node", "ok" if node else "missing", "draws the math at build time" if node else
                 "optional: without it the reader's browser draws the math"))
    browser = find_browser()
    rows.append(("browser", "ok" if browser else "missing", browser or
                 "map and check need Chrome, Edge or Chromium; set HTMLNOTES_BROWSER to its path"))
    katex = os.path.exists(N._cached(N.KATEX + "katex.min.js"))
    rows.append(("KaTeX, fonts", "ok" if katex else "not cached", "cached in ~/.cache/html-notes" if katex else
                 "the first build downloads about 1 MB"))
    mermaid = any(os.path.exists(N._cached(u)) for u in MERMAID)
    rows.append(("Mermaid", "ok" if mermaid else "not cached", "cached, for maps" if mermaid else
                 "the first map downloads about 3 MB"))
    width = max(len(r[0]) for r in rows)
    for name, status, note in rows:
        print(f"{name:<{width}}  {status:<10}  {note}")
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------- new

def cmd_new(args):
    note = os.path.abspath(args.folder)
    for f in ("cites.py", "content.html", "calibration.md"):
        if os.path.exists(os.path.join(note, f)):
            sys.exit(f"unfold: {os.path.join(note, f)} exists; nothing written")
    os.makedirs(os.path.join(note, "figures"), exist_ok=True)
    sources = []
    for i, pdf_path in enumerate(args.pdf or [], 1):
        try:
            rel = os.path.relpath(os.path.abspath(pdf_path), note).replace(os.sep, "/")
        except ValueError:  # another drive on Windows
            rel = os.path.abspath(pdf_path).replace(os.sep, "/")
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        abbr = re.split(r"[_\-\s]", stem)[0] or f"S{i}"
        sources.append(f'source("s{i}", {rel!r}, {stem!r}, {abbr!r})  # short title, offset, cols=2 for two columns')
    title = args.title or args.name
    cites = "\n".join([
        f'"""Citations for {args.name}. Build: uv run <skill>/scripts/note.py build <this folder>"""',
        "import os",
        "from notelib import config, source, pdf, link",
        "",
        "HERE = os.path.dirname(os.path.abspath(__file__))  # source paths below are relative to this folder",
        f"config(root=HERE, name={args.name!r}, title={title!r}, out=HERE)",
        "",
        *(sources or ['# source("s1", "path/to/source.pdf", "Author, Title (year)", "Author", offset=0, cols=1)']),
        '# pdf("key", "s1", 1, "§1, Eq. (1)", "start anchor", "end anchor")',
        ""])
    content = f'<header class="titleblock">\n<h1>{html.escape(title)}</h1>\n<div class="abstract"><p></p></div>\n</header>\n'
    open(os.path.join(note, "cites.py"), "w", encoding="utf-8").write(cites)
    open(os.path.join(note, "content.html"), "w", encoding="utf-8").write(content)
    open(os.path.join(note, "calibration.md"), "w", encoding="utf-8").write("# Calibration\n")
    print(f"new note -> {note}\n  cites.py, content.html, calibration.md, figures/")


# ---------------------------------------------------------------- find

FOLD = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "­": "",
                      "−": "-", "‐": "-", "‑": "-", "–": "-", "—": "-",
                      "‘": "'", "’": "'", "“": '"', "”": '"'})


def fold_text(s):
    return " ".join(s.translate(FOLD).split()).lower()


def cmd_find(args):
    need_pymupdf()
    import pymupdf
    phrase, shown = fold_text(args.phrase), 0
    for path in args.pdfs:
        if not os.path.exists(path):
            print(f"no such file: {path}")
            continue
        doc = pymupdf.open(path)
        for number, page in enumerate(doc, 1):
            text = fold_text(page.get_text())
            count = text.count(phrase)
            if not count:
                continue
            searchable = bool(page.search_for(args.phrase))
            if searchable and count == 1:
                verdict = "anchor ok"
            elif searchable:
                verdict = f"appears {count} times on this page; a crop starts at the first"
            else:
                verdict = "not searchable as typed (ligature, math glyph or special dash): pick plain words nearby"
            at = text.find(phrase)
            print(f"{os.path.basename(path)}, PDF page {number}: {verdict}\n"
                  f"    ...{text[max(0, at - 70): at + len(phrase) + 70]}...")
            shown += 1
            if shown >= args.max:
                return
    if not shown:
        print("no page holds this phrase (ligatures, dashes and quotes were folded before the search)")


# ---------------------------------------------------------------- build

def cmd_build(args):
    cmd = [sys.executable, os.path.join(HERE, "build.py"), os.path.abspath(args.folder)]
    sys.exit(subprocess.call(cmd + (["--share"] if args.share else [])))


# ---------------------------------------------------------------- map

MAP_PAGE = """<!doctype html><meta charset="utf-8"><body><script>%s</script>
<script>
mermaid.initialize({startOnLoad: false, htmlLabels: false, flowchart: {htmlLabels: false}});
mermaid.render("map", %s).then(r => {
  const t = document.createElement("textarea"); t.id = "svgout"; t.textContent = r.svg; document.body.appendChild(t);
}).catch(e => {
  const t = document.createElement("textarea"); t.id = "err"; t.textContent = String(e); document.body.appendChild(t);
});
</script></body>"""


def cmd_map(args):
    note, config, out = load(args.folder)
    source = os.path.join(note, "map.mmd")
    if not os.path.exists(source):
        sys.exit(f"unfold: no map.mmd in {note}")
    browser = need_browser()
    script = None
    for url in MERMAID:
        try:
            script = N.fetch(url).decode("utf-8")
            break
        except Exception:
            continue
    if script is None:
        sys.exit("unfold: could not download Mermaid from jsDelivr or unpkg")
    os.makedirs(CHECK, exist_ok=True)
    page = os.path.join(CHECK, config["name"] + "-map.html")
    mmd = open(source, encoding="utf-8").read()
    open(page, "w", encoding="utf-8").write(MAP_PAGE % (script.replace("</script", "<\\/script"), json.dumps(mmd)))
    dom = run_browser(browser, Path(page).as_uri(), ["--dump-dom"]).stdout.decode("utf-8", "replace")
    found = re.search(r'<textarea id="svgout">(.*?)</textarea>', dom, re.S)
    if not found:
        err = re.search(r'<textarea id="err">(.*?)</textarea>', dom, re.S)
        sys.exit("unfold: Mermaid did not draw the map: " + (html.unescape(err.group(1)) if err else "no output"))
    svg = html.unescape(found.group(1))
    try:  # an <img> shows an SVG only when it is well-formed XML
        import xml.etree.ElementTree as ET
        ET.fromstring(svg)
    except ET.ParseError as err:
        sys.exit(f"unfold: Mermaid's SVG is not well-formed XML ({err}); the page could not show it")
    figures = os.path.join(note, "figures")
    os.makedirs(figures, exist_ok=True)
    dest = os.path.join(figures, "map.svg")
    open(dest, "w", encoding="utf-8").write(svg)
    print(f"map -> {dest}")


# ---------------------------------------------------------------- check

CHECK_JS = r"""<script>
addEventListener("load", () => setTimeout(() => {
  const wide = e => e.scrollWidth > e.clientWidth + 1;
  const ids = new Set([...document.querySelectorAll("[id]")].map(e => e.id));
  const r = {
    math_errors: document.querySelectorAll(".katex-error").length,
    broken_images: [...document.images].filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.alt || "image"),
    wide_math: [...document.querySelectorAll(".katex-display, .eqd")].filter(wide).length,
    wide_code: [...document.querySelectorAll("pre.code")].filter(wide).map(e => e.textContent.trim().split("\n")[0].slice(0, 50)),
    wide_tables: [...document.querySelectorAll(".tablewrap")].filter(wide).length,
    citations: document.querySelectorAll("a.cite").length,
    dead_xrefs: [...document.querySelectorAll("a.xref")].map(a => (a.getAttribute("href") || "").slice(1)).filter(h => h && !ids.has(h)),
    height: document.documentElement.scrollHeight,
  };
  const t = document.createElement("textarea"); t.id = "note-check"; t.textContent = JSON.stringify(r);
  document.body.appendChild(t);
}, 2500));
</script>"""
POINTS_JS = '<script>addEventListener("load", () => setTimeout(() => { try { lvFold("points"); } catch (e) {} }, 800));</script>'


def cmd_check(args):
    note, config, out = load(args.folder)
    name = config["name"]
    reader = os.path.join(out, name + ".html")
    if not os.path.exists(reader):
        sys.exit(f"unfold: {reader} does not exist; run note.py build first")
    browser = need_browser()
    where = os.path.join(CHECK, name)
    os.makedirs(where, exist_ok=True)
    page = re.sub(r'(<header class="titleblock"[^>]*?)\s+data-live', r"\1", open(reader, encoding="utf-8").read())
    read_copy, points_copy = os.path.join(where, name + "-read.html"), os.path.join(where, name + "-points.html")
    open(read_copy, "w", encoding="utf-8").write(page.replace("</body>", CHECK_JS + "</body>"))
    open(points_copy, "w", encoding="utf-8").write(page.replace("</body>", POINTS_JS + "</body>"))
    results, problems = {}, False
    for width in (1440, 500):
        dom = run_browser(browser, Path(read_copy).as_uri(), ["--dump-dom", f"--window-size={width},1200"])
        found = re.search(r'<textarea id="note-check">(.*?)</textarea>', dom.stdout.decode("utf-8", "replace"), re.S)
        if not found:
            sys.exit(f"unfold: the browser returned no check result at {width} px")
        r = json.loads(html.unescape(found.group(1)))
        results[width] = r
        problems |= bool(r["math_errors"] or r["broken_images"] or r["dead_xrefs"])
        line = (f"{width:>4} px: math errors {r['math_errors']}, broken images {len(r['broken_images'])}"
                f"{' ' + str(r['broken_images']) if r['broken_images'] else ''}, dead cross-references "
                f"{len(r['dead_xrefs'])}, wide displays {r['wide_math']}, wide tables {r['wide_tables']}")
        if width == 1440:
            line += f", wide code blocks {len(r['wide_code'])}" + (f" {r['wide_code']}" if r["wide_code"] else "")
            line += f", citations {r['citations']}"
        print(line)
    shots = []
    for copy, width, label in ((read_copy, 1440, "read-1440"), (read_copy, 500, "read-500"), (points_copy, 1440, "points-1440")):
        shot = os.path.join(where, f"{name}-{label}.png")
        height = min(results[width]["height"] + 40, 16000)
        run_browser(browser, Path(copy).as_uri(), [f"--screenshot={shot}", f"--window-size={width},{height}"])
        shots.append(shot)
    print("screenshots:\n  " + "\n  ".join(shots))
    sys.exit(1 if problems else 0)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(prog="note.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor").set_defaults(run=cmd_doctor)
    p = sub.add_parser("new"); p.add_argument("folder"); p.add_argument("name"); p.add_argument("--title")
    p.add_argument("--pdf", nargs="*"); p.set_defaults(run=cmd_new)
    p = sub.add_parser("find"); p.add_argument("phrase"); p.add_argument("pdfs", nargs="+")
    p.add_argument("--max", type=int, default=20); p.set_defaults(run=cmd_find)
    p = sub.add_parser("build"); p.add_argument("folder"); p.add_argument("--share", action="store_true"); p.set_defaults(run=cmd_build)
    p = sub.add_parser("map"); p.add_argument("folder"); p.set_defaults(run=cmd_map)
    p = sub.add_parser("check"); p.add_argument("folder"); p.set_defaults(run=cmd_check)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
