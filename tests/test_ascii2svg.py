"""Tests for ascii2svg.

Run:  python3 tests/test_ascii2svg.py      (no extra installs)
 or:  python3 -m pytest tests
"""
import html
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


def pipeline(text, style="glow", square=False, **look):
    lines, notes = a2s.prepare(text)
    cells, nr, nc = a2s.build_grid(lines)
    drawn, info = a2s.interpret(cells, nr, nc)
    draw = {k: ((drawn[k], w) if k in drawn else (t, w)) for k, (t, w) in cells.items()}
    svg, stats = a2s.render_svg(draw, nr, nc, style, square, **look)
    return cells, draw, svg, stats, notes


def glow_hits(svg):
    """Label characters sitting on visible glow (own titles on plates are fine)."""
    cw, ch = 9.0, 18.0
    boxes, glows = [], []
    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"'
                         r'(?: rx="[\d.]+")? class="(glow|fill|plate)[ "]', svg):
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
    for x, y, t in text_cells(svg):
        w = a2s.width_of(t)                              # '&gt;' is one character wide
        cell = (x - w * cw / 2, y - 5 - ch / 2, x + w * cw / 2, y - 5 + ch / 2)
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


LOOKS = [dict(theme="dark", color=True), dict(theme="auto", color=True, animate="flow"),
         dict(theme="light", animate="draw")]


def test_every_look_roundtrips_exactly():
    for name in FIXTURES:
        for look in LOOKS:
            for style in ("glow", "flat"):
                cells, draw, svg, _, _ = pipeline(fx(name), style, **look)
                assert a2s.self_check(svg, draw, cells) == [], (name, look, style)


_LINE_CLS = r'(sgl|dbl|dbl-gap|sgl dash n[234])'


def _segments(body):
    """Every connector piece, however it is written: one <line> each (animated) or subpaths of one
    <path> per style (a still drawing). -> sorted [(class, piece)]"""
    out = []
    hue = lambda rest: re.search(r'data-h="(\d+)"', rest).group(1) if "data-h" in rest else ""
    for x1, y1, x2, y2, cls, rest in re.findall(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" '
                                                r'class="%s"([^>]*)/>' % _LINE_CLS, body):
        if x1 != x2 and y1 != y2:
            out.append((cls, hue(rest), f"M{x1} {y1}L{x2} {y2}"))
        else:
            out.append((cls, hue(rest), f"M{x1} {y1}H{x2}" if y1 == y2 else f"M{x1} {y1}V{y2}"))
    for d, cls, rest in re.findall(r'<path d="(M[^"]*)" class="%s"([^>]*)/>' % _LINE_CLS, body):
        out += [(cls, hue(rest), "M" + sub) for sub in d.split("M")[1:]]
    runs, rest = {}, []                                   # pieces that touch on one line are one line
    for cls, h, piece in out:
        m = re.fullmatch(r"M([\d.]+) ([\d.]+)([HV])([\d.]+)", piece)
        if not m:
            rest.append((cls, h, piece))
            continue
        x, y, op, e = m.group(1), m.group(2), m.group(3), float(m.group(4))
        key, a = (cls, h, op, y if op == "H" else x), float(x if op == "H" else y)
        runs.setdefault(key, []).append((min(a, e), max(a, e)))
    for key, iv in runs.items():
        iv.sort()
        cur = list(iv[0])
        for a, b in iv[1:] + [(float("inf"), 0)]:
            if a <= cur[1] + 0.01:
                cur[1] = max(cur[1], b)
                continue
            rest.append((key[0], key[1], f"{key[2]}{key[3]}:{cur[0]:g}-{cur[1]:g}"))
            cur = [a, b]
    return sorted(rest)


def _strip_motion(svg):
    body = svg[svg.index("</style>"):]
    body = re.sub(r' pathLength="1"| style="[^"]*"| class="r\d+"', "", body).replace(' class="r0 ', ' class="')
    body = re.sub(r' class="r\d+ ', ' class="', body)
    body = re.sub(r'<g class="pulse".*?</g>', "", body)
    segs = _segments(body)
    body = re.sub(r'<(line|path) [^>]*class="%s"[^>]*/>' % _LINE_CLS, "", body)
    return body, segs


def text_cells(svg):
    """(x, y, character) for every drawn character, whether it has its own <text> or sits in a run."""
    for xs, y, t in re.findall(r'<text x="([\d. ]+)" y="([\d.]+)"[^>]*>(.*?)</text>', svg):
        t, xs = html.unescape(t), xs.split()
        pairs = [(xs[0], t)] if len(xs) == 1 else [(x, c) for x, c in zip(xs, t) if c != " "]
        yield from ((float(x), float(y), c) for x, c in pairs)


def chars(svg):
    return [c for *_, c in text_cells(svg)]


def test_animation_ends_on_the_static_drawing():
    """Animated = static + timing only, and every animation reverts to the static state when done."""
    for name in FIXTURES:
        for kw in (dict(theme="auto", color=True), dict(style="shadow")):
            style = kw.pop("style", "glow")
            still = pipeline(fx(name), style, **kw)[2]
            moving = pipeline(fx(name), style, animate="flow", **kw)[2]
            assert _strip_motion(moving) == _strip_motion(still), name
    css = re.search(r"<style>(.*)</style>", moving).group(1)
    shorthands = [a for a in re.findall(r"animation:([^;}]+)", css) if not a.startswith("none")]
    assert shorthands and all(a.strip().endswith("backwards") for a in shorthands), shorthands
    assert "forwards" not in css and "infinite" not in css and "prefers-reduced-motion" in css
    assert all(g.startswith('<g class="pulse" opacity="0">') for g in re.findall(r'<g class="pulse"[^>]*>', moving))


def test_flow_follows_every_arrow_from_its_source():
    get_routes = lambda name: pipeline(fx(name), animate="flow")
    _, draw, svg, stats, _ = get_routes("complex_unicode.txt")
    assert stats["flows"] == stats["arrowheads"] == 18
    _, draw, svg, stats, _ = get_routes("ascii_fanout.txt")
    paths = re.findall(r'<animateMotion path="([^"]+)"', svg)
    starts = sorted(p.split("L")[0] for p in paths)
    gateway_foot = "M%g %g" % (12 + 14 * 9 + 4.5, 12 + 2 * 18 + 9)         # the ┬ under Gateway
    assert stats["flows"] == 4 and starts.count(gateway_foot) == 2, starts
    assert pipeline(fx("ascii_fanout.txt"), animate="draw")[3]["flows"] == 0


def test_color_groups_boxes():
    svg = pipeline(fx("complex_unicode.txt"), color=True)[2]
    tints = re.findall(r'class="fill (t\w+)"', svg)
    assert len(tints) == 28 and tints.count("tn") == 1                 # only the outer platform box is neutral
    assert len({t[:2] for t in tints if t != "tn"}) == 6                # six groups, six hues


