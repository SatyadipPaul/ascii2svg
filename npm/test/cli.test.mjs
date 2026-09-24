// The npm command line: files (relative and absolute), stdin, JSON reports, exit codes and MCP.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const cli = fileURLToPath(new URL("../cli.js", import.meta.url));
const fixture = fileURLToPath(new URL("../../tests/fixtures/ascii_basic.txt", import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "a2s-npm-"));
const run = (args, input) => spawnSync(process.execPath, [cli, ...args], { cwd: dir, input, encoding: "utf8" });

test("--version", () => {
  const r = run(["--version"]);
  assert.equal(r.status, 0);
  assert.match(r.stdout, /^ascii2svg \d+\.\d+\.\d+/);
});

test("absolute paths in and out, with a JSON report", () => {
  const out = join(dir, "abs.svg");
  const r = run([fixture, "-o", out, "--json", "--brief"]);
  assert.equal(r.status, 0, r.stderr);
  const report = JSON.parse(r.stdout);
  assert.equal(report.status, "ok");
  assert.equal(report.svg, out);                         // the path as given, not the mount inside Python
  assert.match(readFileSync(out, "utf8"), /^<svg /);
});

test("relative paths, a directory output and stdin", () => {
  writeFileSync(join(dir, "d.txt"), readFileSync(fixture));
  assert.equal(run(["d.txt", "-o", "rel.svg"]).status, 0);
  assert.ok(existsSync(join(dir, "rel.svg")));
  assert.equal(run(["d.txt", "-o", "outdir/"]).status, 0);
  assert.ok(existsSync(join(dir, "outdir", "d.svg")));
  const piped = run(["-", "--check"], readFileSync(fixture, "utf8"));
  assert.equal(JSON.parse(piped.stdout).status, "ok");
});

test("errors keep the Python CLI's exit codes and hints", () => {
  const missing = run(["nope.txt", "--json"]);
  assert.equal(missing.status, 1);
  assert.equal(JSON.parse(missing.stdout).status, "bad_input");
  const png = run([fixture, "--png", "x.png", "--json"]);
  assert.equal(JSON.parse(png.stdout).status, "usage_error");
  assert.match(JSON.parse(png.stdout).hint, /pip install/);
});

test("--mcp answers JSON-RPC and writes files where asked", () => {
  const target = join(dir, "mcp.svg");
  const lines = [
    { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18" } },
    { jsonrpc: "2.0", method: "notifications/initialized" },
    { jsonrpc: "2.0", id: 2, method: "tools/call",
      params: { name: "render_diagram", arguments: { diagram: "+--+\n|ab|\n+--+", output_path: target } } },
  ].map((m) => JSON.stringify(m)).join("\n") + "\n";
  const r = run(["--mcp"], lines);
  const replies = r.stdout.trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(replies.map((m) => m.id), [1, 2]);
  assert.equal(JSON.parse(replies[1].result.content[0].text).status, "ok");
  assert.ok(existsSync(target));
});
