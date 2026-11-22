#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pymupdf", "pillow", "fonttools", "brotli"]
# ///
"""Build a source-anchored HTML note.

  uv run build.py NOTE_DIR          (uv installs the dependencies above on first use)
  python build.py NOTE_DIR          (after pip install -r requirements.txt)

Repository layout (config(..., out=NOTES_DIR) in cites.py):
  python build.py NOTE_DIR            -> <out>/<name>.html: one self-contained file for readers
                                         (crops, figures, KaTeX and fonts inlined; links open the local PDFs);
                                         intermediates in NOTE_DIR/_build/
  python build.py NOTE_DIR --share    -> also NOTE_DIR/_build/<name>_share.html: one file for people outside
                                         the repo; citations open public URLs from source(share=...) or only preview

Legacy layout (no out=): outputs go to root as before
  python build.py NOTE_DIR               -> <root>/<name>.html + <root>/<name>_files/
  python build.py NOTE_DIR --standalone  -> also <root>/<name>_standalone.html
  python build.py NOTE_DIR --share       -> also <root>/<name>_share.html

Needs PyMuPDF; single-file outputs also use Pillow (WebP images) and fontTools+brotli (font subsetting)
when installed, and download KaTeX + Computer Modern once into ~/.cache/html-notes.
"""
import importlib.util, os, sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notelib as N

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 1:
        sys.exit(__doc__)
    note_dir = os.path.abspath(args[0])
    spec = importlib.util.spec_from_file_location("cites", os.path.join(note_dir, "cites.py"))
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
    N.CONFIG["note_dir"] = note_dir
    root, name, out_dir = N.CONFIG["root"], N.CONFIG["name"], N.CONFIG.get("out")
    build_dir = os.path.join(note_dir, "_build") if out_dir else root
    os.makedirs(build_dir, exist_ok=True)
    assets = os.path.join(build_dir, name + "_files")

    errors = N.render_crops(assets)
    if errors:
        sys.exit("anchor errors:\n  " + "\n  ".join(errors))

    page, used, n_sn = N.assemble(share=False)
    plain = os.path.join(build_dir, name + ".html")
    open(plain, "w", encoding="utf-8").write(page)
    for f in os.listdir(assets):  # drop crops the note no longer cites
        if f.endswith(".png") and f[:-4] not in used:
            os.remove(os.path.join(assets, f))
    print(f"{len(used)} citations, {n_sn} sidenotes")

    if out_dir:
        out = os.path.join(out_dir, name + ".html")
        open(out, "w", encoding="utf-8").write(N.standalone(page, assets))
        print(f"reader's file ({os.path.getsize(out) / 1e6:.1f} MB) -> {out}")
    else:
        print(f"-> {plain}")
        if "--standalone" in flags:
            out = os.path.join(root, name + "_standalone.html")
            open(out, "w", encoding="utf-8").write(N.standalone(page, assets))
            print(f"standalone ({os.path.getsize(out) / 1e6:.1f} MB) -> {out}")
    if "--share" in flags:
        shared, _, _ = N.assemble(share=True)
        out = os.path.join(build_dir, name + "_share.html")
        open(out, "w", encoding="utf-8").write(N.standalone(shared, assets))
        print(f"share ({os.path.getsize(out) / 1e6:.1f} MB) -> {out}")
        for rel in N.attach(os.path.join(build_dir, "share")):
            print(f"  attached -> {os.path.join(build_dir, 'share', rel)}")

main()
