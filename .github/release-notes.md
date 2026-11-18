# 1.18.0: twice as fast, highlight a path, link the boxes, tune the look

The same drawings, byte for byte, in about half the time. And three new ways to make a diagram say more: show one path through it, make its boxes clickable, and match your brand.

```bash
pip install -U ascii2svg
npm install @satyadip28/asciitosvg@1.18.0
```

## New

- **Highlight a path.** `--highlight "Web,API,DB"` keeps those boxes, the lines between them and the labels on those lines bright, and fades the rest; pulses run only on the bright path. Names are the ones `--describe` reports. A named container lights only its own frame and words, so a path can run through containers. [See it](https://satyadippaul.github.io/ascii2svg/highlight.svg).
- **Links, tooltips and tints per box.** `--boxes '{"API": {"link": "https://...", "tooltip": "REST, v2", "tint": "#ffe8cc"}}'`. Links are http(s), mailto or relative only; `javascript:` and `data:` are refused. They work where the SVG is a page or an `<object>`, not inside `<img>`.
- **Design tokens.** `--tokens brand.json` sets `ink`, `bg`, `accent`, `neutral`, `hover`, `glow`, box `hues`, tree `branch` colours, `stroke`, `font_size`, `flow_speed` and `flow_rest`, for both themes or for light and dark separately. Every value is checked before it reaches the SVG; `--schema` lists them all.
- **`--names`** puts `data-name` on each box, for your own CSS or scripts.
- **`ascii2svg.parse(text)`** reads a diagram once; `d.svg(**look)`, `d.render(**look)` and `d.describe()` reuse that reading. Drawing 5 looks of each diagram is 2.8x faster than 1.17. A `Diagram` shows itself inline in Jupyter.
- The MCP `render_diagram` tool and the npm package take `highlight`, `boxes`, `tokens` and `names` too.

## Faster

About 2x faster on everyday diagrams, and 4x faster for `--repair` with `--describe` on large ones (1,200 boxes: 4.0 s to 0.9 s). Nothing you see changed: 870 renders (every test diagram and example, in every preset and option set) are byte-identical to 1.17.0, and so is every image on the website.

- The parser visits only the cells that hold the characters each pass looks for, instead of scanning the whole grid a dozen times.
- Finding which box sits inside which no longer compares every box with every other.
- Repair keeps the grid's size up to date instead of recounting every cell on each step.
- `tools/bench.py` runs the old and new engine in turns and compares every output; CI fails on a slow-down or any change in output.

85 tests over 43 test diagrams, plus the npm package's parity tests (every render byte-identical to Python, now including the new options). CI covers Python 3.9–3.13 and Node 20/24 on Linux, Windows and macOS.
