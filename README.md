<p align="center">
  <a href="https://satyadippaul.github.io/ascii2svg/playground.html"><img src="https://satyadippaul.github.io/ascii2svg/banner.svg" width="900" alt="ascii2svg, in block letters with a drop shadow, above three boxes: your text diagram, ascii2svg (repair, draw, self-check), and SVG exactly 1:1"></a>
</p>

<h3 align="center">Your text diagrams, drawn properly. Every character stays exactly where you put it.</h3>

<p align="center">
  <a href="https://pypi.org/project/ascii2svg/"><img src="https://img.shields.io/pypi/v/ascii2svg?style=flat-square&color=0969da&label=pypi" alt="PyPI version"></a>
  <a href="https://pypi.org/project/ascii2svg/"><img src="https://img.shields.io/pypi/pyversions/ascii2svg?style=flat-square" alt="Python 3.9+"></a>
  <a href="https://github.com/SatyadipPaul/ascii2svg/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/SatyadipPaul/ascii2svg/test.yml?branch=main&style=flat-square&label=tests" alt="Tests"></a>
  <img src="https://img.shields.io/badge/dependencies-0-2ea44f?style=flat-square" alt="Zero dependencies">
  <a href="#built-for-agents"><img src="https://img.shields.io/badge/MCP-ready-8250df?style=flat-square" alt="MCP server"></a>
  <a href="https://github.com/SatyadipPaul/ascii2svg/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SatyadipPaul/ascii2svg?style=flat-square" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://satyadippaul.github.io/ascii2svg/playground.html"><b>Playground</b></a> ·
  <a href="https://github.com/SatyadipPaul/ascii2svg/blob/main/GUIDE.md"><b>Guide</b></a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#gallery">Gallery</a> ·
  <a href="#llm-diagrams-fixed">Fix LLM diagrams</a> ·
  <a href="#built-for-agents">For agents</a> ·
  <a href="https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill">Claude skill</a>
</p>

<p align="center">
  <a href="https://satyadippaul.github.io/ascii2svg/playground.html"><img src="https://satyadippaul.github.io/ascii2svg/demo.gif" width="880" alt="Screen recording of the ascii2svg playground: a misaligned, model-drawn diagram gets 10 warnings, Fix alignment makes it render cleanly, a diagram is typed and renders live, then a tour of combination and Mermaid-style diagrams"></a>
  <br><sub>The <a href="https://satyadippaul.github.io/ascii2svg/playground.html">playground</a> runs entirely in your browser: fix a model's misaligned diagram, type one live, browse the gallery.</sub>
</p>

You sketch a diagram in plain text: in a README, a code comment, a chat with an AI. It looks
right in a monospace font and falls apart everywhere else (Slack, email, Confluence, slides,
a phone). **ascii2svg turns it into a crisp SVG** that draws itself, follows your reader's light or
dark mode, and shows data moving along the arrows.

