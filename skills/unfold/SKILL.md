---
name: "unfold"
description: "Build a reading note with the reader as one self-contained HTML page, one calibrated section at a time: ground the reader with a few questions, plan a minimal map to their goal, write one section, check it with questions, then revise or advance. Every claim carries a citation chip that previews the cropped PDF passage on hover. Key sentences (the k tag) form each section's skeleton and drive the fold levels and Lecture Mode, where the reader plays the note click by click with narration and a laser pointer. Use when someone asks for a note, reading note, study note, 'learn this with me', 'build a note together', hover-preview citations, a note to play as a lecture, a rebuild of an existing note, or sends questions or unfamiliar words about a note they are reading. Also offer it when they send sources or ask a question worth learning properly."
---

# unfold

This skill builds a NotesTeX-style HTML note together with a reader, one section at a time. Every statement carries a citation to its source: a citation chip shows a crop of the cited PDF passage on hover, and a click opens the PDF at that page. The note folds to its skeleton and plays as a lecture.

All paths below are relative to this skill's folder (the folder that holds this file): the engine is `scripts/`, the page design `assets/`, and two references sit in `references/`.

Three questions have three homes, kept apart so that each can change on its own:

| Question | Where |
|---|---|
| How does a sentence read? | `references/style-default.md`, a swappable default. This file holds no prose rules. |
| What makes a good note? | **Note principles** below. |
| How do we plan, organize, build and present a note? | the rest of this file, with `references/live-mode.md` for Lecture Mode. |

Read the style file and the note principles before planning or writing any section.

**No note is written in one pass.** The reader reads slowly and wants to process, not only read. Work in a loop: **ground** the reader, **plan** a minimal map to their goal, then for each section **write → check → revise or advance**. The reader's answers after each section decide what the next section says.

## Note principles

1. **Opening.** A note opens with what it establishes: its first sentence states the main result in terms the reader already holds, and the next sentence or two say how we get there. Each section opens with the statement it establishes or the question it answers.
2. **Statements and derivations.** Results that later sections use sit in statement blocks with the derivation folded directly beneath. The body reads through with every derivation, widget and margin note skipped. A short computation stays next to its result, and the body does not restate a block's result in words.
3. **Definitions** arrive at first need. A concept that later sections lean on gets a full introduction, not one clause.
4. **One principle.** When the material shares a principle, state it once near the start and point back to it where later sections apply it.
5. **Sources.** The physics is the subject of the sentence and the citation follows the claim; a chip goes only on a claim that appears on the cited page. Quote only a definition or rule whose exact wording matters, verbatim, never spliced out of order. A paraphrase changes notation, never content. When reproducing a paper, the authors' step and ours go in separate paragraphs. An explanation, figure or notation of our own is marked as ours in a margin note. A note holds no critiques, errata or questions for authors unless the reader asks.
6. **Skeleton.** Before writing a section's prose, write its key sentences: one, sometimes two per paragraph, each readable on its own, so that the key sentences in order read as the skeleton of the section. Build the skeleton from the plan's nodes and edges, then write the prose around it.
7. **Closure.** Every term and symbol that carries weight is one the reader already holds or one introduced where they first meet it. Notation counts as much as words. Before a formula appears, the reader knows why it takes its form.
8. **Momentum.** At every paragraph break the reader holds the result just reached and has a feel for what comes next; a paragraph that only names things is merged into one that does work. Each section leaves a question open and the next answers it; when the only reason for a section is that it comes next, the order is wrong. Across a check question, the first section ends by pointing at the next question, and the next opens by resolving the reader's guess.
9. **Minimal and incremental.** Build backward from the goal: ask what the reader must hold to see the goal follow, ask the same of each answer, and stop at what they already hold. Cut any piece that no later piece uses; never re-teach what the reader holds. Each piece is one step from what comes before it; a step that needs two explanations becomes two steps. Every starting point is something the reader accepts at face value.
10. **Completion.** A note is complete when the reader sees its goal as obviously true. Until then each section answers its question in full; after that, add nothing.

