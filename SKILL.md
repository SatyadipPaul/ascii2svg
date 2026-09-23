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
python3 scripts/ascii2svg.py diagram.txt --check --describe          # 1. validate; writes nothing
python3 scripts/ascii2svg.py diagram.txt -o diagram.svg --preset readme --json --brief   # 2. render
```

- `scripts/` is inside this skill's folder; use the full path to it if you are elsewhere.
  On Windows, `python` instead of `python3`. No packages are needed. If `ascii2svg` is on
  PATH (`pip install ascii2svg`), you can call that instead.
- **Write the diagram to a file** (or pipe it with `-`). Don't use `--text`: tool-call arguments
  turn newlines into literal `\n`, and the diagram collapses into one line of text.
- A markdown file is fine: the first ```` ``` ```` code block is used automatically. Add
  `--all-blocks -o DIR/` to render every diagram in it (other code blocks are skipped), or
  `--block N` for one. Several input files work the same way. Each warning's
  `source_line`/`source_col` points into the file you passed, and so does its hint.
- Always pass `--json`, or `--check`, which implies it. Every outcome is then one JSON object on
  stdout, usage errors included. Add `--brief` so the report doesn't embed the markup.

## Check, fix, render

1. Run `--check --describe` on your draft.
2. Read `status` and `summary`. They come first in the report.
3. For each warning, apply its `hint`: it names the character and the line/col in your file
   to move or change (`dangling_line`, `broken_join`). Re-run until `status` is `ok`.
4. Read `diagram.edges` (`{"from": {"name": "API"}, "to": {"name": "DB"}}`). Confirm every
   arrow connects what you meant; a missing edge usually means a misaligned arrow.
5. Render with the preset for the destination (below), then tell the user the `summary`.

**If a model drew the diagram (including you), add `--repair`.** It fixes ragged walls, emoji
width drift, connectors a column or two off and arrows that stop short, without changing any
words. `repair.edits` lists every change and `repair.text` is the corrected diagram: offer to
put it back in the user's file, so their source matches the picture.

| `status` | What to do |
|---|---|
| `ok` | Done. Share the file |
| `warnings` | Rendered, but likely misaligned: apply the hints (you can still share it if the user is happy) |
| `self_check_failed` | **Do not share the output.** Tell the user; it is a bug in the tool |
| `bad_input` / `usage_error` | Nothing rendered: read `error` and `hint`, fix the call |

- `escaped_newlines`: your input arrived as one line with literal `\n`. Write it to a file instead
  (or add `--unescape`).
- `unclosed_box`: an ASCII box that never closes stays plain text; the hint names the broken
  wall (e.g. a `<` where a `|` belongs). `no_structure`: box pieces but no box at all.
- A warning means evidence of a mistake. Lines ending at labels, sequence messages `│───▶│`,
  axis ticks and lifeline ends are fine and don't warn.
- `normalized`: what was cleaned up (tabs, odd spaces, code fence). Mention it if it matters.

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
- Keep a connector's column (or row) identical from start to arrowhead. Off-by-one is the
  most common mistake, and the `dangling_line` hint will point at it.

## Pick the preset from where the diagram is going

Most people won't name options. Choose from the destination; if it isn't clear, use `chat`.

| Destination | Preset | Same as |
|---|---|---|
| GitHub README, docs site, wiki that shows SVG | `--preset readme` | `--theme auto --color --animate flow` |
| Tall diagram (≈45+ rows) to scroll through, or "a page I can share" | `--preset page` + `-o NAME.html` | `--html --theme auto --color --animate scroll` |
| Slides | `--preset slides` | `--color --animate draw` |
| Slack, email, Jira, chat apps | `--preset chat --png` | `--color` (+ PNG, needs `pip install cairosvg`) |
| Print, PDF, formal docs | `--preset print` | `--style flat --square` |
| Dark-mode page or app | `--preset dark` | `--theme dark --color` |
| The user wants it plain | no preset | |

- Explicit flags override a preset: `--preset readme --no-color`, `--preset slides --theme dark`.
- `scroll` only works as a web page (an SVG shown as an image can't see the page scroll), so
  it is refused for `.svg` output. For a tall diagram going into a README, use `readme` there
  and offer the `page` version as well. The report's `tips` suggests this; pass it on.
- Animation never changes the final picture, stops under *reduce motion*, and PNGs are always
  the finished still drawing.
- Tell the user what you picked in one line, e.g. "animated, colour, follows dark mode",
  so they can ask for something else.

## Options

`--preset readme|slides|chat|print|dark|page` · `--check` · `--describe` · `--brief` · `--json` ·
`--color / --no-color` · `--theme light|dark|auto` · `--animate [draw|flow|scroll]` · `--html` ·
`--style glow|shadow|flat` · `--square` · `--png [PATH]` · `--strict` · `--unescape` ·
`--repair` · `--all-blocks` · `--block N` · `--accent #HEX` · `--font NAME` · `--width PX` ·
`--tab-size N` · `--title TEXT` · `--max-rows` / `--max-cols` (default 1000 × 400).
`--mcp` runs it as an MCP server (tools `render_diagram`, `check_diagram`) if the user wants it
wired into their editor: `claude mcp add ascii2svg -- ascii2svg --mcp`.
`--schema` prints all of this, and the report fields, as JSON.

For someone who'd rather not use a command line at all, point them to the browser playground: https://satyadippaul.github.io/ascii2svg/playground.html (paste, preview, download; nothing is uploaded).
