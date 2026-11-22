# Lecture Mode: a note played as a lecture

Read this before writing a section that the reader will play, or before rebuilding an older note. The picture behind the mode is a lecturer with a slide deck and a laser pointer: the board holds only the core of the argument, the spoken narration falls below it, and a finished board slides up and becomes the regular note. The engine is `assets/lecture.css` and `assets/lecture.js`, which the build inlines into `assets/template.html`.

## What the reader sees

- The page opens on the title and the first paragraph of the abstract. Each click, Space or → plays one beat; ← goes back; a reload resumes at the same beat.
- On the first visit to a note that opens in a lecture, a small card lists these controls; the first step of the lecture or "Got it" closes it, and "?" brings it back.
- A board beat writes one thing into the note: a key sentence, a statement block, a display equation, a figure.
- A narration beat shows one sentence under the last block written, and the pointer travels to what the sentence is about.
- When a section ends, the next heading moves to the top of the screen and the finished section stays above as the note.
- After the last beat the page is the regular note at the Read level. The "Lecture" button starts the lecture again.

## The one rule

An element shows when the reader has played it and the fold level keeps it. Outside a lecture every element counts as played, so a regular note and a played note are the same page.

The beat being played is always readable. When the fold level keeps it, it appears in its own place; when the level folds it away, it appears in the narration block until the next click.

| Level (key) | Keeps |
|---|---|
| Full (1) | everything, with every proof open |
| Read (2) | the note as written |
| Points (3) | key sentences, blocks, equations, figures |
| Statements (4) | headings, definitions, results |

A lecture starts at Points (at Read in a note without key sentences) and ends at Read. Once the reader picks a level, the page never changes it for them.

## Markup

Nothing is needed to play an existing note: every `<k>`, `p.key`, block, display and figure is a board beat, and each run of other text in a paragraph is one narration beat. For a section written for the lecture, add:

- `data-live` on `<header class="titleblock">`: the note opens in the lecture.
- `<say>…</say>` around each narration sentence, in the paragraph where the sentence belongs in the note.
- `at="id"`, `ink="dot|line|box|hl"` and `keep` on a `<say>`, a `<k>` or a board element. `at` takes one or more ids; without `at`, the pointer marks the element itself. `keep` leaves the mark in the note after the lecture.
- `\htmlId{id}{…}` around a term inside an equation, or `<span id="…">` around words, to make a target. `\htmlId` needs KaTeX's `trust` option, which both the build and the page enable.
- `<div class="check predict">` with a question and a list whose items each end in `<span class="r">…</span>`, the reply to that choice.
- `<div class="check ask">` with one question. The page adds an answer box, a confidence field and a button that copies the answer for the chat.

```html
<p class="disp">\[ g_{\mu\nu}=\htmlId{m-re}{\mathrm{Re}\langle\partial_\mu u|\partial_\nu u\rangle}-\htmlId{m-aa}{A_\mu A_\nu} \]</p>
<p><say at="m-re" ink="dot">…one sentence about the first term.</say></p>
<p class="key" at="m-aa" ink="box" keep>Subtracting \(A_\mu A_\nu\) removes …</p>
```

**How the pointer finds its target.** The page resolves each `at` id with `getElementById`, takes the union of the bounding boxes of the visible glyphs inside it (equation tags and KaTeX's hidden MathML excluded), and draws the mark in an ink layer laid over the page. Kept marks are redrawn when the layout changes.

## Writing for the lecture

- The board is the skeleton of the section (SKILL.md, note principles): the reader must be able to follow the section from the board alone, without anyone talking.
- A narration beat carries one step and points at one target. It states a relation between things on the board, or a consequence that the reader can check in one line against what the board shows; anything longer belongs in the note's prose or a folded proof.
- The reader later reads the narration as prose without the pointer, so each sentence must read on its own, as a key sentence does.
- Sources stay out of the narration as actors: a narration sentence states the physics, and the citation chip sits on the board item it supports.
- The first board starts from the floor that calibration found (SKILL.md, Phase 1).
- A mark with `keep` is permanent emphasis in the note, so keep few: a boxed equation stays a box.
- A prediction question of the section loop becomes a `check predict`, placed before the step it predicts. The first check question after a section becomes a `check ask` at the end of the section; follow-up questions stay in the chat, because each one is chosen from the previous answer. Both kinds of check leave the page when the section ends, so the finished note holds no check questions.
- Deliver one section at a time, as in the section loop. A lecture that the reader finished resumes at the new section after it is added.

## Upgrading an older note

Rebuild the note with `scripts/build.py`; it needs no new markup to play.

- How well a note plays depends on its `<k>` marks. Without them, the board holds only blocks, equations and figures, every prose paragraph is one narration beat, and the page offers no Points level. Before rebuilding a note without `<k>`, mark one existing sentence per paragraph as SKILL.md describes (words unchanged).
- Adding `<say>`, pointer targets or checks to an old note is new writing; do it only for a note the reader wants to play.

## Checks before delivery

- The browser console lists every `at` id that has no element ("live mode: no element with id …"); `LV.missing` holds the same list.
- Step through the new section with `lvNext()` and look at each pointer target and each kept mark at the Points and Read levels (`lvFold("points")`, `lvFold("read")`).
- After `lvFinish()`, at the Read level, the note shows every sentence and no check question.