## Files of a note

A note lives in its own folder, `NOTE_DIR/`:

| File | Holds |
|---|---|
| `cites.py` | the citation registry (Reference → `cites.py` API) |
| `content.html` | the note body (Reference → Markup) |
| `calibration.md` | what the reader holds: goal, strands, floors and ceilings, phrasings that confused them, updated after every check |
| `plan.md`, `map.mmd` | the plan graph and its map |
| `figures.py`, `figures/` | figure script and its PNGs, when the note has figures |
| the cited PDFs | next to `cites.py`, or wherever `config(root=...)` points |
| `<name>.html` | the reader's file, written by the build (to `config(out=...)`) |
| `_build/` | crops and intermediates, written by the build |

`calibration.md` and `plan.md` are working files for whoever writes the note; the reader does not need to read them. They keep later sections consistent with earlier ones, and let a new session pick up a half-finished note.

## Where each piece of content goes

| Content | Place |
|---|---|
| The map of the note (plan graph, current position) | figure right after the title block |
| Every concept the argument depends on | body |
| Statements and definitions | `def`/`thm` blocks, ending with their citations |
| Derivations | folded `Proof` directly under the statement |
| Notation reference and optional background | explainer widget (`details.aside`) |
| One-line glosses, notation translation between sources, links to other notes, neutral facts about a source, pointers to omitted material, a mark that something is ours | margin (`<sn>`, `<en>`) |
| Lattices, zones, bands, energy-level pictures | figure computed for the note from cited formulas, with the formula cited in the caption |
| Check questions of the loop | chat, never the note (Lecture Mode is the one exception: `references/live-mode.md`) |

When no source covers what the reader needs, first look for a textbook or paper that does and cite it; only then write our own explanation and mark it as ours. When a note starts from a question instead of from sources, find the sources: a textbook for foundations, papers for the current result.

## Phase 1: ground and plan

1. **Offer.** When someone sends sources or asks a question that deserves more than a chat answer, ask in one line whether they want to build a note on it, and start only on a yes. When they only want to read, ground them once (step 4), then write every section's skeleton and prose without the per-section checks.
2. **Gather context:** what the reader sends (sources, a question, their own notes), existing notes on the topic, and the purpose the note serves (a class, a talk, a paper, a meeting).
3. **Make the goal concrete.** Ask until the goal is one statement the reader wants to see as obviously true ("I want to understand X" usually means one of several things). Write it at the top of `calibration.md`.
4. **Ground the reader.** Read `calibration.md` first if it exists, and ask only about what it leaves open.
   - List the strands: the things the goal depends on.
   - Ask one question at a time in chat, choosing each from the previous answer, and ask for the answer, a confidence as a percentage, and one line of reasoning.
   - Pitch each strand's first question near the hardest thing the goal needs. Correct and confident: jump up. Correct but unsure: step up gently. Wrong: step down to find where understanding ends. Wrong and confident: a misconception; probe its extent.
   - Stop when each strand has a floor (what they get right) and a ceiling (what they miss). Every question must move a floor or a ceiling.
   - Record strands, floors, ceilings and any confusing phrasing in `calibration.md`.
5. **Extract text.** Dump every source's page text with markers (`===== file PDF page n =====`) using PyMuPDF, and read it to choose quotes. Slides and figures lose content in extraction, so render them with `page.get_pixmap(dpi=70)` and look at the images.
6. **Write the plan** in `plan.md`: a graph built backward from the goal (principle 9).
   - Each node records a short label, the statement it establishes, its terms, symbols and equations (for closure), its source pages, the question its predecessor leaves open (for momentum), and which later nodes use it.
   - Try deleting each node in turn; if every later node still follows, the node goes.
   - Mark a few nodes as checkpoints, where several strands meet.
