#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pymupdf", "pillow", "fonttools", "brotli"]
# ///
"""Rebuild every note listed in a manifest with the current template and engine.

  uv run rebuild_all.py MANIFEST.json [name-substring]
  python rebuild_all.py MANIFEST.json [name-substring]

The manifest looks like examples/notes.json:
  {"notes": [{"name": "...", "note_dir": "quantum-geometry", "parts": [], "flags": [], "post": []}]}
note_dir is relative to the manifest's folder. For each note: concatenate its part files into content.html
(when "parts" is set), run build.py with the note's flags, then run its "post" scripts (paths relative to
note_dir). Run after any change to assets/ or scripts/.
"""
import json, os, subprocess, sys

if len(sys.argv) < 2:
    sys.exit(__doc__)
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
manifest = os.path.abspath(sys.argv[1])
base = os.path.dirname(manifest)
only = sys.argv[2].lower() if len(sys.argv) > 2 else ""
PY = sys.executable

with open(manifest, encoding="utf-8") as f:
    notes = json.load(f)["notes"]
for note in notes:
    if only and only not in note["name"].lower():
        continue
    d = os.path.join(base, note["note_dir"])
    print(f"== {note['name']}")
    if note.get("parts"):
        with open(os.path.join(d, "content.html"), "w", encoding="utf-8") as out:
            for p in note["parts"]:
                out.write(open(os.path.join(d, p), encoding="utf-8").read())
    subprocess.run([PY, os.path.join(SKILL, "scripts", "build.py"), d, *note.get("flags", [])], check=True)
    for script in note.get("post", []):
        subprocess.run([PY, os.path.join(d, script)], check=True, cwd=d)