def test_scroll_reveal_is_driven_by_the_page():
    cells, draw, svg, stats, _ = pipeline(fx("complex_unicode.txt"), color=True, animate="scroll")
    assert a2s.self_check(svg, draw, cells) == [] and 'data-reveal="scroll"' in svg
    assert _strip_motion(svg) == _strip_motion(pipeline(fx("complex_unicode.txt"), color=True)[2])
    css = re.search(r"<style>(.*)</style>", svg).group(1)
    assert "a2s-on" in css and not re.search(r"(^|})\.sgl,\.dbl\{animation", css)   # nothing plays by itself
    assert stats["flows"] == 18 and svg.count('begin="indefinite"') == 36             # pulses wait for the page
    page = a2s.to_html(svg, "t", "auto")
    assert page.startswith("<!doctype html>") and svg.strip() in page and "IntersectionObserver" in page
    assert "prefers-reduced-motion" in page and "<script" not in svg                   # no script inside the SVG
    assert "<script" not in a2s.to_html(pipeline(fx("ascii_fanout.txt"), animate="flow")[2])


def test_self_check_catches_planted_faults():
    cells, draw, svg, _, _ = pipeline(fx("complex_unicode.txt"))
    letter = svg.replace(">API Gateway</text>", ">API GateWay</text>", 1)
    m = re.search(r'M([\d.]+) ([\d.]+)Q([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', svg)
    hx, cy, qx, qy, vx, vy = map(float, m.groups())
    corner = svg.replace(m.group(0), f'M{2 * qx - hx:g} {cy:g}Q{qx:g} {qy:g} {vx:g} {vy:g}', 1)
    line = re.sub(r'(<path d="[^"]*?)M[\d.]+ [\d.]+V[\d.]+', r"\1", svg, count=1)      # one piece of line gone
    run = re.search(r'<text x="([\d. ]+)"', svg).group(1)
    shifted = svg.replace(f'<text x="{run}"', '<text x="%s"' % " ".join(f"{float(v) + 9:g}" for v in run.split()), 1)
    short = svg.replace(f'<text x="{run}"', '<text x="%s"' % " ".join(run.split()[:-1]), 1)   # a run missing an x
    for bad in (letter, corner, line, shifted, short):
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


def test_markdown_table_stays_text_and_ascii_trees_are_drawn():
    cells, draw, *_ = pipeline(fx("markdown_table.txt"))
    assert draw == cells
    for name in ("ascii_tree.txt", "tree_cargo_ascii.txt"):                  # `tree`, `cargo tree` in ASCII
        cells, draw, svg, _, _ = pipeline(fx(name))
        assert a2s.self_check(svg, draw, cells) == [] and not set(chars(svg)) & set("|`"), name
    for text in ("see |-- here", "a\n|-- b", "a\n|-- b\n|-- c", "ls\n`--x", "x |-- y\n  `-- z",
                 "| a | b |\n|---|---|\n| 1 | 2 |", "a\n|--b\n`--c"):       # no closing '`--', no name, not under a label
        cells, draw, *_ = pipeline(text)
        assert draw == cells, text


def test_arrow_text_without_structure_stays_text():
    cells, draw, *_ = pipeline("x + y = z\nC++ and a->b\nmaps x -> y\nrun --dry-run\nfn f(s: &str) -> Result<T>\n")
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
    assert code == 0 and out.startswith("<svg") and "self-check exact" in err
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


def test_library_api():
    svg, report = a2s.render(fx("ascii_fanout.txt"), color=True, animate="flow")
    assert svg.startswith("<svg") and report["roundtrip"] == "exact" and report["exit_code"] == 0
    assert report["flows"] == 4 and report["color"] is True
    page, report = a2s.render(fx("complex_unicode.txt"), animate="scroll", html=True, theme="auto")
    assert page.startswith("<!doctype html>") and report["roundtrip"] == "exact"
    for bad in (dict(animate="scroll"), dict(theme="sepia"), dict(style="neon")):
        try:
            a2s.render("+--+\n|  |\n+--+", **bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


def test_help_is_written_for_models():
    out = cli("--help")[1]
    assert "exit codes" in out and "--json" in out and "stays text" in out and "--animate" in out


def test_cli_looks():
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "--json", "--animate", "--color", "--theme", "auto")
    r = json.loads(out)
    assert (code, r["animate"], r["color"], r["theme"], r["flows"], r["roundtrip"]) == (0, "flow", True, "auto", 4, "exact")
    assert "prefers-color-scheme:dark" in r["svg"] and "<animateMotion" in r["svg"]
    assert cli("--text", "+--+", "--animate", "sideways")[0] == 1           # usage error: 1, never 2
    assert cli("--text", "+--+", "--animate", "scroll")[0] == 1               # scroll needs a web page
    code, out, _ = cli(os.path.join(FX, "complex_unicode.txt"), "--json", "--html", "--animate", "scroll")
    r = json.loads(out)
    assert code == 0 and r["html"].startswith("<!doctype html>") and r["roundtrip"] == "exact" and not r["tips"]
    r = json.loads(cli(os.path.join(FX, "complex_unicode.txt"), "--json", "--animate")[1])
    assert r["tips"] and "scroll" in r["tips"][0]                             # tall + timed: suggest scroll


# ── agent contract ───────────────────────────────────────────────────────────
MISALIGNED = "+------+\n| api  |\n+--+---+\n   |\n    v\n+------+\n| db   |\n+------+\n"


def test_usage_errors_are_json_and_never_exit_2():
    code, out, _ = cli("--text", "+--+", "--animate", "sideways", "--json")
    r = json.loads(out)
    assert (code, r["status"], r["exit_code"]) == (1, "usage_error", 1) and "flow" in r["choices"], r
    code, out, _ = cli("--text", "+--+", "--colour", "--json")
    r = json.loads(out)
    assert code == 1 and "--color" in r["hint"], r
    code, out, err = cli("--text", "+--+", "--colour")                        # no --json: hint on stderr
    assert code == 1 and out == "" and "hint:" in err and "--color" in err


def test_json_is_ascii_safe():
    code, out, _ = cli(os.path.join(FX, "complex_unicode.txt"), "--json")
    assert out.isascii() and json.loads(out)["roundtrip"] == "exact"


def test_status_and_summary_come_first():
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "--json", "--brief")
    r = json.loads(out)
    assert list(r)[:3] == ["status", "summary", "exit_code"] and r["status"] == "ok"
    assert "3 boxes and 4 arrows" in r["summary"] and "svg" not in r              # --brief: no markup


def test_escaped_newlines_are_caught_and_can_be_fixed():
    code, out, _ = cli("--text", r"+----+\n| hi |\n+----+", "--json", "--brief")
    r = json.loads(out)
    assert r["status"] == "warnings" and r["warnings"][0]["code"] == "escaped_newlines", r
    code, out, _ = cli("--text", r"+----+\n| hi |\n+----+", "--json", "--brief", "--unescape")
    r = json.loads(out)
    assert (r["status"], r["boxes"], r["rows"]) == ("ok", 1, 3), r


def test_near_miss_gets_a_concrete_fix():
    code, out, _ = cli("-", "--json", "--brief", stdin=MISALIGNED.encode())
    r = json.loads(out)
    w = r["warnings"][0]
    assert (r["status"], w["code"], w["row"], w["col"]) == ("warnings", "dangling_line", 4, 4), r
    assert "line 5 col 5" in w["hint"] and "one column right" in w["hint"] and w["hint"] in r["summary"]
    fixed = MISALIGNED.replace("    v", "   v")
    r = json.loads(cli("-", "--json", "--brief", stdin=fixed.encode())[1])
    assert (r["status"], r["arrowheads"]) == ("ok", 1), r