7. **Have a second model review the plan** (a subagent, ideally a different strong model) on the first plan and again only when the plan is restructured: roots change, a strand is added or dropped, the route to the goal changes.
   - Brief: the goal, `calibration.md`, `plan.md`, the extracted-text paths, and the line "Report issues only; do not propose wording; do not edit files."
   - Ask which nodes could be cut, which roots are disguised theorems, which steps are too large, which nodes the goal still needs, and whether every quote and citation holds.
   - Accept what improves focus and accuracy, push back with reasons where the reader's goals decide otherwise, and finish with a round that asks for must-fix items only.
   - The reviewer's wording never reaches the note.
8. **Draw the map** from the plan (Reference → Map), place it right after the title block, show it with two or three sentences on the route, and wait for the reader's approval before writing section 1.

## Phase 2: the section loop

1. **Write the next section only,** pitched from `calibration.md`; never write ahead of the reader's answers or add what the plan does not need. Write the section's key sentences first (principle 6), show them when the reader asked to be taught, then write the prose around them.
   - When the next node has a step the reader could guess, ask one prediction question in chat before writing it, and open the section by resolving the guess. When there is nothing to guess, skip it.
2. **Build:** `uv run scripts/build.py NOTE_DIR` (or `python scripts/build.py NOTE_DIR` after `pip install -r requirements.txt`), with `scripts/` taken from this skill's folder. The build lists every anchor it cannot find; fix those, rebuild, and look at a sample of the crops in `NOTE_DIR/_build/<name>_files/`: at least one each from single-column, two-column and slide sources.
3. **Review every figure** at full size after each render: no label crossing a line, arrow, border or another label; no legend over data; nothing clipped. Fix and re-render before embedding.
4. **Verify the page** in a browser (Reference → Verification): the new section as screenshots, a citation preview, the phone-width layout, zero `katex-error` elements, no display equation wider than the column, the new section at the Points level. Check every quote and citation against the extracted text.
5. **Deliver the section,** say which section is new, and wait for the reader to read it.
6. **Check the section** once they have read it.
   - Ask 2–4 questions in chat, one at a time, each chosen after the previous answer, with answer, confidence and one line of reasoning.
   - Each question targets one step of the section and is answerable from the note so far. Prefer questions that apply the step to a new case over questions that recite it.
   - In a multiple-choice question, each wrong option is the answer one specific wrong model gives, so that a miss names the paragraph to fix.
   - At a checkpoint, the questions combine several sections.
7. **Decide** from the answers, and say in one line what was decided:
   - **Landed:** advance the map's highlight and write the next node.
   - **One step shaky:** rewrite that paragraph, rebuild, and ask one fresh question on it in a new situation, never the same question.
   - **Foundation missing:** add the node to the plan and the map and write that section first.
   - **Already held:** cut the node from the plan and the map.
   - Update `calibration.md` with what the answers showed.
8. **Stop** when the reader sees the goal as obviously true, or says they are done (principle 10). Package on request (Reference → Packaging).

## Messages while reading

Between checks the reader sends three kinds of message. Each one recalibrates `calibration.md` for the rest of the note, not only the passage it names.

- **Words or notations they are unsure of.** Record which basics are missing and which phrasings confused them; revise the named section and pitch the sections not yet written the same way; place each new item by the table above. A missing foundation becomes a node in the plan and the map.
- **Conceptual questions.** Answer in chat first, with the derivation written out and a pointer to where the concept already appears in the note, and offer to fold the answer in. When asked, search the sources for citable passages, register the citations, mark anything of our own as ours, and place it by the table.
- **Requests to update.** Insert the new material, renumber sections and blocks, update every cross-reference (such as "Definition 1.3" becoming "Definition 1.6"), rebuild every output that already exists, re-verify, and report what changed section by section. Version control replaces backup copies of `content.html`.

## Fold levels, key sentences and Lecture Mode

Every note built with the template has four fold levels (keys 1–4: Full, Read, Points, Statements) and a "Lecture" button that plays the note one beat per click, with narration under the board and a laser pointer; a played note ends as the regular note at Read. The key sentences (`<k>`, Reference → Markup) decide what Points keeps and what a lecture writes on the board. Before writing a section that the reader will play, or rebuilding an old note, read `references/live-mode.md`.

