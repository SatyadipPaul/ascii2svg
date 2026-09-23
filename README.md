# ascii2svg

Render ASCII / Unicode box diagrams as SVG, **1:1**: every character keeps its exact grid cell.
Built to be called by LLM agents: text in, SVG plus a JSON report out.

```bash
cat diagram.txt | python3 scripts/ascii2svg.py -o diagram.svg --json
```
```json
{"ok": true, "rows": 72, "cols": 96, "style": "glow", "boxes": 28, "arrowheads": 18,
 "roundtrip": "exact", "warnings": [], "normalized": [], "svg": "diagram.svg", "exit_code": 0, "...": "..."}
```

## Install

Nothing is required beyond Python 3.8+. Either copy `scripts/ascii2svg.py` anywhere, or:

```bash
pip install .                # adds the `ascii2svg` command
pip install ".[width,png]"   # optional: wcwidth (widths) + cairosvg (--png)
```

As a Claude skill: copy this whole folder into your skills directory. `SKILL.md` tells the
model when and how to use it.

## Usage

```
ascii2svg [INPUT] [-o OUT.svg] [--json] [--style glow|shadow|flat] [--square]
          [--png [PATH]] [--strict] [--text TEXT] [--tab-size N] [--title TEXT]
```

| Input | How |
|---|---|
| File | `ascii2svg diagram.txt -o out.svg` |
| stdin | `cat diagram.txt \| ascii2svg > out.svg` |
| Inline | `ascii2svg --text "$DIAGRAM" --json` (the SVG comes back inside the JSON when there's no `-o`) |
| Markdown | The first ```` ``` ```` code block is used; prose around it is dropped (and reported) |

stdout is always exactly one thing: the SVG, or (with `--json`) the report.
A one-line human summary goes to stderr.

## What gets drawn

| Source | Drawn as lines when… | Otherwise |
|---|---|---|
| `─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╪`, `▼▲▶◀` | always | – |
| ASCII `+` `-` `\|` | they form a closed box, or attach to one directly or through `+` junctions | stay text |
| ASCII `v ^ < >` | they end a line that is drawn, or point at a box (touching, or one space away) | stay text |

When unsure, a character stays text, so the worst case is the character itself in its own
cell, never a wrong shape. `a->b`, `--dry-run`, `user_id`, `C:\temp`, markdown tables and
`|--` file trees all stay exactly as written.

## JSON report

| Field | Meaning |
|---|---|
| `ok`, `exit_code` | Overall result (see exit codes) |
| `roundtrip` | `exact`: the SVG was read back and matches the input cell for cell |
| `rows`, `cols`, `boxes`, `arrowheads`, `text_cells` | What was found |
| `ascii_drawn_as_lines` | ASCII characters drawn as lines |
| `ascii_line_like_kept_as_text` | ASCII `- \| +` not drawn because they don't attach to anything |
| `normalized` | Every clean-up applied (tabs, odd spaces, zero-width and control characters, colour codes, code fence, indentation, bad UTF-8) |
| `warnings` | Line ends that meet nothing, with 1-based `row`/`col`: usually a misaligned source |
| `svg`, `png` | Output paths (or the SVG markup itself when no `-o` is given) |
| `self_check_problems` | Only when `roundtrip` isn't exact |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | OK (warnings allowed) |
| 1 | Bad input or usage (message in `error`) |
| 2 | Self-check failed: the SVG is not 1:1. Don't use it |
| 3 | `--strict` and there were warnings |

## Using it from any agent framework (function calling)

Expose it as one tool and run the CLI in the handler:

```json
{
  "name": "render_ascii_diagram",
  "description": "Render an ASCII/Unicode box diagram to an SVG file, keeping every character in place. Returns a JSON report; exit_code 0 means success.",
  "input_schema": {
    "type": "object",
    "properties": {
      "diagram": {"type": "string", "description": "The diagram text (a markdown code block is fine)"},
      "output_path": {"type": "string", "description": "Where to write the .svg"},
      "style": {"type": "string", "enum": ["glow", "shadow", "flat"]}
    },
    "required": ["diagram", "output_path"]
  }
}
```

```python
import json, subprocess, sys

def render_ascii_diagram(diagram, output_path, style="glow"):
    p = subprocess.run([sys.executable, "scripts/ascii2svg.py", "-o", output_path,
                        "--style", style, "--json"], input=diagram.encode(), capture_output=True)
    return json.loads(p.stdout)          # always JSON, including on errors
```

## How 1:1 is guaranteed

Every run parses the SVG it just wrote (lines, curves, arrowheads, text positions) back into
a character grid and compares it with the input cell by cell. ASCII characters may only
appear as the line they stand for (`-`→`─`, `|`→`│`, `+`→corner or junction, `v`→`▼`).
Any mismatch means exit code 2.

## Tests

```bash
python3 tests/test_ascii2svg.py        # or: python3 -m pytest tests
```

20 tests over 11 test diagrams: round-trip in every style, the ASCII traps, glow never behind
a label, planted faults that must be caught, byte-identical repeat runs, width fallback vs
`wcwidth`, and CLI behaviour. They pass with and without the optional packages.

## Not in v1

- **Auto-repair of misaligned diagrams.** It warns with row/column instead.
- **ASCII rounded corners (`.-'`) and diagonals (`/ \`).** These stay text.
- **Free-floating ASCII connectors that touch no box** (e.g. `A ---> B` between plain words). These stay text.
- **An MCP server and a JS/npm port.**
- **Checked renderers.** Output is verified in cairo and resvg. It was not checked in a real browser here (no browser in the build sandbox). Neither effect uses SVG filters.
