// @satyadippaul/ascii2svg: the ascii2svg Python library, running unchanged in Pyodide (CPython
// compiled to WebAssembly). Same drawing, same 1:1 self-check and same JSON report as
// `pip install ascii2svg`, in Node and in the browser.
import { loadPyodide } from "pyodide";

const SOURCE = new URL("./ascii2svg.py", import.meta.url);
const isNode = typeof process !== "undefined" && !!process.versions?.node;
let engine = null;

async function source() {
  if (isNode) {
    const { readFile } = await import("node:fs/promises");
    return readFile(SOURCE, "utf8");
  }
  const res = await fetch(SOURCE);
  if (!res.ok) throw new Error(`cannot load ascii2svg.py (${res.status})`);
  return res.text();
}

/**
 * Start Python and load ascii2svg. Called for you by render(); call it early to hide the
 * start-up time (about a second in Node, a few seconds and ~12 MB on a first browser visit).
 * In a browser bundle, pass `indexURL` (where Pyodide's files are served, e.g. the jsDelivr CDN).
 */
export function load({ indexURL, stdout, stderr } = {}) {
  engine ??= (async () => {
    const py = await loadPyodide({ ...(indexURL ? { indexURL } : {}), ...(stdout ? { stdout } : {}),
                                   ...(stderr ? { stderr } : {}) });
    py.FS.mkdirTree("/home/pyodide/ascii2svg");
    py.FS.writeFile("/home/pyodide/ascii2svg/ascii2svg.py", await source());
    py.runPython(`
import json, sys
sys.path.insert(0, "/home/pyodide/ascii2svg")
import ascii2svg

def _js_render(text, opts):
    try:
        markup, report = ascii2svg.render(text, **json.loads(opts))
    except (ValueError, TypeError) as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"markup": markup, "report": report})
`);
    return py;
  })();
  engine.catch(() => { engine = null; });              // a failed start can be retried
  return engine;
}

const SNAKE = { tabSize: "tab_size" };

/**
 * Render a text diagram. Options match the Python library and the CLI:
 * preset, style, square, theme, color, animate, html, accent, font, width, title, tabSize,
 * describe, unescape, strict, repair.
 * Resolves to { markup, report }: markup is the SVG (or a web page with html: true), and report is
 * what `ascii2svg --json` prints. Check report.status: "ok" or "warnings" are usable,
 * "self_check_failed" is not. Rejects with an Error for empty or oversized input and bad options.
 */
export async function render(text, options = {}) {
  if (typeof text !== "string") throw new TypeError("render(text): text must be a string");
  const opts = Object.fromEntries(Object.entries(options).map(([k, v]) => [SNAKE[k] ?? k, v]));
  const py = await load();
  const out = JSON.parse(py.globals.get("_js_render")(text, JSON.stringify(opts)));
  if (out.error) throw new Error(out.error);
  return out;
}

/** Validate a diagram without keeping the drawing: the report, with its boxes and edges. */
export async function check(text, options = {}) {
  return (await render(text, { ...options, describe: true })).report;
}

/** The ascii2svg version inside (the same as the Python package's). */
export async function version() {
  return (await load()).runPython("ascii2svg.__version__");
}