A fix to the engine or template goes into `scripts/`, `assets/` and this file. A note picks up a template change when it is next rebuilt; `scripts/rebuild_all.py MANIFEST.json` rebuilds every note a manifest lists (see `examples/notes.json` in the repository).

## Reference

### Environment

`uv run scripts/build.py NOTE_DIR` installs the dependencies from the script's header on first use. Without uv: `pip install -r requirements.txt`. Only PyMuPDF is required; Pillow and fontTools with brotli shrink the single-file output; NumPy and Matplotlib draw figures. KaTeX and Computer Modern are downloaded once into `~/.cache/html-notes`. When `node` is on `PATH`, the build draws the math at build time, so it shows in viewers that do not run scripts; without `node`, the page draws it when it opens. When the CDNs in `notelib.py` are blocked, the engine falls back to the npm registry (KaTeX) and raw GitHub (fonts).

### Map

Write the map as Mermaid `graph TD` in `map.mmd`, generated from the plan: roots at the top, the goal at the bottom, `A --> B` meaning A must be understood before B. Labels are a few words; the precision lives in the plan.
- `classDef` styles: `held` (what the reader already holds, grey), `done` (sections written and checked, filled), `current` (the section being read, highlighted), `checkpoint` (double border), `goal`.
- Render with `mmdc -i map.mmd -o figures/map.svg -b white` (`npx -y @mermaid-js/mermaid-cli` when `mmdc` is absent).
- Embed as `<figure class="plot" id="map"><img src="figures/map.svg" alt="Map of the note"><figcaption><span class="sc">Map.</span> …</figcaption></figure>` right after the title block.
- Re-render after every decision in the loop.

### `cites.py` API

```python
import os
from notelib import config, source, pdf, link
HERE = os.path.dirname(os.path.abspath(__file__))
config(root=HERE, name="output_basename", title="Note Title", out=HERE)
source("roig", "Roig_2024.pdf", "Roig et al., PRB 110, 144412", "Roig",
       offset="144412-{p}", cols=2, share="https://doi.org/10.1103/PhysRevB.110.144412")
source("apx", "AppendixA.pdf", "Appendix A", "App. A", offset=-107)            # printed = PDF - offset
source("nr", "slides.pdf", "Seminar slides", "Slides")                         # no printed numbers
pdf("roig-eq1", "roig", 3, "§II.B, Eq. (1)", "The general minimal model", "change sign under the interchange")
pdf("nr-7", "nr", 7, "slide 7", mode="page")                                   # whole page preview
pdf("apx-A5", "apx", 2, "Eqs. (A.5)–(A.8)", "Including spin", None)            # to bottom of text
link("web-x", "Project page", "https://example.org/page", "quoted text from the page", "accessed 2026-01-01")
```

- **Handwritten or scanned pages** have no searchable text: cite them with `mode="page"`, or `frac=(top, bottom)` for a horizontal band given as fractions of the page height. When a book's printed page offset varies, pass `printed="482"` per citation.
- **`pdf(key, src, page, where, start, end, mode="crop", pad=(top, bottom))`.** The crop runs from the first match of `start` to the first later match of `end` on the 1-based PDF `page`, across the full text width; with `cols=2` it covers only the matched column. `start=None` begins at the top of the text and `end=None` ends at its bottom.
- **Anchors** are short phrases of ordinary words that appear once on the page. Ligatures (fi, fl), math glyphs and calligraphic letters don't match in search. When a quote starts on the previous page, cite both pages with two keys. To include an equation that follows a phrase, end on the next prose phrase after it, or use `end=None`. Check new anchors before a full build by rendering only the new keys with `notelib.render_crops`.
- **Default chip labels** are `Abbr p. <printed>`, or `Slides n` when there are no printed numbers; `[[key|label]]` overrides one.
- **Private material:** email links and unpublished sources get `private=True`; `--share` removes their links but keeps their previews.
- **Web pages** that cannot be downloaded as PDFs are cited with `link()`, whose `text` is a verbatim excerpt retrieved from the page.

