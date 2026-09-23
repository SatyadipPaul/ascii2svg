"""Tests for ascii2svg.

Run:  python3 tests/test_ascii2svg.py      (no extra installs)
 or:  python3 -m pytest tests
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(os.path.dirname(HERE), "scripts", "ascii2svg.py")
FX = os.path.join(HERE, "fixtures")
_spec = importlib.util.spec_from_file_location("ascii2svg", CLI)
a2s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a2s)
FIXTURES = sorted(os.listdir(FX))


def fx(name):
    return open(os.path.join(FX, name), encoding="utf-8").read()


def cli(*args, stdin=None, env=None):
    p = subprocess.run([sys.executable, CLI, *args], input=stdin, capture_output=True, env=env)
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")


def pipeline(text, style="glow", square=False):
    lines, notes = a2s.prepare(text)
    cells, nr, nc = a2s.build_grid(lines)
    drawn, info = a2s.interpret(cells, nr, nc)
    draw = {k: ((drawn[k], w) if k in drawn else (t, w)) for k, (t, w) in cells.items()}
    svg, stats = a2s.render_svg(draw, nr, nc, style, square)
    return cells, draw, svg, stats, notes


def glow_hits(svg):
    """Label characters sitting on visible glow (own titles on plates are fine)."""
    cw, ch = 9.0, 18.0
    boxes, glows = [], []
    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"'
                         r'(?: rx="[\d.]+")? class="(glow|fill|plate)"', svg):
        x, y, w, h = map(float, m.groups()[:4])
        if m.group(5) == "glow":
            glows.append((x, y, x + w, y + h))
        elif m.group(5) == "fill":
            boxes.append({"fill": (x, y, x + w, y + h), "glow": glows, "plates": []})
            glows = []
        else:
            boxes[-1]["plates"].append((x, y, x + w, y + h))
    hit = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    inside = lambda a, b: b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    n = 0
    for x, y, t in re.findall(r'<text x="([\d.]+)" y="([\d.]+)">(.*?)</text>', svg):
        w = a2s.width_of(t)
        cell = (float(x) - w * cw / 2, float(y) - 5 - ch / 2, float(x) + w * cw / 2, float(y) - 5 + ch / 2)
        for b in boxes:
            if inside(cell, b["fill"]) or any(inside(cell, p) for p in b["plates"]):
                continue
            n += any(hit(cell, g) for g in b["glow"])
    return n


# ── 1:1 in every style ───────────────────────────────────────────────────────
def test_every_fixture_roundtrips_exactly_in_every_style():
    for name in FIXTURES:
        for style in ("glow", "shadow", "flat"):
            for square in (False, True):
                cells, draw, svg, _, _ = pipeline(fx(name), style, square)
                assert a2s.self_check(svg, draw, cells) == [], (name, style, square)


def test_self_check_catches_planted_faults():
    cells, draw, svg, _, _ = pipeline(fx("complex_unicode.txt"))
    letter = svg.replace(">y</text>", ">Y</text>", 1)
    m = re.search(r'<path d="M([\d.]+) ([\d.]+)Q([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', svg)
    hx, cy, qx, qy, vx, vy = map(float, m.groups())
    corner = svg.replace(m.group(0), f'<path d="M{2 * qx - hx:g} {cy:g}Q{qx:g} {qy:g} {vx:g} {vy:g}"', 1)
    line = re.sub(r'<line x1="[\d.]+" y1="[\d.]+" x2="[\d.]+" y2="[\d.]+" class="sgl"/>', "", svg, count=1)
    for bad in (letter, corner, line):
        assert bad != svg
        assert a2s.self_check(bad, draw, cells), "planted fault was not caught"


def test_output_is_deterministic():
    assert pipeline(fx("complex_unicode.txt"))[2] == pipeline(fx("complex_unicode.txt"))[2]


# ── Unicode diagram ──────────────────────────────────────────────────────────
def test_complex_diagram_counts():
    code, out, _ = cli(os.path.join(FX, "complex_unicode.txt"), "--json")
    r = json.loads(out)
    assert (code, r["boxes"], r["arrowheads"], len(r["warnings"]), r["roundtrip"]) == (0, 28, 18, 0, "exact")


# ── ASCII detection: draw structure, never labels ────────────────────────────
def test_ascii_labels_stay_text():
    cells, draw, *_ = pipeline(fx("ascii_labels.txt"))
    for r in range(1, 7):                       # every label row inside the first box
        for c in range(1, 29):
            assert draw[(r, c)] == cells[(r, c)], (r, c, cells[(r, c)], draw[(r, c)])
    assert draw[(7, 14)][0] == "┬"              # junction on the bottom edge
    assert draw[(9, 14)][0] == "▼"              # the real arrow is drawn...
    assert draw[(6, 14)][0] == "v"              # ...the v in "video" above the junction is not


def test_ascii_fanout_junctions_and_arrows():
    cells, draw, svg, stats, _ = pipeline(fx("ascii_fanout.txt"))
    got = {k: draw[k][0] for k in [(2, 14), (4, 6), (4, 14), (4, 22), (6, 6), (6, 22), (8, 13), (11, 6), (11, 10)]}
    assert got == {(2, 14): "┬", (4, 6): "┌", (4, 14): "┴", (4, 22): "┐", (6, 6): "▼", (6, 22): "▼",
                   (8, 13): "◀", (11, 6): "└", (11, 10): "▶"}, got
    assert stats["boxes"] == 3


def test_titled_ascii_box_keeps_title_text():
    cells, draw, svg, stats, _ = pipeline(fx("ascii_titled.txt"))
    title = "".join(draw[(0, c)][0] for c in range(4, 18))
    assert title == "order-svc (v2)" and stats["boxes"] == 3


def test_markdown_table_and_tree_stay_text():
    for name in ("markdown_table.txt", "ascii_tree.txt"):
        cells, draw, *_ = pipeline(fx(name))
        assert draw == cells, name


def test_arrow_text_without_structure_stays_text():
    cells, draw, *_ = pipeline("User ---> Server\nx + y = z\nC++ and a->b\n")
    assert draw == cells


# ── clean-up ─────────────────────────────────────────────────────────────────
def test_broken_input_is_cleaned_and_flagged():
    code, out, _ = cli(os.path.join(FX, "broken_misaligned.txt"), "--json")
    r = json.loads(out)
    changes = {n["change"] for n in r["normalized"]}
    assert code == 0 and "expanded tabs" in changes and "non-breaking or unusual spaces -> space" in changes
    assert r["warnings"], "misaligned diagram should produce connector warnings"
    assert cli(os.path.join(FX, "broken_misaligned.txt"), "--strict")[0] == 3


def test_fence_prose_ansi_zero_width():
    lines, notes = a2s.prepare("intro\n```text\n\x1b[31m+--+\x1b[0m\n|a\u200b |\n+--+\n```\nafter\n")
    assert lines == ["+--+", "|a |", "+--+"]
    kinds = {n["change"] for n in notes}
    assert {"used the first markdown code block", "removed terminal colour codes",
            "removed invisible or control characters"} <= kinds


def test_zwj_and_combining_kept_as_one_cell():
    assert a2s.clusters("a\u0301👩\u200d💻b") == ["a\u0301", "👩\u200d💻", "b"]


def test_width_fallback_agrees_with_wcwidth():
    if a2s._wcswidth is None:
        return
    real = a2s._wcswidth
    for name in FIXTURES:
        for line in fx(name).split("\n"):
            for cl in a2s.clusters(line):
                a2s._wcswidth = real
                w1 = a2s.width_of(cl)
                a2s._wcswidth = None
                w2 = a2s.width_of(cl)
                a2s._wcswidth = real
                assert w1 == w2, (name, cl, w1, w2)


# ── glow never sits behind a label ───────────────────────────────────────────
def test_glow_never_behind_a_label():
    for name in FIXTURES:
        assert glow_hits(pipeline(fx(name))[2]) == 0, name
    tight = pipeline("+----+label\n|  a |\n+----+\n")[2]          # text touching a box: glow must shrink
    assert glow_hits(tight) == 0


def test_glow_check_can_fail():
    svg = pipeline(fx("complex_unicode.txt"))[2]
    grow = lambda m: (f'<rect x="{float(m[1]) - 8:g}" y="{float(m[2]) - 8:g}" width="{float(m[3]) + 16:g}" '
                      f'height="{float(m[4]) + 16:g}" rx="1" class="glow"')
    bigger = re.sub(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="[\d.]+" class="glow"',
                    grow, svg)
    assert glow_hits(bigger) > 0


# ── command line ─────────────────────────────────────────────────────────────
def test_cli_stdin_text_and_inline_svg():
    code, out, err = cli(stdin=fx("ascii_basic.txt").encode())
    assert code == 0 and out.startswith("<svg") and "round-trip=exact" in err
    code, out, _ = cli("--text", fx("ascii_basic.txt"), "--json")
    r = json.loads(out)
    assert code == 0 and r["svg"].startswith("<svg") and r["boxes"] == 3


def test_cli_errors_are_clean():
    assert cli("--text", "   \n\n", "--json")[0] == 1
    assert cli("/no/such/file.txt")[0] == 1
    code, out, _ = cli(os.path.join(FX, "complex_unicode.txt"), "--max-rows", "10", "--json")
    assert code == 1 and "limit" in json.loads(out)["error"]
    assert cli("--text", "+--+", "--png", "--json")[0] == 1          # --png without a path or -o


def test_cli_invalid_utf8_reported():
    code, out, _ = cli("-", "--json", stdin=b"+--+\n|\xff |\n+--+\n")
    r = json.loads(out)
    assert code == 0 and any("UTF-8" in n["change"] for n in r["normalized"])


def test_cli_png(tmp=os.path.join(HERE, "_tmp_out")):
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        return
    os.makedirs(tmp, exist_ok=True)
    svg = os.path.join(tmp, "d.svg")
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "-o", svg, "--png", "--json")
    r = json.loads(out)
    assert code == 0 and os.path.getsize(r["png"]) > 1000 and open(svg).read().startswith("<svg")


def test_cli_output_is_utf8_on_any_console():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}     # what a Windows console gives by default
    env.pop("PYTHONUTF8", None)
    code, out, err = cli(os.path.join(FX, "broken_misaligned.txt"), "--json", env=env)
    assert code == 0 and json.loads(out)["warnings"], err
    code, out, err = cli("--help", env=env)
    assert code == 0 and "─│┌┐" in out, err
    code, out, err = cli(os.path.join(FX, "wide_chars.txt"), env=env)      # SVG with emoji/CJK on stdout
    assert code == 0 and ">🚀</text>" in out and ">数</text>" in out, err


def test_help_is_written_for_models():
    out = cli("--help")[1]
    assert "exit codes" in out and "--json" in out and "stays text" in out


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
