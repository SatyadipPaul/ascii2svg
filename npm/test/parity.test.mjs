// The npm package must give exactly what the Python package gives: the same SVG bytes and the
// same report, for every test diagram in several looks. Needs `python` (or $PYTHON) on PATH.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { render, version } from "../index.js";

const repo = fileURLToPath(new URL("../../", import.meta.url));
const fixtures = `${repo}tests/fixtures/`;
const names = readdirSync(fixtures).filter((n) => n.endsWith(".txt"));
const LOOKS = [
  {},
  { preset: "readme" },
  { color: true, theme: "dark", describe: true },
  { repair: true, describe: true },
  { html: true, animate: "scroll", style: "shadow", square: true },
  { preset: "explore", fold: 1, describe: true },
  { portable: true, style: "flat" },
];

// One Python run renders every case with the Python package (wcwidth kept out, as in Pyodide).
const PY = `
import json, sys
sys.modules["wcwidth"] = None
sys.path.insert(0, sys.argv[1] + "scripts")
import ascii2svg
cases = json.loads(sys.stdin.read())
out = []
for name, looks in cases:
    text = open(sys.argv[1] + "tests/fixtures/" + name, encoding="utf-8").read()
    try:
        markup, report = ascii2svg.render(text, **looks)
        out.append({"markup": markup, "report": report})
    except ValueError as e:
        out.append({"error": str(e)})
sys.stdout.buffer.write(json.dumps(out).encode())
`;

const cases = names.flatMap((n) => LOOKS.map((l) => [n, l]));
const expected = JSON.parse(execFileSync(process.env.PYTHON ?? "python", ["-c", PY, repo], {
  input: JSON.stringify(cases), maxBuffer: 1 << 30,
}).toString("utf8"));

test("the version inside matches the Python package", async () => {
  const src = readFileSync(`${repo}scripts/ascii2svg.py`, "utf8");
  assert.equal(await version(), src.match(/__version__ = "([^"]+)"/)[1]);
  assert.equal(JSON.parse(readFileSync(new URL("../package.json", import.meta.url))).version, await version());
});

test(`${cases.length} renders are byte-identical to the Python package`, async () => {
  for (const [i, [name, looks]] of cases.entries()) {
    const want = expected[i];
    let got;
    try {
      got = await render(readFileSync(fixtures + name, "utf8"), looks);
    } catch (e) {
      got = { error: e.message };
    }
    const label = `${name} ${JSON.stringify(looks)}`;
    assert.equal(got.error, want.error, label);
    assert.equal(got.markup, want.markup, label);
    assert.deepEqual(got.report, want.report, label);
  }
});