### Markup in `content.html`

- **Citation:** `[[key]]` or `[[key|Gurrieri (1.2)]]`. Several in a row are fine: `[[nr-7|Slides 7]] [[nr-8|8]]`.
- **Sidenote:** `<sn>…</sn>`, numbered and italic in the right margin, inside a `<p>` right after the word it annotates.
- **Margin note:** `<en>…</en>`, unnumbered, before a table or at the start of a paragraph so that it aligns with the top.
- **Title block:** `<header class="titleblock"><h1>…</h1><p class="subtitle">…</p><div class="abstract"><p>…</p></div></header>`.
- **Parts** (a long note in one page): `<div class="part" data-part="II"><h1>Title</h1><p class="partsub">Lectures 5–8 · Homework 2</p></div>` between sections, with sections numbered continuously across parts.
- **Sections:** `<section><h2 data-num="2">Title</h2> … </section>`; `<h2 class="unnumbered">` for the source list; subsections `<h3 data-num="2.1">Title</h3>`.
- **Side outline:** built automatically from parts, `h2` and `h3` once the note has four or more headings: foldable, highlights the current section, pinned beside the text from 1400 px and behind the "☰ Outline" button below. Every heading gets a stable id (`part-II`, `sec-9`, `sec-9-1`).
- **Key sentences:** `<k>…</k>` around the sentence that carries a paragraph's step: one per paragraph, sometimes two, anywhere in the paragraph. Each one reads on its own, and a section's key sentences in order form its skeleton (principle 6).
  - The marks decide three things: key sentences render bold; the Points level keeps only them, with blocks, equations and figures; a lecture writes each `<k>` on the board as one beat and plays the rest of the paragraph as narration.
  - `class="key"` marks a whole paragraph or display as key. Use it rarely: Points never folds such a paragraph, so a note made of `p.key` paragraphs barely shrinks at Points.
  - Headings, `def`/`thm` blocks, display equations and figures stay at Points without a mark; proofs and explainer widgets stay folded and carry no marks.
  - Before rebuilding a note that has no `<k>`, mark one existing sentence per paragraph, words unchanged, and check at Points that the marked sentences read as the skeleton. Without marks a note still builds and plays, but its board holds only blocks, equations and figures, and the page offers no Points level.
- **Lecture Mode markup** (`<say>`, `at`, `ink`, `keep`, `\htmlId`, `check predict|ask`, `data-live`): `references/live-mode.md`.
- **Theorem-like blocks:** `<div class="env def|thm|ex|rem" data-label="Definition 2.1"><p><b>Name.</b> …</p></div>`. The `data-label` hangs in the left margin, and a block may contain lists.

  | Class | Style | Content |
  |---|---|---|
  | `def` | cerulean | definitions, conventions, reusable objects |
  | `thm` | dandelion | results and statements |
  | `ex` | black rule | worked examples, constructions, labeled illustrations of our own |
  | `rem` | unboxed, italic label | remarks |
  | `hw` | maroon | a homework problem statement, quoted and cited; its solution follows as `<details class="proof sol"><summary>Solution (official)</summary>…</details>` or "Solution (ours, checked symbolically)" |