It never guesses. Every run reads its own SVG back and checks it against your text, cell by cell,
so what you drew is exactly what you get. And the banner at the top of this page? That's
[plain text](https://github.com/SatyadipPaul/ascii2svg/blob/main/docs/examples/banner.txt) too.

## Highlights

- **Faithful, provably** // every character lands in its exact cell, verified by reading the SVG back. A mismatch is an error, never a quiet surprise.
- **Fixes LLM diagrams** // `--repair` lines up the walls, connectors and arrowheads a chat model got one column wrong, without touching a word.
- **Alive** // lines draw themselves, pulses flow along arrows, tall diagrams unfold as you scroll. Nothing moves for readers who ask for reduced motion.
- **Trees that fold** // call trees, file trees, `npm ls` / `cargo tree` output and mind maps become an SVG whose branches fold when clicked, with a colour per branch. No JSON, no DSL: the text you already have.
- **Small** // one element per word, not per letter, and one path per line style: files are about half the size they were in 1.15.
- **More than boxes** // flowcharts, sequence and state diagrams, C4, UML, ER crow's feet, Gantt and bar charts, diamonds, dashed lines.
- **Agent-native** // one JSON report for every outcome, hints that say exactly what to move, an MCP server and a Claude skill.
- **Zero dependencies** // one Python file for Python 3.9+. The same file runs in your browser and on npm via WebAssembly.

## Quick start

> **New here?** The [guide](https://github.com/SatyadipPaul/ascii2svg/blob/main/GUIDE.md) walks you through it in plain language: how to run it,
> how to draw diagrams that render well, which look to pick, and what to do when something
> doesn't come out as you meant.

**In your browser**, nothing to install: open the [playground](https://satyadippaul.github.io/ascii2svg/playground.html), paste a diagram, pick where it's going, download SVG, PNG or a web page. Nothing is uploaded.

**From the command line:**

```bash
pip install ascii2svg
ascii2svg diagram.txt -o diagram.svg --preset readme     # colour, light/dark, animation
```

**From JavaScript**, no Python needed: `npm install @satyadip28/asciitosvg` (see [Install](#install)).

**With Claude:** add the [skill](https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill),
then just ask *"turn this diagram into an image for my slides"*. Or connect the MCP server:
`claude mcp add ascii2svg -- ascii2svg --mcp`.

### Type this…

```
+------------+     +------------+     +------------+     +-------------+
|    Idea    |---->|   Draft    |---->|   Review   |---->|   Publish   |
+------------+     +------------+     +-----+------+     +-------------+
                         ^                  |
                         |                  |
                         +------------------+
                           needs changes
```

### …get this

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/workflow.svg" alt="The same workflow rendered: four tinted boxes, arrows, and a feedback loop from Review back to Draft" width="720"></p>

Plain `+ - |` became real lines, `v ^ < >` became arrowheads, and the words stayed words.
Unicode box characters (┌─┐ │ └─┘ ╭╮ ═║ ▶) work just as well.

## LLM diagrams, fixed

Ask any chat model for an architecture diagram and the boxes rarely line up: an emoji counted
as one column instead of two, a wall one space short, a connector that drifts sideways
between rows. `--repair` puts them back:

- **Boxes:** walls, corners and edges up to 12 columns off move into line. A box whose words
  don't fit (a long label, or emoji counted as one column) grows to fit them, all rows at once.
- **Connectors:** a piece one or two cells to the side moves into line, and so does a whole
  half of a line that drifted 3-6 columns. Gaps of a cell or two are filled, and an arrow that
  stops short of its box is carried on until it touches (`short_arrow` warns about it first).

| As the model wrote it | `--repair` |
|:-:|:-:|
| <img src="https://satyadippaul.github.io/ascii2svg/llm-before.svg" width="400" alt="An LLM-drawn diagram rendered as-is: three of five boxes not recognised, broken walls, a stray line"> | <img src="https://satyadippaul.github.io/ascii2svg/llm-after.svg" width="400" alt="The same diagram after --repair: five tinted boxes, clean connectors"> |
| 2 of 5 boxes recognised, 10 warnings | 5 boxes, 0 warnings, 5 fixes |

```bash
ascii2svg diagram.txt -o diagram.svg --repair --json
```

```json
{"status": "ok", "summary": "Repaired 5 misalignments. Rendered 5 boxes and 3 arrows (22x51); 1:1 self-check exact.",
 "repair": {"edits": [{"line": 2, "col": 23, "fix": "moved the right wall '│' 1 col left"},
                      {"line": 6, "col": 12, "fix": "moved '│' 1 col left to line it up"}, "..."],
            "text": "┌─────────────────────┐\n│  📱 Mobile app      │\n..."}}
```

- **What it never does:** change your words. Only line characters and spaces move or appear:
  into empty cells, or, when a box grows, along that box's own connector, which gets shorter.
  A test strips every line character from each row, before and after, and checks that what
  remains is identical.
- **What you get back:** every edit with its line and column, and the corrected text in
  `repair.text`, ready to paste back where the diagram came from. Diagrams that were already
  right come back untouched.

In the playground, a diagram with warnings shows a **Fix alignment** button.

## Trees and mind maps that fold

Call trees, dependency trees, file trees and mind maps are usually drawn with a JavaScript library
fed a hand-written JSON tree. Here the tree *is* the text: what `tree`, `npm ls` or `cargo tree`
print, a call tree from a profiler or an LLM, or a mind map you sketch with `├──` and `╰──`.

<p align="center"><a href="https://satyadippaul.github.io/ascii2svg/mindmap.svg"><img src="https://satyadippaul.github.io/ascii2svg/mindmap.svg" width="820" alt="A decision-making mind map drawn by ascii2svg: the root on a dark pill, five main branches each in its own colour, rounded branches fanning out to the right"></a>
<br><sub>Plain text (<a href="https://github.com/SatyadipPaul/ascii2svg/blob/main/docs/examples/mindmap.txt">source</a>).
<a href="https://satyadippaul.github.io/ascii2svg/mindmap.svg">Open it</a> and click any node to fold its branch; the rows close up.</sub></p>

```bash
tree src | ascii2svg - -o src.svg --preset explore          # colour per branch, branches fold
cargo tree | ascii2svg - -o deps.svg --preset explore --fold 1   # start with only the top level open
ascii2svg calls.txt --check --describe                        # the hierarchy as JSON: report.diagram.tree
```

- **What counts as a tree:** plain connectors between words or boxes, with the parent above or to
  the left of its children: `├──` `└──` `│` in Unicode, `|--` and `` `-- `` in ASCII, `├─┬` as `npm ls`
  draws it, a box whose `┬` fans out to other boxes, or branches going right as in a mind map.
  A diagram with arrowheads stays a flowchart.
- **Folding** (`--interactive`, or `--preset explore`): click a node or its ⊖ button, or Tab to it and
  press Enter. Shift folds or unfolds the whole branch. `--fold N` starts with depth N folded.
  Hover lights up the branch below a node.
- **Where it folds:** wherever the SVG's own script may run: the file opened in a browser, a page
  made with `-o tree.html`, an `<object>` or `<iframe>`, the playground. As an `<img>` (GitHub, most
  docs sites) scripts never run, and the reader sees the full drawing, still 1:1 and self-checked.
- **Colours** (`--color` on a tree with no arrows): one colour per main branch, used for its lines
  and a tint behind its label; the root sits on a dark pill; boxes take their branch's tint.

<table>
  <tr>
    <td width="50%" align="center"><a href="https://satyadippaul.github.io/ascii2svg/call-tree.svg"><img src="https://satyadippaul.github.io/ascii2svg/call-tree.svg" width="380" alt="A call tree of OrderService.place_order, each top-level call in its own colour, two calls folded"></a><br><sub><b>Call tree</b>, <code>--fold 2</code>: <a href="https://satyadippaul.github.io/ascii2svg/call-tree.svg">open</a> to unfold</sub></td>
    <td width="50%" align="center"><img src="https://satyadippaul.github.io/ascii2svg/mindmap-boxes.svg" width="380" alt="A mind map of boxes: Product plan fans out to Growth, Quality and Platform, each tinted with its branch colour"><br><sub><b>Boxes fanning out</b>, tinted by branch</sub></td>
  </tr>
</table>

## Gallery

All plain text, all 1:1. The sources are in [`docs/examples/`](https://github.com/SatyadipPaul/ascii2svg/tree/main/docs/examples), and every one is in the [playground](https://satyadippaul.github.io/ascii2svg/playground.html)'s example picker.

<table>
  <tr>
    <td width="50%" align="center"><img src="https://satyadippaul.github.io/ascii2svg/decision-flow.svg" width="420" alt="A checkout flow that fans out into a fraud-score decision tree and converges back into fulfilment"><br><sub><b>Flow → decision tree → flow</b></sub></td>
    <td width="50%" align="center"><img src="https://satyadippaul.github.io/ascii2svg/c4.svg" width="340" alt="A C4 container view: a customer uses a system drawn as a dashed boundary around a web app, an API and a database"><br><sub><b>C4 with a dashed boundary</b></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/uml-class.svg" width="240" alt="A UML class diagram: Dog and Cat inherit from Animal through a hollow triangle"><br><sub><b>UML inheritance</b> <code>△</code></sub></td>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/er.svg" width="420" alt="An ER diagram: CUSTOMER, ORDER and PRODUCT joined by crow's-foot relationships"><br><sub><b>ER crow's feet</b> <code>--||--o&lt;</code></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/gantt.svg" width="420" alt="A release-plan Gantt chart drawn with block characters"><br><sub><b>Gantt with block characters</b> <code>██░░</code></sub></td>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/pivot-table.svg" width="420" alt="A revenue pivot table by region, country and quarter, with subtotals and a callout on a Q3 spike"><br><sub><b>Pivot table with a callout</b></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/cache-sequence.svg" width="400" alt="A sequence diagram whose API lifeline turns into a cache-hit decision and returns a reply"><br><sub><b>Sequence → decision → reply</b></sub></td>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/swimlanes.svg" width="420" alt="Incident-response swimlanes with arrows crossing lanes"><br><sub><b>Swimlanes</b></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/diamond-flow.svg" width="230" alt="A sign-up flowchart with an ASCII diamond decision"><br><sub><b>ASCII diamonds</b> <code>/ \</code></sub></td>
    <td align="center"><img src="https://satyadippaul.github.io/ascii2svg/state.svg" width="260" alt="A publishing state machine: draft, in review, published, with a changes-requested loop"><br><sub><b>State machine</b></sub></td>
  </tr>
</table>

<details>
<summary><b>A bigger one:</b> a 72 × 96 architecture diagram with 28 boxes and 18 flowing arrows</summary>
<br>

The flows follow the real wiring: through junctions, down both branches of a fan-out, and across
the edge of a container. The text is [`tests/fixtures/complex_unicode.txt`](https://github.com/SatyadipPaul/ascii2svg/blob/main/tests/fixtures/complex_unicode.txt).

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/architecture.svg" alt="A 72 by 96 character architecture diagram of an order platform, rendered with colour and flow animation" width="760"></p>

</details>

## Pick a look

Same diagram, same guarantee, five ways:

| Default | Colour | Dark | Print | Alive |
|:-:|:-:|:-:|:-:|:-:|
| <img src="https://satyadippaul.github.io/ascii2svg/looks/default.svg" width="150" alt="default look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/color.svg" width="150" alt="colour look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/dark.svg" width="150" alt="dark look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/flat.svg" width="150" alt="flat print look"> | <img src="https://satyadippaul.github.io/ascii2svg/looks/flow.svg" width="150" alt="animated look"> |
| *(no options)* | `--color` | `--theme dark`<br>`--color` | `--style flat`<br>`--square` | `--animate`<br>`--color`<br>`--theme auto` |

Or let the destination decide: `--preset readme|slides|chat|print|dark|page|explore`.

| Destination | Use |
|---|---|
| GitHub README, docs site | `--preset readme` (`--theme auto --color --animate`), then commit the `.svg` |
| A tall diagram people scroll through | `--preset page` → an `.html` page that [reveals as you scroll](https://satyadippaul.github.io/ascii2svg/architecture.html) |
| A tree or mind map people explore | `--preset explore` → branches that [fold when clicked](https://satyadippaul.github.io/ascii2svg/mindmap.svg) |
| Slides (Keynote, Google Slides, PowerPoint) | `--color --animate draw` for a live build; `--color --png` for a still |
| Slack, email, Jira: anywhere SVG isn't shown | `--color --png` (needs `pip install cairosvg`) |
| Printed docs, a PDF | `--style flat --square` |
| Dark-mode apps | `--theme dark --color` |

<details>
<summary><b>Every look option</b></summary>
<br>

| Option | What it does |
|---|---|
| `--color` | Soft tints grouped by what contains what: each top-level group gets its own hue, nested boxes keep it. Arrows turn accent blue. |
| `--theme light\|dark\|auto` | `auto` follows the reader's system light/dark setting, which suits GitHub READMEs and docs sites. |
| `--animate draw` | The diagram draws itself once, top to bottom: lines are sketched in accent blue and settle to ink, boxes fade in, arrowheads pop, bars grow. |
| `--animate flow` (or bare `--animate`) | `draw`, then glowing pulses keep travelling along every connector toward its arrowhead. |
| `--animate scroll` | For tall diagrams, as a web page: each part appears as the reader scrolls to it, and long connectors grow with the scroll. |
| `-o page.html` (or `--html`) | A standalone web page with the diagram inline. Double-click to open, or email it. |
| `--style glow\|shadow\|flat` | Depth under the boxes. The glow shrinks automatically so it never sits behind a label. |
| `--square` | Keep corners square (they are rounded by default). |
| `--repair` | Fix typical misalignment first (see [LLM diagrams, fixed](#llm-diagrams-fixed)). |
| `--interactive` · `--fold N` | Trees and mind maps fold when clicked (see [Trees and mind maps that fold](#trees-and-mind-maps-that-fold)). |
| `--portable` | One `<text>` per character instead of one per word, for design tools (Inkscape, Figma) and non-browser renderers. Browsers draw both the same; PNG output always uses it. |
| `--accent #hex` · `--font NAME` · `--width PX` | Your brand colour for arrows and animation, a font to try first (e.g. `JetBrains Mono`), and the output width. |

The animation is careful about where it runs:

- **It never changes what's drawn.** An animated file is the static file plus timing. When the
  animation ends, you're looking at exactly what the self-check verified; tools that don't play
  animation (PNG export, most editors) show the finished drawing.
- **It respects the reader.** With *reduce motion* turned on in the OS, nothing moves.
- **`draw` and `flow` need no JavaScript.** They use CSS and SVG `<animate>` only, so they play
  inside a plain `<img>` tag, which is how GitHub, Notion and most docs sites show images.
- **`scroll` is a web page, not just an SVG,** because an image can't see how far you've scrolled
  (and CSS scroll timelines don't drive SVG shapes: we tested it). The page adds about 2 KB of
  plain JavaScript; the SVG inside it is the same self-checked drawing.

</details>

## How it compares

| | **ascii2svg** | Diagram DSLs (Mermaid, PlantUML) | A screenshot of the text |
|---|---|---|---|
| You write | the picture itself, in any editor or chat | code in the tool's language; the layout is automatic | the picture |
| Diagrams you, or an LLM, already have | render as they are | need rewriting in the DSL | work as they are |
| Output | SVG: sharp at any size, light and dark, animated | SVG where the renderer is supported | pixels: blurry when scaled, one theme |
| Proof it's faithful | reads its own SVG back, cell by cell | – | – |
| Misaligned LLM output | `--repair` fixes it and says what moved | – | shows the mistakes |
| Collapsible trees and mind maps | click to fold, from plain text (`--interactive`) | fixed layout, nothing folds | – |
| Output of `tree`, `npm ls`, `cargo tree` | pipe it in as it is | needs converting | works, as pixels |
| Where the picture goes | exactly where you drew it | the layout engine decides | where you drew it |

Choose a DSL when you want the layout done for you. Choose ascii2svg when the text diagram
already exists, or when an LLM writes it, and you want it to look designed without changing
it. Related projects such as [svgbob](https://github.com/ivanceras/svgbob) and
[goat](https://github.com/blampe/goat) also turn ASCII art into SVG and draw more freeform shapes;
ascii2svg focuses on box diagrams, a verified 1:1 result, and agent workflows.

## What gets drawn

| Source | Drawn as lines when… | Otherwise |
|---|---|---|
| ─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ╭ ╮ ╰ ╯ ═ ║ ╔ ╗ ╚ ╝ ╪ ▼ ▲ ▶︎ ◀︎ | always | – |
| Dashed ╌ ╎ ┄ ┆ ┈ ┊ | always, with 2, 3 or 4 dashes per cell; they join, box and carry arrows like any line | – |
| ASCII `+` `-` `\|` | they form a closed box, or attach to one directly or through `+` junctions | stay text |
| ASCII rounded corners `.` above, `'` or `` ` `` below | they close a box (`.--.` over `'--'`), or bend a connector that is drawn (`---.` over `\|`) | stay text (`It's`, `a.b`, `tree` output) |
| ASCII lines between plain words: `A --> B`, `A --HTTP--> B`, `\|` and `v` under a label | an arrowhead points at a word and every loose end rests on one (with a space between on a row); a label set into the line is carried over and reported | stay text (`a-->b`, `x -> y`, `p->next`, `--dry-run`) |
| ASCII `v ^ < >` | they end a line that is drawn, or point at a box (touching, or one space away) | stay text |
| ASCII trees `\|--` `` `-- `` `+--` | a column of `\|` under the start of a label, branches `\|-- name`, ending in `` `-- name `` (as `tree` and `cargo tree` print them) | stay text (markdown tables, `\|--flag`) |
| ╱ ╲ ╳, and ASCII `/` `\` | Unicode always; ASCII when two or more run along their own slope, with no letter or digit beside them | stay text |
| ASCII UML heads `<\|` `\|>` `<>` `*`, and `/_\` `<>` `*` on a vertical line | on a line that touches a box (across, or one space short), or right against a box's top or bottom edge with `\|` or `:` on the other side: inheritance, aggregation, composition | stay text |
| ASCII dashed `- - ->` and dotted `....>` `-.-.->`, `:` down a column | they join a box or end in an arrowhead that points into one; flow pulses hop the gaps | stay text (`Loading...`, dot leaders, `- - -`) |
| UML heads △ ▽ ◁ ▷ ◇ ◆ | a line joins them: triangles touch the parent, diamonds sit on the whole | stay text (bullets, symbols) |
| ER marks `\|` `o` `<` `>` `{` `}`, and `-+-` `o` `/\|\` `\\|/` on vertical lines | on a connector between two boxes: across (`+--\|\|--o<`, even with a foot set in the wall) or up and down | stay text |
| Block elements █ ▓ ▒ ░ ▀ ▄ ▌ ▐ ▁ ▂ ▃ ▅ ▆ ▇ ▏ ▎ ▍ ▋ ▊ ▉ ▖ ▗ ▘ ▝ ▚ ▞ ▙ ▛ ▜ ▟ | always, as exact rectangles, so bars and shading have no seams | – |

When unsure, a character stays text, so the worst case is the character itself in its own cell,
never a wrong shape. `a->b`, `--dry-run`, `user_id`, `C:\temp`, `yes/no`, `TCP/IP`, markdown
tables and `|--` file trees all stay exactly as written.

**How 1:1 is guaranteed:** every run parses the SVG it just wrote (lines, curves, diagonals,
arrowheads, rectangles, rings, feet, text positions) back into a character grid and compares it
with the input, cell by cell. ASCII characters may only appear as the line they stand for
(`-`→`─`, `|`→`│`, `+`→corner or junction, `v`→`▼`, `/`→`╱`). Any mismatch is exit code 2. This
covers every look, including animated ones and the still frame used for PNGs.

## Install

Python 3.9+ and nothing else:

```bash
pip install ascii2svg                 # adds the `ascii2svg` command and the `ascii2svg` module
pip install "ascii2svg[width,png]"    # optional: wcwidth (character widths) + cairosvg (--png)
```

It is a single file with no dependencies, so you can also just copy
[`scripts/ascii2svg.py`](https://github.com/SatyadipPaul/ascii2svg/blob/main/scripts/ascii2svg.py) into your project.

**Node and the browser**, with no Python install:

```bash
npm install @satyadip28/asciitosvg
npx @satyadip28/asciitosvg diagram.txt -o diagram.svg --preset readme
```

```js
import { render } from "@satyadip28/asciitosvg";
const { markup, report } = await render(diagram, { preset: "readme", repair: true });
```

The npm package runs this same Python module in [Pyodide](https://pyodide.org) (CPython on
WebAssembly). Its tests render every test diagram in five looks both ways and require
byte-identical SVG and reports. The CLI and the MCP server (`npx -y @satyadip28/asciitosvg --mcp`)
work as with pip; only `--png` needs the Python package. Details:
[npm/README.md](https://github.com/SatyadipPaul/ascii2svg/blob/main/npm/README.md).

<details>
<summary><b>As a Python library</b></summary>
<br>

```python
import ascii2svg

svg, report = ascii2svg.render(open("diagram.txt").read(), color=True, theme="auto", animate="flow")
assert report["roundtrip"] == "exact"          # the 1:1 self-check passed
open("diagram.svg", "w", encoding="utf-8").write(svg)

page, report = ascii2svg.render(text, color=True, animate="scroll", html=True)   # a scroll-reveal page
```

`render()` takes the same options as the CLI and returns the markup plus the same report as
`--json`. It raises `ValueError` for empty or oversized input and for unknown options.

</details>

<details>
<summary><b>As a Claude skill</b></summary>
<br>

Download [`ascii2svg.skill`](https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill)
from the latest release (or build it: `python3 tools/package_skill.py`), then:

- **claude.ai / Claude desktop:** Customize → Skills → upload `ascii2svg.skill`.
- **Claude Code:** unzip it into `~/.claude/skills/` (you get `~/.claude/skills/ascii2svg/`).

[`SKILL.md`](https://github.com/SatyadipPaul/ascii2svg/blob/main/SKILL.md) tells Claude when to use it, which look fits which destination,
to add `--repair` for model-drawn diagrams, and how to read the report before handing you the file.

</details>

<details>
<summary><b>Command-line reference</b></summary>
<br>

```
ascii2svg [INPUT ...] [-o OUT.svg|OUT.html|DIR/] [--preset NAME] [--json] [--check] [--describe] [--brief]
          [--color] [--theme light|dark|auto] [--animate [draw|flow|scroll]] [--html] [--repair]
          [--style glow|shadow|flat] [--square] [--accent #HEX] [--font NAME] [--width PX]
          [--all-blocks] [--block N] [--unescape] [--strict] [--schema] [--mcp]
          [--png [PATH]] [--text TEXT] [--tab-size N] [--title TEXT]
```

| Input | How |
|---|---|
| File | `ascii2svg diagram.txt -o out.svg` |
| stdin | `cat diagram.txt \| ascii2svg > out.svg` |
| Inline | `ascii2svg --text "$DIAGRAM" --json` (the SVG comes back inside the JSON when there's no `-o`) |
| Markdown | The first ```` ``` ```` code block is used; `--all-blocks` renders every diagram in the file |

stdout is always exactly one thing: the SVG (or the page, with `--html`), or (with `--json`) the
report. A one-line summary goes to stderr.

</details>

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
  `summary` come first, so a truncated report still says what happened.
- **Warnings you can act on:** each has a stable `code`, a 1-based `row`/`col`, the source `line`,
  and a `hint`. When a line misses its partner by one cell, the hint says where it is.
- **No false alarms on well-formed diagrams:** a line may end at a label, meet another line
  side-on (sequence messages `│───▶│`), or stop in open space (axis ticks, lifeline ends).
- **`--describe`** says what the diagram *means*: boxes (name, title, text, position, parent) and
  edges (`Gateway → Orders`), with a `kind` where the notation says more: `inheritance`,
  `aggregation`, `composition`, `relationship` with ER `cardinality` (`["one", "zero or many"]`),
  or `link` for a plain line, and the `label` set into a line (`--HTTP-->`). An endpoint that is
  not a box is the word it points at (`{"text": "Postgres"}`).
- **No hangs:** if you forget the input and stdin stays silent, it fails after 5 seconds with `bad_input`.
- **`--schema`** prints every option, preset, exit code, warning code and report field as JSON:
  enough to build a correct tool definition without reading docs.

**As an MCP server** (Claude Code, Claude Desktop, Cursor, any MCP client):

```bash
claude mcp add ascii2svg -- ascii2svg --mcp
```

```json
{"mcpServers": {"ascii2svg": {"command": "ascii2svg", "args": ["--mcp"]}}}
```

Two tools, no dependencies: **`check_diagram`** validates and describes, **`render_diagram`** writes
`.svg` or `.html` with any preset or style option, and both take `repair`. The diagram travels as a
JSON string, so the escaped-newline problem can't happen. Tested against the official MCP Python SDK.

<details>
<summary><b>Report fields, exit codes, batches, and a tool definition for any framework</b></summary>
<br>

| Field | Meaning |
|---|---|
| `status` | `ok` · `warnings` · `self_check_failed` · `bad_input` · `usage_error` |
| `summary` | One sentence to pass on to the user |
| `exit_code`, `ok` | See exit codes; `ok` is false only when the self-check failed |
| `roundtrip` | `exact`: the output was read back and matches the input cell for cell |
| `warnings` | `{code, row, col, char, line, issue, hint}`; codes: `dangling_line`, `broken_join`, `short_arrow`, `unclosed_box`, `escaped_newlines`, `no_structure` |
| `diagram` | With `--describe`: `{boxes: [...], edges: [{from, to, kind?, cardinality?, label?}], tree?}`; an endpoint is `{box, name}`, `{text}` or `{cell}`; `tree` is the hierarchy, nested `{name, box?, row, col, children?}`, and each parent → child is an edge of kind `branch` |
| `repair` | With `--repair`: `{edits: [{line, col, fix}], text}` |
| `rows`, `cols`, `boxes`, `arrowheads`, `flows`, `text_cells` | What was found |
| `folds`, `bytes` | Nodes that fold (with `--interactive`), and the size of the output |
| `style`, `theme`, `color`, `animate`, `html`, `interactive`, `preset` | The look that was rendered |
| `normalized` | Every clean-up applied (tabs, odd spaces, zero-width and control characters, colour codes, code fence, indentation, bad UTF-8, `--unescape`) |
| `tips` | Suggestions, e.g. `--animate scroll` when a timed animation would finish off-screen |
| `svg` / `html`, `png` | Output paths, or the markup itself when there is no `-o` (unless `--brief` / `--check`) |
| `self_check_problems` | Only when `roundtrip` isn't exact |

| Exit code | Meaning |
|---|---|
| 0 | OK (warnings allowed) |
| 1 | Bad input or usage: read `error` and `hint` |
| 2 | Self-check failed: the output is not 1:1. Don't use it |
| 3 | `--strict` and there were warnings |

**Many diagrams at once:**

```bash
ascii2svg README.md --all-blocks -o diagrams/ --preset readme   # every diagram in the file
ascii2svg docs/*.txt -o out/ --check                            # several files, one report each
ascii2svg README.md --block 3 -o flow.svg                       # just the third code block
```

Code blocks without lines or boxes are skipped and listed under `skipped`. Every warning carries
`source_line`/`source_col`: its position in the file you passed.

**As a tool in any agent framework:** pass the diagram on stdin, never through `--text`
(escaped newlines are the most common way agents break diagrams):

```python
import json, subprocess

def render_ascii_diagram(diagram, output_path, preset="readme", describe=False):
    args = ["ascii2svg", "-", "-o", output_path, "--preset", preset, "--json", "--brief", "--repair"]
    p = subprocess.run(args + (["--describe"] if describe else []), input=diagram.encode(), capture_output=True)
    return json.loads(p.stdout)          # always one JSON object, including on errors
```

</details>

## Roadmap

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/timeline.svg" width="700" alt="ascii2svg release by release, drawn by ascii2svg: a vertical spine of version boxes from 1.0 at the bottom to 1.15, each with a dotted leader to a diamond marker and what it shipped, arrows flowing upward, and a dashed next box at the top inviting ideas"></p>

<p align="center"><sub>Drawn by ascii2svg from <a href="https://github.com/SatyadipPaul/ascii2svg/blob/main/docs/examples/timeline.txt">plain text</a>: version boxes on a spine, dotted leaders ending in diamond markers (hollow for what's planned), pulses flowing from each release to the next, and the dashed future on top.</sub></p>

<details>
<summary><b>The same roadmap as a board</b></summary>
<br>

<p align="center"><img src="https://satyadippaul.github.io/ascii2svg/roadmap.svg" width="820" alt="The ascii2svg roadmap as a board: a block-character progress bar, six shipped milestones snaking through a solid container, and a dashed box inviting the next idea"></p>

</details>

<details>
<summary><b>The roadmap as a checklist</b></summary>
<br>

- [x] Boxes, arrows and junctions, in ASCII and Unicode, verified 1:1
- [x] Colour, light/dark/auto themes, draw and flow animation, scroll-reveal pages
- [x] Agent CLI: JSON reports, hints, `--describe`, presets, `--schema`, MCP server, Claude skill
- [x] Browser playground (Pyodide), with share links and PNG export
- [x] `--repair` for LLM-drawn diagrams
- [x] Block-element charts, diagonals and diamonds, dashed lines, UML heads, ER crow's feet
- [x] ER crow's feet on vertical connectors (`-+-` ticks, `o` rings, `/|\` and `\|/` feet)
- [x] ASCII UML heads (`<|--` `<>--` `*--`) and ASCII dashed and dotted lines (`- - ->` `....>` `:`)
- [x] Repairing bigger misalignments: boxes that must grow, walls and edges up to 12 columns off, lines split 3-6 apart, arrows that stop short
- [x] ASCII rounded corners and bends (`.--.` `'--'`)
- [x] Arrows between plain words (`A --> B`, `A --HTTP--> B`, `|` and `v` under a label)
- [x] Vertical ASCII UML heads (`/_\` `<>` `*` under or over a box)
- [x] On npm: `@satyadip28/asciitosvg`, the same module in WebAssembly, byte-identical by test
- [x] Trees and mind maps that fold (`--interactive`, `--preset explore`), a colour per branch, ASCII `tree` output, `--describe` trees
- [x] SVGs about half the size: a `<text>` per word, one path per line style, a lighter glow

Everything planned has shipped. Have an idea, or a diagram that doesn't render the way you meant?
[Open an issue](https://github.com/SatyadipPaul/ascii2svg/issues).

</details>

## Contributing

Issues and pull requests are welcome, and a diagram that renders wrongly is the most useful bug
report there is: paste the text and say what you expected.

```bash
python3 tests/test_ascii2svg.py        # 73 tests over 36 test diagrams (or: python3 -m pytest tests)
cd npm && npm install && npm test      # the npm package: byte-identical to Python on every test diagram
python3 docs/build.py                  # regenerate every image on this page and the playground files
```

New shapes come with a test diagram in [`tests/fixtures/`](https://github.com/SatyadipPaul/ascii2svg/tree/main/tests/fixtures), and every fixture
must round-trip exactly in every style and look. That's the one rule: never a wrong picture.

<details>
<summary><b>What the tests cover</b></summary>
<br>

- round-trip in every style and every look; animation that ends on the static drawing and respects reduced motion
- flow routes that start at the right box; scroll reveal driven by the page, with no script inside the SVG
- colour groups; glow never behind a label; planted faults that must be caught; byte-identical repeat runs
- the ASCII traps; width fallback vs `wcwidth`; UTF-8 output on Windows consoles; the `render()` library API
- the agent contract: JSON usage errors, status and summary, near-miss hints, escaped-newline and
  broken-box detection, `--describe` edges, presets, `--schema`, no hang on a forgotten input
- every diagram in a markdown file, several inputs, positions mapped back to the file, the MCP protocol
- the browser playground runs exactly this module, and every playground example round-trips
- no false alarms on sequence diagrams, timelines, charts and dashed boundaries; real mistakes still warn
- `--repair`: every LLM fixture repaired to `ok`, text provably unchanged, good diagrams untouched;
  a box grows for a long label or emoji, a split line is joined (never doubled), a short arrow reaches its box
- block elements as exact rectangles; `/ \` only as runs, never inside `yes/no` or `C:\Users`
- dashed lines keep their dash count, form boxes and carry arrows; ASCII `- - ->`, `....>` and `:` too,
  while `Loading...`, dot leaders and `- - -` stay text; ASCII UML heads `<|` `<>` `*` are drawn and described
- UML triangles and diamonds, ER ticks, rings and crow's feet across and up and down; `--describe` names each relationship and its cardinality
- trees: call trees, `npm ls`, `cargo tree` and `tree` output, left-to-right mind maps and box fan-outs read into
  the right hierarchy; flowcharts and timelines are not trees; an interactive SVG is the static drawing plus
  a script; fold data is escaped; branch colours only on pure trees; PNG frames place every character alone
- ASCII UML heads up and down (`/_\` `<>` `*`), drawn and described; rounded ASCII boxes and bends; arrows between plain words and labels set into lines, while `a-->b`,
  `x -> y`, `p->next`, `--dry-run`, markdown tables and `print("  -->")` stay text

They pass with and without the optional packages.

</details>

## License

[MIT](https://github.com/SatyadipPaul/ascii2svg/blob/main/LICENSE). Use it, change it and ship it, commercially too; keep the copyright notice.

<p align="center"><sub>Every diagram on this page was drawn by ascii2svg from plain text, and checked cell by cell against it.</sub></p>
