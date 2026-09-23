// Runs ascii2svg in Pyodide (CPython compiled to WebAssembly), off the page's main thread.
// A module worker: classic importScripts() of a CDN script is blocked in some embedded browsers.
// Messages in:  {id, text, opts}            Messages out: {type: "status"|"ready"|"fatal"|"result", ...}
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";

const ready = (async () => {
  postMessage({ type: "status", text: "Downloading Python (about 12 MB, first visit only)…" });
  const py = await loadPyodide({ indexURL: PYODIDE });
  postMessage({ type: "status", text: "Loading ascii2svg…" });
  const src = await (await fetch(new URL("ascii2svg.py", import.meta.url), { cache: "no-cache" })).text();
  py.FS.writeFile("/home/pyodide/ascii2svg.py", src);
  py.runPython(`
import json, sys
sys.path.insert(0, "/home/pyodide")
import ascii2svg

def pg_render(text, opts):
    try:
        markup, report = ascii2svg.render(text, **json.loads(opts))
    except ValueError as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"markup": markup, "report": report})
`);
  postMessage({ type: "ready", version: py.runPython("ascii2svg.__version__") });
  return py.globals.get("pg_render");
})();

ready.catch((e) => postMessage({ type: "fatal", error: String(e) }));

onmessage = async (e) => {
  const render = await ready;
  const t0 = performance.now();
  let out;
  try {
    out = JSON.parse(render(e.data.text, JSON.stringify(e.data.opts)));
  } catch (err) {
    out = { error: "internal error: " + err };
  }
  postMessage({ type: "result", id: e.data.id, ms: Math.round(performance.now() - t0), ...out });
};
