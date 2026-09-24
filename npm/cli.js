#!/usr/bin/env node
// The ascii2svg command line, from npm: the Python CLI running in Pyodide. The host's drives are
// mounted into Python's virtual filesystem, so file paths work as usual, and output is streamed
// byte for byte. `--mcp` serves MCP on stdio, the same server as the Python package's.
import { existsSync, writeSync } from "node:fs";
import { createInterface } from "node:readline";
import { load } from "./index.js";

const argv = process.argv.slice(2);
const windows = process.platform === "win32";

function mountHost(py) {
  if (windows) {                                        // every drive: C:\ -> /mnt/c
    for (const d of "ABCDEFGHIJKLMNOPQRSTUVWXYZ") {
      if (existsSync(`${d}:\\`)) {
        py.FS.mkdirTree(`/mnt/${d.toLowerCase()}`);
        py.mountNodeFS(`/mnt/${d.toLowerCase()}`, `${d}:\\`);
      }
    }
  } else {
    py.FS.mkdirTree("/mnt/host");
    py.mountNodeFS("/mnt/host", "/");
  }
  py.runPython(`
import os, re, ascii2svg
WINDOWS = ${windows ? "True" : "False"}

def _fs(p):
    if WINDOWS:
        p = p.replace("\\\\", "/")
        m = re.match(r"^([A-Za-z]):/?(.*)$", p)
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}" if m else p
    return "/mnt/host" + p if p.startswith("/") else p

def _host(p):
    if WINDOWS:
        m = re.match(r"^/mnt/([a-z])(/.*)?$", p)
        return (m.group(1).upper() + ":" + (m.group(2) or "/")).replace("/", "\\\\") if m else p
    return p[len("/mnt/host"):] or "/" if p.startswith("/mnt/host") else p

ascii2svg._fs, ascii2svg._host = _fs, _host
os.chdir(_fs(${JSON.stringify(process.cwd())}))
`);
}

function readStdin(firstChunkMs) {
  // All of stdin. With firstChunkMs, give up (empty) when nothing arrives in time, like the
  // Python CLI's implicit stdin, so an agent that forgot the input gets an error, not a hang.
  return new Promise((resolve) => {
    const parts = [];
    let timer = null;
    const done = () => { clearTimeout(timer); process.stdin.pause(); resolve(Buffer.concat(parts)); };
    if (firstChunkMs != null) timer = setTimeout(done, firstChunkMs);
    process.stdin.on("data", (b) => { clearTimeout(timer); parts.push(b); });
    process.stdin.on("end", done);
    process.stdin.on("error", done);
  });
}

async function main() {
  const py = await load();
  const out = (fd) => ({ write: (buf) => { writeSync(fd, buf); return buf.length; } });
  py.setStdout(out(1));
  py.setStderr(out(2));
  mountHost(py);
  py.runPython(`
import json, sys, ascii2svg

def _js_stdin(argv):
    """'explicit' when this run reads stdin because of '-', 'implicit' when it reads it for lack
    of any other input, '' when it doesn't read stdin at all."""
    import contextlib, io
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            args, _ = ascii2svg.build_parser().parse_known_args(argv)   # --help, --version: exit here
    except BaseException:
        return ""
    if args.mcp or args.schema:
        return ""
    inputs = args.input or []
    if "-" in inputs:
        return "explicit"
    return "implicit" if not inputs and args.text is None else ""

def _js_main(argv):
    sys.argv = ["ascii2svg"] + list(argv)
    try:
        return ascii2svg.main(list(argv)) or 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
`);
  const argvPy = py.toPy(argv);

  if (argv.includes("--mcp")) {                         // MCP over stdio, one JSON-RPC message per line
    const reply = py.globals.get("ascii2svg").mcp_reply;
    const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
    for await (const line of rl) {
      const answer = reply(line);
      if (answer != null) writeSync(1, answer + "\n");
    }
    return 0;
  }

  const mode = py.globals.get("_js_stdin")(argvPy);
  let data = null;
  if (mode && !process.stdin.isTTY) {
    const wait = mode === "explicit" ? null : 1000 * Number(process.env.ASCII2SVG_STDIN_WAIT ?? 5);
    data = await readStdin(wait);
  }
  let given = false;
  py.setStdin({
    stdin: () => { if (given || data == null) return null; given = true; return data; },
    isatty: mode === "implicit" && !!process.stdin.isTTY,
  });
  return py.globals.get("_js_main")(argvPy);
}

main().then(
  (code) => { process.exitCode = code; },
  (err) => {
    process.stderr.write(`ascii2svg: ${err?.message ?? err}\n`);
    process.exitCode = 1;
  },
);
