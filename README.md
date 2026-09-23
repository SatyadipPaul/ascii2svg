# ascii2svg

**Your text diagrams, drawn properly. Every character stays exactly where you put it.**

[**Try it in your browser**](https://satyadippaul.github.io/ascii2svg/playground.html) · [Live demo](https://satyadippaul.github.io/ascii2svg/) · [Scroll demo](https://satyadippaul.github.io/ascii2svg/architecture.html) · [Download the Claude skill](https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill)

<p align="center">
  <img src="https://satyadippaul.github.io/ascii2svg/how-it-works.svg" alt="ascii2svg pipeline: your diagram, find boxes and arrows, draw, read the SVG back, compare cell by cell, ready to share" width="640">
</p>

You sketch a diagram in plain text, in a README, a code comment, a chat with an AI, or a
notes app. It looks right in a monospace font and falls apart everywhere else: Slack,
email, Confluence, slides, a phone.

`ascii2svg` turns it into a crisp SVG that draws itself, follows your reader's light or dark
mode, and shows data moving along the arrows. It is still **1:1**: every run reads its
own SVG back and checks it against your text, cell by cell. If anything moved, it tells you.

## Type this…

```
+------------+     +------------+     +------------+     +-------------+
|    Idea    |---->|   Draft    |---->|   Review   |---->|   Publish   |
+------------+     +------------+     +-----+------+     +-------------+
                         ^                  |
                         |                  |
                         +------------------+
                           needs changes
```

## …get this

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/workflow.svg" alt="The same workflow rendered: four tinted boxes, arrows, and a feedback loop from Review back to Draft" width="720"></p>

```bash
python3 scripts/ascii2svg.py workflow.txt -o workflow.svg --color --theme auto --animate
```

Plain `+ - |` became real lines, `v ^ < >` became arrowheads, and the words stayed words.
It works just as well with Unicode box characters (`┌─┐ │ └─┘ ╭╮ ═║ ▶`).

## Who it's for

**If you don't write code:** open the [playground](https://satyadippaul.github.io/ascii2svg/playground.html), paste your diagram, pick where it's going, and download the SVG, PNG or a web page. It runs entirely in your browser (Python compiled to WebAssembly via Pyodide); nothing is uploaded. Or ask Claude. With this repo installed as a skill, say
*"turn this diagram into an image for my slides"* or *"make this look nice for our wiki"*,
and it picks the options for where the diagram is going, checks the result, and hands you the file.
Nothing to learn.

**If you do:** it's one Python file with no dependencies. It reads a file, stdin, or `--text`, and
writes an SVG plus a JSON report that an agent or a CI job can check (`exit_code`, `roundtrip`, `warnings`).
It never guesses: a character it isn't sure about stays text.

## Pick a look

Same diagram, same guarantee, five ways:

| Default | Colour | Dark | Print | Alive |
|:-:|:-:|:-:|:-:|:-:|
| <img src="https://satyadippaul.github.io/ascii2svg/looks/default.svg" width="150" alt="default look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/color.svg" width="150" alt="colour look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/dark.svg" width="150" alt="dark look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/flat.svg" width="150" alt="flat print look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/flow.svg" width="150" alt="animated look"> |
| *(no options)* | `--color` | `--theme dark`<br>`--color` | `--style flat`<br>`--square` | `--animate`<br>`--color`<br>`--theme auto` |

| Option | What it does |
|---|---|
| `--color` | Soft tints grouped by what contains what: each top-level group gets its own hue, nested boxes keep it. Arrows turn accent blue. |
| `--theme light\|dark\|auto` | `auto` follows the reader's system light/dark setting, which suits GitHub READMEs and docs sites. |
| `--animate draw` | The diagram draws itself once, top to bottom: lines are sketched in accent blue and settle to ink, boxes fade in, arrowheads pop. |
| `--animate flow` (or bare `--animate`) | `draw`, then glowing pulses keep travelling along every connector toward its arrowhead, so readers can see where things go. |
| `--animate scroll` | For tall diagrams, as a web page: each part appears as the reader scrolls to it, and long connectors grow downward with the scroll. See below. |
| `-o page.html` (or `--html`) | A standalone web page with the diagram inline. Double-click to open, or email it. |
| `--style glow\|shadow\|flat` | Depth under the boxes. The glow shrinks automatically so it never sits behind a label. |
| `--square` | Keep corners square (they are rounded by default). |
| `--accent #hex` · `--font NAME` · `--width PX` | Your brand colour for arrows and animation, a font to try first (e.g. `JetBrains Mono`), and the output width. None of them affect the 1:1 check. |

The animation is careful about where it runs:

- **It never changes what's drawn.** An animated file is the static file plus timing. When
  the animation ends, you're looking at exactly what the self-check verified. Tools that
  don't play animation (PNG export, most editors) show the finished drawing.
- **It respects the reader.** With *reduce motion* turned on in the OS, nothing moves.
- **`draw` and `flow` need no JavaScript.** They use CSS and SVG `<animate>` only, so they play
  inside a plain `<img>` tag, which is how GitHub, Notion and most docs sites show images.
- **Hover a box** in a browser and it lights up. That helps when you're presenting.

## Tall diagrams: reveal as you scroll

A 70-row architecture diagram drawn on a timer finishes before anyone scrolls down to it.
With `--animate scroll`, the diagram unfolds with the reader instead:

```bash
python3 scripts/ascii2svg.py architecture.txt -o architecture.html --color --theme auto --animate scroll
```

- Boxes and labels fade in as they reach the lower edge of the screen.
- Long vertical connectors are drawn *by the scroll*: they grow downward in accent blue as you
  read, then settle to ink.
- Each flow pulse starts once its whole route is on screen.
- With *reduce motion* on, the page shows the finished diagram.

**Why a web page, not just an SVG?** An SVG shown as an image (which is how GitHub READMEs,
Notion and most docs sites show them) can't see the page it sits in, so it can't know how
far you've scrolled. CSS scroll timelines don't drive SVG shapes either: we tested it, and
Chromium leaves them inactive. So `scroll` writes an `.html` page with the SVG inline and about
2 KB of plain JavaScript (IntersectionObserver and CSS animations, no libraries). It uses only
standard browser features and works offline, though so far it has been tested in Chromium only. `--animate scroll` with a plain `.svg` output
is refused with an explanation. The SVG inside the page is the same self-checked drawing; the
script only decides *when* each part appears.

**Try it:** [open the scroll demo](https://satyadippaul.github.io/ascii2svg/architecture.html) and scroll.
It's [`docs/architecture.html`](https://github.com/SatyadipPaul/ascii2svg/blob/main/docs/architecture.html), served by GitHub Pages.

## Where is it going?

| Destination | Use |
|---|---|
| GitHub README, docs site | `--theme auto --color --animate`, then commit the `.svg` |
| A tall diagram people will scroll through, or a page to share | `-o diagram.html --color --theme auto --animate scroll` |
| Slides (Keynote, Google Slides, PowerPoint) | `--color --animate draw` for a live build. For a still, `--color --png` |
| Slack, email, Jira, anywhere SVG isn't shown | `--color --png` (needs `pip install cairosvg`). PNGs are always the finished frame |
| Printed docs, a PDF | `--style flat --square` |
| Dark-mode apps | `--theme dark --color` |

## A bigger one

The flows follow the real wiring: through junctions, down to both branches of a fan-out, and
across the edge of a container.

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/architecture.svg" alt="A 72 by 96 character architecture diagram of an order platform, rendered with colour and flow animation" width="760"></p>

<details><summary>The text it came from (72 × 96 characters)</summary>

See [`tests/fixtures/complex_unicode.txt`](https://github.com/SatyadipPaul/ascii2svg/blob/main/tests/fixtures/complex_unicode.txt). 28 boxes, 18 arrows, a
call tree and double-line borders, all drawn from plain text.

</details>

## Install

Python 3.9+ and nothing else:

```bash
pip install ascii2svg                 # adds the `ascii2svg` command and the `ascii2svg` module
pip install "ascii2svg[width,png]"    # optional: wcwidth (character widths) + cairosvg (--png)
```

It is a single file with no dependencies, so you can also just copy
[`scripts/ascii2svg.py`](https://github.com/SatyadipPaul/ascii2svg/blob/main/scripts/ascii2svg.py) into your project.

**As a Python library:**

```python
import ascii2svg

svg, report = ascii2svg.render(open("diagram.txt").read(), color=True, theme="auto", animate="flow")
assert report["roundtrip"] == "exact"          # the 1:1 self-check passed
open("diagram.svg", "w", encoding="utf-8").write(svg)

page, report = ascii2svg.render(text, color=True, animate="scroll", html=True)   # a scroll-reveal page
```

`render()` takes the same options as the CLI (`style`, `square`, `theme`, `color`, `animate`, `html`,
`title`, `tab_size`) and returns the markup plus the same report as `--json`. It raises `ValueError`
for empty or oversized input and for unknown options.

**As a Claude skill:** download [`ascii2svg.skill`](https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill)
from the latest release (or build it: `python3 tools/package_skill.py` → `dist/ascii2svg.skill`), then:

- **claude.ai / Claude desktop:** Customize → Skills → upload `ascii2svg.skill`.
- **Claude Code:** unzip it into `~/.claude/skills/` (you get `~/.claude/skills/ascii2svg/`).

[`SKILL.md`](https://github.com/SatyadipPaul/ascii2svg/blob/main/SKILL.md) tells Claude when to use it, which look fits which destination (including
`scroll` pages for tall diagrams), and how to read the report before handing you the file.

## Usage

```
ascii2svg [INPUT ...] [-o OUT.svg|OUT.html|DIR/] [--preset NAME] [--json] [--check] [--describe] [--brief]
          [--color] [--theme light|dark|auto] [--animate [draw|flow|scroll]] [--html]
          [--style glow|shadow|flat] [--square] [--accent #HEX] [--font NAME] [--width PX]
          [--all-blocks] [--block N] [--unescape] [--strict] [--schema] [--mcp]
          [--png [PATH]] [--strict] [--text TEXT] [--tab-size N] [--title TEXT]
```

| Input | How |
|---|---|
| File | `ascii2svg diagram.txt -o out.svg` |
| stdin | `cat diagram.txt \| ascii2svg > out.svg` |
| Inline | `ascii2svg --text "$DIAGRAM" --json` (the SVG comes back inside the JSON when there's no `-o`) |
| Markdown | The first ```` ``` ```` code block is used. Prose around it is dropped (and reported) |

stdout is always exactly one thing: the SVG (or the page, with `--html`), or (with `--json`) the report. A one-line
summary goes to stderr.

## What gets drawn

| Source | Drawn as lines when… | Otherwise |
|---|---|---|
| `─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╪`, `▼▲▶◀` | always | – |
| ASCII `+` `-` `\|` | they form a closed box, or attach to one directly or through `+` junctions | stay text |
| ASCII `v ^ < >` | they end a line that is drawn, or point at a box (touching, or one space away) | stay text |

When unsure, a character stays text, so the worst case is the character itself in its own cell,
never a wrong shape. `a->b`, `--dry-run`, `user_id`, `C:\temp`, markdown tables and `|--` file
trees all stay exactly as written.

## How 1:1 is guaranteed

Every run parses the SVG it just wrote (lines, curves, arrowheads, text positions) back into a
character grid and compares it with the input, cell by cell. ASCII characters may only appear as
the line they stand for (`-`→`─`, `|`→`│`, `+`→corner or junction, `v`→`▼`). Any mismatch is
exit code 2. This covers every look, including animated ones and the still frame used for PNGs.

## Built for agents

Every outcome is machine-readable, nothing hangs, and every problem comes with a fix.

**The loop:** draft the diagram, check it, fix what the hints say, then render.

```bash
ascii2svg draft.txt --check --describe      # validate + structure; writes nothing
ascii2svg draft.txt -o out.svg --preset readme --json --brief
```

```json
{"status": "warnings",
 "summary": "Rendered 2 boxes and 0 arrows (8x8); 1:1 self-check exact. 1 warning, first: row 4 col 4 (dangling_line): the arrowhead 'v' at row 5 col 5 is one column right; move one of them so they line up",
 "exit_code": 0, "...": "..."}
```

- **One JSON object on stdout for every outcome** with `--json` (or `--check`), including usage
  errors: `{"status": "usage_error", "hint": "'--colour': did you mean --color?"}`. `status` and
  `summary` come first, so a truncated report still says what happened. The JSON is ASCII-safe,
  so any harness on any OS decodes it the same way.
- **Warnings you can act on:** each has a stable `code`, a 1-based `row`/`col`, the source `line`,
  and a `hint`. When a line misses its partner by one cell, the hint says where it is.
- **Silently wrong input is caught:** one-line input with literal `\n` (`escaped_newlines`; fix it with
  `--unescape`), and ASCII boxes that never close (`unclosed_box`: the hint names the broken wall,
  e.g. "its left wall at line 5 col 23 is '<'").
- **No false alarms on well-formed diagrams:** a line may end at a label, meet another line
  side-on (sequence messages `│───▶│`, drawn touching), or stop in open space (axis ticks,
  lifeline ends). A warning means there is evidence of a mistake: a partner one cell off, a
  line that stops just short of a box, a junction with a missing arm, or a box that never closes.
- **`--describe`** adds what the diagram *says*: boxes (name, title, text, position, parent) and
  edges (`Gateway → Orders`), so you can check that the picture means what you intended.
- **`--preset readme|slides|chat|print|dark|page`** picks the look from the destination.
  Explicit flags still win (`--preset readme --no-color`).
- **`--brief`** never embeds the markup; without it, `--json` without `-o` returns the markup
  inline, which can run to 150 KB for a large diagram.
- **No hangs:** if you forget the input and stdin stays silent, it fails after 5 seconds with
  `bad_input`. Pass `-` to wait for stdin on purpose.
- **`--schema`** prints every option (kind, choices, default), preset, exit code, warning code and
  report field as JSON: enough to build a correct tool definition without reading docs.

### Report fields

| Field | Meaning |
|---|---|
| `status` | `ok` · `warnings` · `self_check_failed` · `bad_input` · `usage_error` |
| `summary` | One sentence to pass on to the user |
| `exit_code`, `ok` | See exit codes; `ok` is false only when the self-check failed |
| `roundtrip` | `exact`: the output was read back and matches the input cell for cell |
| `warnings` | `{code, row, col, char, line, issue, hint}`; codes: `dangling_line`, `broken_join`, `unclosed_box`, `escaped_newlines`, `no_structure` |
| `diagram` | With `--describe`: `{boxes: [...], edges: [{from, to}]}`; an endpoint is `{box, name}`, `{text}` or `{cell}` |
| `rows`, `cols`, `boxes`, `arrowheads`, `flows`, `text_cells` | What was found |
| `style`, `theme`, `color`, `animate`, `html`, `preset` | The look that was rendered |
| `ascii_drawn_as_lines`, `ascii_line_like_kept_as_text` | How ASCII `- \| + v ^ < >` were read |
| `normalized` | Every clean-up applied (tabs, odd spaces, zero-width and control characters, colour codes, code fence, indentation, bad UTF-8, `--unescape`) |
| `tips` | Suggestions, e.g. `--animate scroll` when a timed animation would finish off-screen |
| `svg` / `html`, `png` | Output paths, or the markup itself when there is no `-o` (unless `--brief` / `--check`) |
| `self_check_problems` | Only when `roundtrip` isn't exact |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | OK (warnings allowed) |
| 1 | Bad input or usage: read `error` and `hint` |
| 2 | Self-check failed: the output is not 1:1. Don't use it |
| 3 | `--strict` and there were warnings |

### Many diagrams at once

```bash
ascii2svg README.md --all-blocks -o diagrams/ --preset readme   # every diagram in the file
ascii2svg docs/*.txt -o out/ --check                            # several files, one report each
ascii2svg README.md --block 3 -o flow.svg                       # just the third code block
```

Code blocks without lines or boxes (your `bash` and `python` examples) are skipped and listed under
`skipped`. Output files are named after the input (`README-2.svg` for its second code block). The
report holds one entry per diagram under `diagrams`, and its top-level `status`, `summary` and
`exit_code` cover the whole batch. Every warning also carries `source_line`/`source_col`: its position
in the file you passed, not in the extracted block, and the hint uses the same numbers.

### As an MCP server

```bash
claude mcp add ascii2svg -- ascii2svg --mcp          # Claude Code
```

```json
{"mcpServers": {"ascii2svg": {"command": "ascii2svg", "args": ["--mcp"]}}}
```

The second form works for Claude Desktop, Cursor, and any other MCP client. Two tools, no dependencies:

- **`check_diagram`** validates a diagram and returns the report, with boxes and edges; it writes nothing.
- **`render_diagram`** writes `output_path` (`.svg`, or `.html` for a page) with any preset or style option.

The diagram travels as a JSON string, so the escaped-newline problem can't happen. Tested against the
official MCP Python SDK.

### As a tool in any agent framework

Pass the diagram on stdin (or as a file), never through `--text`: escaped newlines are the most
common way agents break diagrams.

```python
import json, subprocess

def render_ascii_diagram(diagram, output_path, preset="readme", describe=False):
    args = ["ascii2svg", "-", "-o", output_path, "--preset", preset, "--json", "--brief"]
    p = subprocess.run(args + (["--describe"] if describe else []), input=diagram.encode(), capture_output=True)
    return json.loads(p.stdout)          # always one JSON object, including on errors
```

Or skip the subprocess and call the library: `svg, report = ascii2svg.render(diagram, preset="readme")`.

## Tests

```bash
python3 tests/test_ascii2svg.py        # or: python3 -m pytest tests
python3 docs/build.py                  # regenerate every image in this README
```

48 tests over 17 test diagrams:
- round-trip in every style and every look
- animation that ends on the static drawing and respects reduced motion
- flow routes that start at the right box
- scroll reveal driven by the page, with no script inside the SVG
- colour groups
- the ASCII traps
- glow never behind a label
- planted faults that must be caught
- byte-identical repeat runs
- width fallback vs `wcwidth`
- CLI behaviour, including UTF-8 output on Windows consoles, and the `render()` library API
- the agent contract: JSON usage errors (never exit 2), status and summary, near-miss hints,
  escaped-newline and broken-box detection, `--describe` edges, presets, `--schema`, and no hang
  on a forgotten input
- every diagram in a markdown file, several inputs, positions mapped back to the file, style
  options, and the MCP server's protocol
- the browser playground runs exactly this module, and every playground example round-trips
- no false alarms on sequence diagrams, timelines, charts with ticks and dashed boundaries, while
  real mistakes (a gap before a box, a broken wall) still warn; touching lines are drawn touching

They pass with and without the optional packages.

## License

[MIT](https://github.com/SatyadipPaul/ascii2svg/blob/main/LICENSE). Use it, change it and ship it, commercially too; keep the copyright notice.

## Not yet

- **Auto-repair of misaligned diagrams.** It warns with row/column instead.
- **ASCII rounded corners (`.-'`) and diagonals (`/ \`).** These stay text.
- **Free-floating ASCII connectors that touch no box** (e.g. `A ---> B` between plain words). These stay text.
- **An MCP server and a JS/npm port.**
- **Every renderer checked.** The original static look was verified in cairo and resvg. The new
  looks (colour, themes, animation) have been checked in Chromium only so far, not yet in
  Firefox, Safari, or through cairo for `--png`.