def test_broken_join_names_the_right_character():
    _, report = a2s.render("┌──┐\n│  │\n└──┘\n─┌─\n")            # ─ runs into ┌, which has no arm back
    joins = [w for w in report["warnings"] if w["code"] == "broken_join"]
    assert joins and "use '┬' instead of '┌'" in joins[0]["hint"], report["warnings"]


def test_unclosed_box_says_which_wall_breaks():
    _, report = a2s.render("+----+\n| hi |\n+---+\n")                          # bottom edge too short
    assert [w["code"] for w in report["warnings"]] == ["unclosed_box"], report["warnings"]
    _, report = a2s.render("+------+\n| hi   |\n| yo   <\n+------+\n")      # '<' in a wall, no connector
    w = [w for w in report["warnings"] if w["code"] == "unclosed_box"]
    assert len(w) == 1 and "right wall at line 3 col 8 is '<'" in w[0]["hint"], w
    assert report["status"] == "warnings"                                       # never a silent 'ok'
    _, report = a2s.render("a +- b -+ c\n")                                     # pieces, but no box starts
    assert [w["code"] for w in report["warnings"]] == ["no_structure"]
    for name in ("markdown_table.txt", "ascii_tree.txt", "ascii_labels.txt", "ascii_fanout.txt", "ascii_titled.txt"):
        assert not [w for w in a2s.render(fx(name))[1]["warnings"]
                    if w["code"] in ("no_structure", "unclosed_box")], name


def test_no_false_alarms_on_well_formed_diagrams():
    """Sequence messages │──▶│, lifeline ends, axis ticks, labels below lines, titles in borders."""
    for name in ("sequence.txt", "timeline.txt", "gantt_ticks.txt", "xy_chart.txt", "c4_dashed.txt",
                 "complex_unicode.txt", "ascii_fanout.txt", "unicode_labels.txt"):
        report = a2s.render(fx(name))[1]
        assert report["status"] == "ok", (name, report["warnings"])


def test_touching_lines_are_drawn_touching():
    svg = a2s.render(fx("sequence.txt"))[0]
    life = 12 + 4 * 9 + 4.5                                                      # the Client lifeline's x
    assert re.search(r'M%g [\d.]+H' % (life + 0.7), svg), "message should start at the lifeline"
    cells, draw, svg, _, _ = pipeline(fx("sequence.txt"))
    assert a2s.self_check(svg, draw, cells) == []                               # the lifeline still reads back as │


def test_real_mistakes_still_warn():
    _, r = a2s.render("┌────┐\n│ a  │\n└─┬──┘\n  │\n\n┌────┐\n│ b  │\n└────┘\n")   # stops one row short
    w = r["warnings"]
    assert [x["code"] for x in w] == ["dangling_line"] and "stops 1 cell short of '─' at line 6 col 3" in w[0]["hint"], w
    _, r = a2s.render("──  ┐\n\n    │\n")                                        # two gaps from one corner
    corner = [x for x in r["warnings"] if (x["row"], x["col"]) == (1, 5)]
    assert len(corner) == 1 and "also toward" in corner[0]["issue"], r["warnings"]  # one warning per character


def test_check_validates_and_writes_nothing(tmp=os.path.join(HERE, "_tmp_check.svg")):
    if os.path.exists(tmp):
        os.remove(tmp)
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "-o", tmp, "--check")
    r = json.loads(out)
    assert code == 0 and r["status"] == "ok" and not os.path.exists(tmp) and "svg" not in r


def test_describe_says_what_connects_to_what():
    _, report = a2s.render(fx("ascii_fanout.txt"), describe=True)
    d = report["diagram"]
    assert [b["name"] for b in d["boxes"]] == ["Gateway", "Orders", "Payments"]
    edges = {(e["from"].get("name") or e["from"].get("text"), e["to"].get("name") or e["to"].get("text"))
             for e in d["edges"]}
    assert edges == {("Gateway", "Orders"), ("Gateway", "Payments"), ("Payments", "Orders"),
                     ("Orders", "audit.log")}, edges
    _, report = a2s.render(fx("complex_unicode.txt"), describe=True)
    names = {(e["from"].get("name"), e["to"].get("name")) for e in report["diagram"]["edges"]}
    assert ("JWT AuthFilter", "RateLimiter") in names and ("RateLimiter", "Router") in names
    byname = {b["name"]: b for b in report["diagram"]["boxes"]}
    assert byname["TaxCalculator"]["parent"] == byname["PricingEngine"]["id"]


def test_presets_and_explicit_flags():
    _, r = a2s.render(fx("ascii_fanout.txt"), preset="readme")
    assert (r["theme"], r["color"], r["animate"], r["preset"]) == ("auto", True, "flow", "readme")
    _, r = a2s.render(fx("ascii_fanout.txt"), preset="readme", animate="draw", color=False)
    assert (r["theme"], r["color"], r["animate"]) == ("auto", False, "draw")
    page, r = a2s.render(fx("ascii_fanout.txt"), preset="page")
    assert page.startswith("<!doctype html>") and r["html"] is True and r["animate"] == "scroll"
    r = json.loads(cli(os.path.join(FX, "ascii_fanout.txt"), "--check", "--preset", "dark", "--no-color")[1])
    assert (r["theme"], r["color"]) == ("dark", False)


def test_schema_describes_every_option():
    code, out, _ = cli("--schema")
    s = json.loads(out)
    listed = {f for o in s["options"] for f in o["flags"]}
    real = {f for a in a2s.build_parser()._actions for f in a.option_strings} - {"-h", "--help", "--version"}
    assert code == 0 and real <= listed and set(s["presets"]) == set(a2s.PRESETS)
    assert set(s["exit_codes"]) == {"0", "1", "2", "3"}
    assert {"dangling_line", "broken_join", "escaped_newlines", "no_structure"} <= set(s["warning_codes"])


