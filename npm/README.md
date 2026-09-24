# @satyadip28/asciitosvg

Render ASCII and Unicode box diagrams as clean SVG, with every character in its exact cell and a
1:1 self-check that reads the drawing back. This is the [ascii2svg](https://github.com/SatyadipPaul/ascii2svg)
Python library, running unchanged in [Pyodide](https://pyodide.org) (CPython compiled to
WebAssembly). You get the same drawing, the same `--repair` and the same JSON report as
`pip install ascii2svg`, in Node and in the browser, with no Python install.

```bash
npm install @satyadip28/asciitosvg
```

New to it? The [guide](https://github.com/SatyadipPaul/ascii2svg/blob/main/GUIDE.md) explains, in plain language, how to draw diagrams that render
well, which look to pick, and how to read and fix warnings.

<img src="https://satyadippaul.github.io/ascii2svg/looks/color.svg" width="420" alt="A rendered diagram: three tinted boxes joined by arrows">

## Library

```js
import { render } from "@satyadip28/asciitosvg";

const { markup, report } = await render(`
+--------+      +--------+
|  API   |----->|   DB   |
+--------+      +--------+
`, { preset: "readme", describe: true });

report.status;          // "ok" | "warnings" | "self_check_failed" (don't use the output)
report.summary;         // "Rendered 2 boxes and 1 arrow (3x26); 1:1 self-check exact."
report.diagram.edges;   // [{ from: { box: "b1", name: "API" }, to: { box: "b2", name: "DB" } }]
markup;                 // the SVG, or a web page with { html: true }
```

The options match the CLI and the Python `render()`: `preset` (`readme`, `slides`, `chat`,
`print`, `dark`, `page`, `explore`), `style`, `square`, `theme`, `color`, `animate`, `html`, `accent`,
`font`, `width`, `title`, `tabSize`, `describe`, `unescape`, `strict`, `repair`, `interactive`
(trees and mind maps fold when clicked), `fold` (start folded at this depth) and `portable`. Bad input or options
reject with an `Error` whose message says what's wrong. `check(text)` resolves to the report
with its boxes and edges. `version()` resolves to the ascii2svg version inside.

**Start-up.** The first call starts Python, which takes about a second in Node. After that, a
diagram renders in milliseconds. Call `load()` early to hide the wait.

**Browser.** In a bundle, tell Pyodide where its files are:
`await load({ indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/" })`. The first visit
downloads about 12 MB, which the browser then caches. The
[playground](https://satyadippaul.github.io/ascii2svg/playground.html) works this way.

## Command line

```bash
npx @satyadip28/asciitosvg diagram.txt -o diagram.svg --preset readme
npx @satyadip28/asciitosvg draft.txt --check --describe      # validate + structure, write nothing
cat diagram.txt | npx @satyadip28/asciitosvg - --repair --json
```

It is the Python CLI, flag for flag. Files are read and written where you point, stdin works,
and exit codes are the same (0 ok, 1 bad input, 2 self-check failed, 3 `--strict` with
warnings). The one exception is `--png`, which needs the Python package and cairosvg.

**MCP server** for Claude Code and other agents:

```bash
claude mcp add ascii2svg -- npx -y @satyadip28/asciitosvg --mcp
```

## Same output as Python, by test

The package ships the exact `ascii2svg.py` from the Python release with the same version number.
Its tests render every test diagram in five looks with this package and with the Python package
(155 renders), and require identical SVG bytes and identical reports.

MIT licence. Docs, gallery and roadmap: https://github.com/SatyadipPaul/ascii2svg
