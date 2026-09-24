# How to use ascii2svg

ascii2svg takes a diagram you drew with ordinary characters (in a text file, a README, a code
comment or a chat with an AI) and turns it into a clean SVG image. Every character stays in the
exact spot where you put it. Each time it runs, it reads its own picture back and checks it
against your text, so what you drew is what you get.

This guide goes in the order you'll need it: how to run it, how to draw so that it renders
well, how to pick a look, and what to do when something doesn't come out as you meant.

**Contents**

1. [Pick how you'll run it](#1-pick-how-youll-run-it)
2. [Your first diagram](#2-your-first-diagram)
3. [Drawing diagrams that render well](#3-drawing-diagrams-that-render-well)
4. [Choosing a look for where it's going](#4-choosing-a-look-for-where-its-going)
5. [Checking the result and fixing what's wrong](#5-checking-the-result-and-fixing-whats-wrong)
6. [Working with an AI assistant](#6-working-with-an-ai-assistant)
7. [Using it from code](#7-using-it-from-code)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Pick how you'll run it

There are four ways in. They all give the same result for the same text.

**In your browser, with nothing to install.** Open the
[playground](https://satyadippaul.github.io/ascii2svg/playground.html) and paste your diagram
into the box on the left. The picture updates as you type.
- **Choose a look:** "For" says where the image is going (README, slides, chat, print and so on).
  The other controls adjust colour, theme, depth and animation.
- **Get the result:** Download SVG, Download PNG, Download page, Copy SVG, or Copy share link
  (a link that opens the playground with your diagram and settings).
- **When something's off:** if the diagram has problems, they're listed under the picture, and
  **Fix alignment** repairs the typical ones for you.

Everything runs on your own computer, and nothing is uploaded.

**On the command line**, with Python or with Node. Pick whichever you already have:

```bash
pip install ascii2svg                          # Python 3.9 or newer
ascii2svg diagram.txt -o diagram.svg

npx @satyadippaul/ascii2svg diagram.txt -o diagram.svg   # Node 18 or newer, no install step
```

**From your own code**, in Python or JavaScript. See [section 7](#7-using-it-from-code).

**Through Claude or another AI assistant**, as a skill or an MCP server. See
[section 6](#6-working-with-an-ai-assistant).

---

## 2. Your first diagram

**Step 1: write the diagram.** Save this as `diagram.txt`:

```text
+---------+      +---------+      +---------+
|   Web   |----->|   API   |----->|   DB    |
+---------+      +---------+      +---------+
```

**Step 2: render it.**

```bash
ascii2svg diagram.txt -o diagram.svg
```

**Step 3: read the line it prints.**

```text
ascii2svg: Rendered 3 boxes and 2 arrows (3x45) to diagram.svg; 1:1 self-check exact.
```

This line tells you what it found: three boxes and two arrows. "1:1 self-check exact" means it
read the finished SVG back and every character is where your text says it should be. If the
counts are lower than you expected, part of the drawing stayed as plain text;
[section 5](#5-checking-the-result-and-fixing-whats-wrong) shows how to find out why.

**Step 4: use the image.** In a README or any markdown page:

```markdown
![How a request flows](diagram.svg)
```

For a GitHub README, add `--preset readme`. The image then follows the reader's light or dark
mode, gets soft colours, and shows little pulses travelling along the arrows.

---

## 3. Drawing diagrams that render well

**The one idea behind all the rules:** ascii2svg only turns a character into a line when it is
sure that's what you meant. Anything else stays as text, in the same place. The worst case is
therefore never a wrong shape, only a character left as it was. The rules below make what you
mean unmistakable.

### Boxes

- **Close every box.** It needs a corner at each of its four corners, an edge along the top and
  the bottom, and a wall down each side, all lined up in the same columns. Use `+` for corners,
  `-` for edges and `|` for walls:

  ```text
  +----------+
  |  Orders  |
  +----------+
  ```

- **Round corners if you like.** Put `.` at the top corners and `'` at the bottom ones. In a
  diagram that has both kinds, each box keeps the corners you gave it.

  ```text
  .----------.
  |  Orders  |
  '----------'
  ```

- **Leave a space between words and walls.** `| Orders |` is safer than `|Orders|`.
- **Titles can sit on the top edge:** `+-- Orders service ------+`.
- **Boxes can contain boxes.** With colour turned on, each group gets its own tint.
- **Unicode box-drawing characters work just as well.** These are the thin, rounded and
  double-line boxes that many tools and AI models produce. They are drawn as lines wherever
  they appear.

### Arrows and lines

- **A line joins things.** A run of `-` across or `|` down is drawn when it touches a box, or
  when it ends in an arrowhead that points at one.
- **Arrowheads are `>` `<` `v` `^`.** Put the arrowhead right against the box it points at, or
  at most one space away.
- **Keep a vertical line in one column all the way down,** and a horizontal one on one row.
  Being off by one column is the most common mistake, and the warnings will point it out.
- **Turn or branch with `+`.** It's a corner where a line bends, and a junction where a line
  splits. For a rounded bend, use `.` where the line turns down and `'` where it turns up.

  ```text
  +--------+
  | Client |
  +--------+
       |
  +----+-----+
  |          |
  v          v
  +-----+  +-----+
  | Web |  | API |
  +-----+  +-----+
  ```

- **Label an arrow** by writing the words just above or below the line, or inside the line:
  `--HTTP-->`.
- **Arrows can join plain words** without any boxes. Leave a space between each word and its
  line, and use at least two dashes: `Client --> Server`, `request --> parse --> store`,
  `Browser <--> CDN`. Down a page, put `|` and `v` under a word. In code, `a->b` and
  `fn f() -> T` stay text.
- **Dashed and dotted lines:** `- - ->` for dashed, `....>` or `-.-.->` for dotted, and a
  column of `:` for a dotted vertical line.
- **Diagonals:** `/` and `\` are drawn when two or more run along the same slope, as in an ASCII
  diamond or a fan-out. A lone slash, as in `yes/no` or `C:\temp`, stays text.

### Notation for software diagrams

- **UML class diagrams:** `<|--` (inheritance), `<>--` (aggregation) and `*--` (composition),
  with the head against the box. On a vertical line, hang `/_\` under the parent box, or put
  `<>` or `*` right against a box's edge. `--describe` then names each relationship.
- **ER diagrams:** crow's-foot marks on a connector between two boxes, such as `+--||--o<`,
  across or up and down. `--describe` reports the cardinality ("one", "zero or many").
- **Charts and timelines:** block characters (█ ▓ ▒ ░ and the eighths ▁ ▂ ▃ ▌ ▐) are drawn as
  exact rectangles, so bars and Gantt charts have no gaps between cells.

### Things that deliberately stay text

Hyphens in words, `a->b`, `--dry-run`, `user_id`, `C:\temp`, `yes/no`, `It's`, `Loading...`,
markdown tables and `|--` file trees are all left exactly as written. You don't have to avoid
them.

### Emoji and other wide characters

Emoji and Chinese, Japanese and Korean characters take up two columns. Many editors, and most
AI models, count them as one, so the right wall of that row ends up one column out. Either add
the missing space by hand, or run with `--repair`, which fixes it for you.

---

## 4. Choosing a look for where it's going

The simplest way is to say where the image will be used, with `--preset`:

| Where it's going | Use | What you get |
|---|---|---|
| A GitHub README or docs site | `--preset readme` | Soft colours, follows the reader's light or dark mode, pulses along the arrows |
| Slides | `--preset slides` | Colour, and the diagram draws itself once when shown |
| Slack, email, chat | `--preset chat`, plus `--png` if the app won't show SVG | Colour, no motion |
| Print or PDF | `--preset print` | Flat and square, no shadows |
| A dark app or page | `--preset dark` | Dark background, colour |
| A long diagram people scroll through | `--preset page -o diagram.html` | A web page where each part appears as you scroll to it |

You can also set things one by one. `--color` adds tints and blue arrows. `--theme light`,
`dark` or `auto` sets the colours. `--animate draw` draws the diagram once, and `--animate flow`
adds pulses. `--style glow`, `shadow` or `flat` sets the depth, and `--square` keeps corners
sharp. Options you set yourself win over the preset.

A few things are good to know:
- **Animation plays in a README.** GitHub shows SVGs through an `<img>` tag, and the animation
  needs no JavaScript.
- **Readers who turn on "reduce motion"** in their system settings see a still picture.
- **An animated diagram ends exactly on the still one,** so nothing is lost for tools that don't
  play animation.
- **PNG output needs the Python package** and `pip install cairosvg`. It isn't available in the
  npm package.

---

## 5. Checking the result and fixing what's wrong

### Read the summary

Every run ends with one line like the one in [section 2](#2-your-first-diagram). With `--json`,
the same information comes as a report you can read in a program. Its `status` is one of these:

- **ok:** everything was drawn as intended.
- **warnings:** the image is fine and faithful, but something looks like a mistake in the text,
  such as a line that stops one column short of a box. Each warning says where it is and what to
  change.
- **self_check_failed:** the image didn't match the text. This should never happen. Don't use
  that image, and please [open an issue](https://github.com/SatyadipPaul/ascii2svg/issues) with
  your diagram.

### What the warnings mean

| Warning | What it means | What to do |
|---|---|---|
| `unclosed_box` | Something starts like a box (`+---+` with a wall below it) but never closes, so it stayed text | The hint names the wall or edge that breaks. Line it up, or run `--repair` |
| `dangling_line` | A line ends in empty space right next to something it probably meant to reach | The hint says where the partner is, often one column over |
| `short_arrow` | An arrowhead stops a few spaces short of the box it points at | Extend the line to touch the box, or run `--repair` |
| `broken_join` | A line runs into a corner or junction that has no arm pointing back at it | Use the junction character the hint suggests |
| `no_structure` | There were box pieces, but no complete box, so everything stayed text | Close at least one box (see [Boxes](#boxes)) |
| `escaped_newlines` | The input is one long line with `\n` written in it, a common slip when a program passes text along | Pass real line breaks, or add `--unescape` |

### Check before you render

- `--check` validates the diagram and writes nothing.
- `--describe` adds what ascii2svg understood: each box with its name, and each arrow with where
  it starts and ends. Use it to confirm that the arrows connect what you meant, for example
  "Web → API".

```bash
ascii2svg diagram.txt --check --describe
```

### Let it fix the alignment

`--repair` fixes the misalignments people and AI models make most often:
- **Boxes:** ragged walls; walls, corners and edges up to 12 columns off; a box too narrow for
  its words (it grows).
- **Lines:** lines that drift sideways, or break in two, between rows.
- **Arrows:** arrows that stop short of their box.

It only ever moves or adds line characters and spaces. **Your words never change.** The report
lists every edit, and `repair.text` holds the corrected diagram, so you can paste it back into
your file and keep the text and the picture in step.

```bash
ascii2svg diagram.txt -o diagram.svg --repair
```

---

## 6. Working with an AI assistant

### Asking a model to draw a diagram

Models draw good diagrams but often misalign them by a column or two, especially around emoji.
Ask for plain ASCII boxes, then render with `--repair`. Pasting these instructions into your
request helps:

```text
Draw the diagram in plain ASCII inside a code block:
- boxes: + at the four corners, - along the top and bottom, | down both sides,
  with every row of a box the same width
- one space between each label and the wall
- lines: - across and | down, each kept in a single column or row
- arrowheads > < v ^ touching the box they point at
- + where a line turns or branches
- no emoji inside boxes
```

### As a Claude skill

Download [`ascii2svg.skill`](https://github.com/SatyadipPaul/ascii2svg/releases/latest/download/ascii2svg.skill).
- **In the Claude app,** go to Customize → Skills and upload it.
- **In Claude Code,** unzip it into `~/.claude/skills/`.

Then just ask, for example: *"turn this diagram into an image for my slides"*. Claude checks the
diagram, repairs it, picks the right look and tells you what it found.

### As an MCP server

This works in Claude Code, Claude Desktop, Cursor and other MCP clients:

```bash
claude mcp add ascii2svg -- ascii2svg --mcp                      # with the Python package
claude mcp add ascii2svg -- npx -y @satyadippaul/ascii2svg --mcp  # or with Node
```

This gives the assistant two tools: `check_diagram` validates and describes a diagram, and
`render_diagram` writes the image. A good assistant works in a loop:
1. Draft the diagram.
2. Check it, and apply each warning's hint.
3. Confirm that the edges are the ones intended.
4. Render with a preset that suits the destination.

---

## 7. Using it from code

**Python:**

```python
import ascii2svg

svg, report = ascii2svg.render(open("diagram.txt").read(), preset="readme", repair=True)
if report["status"] != "self_check_failed":
    open("diagram.svg", "w", encoding="utf-8").write(svg)
print(report["summary"])
```

**JavaScript** (Node or a browser), after `npm install @satyadippaul/ascii2svg`:

```js
import { render } from "@satyadippaul/ascii2svg";

const { markup, report } = await render(diagramText, { preset: "readme", repair: true });
console.log(report.summary);
```

The options are the same as the command line's: `preset`, `color`, `theme`, `animate`, `style`,
`square`, `html`, `repair`, `describe` and so on. The JavaScript version runs the same Python
code inside WebAssembly, so its output is identical. The first call takes a second or two to
start Python; after that, each diagram takes milliseconds.

**Every diagram in a markdown file:**

```bash
ascii2svg README.md --all-blocks -o diagrams/ --preset readme
```

Code blocks that aren't diagrams are skipped. Use `--block 3` to render only the third one.

**In CI**, to keep the images in step with the text. `--strict` fails the build when a diagram
has warnings:

```yaml
- run: pip install ascii2svg
- run: ascii2svg docs/diagrams/*.txt -o docs/img/ --preset readme --strict
```

---

## 8. Troubleshooting

**A box isn't drawn.** Run with `--check`. An `unclosed_box` warning names the exact wall or
corner that's out of line. Usually one row is a column too long or too short, often because of
an emoji. `--repair` fixes most of these.

**An arrow stayed as text.** A line has to touch a box or end in an arrowhead that points at
one. Between plain words, it also needs a space on each side and at least two dashes. Check that
the arrowhead is against the box, or one space from it, and in the same row or column as the
line.

**The arrow connects the wrong boxes.** Run `--describe` and read the edges. A vertical line
that drifts a column can end up under a different box. Keep it in one column, or let
`--repair` straighten it.

**The picture shows `+`, `-` or `|` as characters.** Those parts didn't form a complete box or
connection, so they were kept as text on purpose. The warnings say which part is incomplete.

**Emoji rows are misaligned.** Emoji take two columns. Add a space to the other rows, or remove
one from the emoji row, or use `--repair`.

**GitHub still shows the old image after I pushed a new one.** GitHub caches images for a few
minutes. Wait a moment, then do a hard refresh (Ctrl+Shift+R or Cmd+Shift+R).

**I need a PNG.** Use the Python package with `pip install cairosvg`, then add `--png`. The
playground's Download PNG button also works, with no install.

**Something rendered differently from what I drew.** That's a bug. Please
[open an issue](https://github.com/SatyadipPaul/ascii2svg/issues) with the text of the diagram.

---

**More detail:** the [README](https://github.com/SatyadipPaul/ascii2svg#readme) has the gallery,
the full table of [what gets drawn](https://github.com/SatyadipPaul/ascii2svg#what-gets-drawn),
every option, and the report fields for programs and agents.
