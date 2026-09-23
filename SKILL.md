---
name: ascii2svg
description: Render ASCII or Unicode box diagrams (architecture diagrams, flowcharts, call trees, box-and-arrow sketches, ┌─┐ or +--+ boxes) as a clean SVG in which every character keeps its exact position, optionally coloured, dark-mode aware, and animated (draws itself, pulses flow along the arrows). Use this whenever a text diagram needs to be shared, exported, embedded in docs, READMEs or slides, or pasted somewhere that breaks monospace alignment (Slack, email, Confluence, Jira) — even if the user only says "render this diagram", "make this look nice", "animate this diagram", "export this as an image", or "turn this into SVG".
---

# ascii2svg

Turns a text diagram into an SVG **1:1**: every character stays in its exact grid cell.
Box and line characters become real drawn lines; everything else stays the same text.
Each run reads the SVG back and checks it against the input, cell by cell, in every look.

## Run it

```bash
python3 scripts/ascii2svg.py diagram.txt -o diagram.svg --json
```

- Write the diagram to a file (or pipe it on stdin) rather than using `--text`: long
  multi-line arguments break in shells.
- A markdown file is fine: the first ```` ``` ```` code block is used automatically.
- Add `--png` to also get `diagram.png` (needs `pip install cairosvg`), useful where SVG
  isn't shown (e.g. email).

## Read the JSON report before you reply

| Field | What to do with it |
|---|---|
| `exit_code` / `ok` | `0` = done. `1` = bad input (read `error`). `2` = self-check failed: **do not share the SVG**; tell the user. `3` = only with `--strict`: warnings present |
| `roundtrip` | `"exact"` means the SVG matches the input cell for cell |
| `warnings` | Line ends that meet nothing (row/col are 1-based). Usually a misaligned source diagram: move the character to the right column, then re-run |
| `normalized` | What was cleaned up (tabs, odd spaces, code fence, colour codes). Mention it if it matters |
| `ascii_line_like_kept_as_text` | ASCII `- \| +` that were **not** drawn as lines because they don't attach to a box. If the user expected lines there, see below |

## What gets drawn

- Unicode lines `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ╭ ╮ ╰ ╯ ═ ║ ╔ ╗ ╚ ╝ ╪` and arrows `▼ ▲ ▶ ◀`: always.
- ASCII `+ - |` and arrowheads `v ^ < >`: only when they form a closed box or attach to
  one (directly, or through `+` junctions). Otherwise they stay text — so `a->b`,
  `--dry-run`, `user_id`, markdown tables and `|--` file trees are left exactly as written.

## Writing diagrams that render well

- Close every box: `+---+` / `|   |` / `+---+`, or `┌───┐` / `│   │` / `└───┘`.
- Keep one space between a label and the box wall.
- Use `+` where a connector meets a box edge or branches; end arrows with `v ^ < >`
  (or `▼ ▲ ▶ ◀`) touching, or one space from, the target box.
- A title can sit on a box's top edge: `+-- Title ---+`.

## Pick the look from where the diagram is going

Most people won't name options. Infer them from the destination; if it isn't clear, use
`--color` alone.

| Destination | Options |
|---|---|
| GitHub README, docs site, wiki that shows SVG | `--theme auto --color --animate` |
| Slides | `--color --animate draw` (or `--color --png` for a still) |
| Slack, email, Jira, chat apps, anything that won't show SVG | `--color --png` |
| Print, PDF, formal docs | `--style flat --square` |
| Dark-mode page or app | `--theme dark --color` |
| The user wants it plain | no options |

- `--animate` (= `flow`): the diagram draws itself, then pulses travel along every arrow.
  `draw` does the drawing only. Animation never changes the final picture, stops under
  *reduce motion*, and needs no JavaScript (it plays in a plain `<img>`).
- `--color`: each group of boxes gets its own soft hue; arrows turn accent blue.
- `--theme auto` follows the reader's light/dark setting.
- PNGs are always the finished, still drawing (the `auto` theme becomes light).
- Tell the user what you picked in one line, e.g. "animated, colour, follows dark mode",
  so they can ask for something else.

## Options

`--color` · `--theme light|dark|auto` · `--animate [draw|flow]` ·
`--style glow|shadow|flat` (default glow) · `--square` (square corners) · `--png [PATH]` ·
`--strict` · `--tab-size N` (default 4) · `--title TEXT` · `--max-rows` / `--max-cols`
(default 1000 × 400)