- **Cross-references (automatic):** after KaTeX renders, the template links every plain-text mention of a numbered object in the note ("Theorem 3.6", "Lemma 4.3", "Definition 5.14", "Remark 3.9", "Figure 5.1", "Table 3.2", "Section 4", "§5.3", and "(4.5)" from `\tag{4.5}`) with a hover preview; a click scrolls there and opens any folded proof around it. Keys come from `data-label`, `\tag`, caption `.sc` numbers and `data-num`, so write references in exactly these forms. An equation number that belongs to another source sits in a chip label (`[[tong-x|Tong (3.5)]]`) or in `<span class="noref">…</span>`; a number right after a capitalized word or a possessive ("Tong (3.5)") is skipped, except after "Equation"/"Eq.", and nothing inside curly quotes is linked. Check with a DOM dump that every `a.xref` target exists.
- **Code and program output:** `<pre class="code">…</pre>` for input, `<pre class="code out">…</pre>` for output. Escape `<`, `>` and `&`.
- **Proof:** `<details class="proof"><summary>Proof</summary><p>…</p></details>`, directly after its statement.
- **Explainer widget:** `<details class="aside"><summary>Background: …</summary><p>…</p></details>`; the summary starts with "Notation:" or "Background:".
- **Figure:** `<figure class="plot"><img src="figures/x.png" alt="…"><figcaption><span class="sc">Figure n.m.</span> … [[cite]]</figcaption></figure>`. Class `narrow` for a small square figure (46% of the column); class `margin` for a small figure that supports one statement, placed immediately before that element as a direct child of the section (it renders at about 300 px, so use ≈20 pt fonts at a 5-inch figure width and few labels). Figures that carry an argument stay in the body. Figures render on a white panel in both themes.
- **Tables:** `<div class="tablewrap"><en>…</en><table><caption><span class="sc">Table 3.2.</span> …</caption>…</table></div>`, styled like booktabs.
- **Math:** KaTeX, `\( … \)` inline and `\[ … \tag{2.1} \]` for display; no `$`; `\lt` and `\gt` for `<` and `>`; wide displays broken with `\begin{aligned}`.
- **Source list:** `<section class="sources">` with `<ol class="biblio">`; local PDFs linked with `<a href="file.pdf">`, which `--share` rewrites to the public URLs.

### Verification

Open the reader's file through a local server (`python -m http.server` in its folder) in a browser, or use headless Chrome with `--screenshot` and `--dump-dom`. Keep test copies outside the note folder.
- **Overflow:** every `.katex-display` with `scrollWidth > clientWidth`, and tables wider than their wrapper, at widths 1600, 1440 (the pinned outline narrows the column from 1400 px) and 500; break each hit with `aligned`/`gathered`. No equation tag may sit on its equation.
- **Preview:** `show(document.querySelector('a.cite[data-k="KEY"]'))` opens a citation preview.
- **Themes:** `data-theme="light"` or `data-theme="dark"` on `<html>`. **Open widgets:** `open` on `details.aside`.
- **Headless screenshots of a later section:** headless Chrome paints blank frames after scrolling, so hide every sibling before the target section in a test copy and screenshot from the top.
- **Lecture Mode:** `LV.missing` lists pointer targets with no element; `lvNext()`, `lvFold(level)` and `lvFinish()` step through a lecture.
- **Handwritten sources:** render pages at 150 dpi, transcribe them with one agent per lecture, page by page, using a model that keeps daggers and indices, and check a sample by hand.
- **Offline single file:** Chrome with `--host-resolver-rules="MAP * ~NOTFOUND"` on a copy in an empty folder; check `document.querySelectorAll('.katex').length` and `document.fonts.check("16px 'Computer Modern Serif'")`.

### Packaging

- **Every build** with `out` set writes `<out>/<name>.html`: one offline file with crops, figures, KaTeX and fonts inlined and the math already drawn; its links open the local PDFs. (A `cites.py` without `out` keeps the older layout: `--standalone` writes `<name>_standalone.html` next to the sources.)
- **`--share`** writes `NOTE_DIR/_build/<name>_share.html` for other people.
  - Citations open the `source(share=...)` URLs, such as DOIs; without one, a citation only previews. A relative `share` path such as `"x.pdf#page={page}"` attaches a copy of the PDF under `_build/share/` (`share_dpi=200` shrinks one too large to publish).
  - `private` links such as emails lose their href.
  - Tell the note's owner what the file still contains: preview crops of unpublished material and the text of any email it quotes. Those decisions are theirs.