def test_forgotten_input_fails_instead_of_hanging():
    env = {**os.environ, "ASCII2SVG_STDIN_WAIT": "0.5"}
    p = subprocess.Popen([sys.executable, CLI, "--json"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    try:
        code = p.wait(timeout=20)                                              # stdin stays open, never written
        r = json.loads(p.stdout.read())
    finally:
        p.stdin.close()
        p.stdout.close()
        if p.poll() is None:
            p.kill()
    assert code == 1 and r["status"] == "bad_input" and "nothing arrived" in r["error"], r


# ── many diagrams, style, MCP ────────────────────────────────────────────────
README_MD = """# Service

```bash
pip install thing
```

```
+-------+     +-------+
| api   |---->| cache |
+---+---+     +-------+
    |
     v
+-------+
| db    |
+-------+
```

```text
┌───────┐    ┌────────┐
│ build ├───▶│ deploy │
└───────┘    └────────┘
```
"""


def _tmpdir(name):
    import shutil
    d = os.path.join(HERE, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    return d


def test_all_blocks_renders_every_diagram_and_skips_code():
    import shutil
    d = _tmpdir("_tmp_blocks")
    try:
        md = os.path.join(d, "README.md")
        open(md, "w", encoding="utf-8").write(README_MD)
        code, out, _ = cli(md, "--all-blocks", "-o", os.path.join(d, "out") + "/", "--json")
        r = json.loads(out)
        assert code == 0 and r["status"] == "warnings" and len(r["diagrams"]) == 2, r["summary"]
        assert [s["source"]["info"] for s in r["skipped"]] == ["bash"]
        assert sorted(os.listdir(os.path.join(d, "out"))) == ["README-2.svg", "README-3.svg"]
        w = r["diagrams"][0]["warnings"][0]                        # the off-by-one v, in file coordinates
        assert (w["code"], w["source_line"], w["source_col"]) == ("dangling_line", 11, 5), w
        assert README_MD.split("\n")[w["source_line"] - 1][w["source_col"] - 1] == "|"
        assert "line 12 col 6" in w["hint"], w["hint"]
        assert README_MD.split("\n")[11][5] == "v"
        code, out, _ = cli(md, "--block", "3", "--check")
        r = json.loads(out)
        assert (r["status"], r["source"]["block"], r["boxes"]) == ("ok", 3, 2)
        assert json.loads(cli(md, "--block", "9", "--check")[1])["status"] == "bad_input"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_several_inputs_one_report_each():
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), os.path.join(FX, "wide_chars.txt"),
                       os.path.join(FX, "no_such_file.txt"), "--check")
    r = json.loads(out)
    assert (code, r["status"]) == (1, "bad_input") and [d["status"] for d in r["diagrams"]] == ["ok", "ok", "bad_input"]
    assert "3 diagrams" in r["summary"] and "1 bad input" in r["summary"]
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), os.path.join(FX, "wide_chars.txt"), "-o", "one.svg", "--json")
    assert code == 1 and "directory" in json.loads(out)["error"]            # -o must be a directory for several


def test_style_options():
    svg, r = a2s.render(fx("ascii_fanout.txt"), color=True, accent="#e8590c", font="JetBrains Mono", width=570)
    assert r["roundtrip"] == "exact" and "#e8590c" in svg and "'JetBrains Mono',ui-monospace" in svg
    assert re.search(r'viewBox="0 0 285 240" width="570" height="480"', svg)
    for bad in (dict(accent="orange"), dict(font="x;}</style>"), dict(width=3)):
        try:
            a2s.render(fx("ascii_fanout.txt"), **bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "--accent", "blue", "--json")
    assert code == 1 and json.loads(out)["status"] == "usage_error"


def test_mcp_server_speaks_the_protocol():
    import shutil
    d = _tmpdir("_tmp_mcp")
    p = subprocess.Popen([sys.executable, CLI, "--mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def rpc(i, method, params=None):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}}) + "\n")
        p.stdin.flush()
        return json.loads(p.stdout.readline())

    try:
        init = rpc(1, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t"}})
        assert init["result"]["protocolVersion"] == "2025-03-26" and "tools" in init["result"]["capabilities"]
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        tools = rpc(2, "tools/list")["result"]["tools"]
        assert {t["name"] for t in tools} == {"render_diagram", "check_diagram"}
        assert all(t["inputSchema"]["required"] == ["diagram"] for t in tools)
        res = rpc(3, "tools/call", {"name": "check_diagram", "arguments": {"diagram": fx("ascii_fanout.txt")}})["result"]
        rep = json.loads(res["content"][0]["text"])
        assert res["isError"] is False and rep["status"] == "ok" and len(rep["diagram"]["edges"]) == 4
        out = os.path.join(d, "nested", "fan.svg")
        res = rpc(4, "tools/call", {"name": "render_diagram",
                                    "arguments": {"diagram": fx("ascii_fanout.txt"), "output_path": out, "preset": "readme"}})["result"]
        rep = json.loads(res["content"][0]["text"])
        assert rep["status"] == "ok" and os.path.getsize(out) > 1000 and rep["svg"] == os.path.abspath(out)
        res = rpc(5, "tools/call", {"name": "render_diagram", "arguments": {"diagram": 42}})["result"]
        assert res["isError"] is True
        assert rpc(6, "tools/call", {"name": "nope"})["error"]["code"] == -32602
        assert rpc(7, "no/such/method")["error"]["code"] == -32601
        assert rpc(8, "ping")["result"] == {}
    finally:
        p.stdin.close()
        code = p.wait(timeout=20)
        p.stdout.close()
        err = p.stderr.read()
        p.stderr.close()
        shutil.rmtree(d, ignore_errors=True)
    assert code == 0 and err == "", err                                        # stdout carried only protocol


def test_playground_runs_the_released_module():
    """docs/playground/ascii2svg.py is what the browser runs; it must be this exact module."""
    play = os.path.join(os.path.dirname(HERE), "docs", "playground")
    if not os.path.isdir(play):                                   # the sdist ships without docs/
        return
    assert open(os.path.join(play, "ascii2svg.py"), "rb").read() == open(CLI, "rb").read(),         "run python3 docs/build.py to refresh the playground's copy"
    examples = json.load(open(os.path.join(play, "examples.json"), encoding="utf-8"))
    for name, text in examples.items():
        assert a2s.render(text)[1]["roundtrip"] == "exact", name


# ── repair ───────────────────────────────────────────────────────────────────
LLM_FIXTURES = ["llm_output.txt", "llm_ascii_ragged.txt", "llm_side_by_side.txt", "llm_arrow_short.txt",
                "broken_misaligned.txt", "llm_big_offsets.txt"]
LINE_CHARS = set("─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╪▼▲▶◀|+-v^<> ")


def _words(lines):
    """Each row with every line character and space removed: what repair must never change."""
    return ["".join(ch for ch in line if ch not in LINE_CHARS) for line in lines]


def test_repair_fixes_llm_style_misalignment():
    for name in LLM_FIXTURES:
        before = a2s.render(fx(name))[1]
        svg, after = a2s.render(fx(name), repair=True, describe=True)
        assert before["status"] == "warnings" and after["status"] == "ok", (name, after["warnings"])
        assert after["roundtrip"] == "exact" and after["repair"]["edits"] and after["repair"]["text"], name
        assert after["boxes"] >= before["boxes"], name
    _, r = a2s.render(fx("llm_output.txt"), repair=True, describe=True)
    edges = {(e["from"].get("name"), e["to"].get("name")) for e in r["diagram"]["edges"]}
    assert r["boxes"] == 5 and edges == {("📱 Mobile app", "API Gateway"), ("API Gateway", "Auth service"),
                                         ("API Gateway", "Orders service"), ("Orders service", "PostgreSQL")}, edges
    _, r = a2s.render(fx("llm_ascii_ragged.txt"), repair=True, describe=True)
    edges = {(e["from"].get("name"), e["to"].get("name")) for e in r["diagram"]["edges"]}
    assert r["boxes"] == 3 and edges == {("Client", "Server"), ("Server", "Database")}, edges


def test_repair_never_changes_text():
    for name in LLM_FIXTURES:
        original = a2s.prepare(fx(name))[0]
        repaired = a2s.render(fx(name), repair=True)[1]["repair"]["text"].split("\n")
        assert len(repaired) == len(original), name
        assert _words(repaired) == _words(original), name


def test_repair_leaves_good_diagrams_alone():
    for name in FIXTURES:
        if name in LLM_FIXTURES:
            continue
        r = a2s.render(fx(name), repair=True)[1]
        assert r["repair"]["edits"] == [] and "text" not in r["repair"], (name, r["repair"]["edits"][:3])


def test_repair_result_is_exact_and_positions_point_into_the_input():
    _, r = a2s.render(fx("broken_misaligned.txt"), repair=True)
    assert r["repair"]["text"] == ("┌──────────────┐\n│ Order service│\n│ 🚀 fast path │\n└─────┬────────┘\n"
                                   "      │\n┌─────▼────────┐\n│ Kafka topic  │\n└──────────────┘")
    fixes = {(e["line"], e["col"]): e["fix"] for e in r["repair"]["edits"]}
    assert fixes[(5, 7)] == "moved '│' 2 col right to line it up", fixes
    code, out, _ = cli(os.path.join(FX, "llm_output.txt"), "--check", "--repair")
    j = json.loads(out)
    assert j["status"] == "ok" and j["summary"].startswith("Repaired 5 misalignments. Rendered 5 boxes"), j["summary"]


def test_block_elements_are_exact_rectangles():
    cells, draw, svg, stats, _ = pipeline("A ████░░ ▏▎▍▌▋▊▉ ▁▂▃▄▅▆▇ ▀▐▔▕ ▘▝▖▗▚▞▙▛▜▟\nB ▓▓▒▒", color=True, animate="draw")
    assert a2s.self_check(svg, draw, cells) == []
    texts = chars(svg)
    assert not any(t in a2s.BLOCKS for t in texts), texts           # no glyphs: rectangles only
    runs = re.findall(r'<rect x="[\d.]+" y="[\d.]+" width="([\d.]+)" height="[\d.]+" class="blk (k\d)"', svg)
    assert ("36", "k4") in runs and ("18", "k1") in runs, runs       # ████ is one rect, ░░ another
    assert svg.count('class="blk k3"') == 1 and svg.count('class="blk k2"') == 1
    assert "crispEdges" in svg and "a2s-grow" in svg


def test_diagonals_draw_only_as_runs():
    text = fx("diagonals.txt")
    cells, draw, svg, stats, _ = pipeline(text)
    assert a2s.self_check(svg, draw, cells) == []
    assert "╱" in {t for t, _ in draw.values()} and "╲" in {t for t, _ in draw.values()}
    assert not set(chars(svg)) & set("/\\")                           # every slash in the fixture is a line
    assert svg.count('class="sgl ext"') >= 4                          # diamond caps + run-ons to the firewall
    for words in ("yes/no", "TCP/IP", r"C:\Users", r"\_/", "a/b/c", "/\n/"):
        cells, draw, svg, _, _ = pipeline(words)
        assert not any(t in a2s.DIAG for t, _ in draw.values()), words
    cells, draw, svg, _, _ = pipeline("╱╲\n╲╱ ╳")
    assert a2s.self_check(svg, draw, cells) == [] and "<text" not in svg


def test_dashed_lines_join_like_lines_and_keep_their_dash_count():
    cells, draw, svg, stats, _ = pipeline(fx("dashed.txt"), color=True, animate="flow")
    assert a2s.self_check(svg, draw, cells) == []
    assert stats["boxes"] == 4 and stats["flows"] == 3                # dashed boxes, pulses along dashed arrows
    for n in "234":
        assert f'class="sgl dash n{n}"' in svg, n
    assert not re.search(r'class="sgl dash[^"]*" pathLength', svg)    # pathLength would stretch the dashes
    swapped = fx("dashed.txt").replace("╌", "┄", 1)                  # the dash count is part of the read-back
    cells, draw, svg, _, _ = pipeline(swapped)
    assert a2s.self_check(svg, draw, cells) == [] and "sgl dash n3" in svg
    d = a2s.describe(*a2s.build_grid(fx("c4_dashed.txt").split("\n")))
    boundary = next(b for b in d["boxes"] if b["name"].startswith("Internet Banking"))
    assert sum(b["parent"] == boundary["id"] for b in d["boxes"]) == 3, d["boxes"]


def test_uml_heads_are_drawn_and_described():
    for name, shapes in (("uml.txt", 3), ("../../docs/examples/mermaid/class.txt", 1)):
        cells, draw, svg, stats, _ = pipeline(fx(name), color=True, animate="draw")
        assert a2s.self_check(svg, draw, cells) == [], name
        assert len(re.findall(r'<polygon[^>]*class="uml', svg)) == shapes, name
        assert not set(chars(svg)) & set("△▽◁▷◇◆"), name
    assert 'class="uml solid"' in pipeline(fx("uml.txt"))[2]                   # ◆ composition is filled
    d = a2s.describe(*a2s.build_grid(fx("uml.txt").split("\n")))
    kinds = {(e["from"]["name"], e["to"]["name"]): e.get("kind") for e in d["edges"]}
    assert kinds == {("Wheel", "Car"): "composition", ("Driver", "Car"): "aggregation",
                     ("Driver", "Person"): "inheritance"}, kinds
    for loose in ("◆ Feature one\n◇ Feature two", "a △ b"):                   # bullets and symbols stay text
        cells, draw, svg, _, _ = pipeline(loose)
        assert "class=\"uml" not in svg and a2s.self_check(svg, draw, cells) == [], loose


def test_er_crows_foot_notation():
    text = fx("er_crowsfoot.txt")
    cells, draw, svg, stats, _ = pipeline(text, color=True)
    assert a2s.self_check(svg, draw, cells) == [] and stats["boxes"] == 3
    assert svg.count('class="ring"') == 2 and svg.count('class="foot"') == 2   # o and < > in the walls
    assert not set(chars(svg)) & set("|<>")                                       # every mark is drawn
    _, report = a2s.render(text, describe=True)
    assert report["status"] == "ok" and not report["warnings"], report["warnings"]
    rel = [(e["from"]["name"], e["to"]["name"], e["cardinality"]) for e in report["diagram"]["edges"]]
    assert rel == [("CUSTOMER", "ORDER", ["one", "zero or many"]), ("ORDER", "PRODUCT", ["zero or many", "one"])], rel
    for plain in ("+---+     +---+\n| a |---->| b |\n+---+     +---+\n",     # an arrow is still an arrow
                  "+---+     +---+\n| a |-----| b |\n+---+     +---+\n"):    # and a plain link a line
        cells, draw, svg, _, _ = pipeline(plain)
        assert 'class="foot"' not in svg and 'class="ring"' not in svg
    _, r = a2s.render("+---+     +---+\n| a |-----| b |\n+---+     +---+\n", describe=True)
    assert [e.get("kind") for e in r["diagram"]["edges"]] == ["link"]


def test_er_crows_foot_runs_vertically_too():
    text = fx("er_vertical.txt")
    cells, draw, svg, stats, _ = pipeline(text, color=True)
    assert a2s.self_check(svg, draw, cells) == [] and stats["boxes"] == 3
    assert svg.count('class="ring"') == 2 and not set(chars(svg)) & set("|o/\\-")
    feet = [ln for ln in re.findall(r'<line [^>]*class="sgl"[^>]*/>', svg) if 'x1="' in ln
            and re.search(r'x1="([\d.]+)"', ln).group(1) != re.search(r'x2="([\d.]+)"', ln).group(1)
            and re.search(r'y1="([\d.]+)"', ln).group(1) != re.search(r'y2="([\d.]+)"', ln).group(1)]
    assert len(feet) == 4                                               # two prongs per foot, drawn as diagonals
    _, r = a2s.render(text, describe=True)
    assert r["status"] == "ok" and not r["warnings"], r["warnings"]
    rel = [(e["from"]["name"], e["to"]["name"], e["cardinality"]) for e in r["diagram"]["edges"]]
    assert rel == [("CUSTOMER", "ORDER", ["one", "zero or many"]), ("ORDER", "SHIPMENT", ["zero or many", "one"])], rel
    uni = "┌──────┐\n│  A   │\n└──┬───┘\n   │\n   ┼\n   │\n   ○\n  ╱│╲\n┌──┴───┐\n│  B   │\n└──────┘\n"
    _, r = a2s.render(uni, describe=True)
    assert r["status"] == "ok" and r["diagram"]["edges"][0]["cardinality"] == ["one", "zero or many"], r["diagram"]
    for plain in ("+---+\n| a |\n+-+-+\n  |\n  v\n+-+-+\n| b |\n+---+\n",       # an arrow down stays an arrow
                  "x\n-+-\ny\n"):                                          # a '-+-' among words stays text
        cells, draw, svg, _, _ = pipeline(plain)
        assert 'class="ring"' not in svg and a2s.self_check(svg, draw, cells) == [], plain


def test_ascii_uml_heads():
    cells, draw, svg, stats, _ = pipeline(fx("uml_ascii.txt"), color=True)
    assert a2s.self_check(svg, draw, cells) == [] and stats["boxes"] == 8
    assert svg.count('class="uml wide"') == 3 and svg.count('class="uml solid"') == 1   # <| <> |> span two cells
    assert not set(chars(svg)) & set("<>|*")
    kinds = [(e["from"]["name"], e["to"]["name"], e.get("kind"))
             for e in a2s.render(fx("uml_ascii.txt"), describe=True)[1]["diagram"]["edges"]]
    assert kinds == [("Dog", "Animal", "inheritance"), ("Wheel", "Car", "aggregation"),
                     ("LineItem", "Order", "composition"), ("Cat", "Pet", "inheritance")], kinds
    for words in ("a <| b", "x <> y", "* bullet item", "2*3-4", "if a<|b-- then"):   # no box: stays text
        cells, draw, svg, _, _ = pipeline(words)
        assert "uml" not in "".join(t for t, _ in draw.values() if t in a2s.UML) and 'class="uml' not in svg, words


def test_ascii_dashed_and_dotted_lines():
    text = fx("dashed_ascii.txt")
    cells, draw, svg, stats, _ = pipeline(text, animate="flow")
    assert a2s.self_check(svg, draw, cells) == [] and stats["flows"] == 4      # pulses hop the gaps in '- - ->'
    glyphs = {"╌", "┈", "┊"}
    assert glyphs <= {t for t, _ in draw.values()}
    _, r = a2s.render(text, describe=True)
    assert r["status"] == "ok" and not r["warnings"], r["warnings"]
    edges = [(e["from"]["name"], e["to"]["name"]) for e in r["diagram"]["edges"]]
    assert edges == [("API", "Queue"), ("API", "Worker"), ("Worker", "Cache"), ("Retry", "DLQ")], edges
    for words in ("Loading...", "Intro ........ 3", "- - -", "wait... then go", "a: b: c", "x - y - z"):
        cells, draw, svg, _, _ = pipeline(words)
        assert not glyphs & {t for t, _ in draw.values()}, words


def test_ascii_rounded_corners():
    text = fx("rounded_ascii.txt")
    cells, draw, svg, stats, _ = pipeline(text)
    assert a2s.self_check(svg, draw, cells) == [] and stats["boxes"] == 7
    drawn = [t for t, _ in draw.values()]
    assert drawn.count("╭") == 6 and drawn.count("╯") == 7              # six boxes, one bend each way
    assert drawn.count("┌") == 1                                           # a '+' box stays square beside them
    _, r = a2s.render(text, describe=True)
    assert r["status"] == "ok" and not r["warnings"], r["warnings"]
    edges = [(e["from"]["name"], e["to"]["name"]) for e in r["diagram"]["edges"]]
    assert edges == [("Ingress", "Web app"), ("Web app", "Worker"), ("Cron", "Worker"), ("Backup", "Postgres")], edges
    _, _, sq, _, _ = pipeline(text, square=True)
    plates = sorted(re.findall(r'rx="([\d.]+)" class="fill"', sq))
    assert plates == ["0"] + ["4"] * 6, plates                             # --square: only '+' corners go sharp
    for words in ("It's done. Don't -- fine.", "a.b.c --- 'quoted' `code`", "He said '---' and left.",
                  "project\n|-- src\n|   `-- main.py\n`-- README.md", ".\n|\n'"):
        cells, draw, svg, _, _ = pipeline(words)
        assert not set("╭╮╰╯") & {t for t, _ in draw.values()}, words


def test_free_floating_connectors_between_words():
    text = fx("floating.txt")
    cells, draw, svg, stats, _ = pipeline(text, animate="flow")
    assert a2s.self_check(svg, draw, cells) == [] and stats["flows"] == 12
    assert {"▶", "◀", "▼", "┴", "╰", "╯"} <= {t for t, _ in draw.values()}
    _, r = a2s.render(text, describe=True)
    assert r["status"] == "ok" and not r["warnings"], r["warnings"]
    edges = [(e["from"]["text"], e["to"]["text"], e.get("label")) for e in r["diagram"]["edges"]]
    assert edges == [("CDN", "Browser", None), ("Browser", "CDN", None), ("CDN", "Origin", None),
                     ("Origin", "Auth service", None), ("Origin", "Orders service", None),
                     ("Auth service", "Postgres", None), ("Orders service", "Postgres", None),
                     ("request", "parse", None), ("parse", "validate", None), ("validate", "store", None),
                     ("Web app", "API", "REST"), ("API", "Billing", "gRPC")], edges
    _, r = a2s.render("+---+         +---+\n| A |--HTTP-->| B |\n+---+         +---+", describe=True)
    assert [(e["from"]["name"], e["to"]["name"], e["label"]) for e in r["diagram"]["edges"]] == [("A", "B", "HTTP")]
    for words in ("a-->b and x->y", "maps x -> y", "node->next = head;", "Name ---- Value", "<!-- note -->",
                  "run --dry-run --verbose --> out", 'print("  -->", name)',
                  "| a | b |\n|---|---|\n| 1 | 2 |", "---\ntitle: x\n---", "- item\n  - sub", "x\n|\ny"):
        cells, draw, *_ = pipeline(words)
        assert draw == cells, words


def test_vertical_ascii_uml_heads():
    text = fx("uml_vertical.txt")
    cells, draw, svg, stats, _ = pipeline(text)
    assert a2s.self_check(svg, draw, cells) == [] and stats["arrowheads"] == 4
    assert svg.count('class="uml tri3"') == 2 and svg.count("pair-r") == 1 and "uml solid" in svg
    _, r = a2s.render(text, describe=True, repair=True)
    assert r["status"] == "ok" and not r["warnings"] and "repairs" not in r, r
    edges = [(e["from"]["name"], e["to"]["name"], e["kind"]) for e in r["diagram"]["edges"]]
    assert edges == [("Car", "Vehicle", "inheritance"), ("Truck", "Vehicle", "inheritance"),
                     ("Driver", "<<iface>>", "inheritance"), ("Wheel", "Car", "aggregation"),
                     ("Cargo", "Truck", "composition")], edges
    for words in ("emoticon /_\\ and <> and * bullets", "a * b <> c /_\\ d", "+---+\n| a |\n+---+\n /_\\"):
        cells, draw, *_ = pipeline(words)
        assert not {"△", "◇", "◆"} & {t for t, _ in draw.values()}, words


def test_npm_package_has_the_same_version():
    pkg = json.load(open(os.path.join(os.path.dirname(HERE), "npm", "package.json"), encoding="utf-8"))
    assert pkg["version"] == a2s.__version__, "bump npm/package.json with __version__"
    assert pkg["name"] == "@satyadip28/asciitosvg" and pkg["bin"]["ascii2svg"] == "cli.js"


def test_repair_reaches_bigger_offsets():
    _, r = a2s.render(fx("llm_big_offsets.txt"), repair=True, describe=True)
    assert r["status"] == "ok" and r["boxes"] == 3, r["warnings"]
    assert r["repair"]["text"].split("\n")[2] == "| (OAuth2)               |----------->|  Postgres   |"
    edges = [(e["from"]["name"], e["to"]["name"]) for e in r["diagram"]["edges"]]
    assert edges == [("Authentication Service", "Users DB"), ("Authentication Service", "🚀 Deploy pipeline")]
    fixes = " ".join(e["fix"] for e in r["repair"]["edits"])
    assert "8 col right" in fixes and "4 cols left to join it up" in fixes
    # an arrow that stops short is flagged, then carried on to touch its box
    short = "+-----+             +-----+\n|  A  |------>      |  B  |\n+-----+             +-----+"
    assert [w["code"] for w in a2s.render(short)[1]["warnings"]] == ["short_arrow"]
    _, r = a2s.render(short, repair=True)
    assert r["status"] == "ok" and r["repair"]["text"].split("\n")[1] == "|  A  |------------>|  B  |"
    # a line split 4 columns apart is joined into one, never doubled
    split = ("+---------+\n|  Client |\n+---------+\n     |\n     |\n         |\n         v\n"
             "+---------+\n|  Server |\n+---------+")
    _, r = a2s.render(split, repair=True)
    assert r["status"] == "ok" and r["repair"]["text"].split("\n")[3:7] == ["     |"] * 3 + ["     v"]


# ── trees: call trees, file trees, dependency trees, mind maps ───────────────
def tree_of(text):
    return a2s.render(text, describe=True)[1]["diagram"].get("tree")


def names(tree):
    return [[n["name"], names(n.get("children", []))] if n.get("children") else n["name"] for n in tree]


def test_trees_are_read_from_every_common_shape():
    assert names(tree_of(fx("tree_calls.txt"))) == [["main()", [["load_config()", ["read_file()", "parse_yaml()"]],
                                                                 ["run_server()", ["bind_port()", ["serve_forever()",
                                                                                                   ["handle_request()"]]]]]]]
    npm = names(tree_of(fx("tree_npm.txt")))                                   # '├─┬ express': the ┬ hands its trunk on
    assert npm == [["app@1.0.0", [["express@4.19.2", ["body-parser@1.20.2", ["send@0.18.0", ["mime@1.6.0"]]]],
                                  "lodash@4.17.21"]]], npm
    cargo = names(tree_of(fx("tree_cargo_ascii.txt")))
    assert cargo[0][0] == "myapp v0.1.0 (/home/me/myapp)" and [c if isinstance(c, str) else c[0] for c in cargo[0][1]] \
        == ["clap v4.5.4", "serde v1.0.197", "tokio v1.37.0"], cargo
    assert names(tree_of(fx("ascii_tree.txt"))) == [["order-service/", [["api/", ["OrderController.java", "dto/"]],
                                                                        "README.md"]]]
    mind = tree_of(fx("mindmap.txt"))                                          # left to right, rounded branches
    assert [n["name"] for n in mind[0]["children"]] == ["Identify the Decision", "Weigh Your Options",
                                                         "Evaluate Trade-offs", "Make the Decision", "Review & Defend"]
    count = lambda ns: sum(1 + count(n.get("children", [])) for n in ns)
    assert count(mind) == 45


def test_describe_lists_every_branch():
    _, r = a2s.render(open(os.path.join(os.path.dirname(HERE), "docs", "examples", "mermaid", "mindmap-tree.txt"),
                           encoding="utf-8").read(), describe=True)
    d = r["diagram"]
    branches = {(e["from"].get("name") or e["from"].get("text"), e["to"].get("name") or e["to"].get("text"))
                for e in d["edges"] if e.get("kind") == "branch"}
    assert {("Product plan", "Growth"), ("Product plan", "Quality"), ("Product plan", "Platform"),
            ("Growth", "SEO"), ("Platform", "Webhooks")} <= branches and len(branches) == 12, branches
    assert d["tree"][0]["box"] == "b1" and [n["name"] for n in d["tree"][0]["children"]] == ["Growth", "Quality", "Platform"]


def test_flowcharts_and_timelines_are_not_trees():
    for name in ("ascii_fanout.txt", "timeline.txt", "sequence.txt", "swimlanes.txt" if os.path.exists(os.path.join(FX, "swimlanes.txt")) else "uml.txt"):
        assert tree_of(fx(name)) is None, name
    _, r = a2s.render(fx("complex_unicode.txt"), describe=True)              # only its call tree is a tree
    assert [n["name"] for n in r["diagram"]["tree"]] == ["POST /api/v1/orders"]


def _static(svg):
    """An interactive SVG without its script and fold groups: what an <img> shows (lines as pieces)."""
    svg = re.sub(r"<script>.*?</script>", "", svg, flags=re.S)
    return _strip_motion(_unfold(svg))


def _unfold(svg):
    svg = re.sub(r' data-g="\d+"', "", svg)
    return re.sub(r"\[data-g\]\{transition.*?(?=@media \(prefers-color-scheme|</style>)", "",
                  svg.replace(a2s._fold_colour_css(a2s.THEMES["light"]), "").replace(a2s._fold_colour_css(a2s.THEMES["dark"]), ""),
                  count=1, flags=re.S)


def test_interactive_svg_is_the_static_drawing_plus_a_script():
    for name in ("mindmap.txt", "tree_calls.txt", "tree_npm.txt", "ascii_tree.txt", "complex_unicode.txt"):
        for look in (dict(color=True, theme="auto"), dict(style="flat")):
            cells, draw, svg, stats, _ = pipeline(fx(name), interactive=True, **look)
            assert a2s.self_check(svg, draw, cells) == [], name
            assert svg.count("<script>") == 1 and stats["folds"] > 0 and "data-g=" in svg, name
            still = pipeline(fx(name), **look)[2]
            assert "<script" not in still and "data-g=" not in still
            assert _static(svg) == _strip_motion(still), name
    cells, draw, svg, stats, _ = pipeline(fx("ascii_fanout.txt"), interactive=True)   # nothing to fold: no script
    assert "<script" not in svg and stats["folds"] == 0


def test_fold_data_is_safe_and_complete():
    text = "root ]]> </script> <b>\n├── a & b\n│   └── x\n└── c\n"
    cells, draw, svg, _, _ = pipeline(text, interactive=True, fold=1)
    assert a2s.self_check(svg, draw, cells) == []
    assert svg.count("]]>") == 1 and svg.count("</script>") == 1                 # only the script's own end
    data = json.loads(re.search(r"\}\)\((\{.*\})\);\]\]>", svg, re.S).group(1))
    assert data["n"] == ["root ]]> </script> <b>", "a & b", "x", "c"] and data["p"] == [-1, 0, 1, 0] and data["f"] == 1
    assert len(data["r"]) == 4 and data["r"][2] == [1]                             # row 3 holds only what 'a' hides
    code, out, _ = cli("-", "--fold", "1", "--json", "--brief", stdin=text.encode())
    r = json.loads(out)
    assert code == 0 and r["interactive"] is True and r["folds"] == 2
    code, out, _ = cli(os.path.join(FX, "ascii_fanout.txt"), "--interactive", "--json", "--brief")
    r = json.loads(out)
    assert r["folds"] == 0 and any("--interactive" in t for t in r["tips"])
    _, r = a2s.render(fx("tree_calls.txt"), preset="explore")
    assert r["interactive"] and r["color"] and r["theme"] == "auto" and r["folds"] == 4


def test_branch_colours_only_for_pure_trees():
    svg = pipeline(fx("mindmap.txt"), color=True)[2]
    assert len(set(re.findall(r'class="sgl" data-h="(\d)"', svg))) == 5              # five main branches, five colours
    assert svg.count('class="pill root"') == 1 and svg.count('class="pill" data-h=') == 5
    assert 'class="a2s-root"' in svg
    for name in ("complex_unicode.txt", "ascii_fanout.txt"):                    # arrows: the usual colours
        svg = pipeline(fx(name), color=True)[2]
        assert "data-h=" not in svg and "pill" not in svg, name
    assert "data-h=" not in pipeline(fx("mindmap.txt"))[2]                       # no --color, no colours


def test_portable_and_png_frames_place_every_character_alone():
    cells, draw, svg, stats, _ = pipeline(fx("complex_unicode.txt"), color=True, runs=False)
    assert a2s.self_check(svg, draw, cells) == [] and svg.count("<text") == stats["text_cells"]
    assert not re.search(r'<text x="[\d.]+ ', svg)                             # cairosvg anchors whole runs
    code, out, _ = cli(os.path.join(FX, "tree_calls.txt"), "--portable", "--json")
    r = json.loads(out)
    assert code == 0 and r["svg"].count("<text") == r["text_cells"]
    assert a2s.render(fx("tree_calls.txt"), portable=True)[0].count("<text") == r["text_cells"]


def test_svg_is_compact():
    cells, draw, svg, stats, _ = pipeline(fx("complex_unicode.txt"))
    assert svg.count("<text") < stats["text_cells"] / 4                        # words, not letters
    assert svg.count('class="glow"') == 7 * stats["boxes"]
    assert len(re.findall(r'<path d="M[^"]*" class="sgl"', svg)) == 1                 # every plain line: one path
    assert not re.search(r'<line [^>]*class="sgl"/>', svg)                           # (arrow shafts stay lines)
    assert len(svg.encode()) < 50_000, len(svg.encode())                        # 87 KB before 1.16


# ── the skill's composing guide ──────────────────────────────────────────────
ROOT = os.path.dirname(HERE)


def test_composing_guide_examples_render_cleanly():
    guide = open(os.path.join(ROOT, "references", "composing.md"), encoding="utf-8").read()
    blocks = re.findall(r"```text\n(.*?)```", guide, re.S)
    assert len(blocks) >= 20, len(blocks)                                       # catalog + recipes
    for text in blocks:
        _, r = a2s.render(text, describe=True)
        assert r["status"] == "ok" and not r["warnings"], (text[:80], r["warnings"][:2])
        assert r["cols"] <= 100, (text[:80], r["cols"])                         # reads on a laptop
    for heading in ("## 1. Take inventory", "## 2. Match each kind to a notation", "## Catalog",
                    "## Recipes", "## When to split instead"):
        assert heading in guide, heading
    helper = re.search(r"```python\n(.*?)```", guide, re.S).group(1)       # the grid helper runs as printed
    out = subprocess.run([sys.executable, "-c", helper], capture_output=True, check=True,     # UTF-8 on any console
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"}).stdout.decode("utf-8")
    _, r = a2s.render(out, describe=True)
    assert r["status"] == "ok" and [(e["from"]["name"], e["to"]["name"]) for e in r["diagram"]["edges"]] == \
        [("Checkout", "Payment provider")], (out, r["diagram"]["edges"])


def test_skill_points_to_the_guide_and_ships_it():
    import zipfile
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "references/composing.md" in skill and "|--` file trees are left exactly" not in skill
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:                 # never into dist/: the release uploads dist/* to PyPI
        out = os.path.join(tmp, "ascii2svg.skill")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "package_skill.py"), out], check=True, capture_output=True)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
    assert names == ["ascii2svg/SKILL.md", "ascii2svg/scripts/ascii2svg.py", "ascii2svg/references/composing.md"], names



def test_repair_moves_a_line_with_its_corner_instead_of_oscillating():
    # the '│' and '┘' agree on a column one right of the box's '┬': moving the '│' alone opened
    # the same gap at the '┘', the next pass moved it back, and repair ping-ponged 200 times
    bad = ("    │  ┌──────┴───────┐       ┌──────┴───────┐\n"
           "    │  │ Reply now    │       │ Price engine │\n"
           "    │  └──────┬───────┘       └──────┬───────┘\n"
           "    │         │                       │\n"
           "    │◀────────┴───────────────────────┘")
    _, r = a2s.render(bad, repair=True)
    assert r["status"] == "ok" and not r["warnings"], r["warnings"]
    assert 1 <= len(r["repair"]["edits"]) <= 5, r["repair"]["edits"]
    assert r["repair"]["text"].split("\n")[3:] == ["│         │                      │",
                                                    "│◀────────┴──────────────────────┘"]
    # the corner can also move away from its line, which then grows by a cell
    grow = "┌──────┐\n│  A   │\n└───┬──┘\n   │\n───┘"
    _, r = a2s.render(grow, repair=True)
    assert r["status"] == "ok" and r["repair"]["text"].split("\n")[3:] == ["    │", "────┘"]
    # whatever it can't fix, repair stops rather than undoing its own edit
    _, r = a2s.render(bad, repair=True)
    fixes = [(e["line"], e["col"]) for e in r["repair"]["edits"]]
    assert len(fixes) == len(set(fixes)), fixes


def test_repair_stops_when_a_fix_would_undo_an_earlier_one():
    flip = {"n": 0}
    def ping_pong(g):                                       # a fixer that always undoes itself
        flip["n"] += 1
        a, b = ((0, 0), (0, 1)) if flip["n"] % 2 else ((0, 1), (0, 0))
        g.put(*b, g.ch(*a))
        g.put(*a, " ")
        g.note(*b, "moved")
        return True
    saved = a2s._repair_connector_once
    a2s._repair_connector_once = ping_pong
    try:
        cells, edits = a2s.repair({(0, 0): ("x", 1)})
    finally:
        a2s._repair_connector_once = saved
    assert flip["n"] == 2 and edits == [] and cells[(0, 0)] == ("x", 1), (flip, edits)


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
