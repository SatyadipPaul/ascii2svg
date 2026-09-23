#!/usr/bin/env python3
"""ascii2svg - turn an ASCII or Unicode box diagram into an SVG, 1:1.

Every character keeps its exact grid cell. Box-drawing characters, and ASCII
+ - | v ^ < > that form a box or attach to one, are drawn as real lines.
Everything else is drawn as the same text in the same place.

Built for LLM agents:   cat diagram.txt | ascii2svg -o diagram.svg --json
As a library:           svg, report = ascii2svg.render(text, color=True, animate="flow")
No required dependencies (uses `wcwidth` for character widths if installed).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata

__version__ = "1.6.0"

# ─── character width ─────────────────────────────────────────────────────────
try:
    from wcwidth import wcswidth as _wcswidth
    WIDTH_SOURCE = "wcwidth"
except ImportError:  # zero-dependency fallback
    _wcswidth = None
    WIDTH_SOURCE = "builtin"


def _joins(ch: str) -> bool:
    """Code points that belong to the previous character on screen."""
    return (unicodedata.category(ch) in ("Mn", "Me") or ch in "\u200d\ufe0e\ufe0f"
            or 0x1F3FB <= ord(ch) <= 0x1F3FF)


def clusters(line: str) -> list[str]:
    out: list[str] = []
    for ch in line:
        if out and (_joins(ch) or out[-1].endswith("\u200d")):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def width_of(cluster: str) -> int:
    if _wcswidth is not None:
        w = _wcswidth(cluster)
    else:
        w = 2 if (unicodedata.east_asian_width(cluster[0]) in ("W", "F")
                  or "\ufe0f" in cluster[1:]) else 1
    return 2 if w >= 2 else 1


# ─── input clean-up ──────────────────────────────────────────────────────────
_SPACES = dict.fromkeys(map(ord, "\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
                                 "\u2007\u2008\u2009\u200a\u202f\u205f"), " ")
_DROP = dict.fromkeys(map(ord, "\u200b\u2060\ufeff"), None)   # ZWJ/ZWNJ are kept on purpose
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_FENCE = re.compile(r"^\s*(```+|~~~+)")


def prepare(text: str, tab_size: int = 4) -> tuple[list[str], list[dict]]:
    """Normalise raw input into grid lines. Every change is reported."""
    lines, notes, _ = prepare_ex(text, tab_size)
    return lines, notes


def prepare_ex(text: str, tab_size: int = 4):
    """prepare(), plus where grid cell (0, 0) sits in the input: {"line": .., "col": ..} (0-based)."""
    notes: list[dict] = []
    skipped = 0
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    first = next((i for i, l in enumerate(lines) if _FENCE.match(l)), None)
    if first is not None:
        close = next((i for i in range(first + 1, len(lines))
                      if _FENCE.match(lines[i]) and not lines[i].strip().strip("`~")), None)
        if close is not None:
            outside = sum(1 for l in lines[:first] + lines[close + 1:] if l.strip())
            fences = sum(1 for l in lines if _FENCE.match(l)) // 2
            lines = lines[first + 1:close]
            skipped = first + 1
            note = {"change": "used the first markdown code block"}
            if outside:
                note["dropped_lines_outside_block"] = outside
            if fences > 1:
                note["other_code_blocks_ignored"] = fences - 1
            notes.append(note)
    out = []
    for n, line in enumerate(lines, 1):
        if _ANSI.search(line):
            line = _ANSI.sub("", line)
            notes.append({"change": "removed terminal colour codes", "line": n})
        if "\t" in line:
            line = line.expandtabs(tab_size)
            notes.append({"change": "expanded tabs", "line": n, "tab_size": tab_size})
        new = line.translate(_SPACES)
        if new != line:
            line = new
            notes.append({"change": "non-breaking or unusual spaces -> space", "line": n})
        new = line.translate(_DROP)
        new = "".join(ch for ch in new if unicodedata.category(ch) != "Cc")
        if new != line:
            line = new
            notes.append({"change": "removed invisible or control characters", "line": n})
        out.append(line.rstrip())
    while out and not out[0]:
        out.pop(0)
        skipped += 1
    while out and not out[-1]:
        out.pop()
    indent = min((len(l) - len(l.lstrip(" ")) for l in out if l), default=0)
    if indent:
        out = [l[indent:] for l in out]
        notes.append({"change": "removed common indentation", "columns": indent})
    return out, notes, {"line": skipped, "col": indent}


_BLOCK = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def code_blocks(text: str) -> list[dict]:
    """Every closed fenced code block: {"block": n, "line": first content line (1-based), "info", "text"}."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        m = _BLOCK.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group(1)
        end = next((j for j in range(i + 1, len(lines))
                    if lines[j].strip().startswith(fence[0] * len(fence)) and not lines[j].strip().strip(fence[0])), None)
        if end is None:
            break
        out.append({"block": len(out) + 1, "line": i + 2, "info": m.group(2).strip(),
                    "text": "\n".join(lines[i + 1:end])})
        i = end + 1
    return out


def build_grid(lines: list[str]):
    """cells[(row, col)] = (text, width); width-0 entries continue a wide character."""
    cells: dict = {}
    ncols = 0
    for r, line in enumerate(lines):
        c = 0
        for cl in clusters(line):
            w = width_of(cl)
            cells[(r, c)] = (cl, w)
            if w == 2:
                cells[(r, c + 1)] = ("", 0)
            c += w
        ncols = max(ncols, c)
    return cells, len(lines), ncols


# ─── line characters ─────────────────────────────────────────────────────────
ARMS = {k: frozenset(v) for k, v in {
    "─": "LR", "│": "UD", "┌": "RD", "┐": "LD", "└": "UR", "┘": "UL", "├": "UDR", "┤": "UDL",
    "┬": "LRD", "┴": "LRU", "┼": "UDLR", "╭": "RD", "╮": "LD", "╰": "UR", "╯": "UL",
    "═": "LR", "║": "UD", "╔": "RD", "╗": "LD", "╚": "UR", "╝": "UL", "╪": "UDLR"}.items()}
DOUBLE = set("═║╔╗╚╝")
ROUNDED = set("╭╮╰╯")
HEADS = {"▼": "D", "▲": "U", "▶": "R", "◀": "L"}      # direction the arrow points
TAIL = {"▼": "U", "▲": "D", "▶": "L", "◀": "R"}       # side the shaft comes from
SINGLE_OF = {frozenset(v): k for k, v in {
    "─": "LR", "│": "UD", "┌": "RD", "┐": "LD", "└": "UR", "┘": "UL", "├": "UDR", "┤": "UDL",
    "┬": "LRD", "┴": "LRU", "┼": "UDLR"}.items()}
SINGLE_OF.update({frozenset("L"): "─", frozenset("R"): "─", frozenset("U"): "│", frozenset("D"): "│"})
ASCII_HEADS = {"v": "▼", "^": "▲", ">": "▶", "<": "◀"}
ASCII_TAIL = {"v": "U", "^": "D", ">": "L", "<": "R"}
# diagonals: which strokes each character draws, corner to corner across its cell
DIAG = {"╱": "/", "╲": "\\", "╳": "/\\"}
DIAG_OF = {"/": "╱", "\\": "╲", "/\\": "╳"}
# 1:1 contract: an ASCII character may be drawn only as the line it stands for
CORR = {"-": set("─┬┴┼"), "|": set("│├┤┼"), "+": set("┌┐└┘├┤┬┴┼─│"),
        "v": {"▼"}, "^": {"▲"}, ">": {"▶"}, "<": {"◀"}, "/": {"╱"}, "\\": {"╲"}}


def _block_table():
    """Block elements -> (shade 1-4, rectangles in eighths of the cell: x0, y0, x1, y1).
    Drawn as exact rectangles instead of font glyphs, so bars and shading have no seams."""
    full = (0, 0, 8, 8)
    t = {"█": (4, [full]), "▓": (3, [full]), "▒": (2, [full]), "░": (1, [full]),
         "▀": (4, [(0, 0, 8, 4)]), "▐": (4, [(4, 0, 8, 8)]), "▔": (4, [(0, 0, 8, 1)]), "▕": (4, [(7, 0, 8, 8)])}
    for k, ch in enumerate("▁▂▃▄▅▆▇", 1):              # lower k eighths
        t[ch] = (4, [(0, 8 - k, 8, 8)])
    for k, ch in enumerate("▏▎▍▌▋▊▉", 1):              # left k eighths
        t[ch] = (4, [(0, 0, k, 8)])
    q = {"a": (0, 0, 4, 4), "b": (4, 0, 8, 4), "c": (0, 4, 4, 8), "d": (4, 4, 8, 8)}   # quadrants
    for ch, parts in zip("▘▝▖▗▚▞▙▛▜▟", ("a", "b", "c", "d", "ad", "bc", "acd", "abc", "abd", "bcd")):
        t[ch] = (4, [q[p] for p in parts])
    return t


BLOCKS = _block_table()
BLOCK_OF = {tuple(sorted((s, r) for r in rects)): ch for ch, (s, rects) in BLOCKS.items()}
MERGEABLE = {ch for ch, (s, rects) in BLOCKS.items() if len(rects) == 1 and rects[0][0] == 0 and rects[0][2] == 8}
DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
OPP = {"U": "D", "D": "U", "L": "R", "R": "L"}


def _alnum(t: str) -> bool:
    return t.isalnum() or t == "_"


def interpret(cells, nrows, ncols):
    """Decide which ASCII characters are lines. Unsure -> keep as text (fail-safe).

    Returns ({(r, c): drawn_unicode_char}, stats)."""
    ch = lambda r, c: cells.get((r, c), (" ", 1))[0]
    struct: set = set()

    # 1) closed boxes: '+' corners, '-' edges (a title may sit on the top edge), '|' walls
    for (r, c) in sorted(cells):
        if ch(r, c) != "+" or ch(r, c + 1) != "-":
            continue
        for c2 in range(c + 2, ncols):
            t2 = ch(r, c2)
            if t2 in ("|", ""):
                break
            if t2 != "+" or ch(r, c2 - 1) != "-":
                continue
            r2 = None
            for rr in range(r + 1, nrows):
                a, b = ch(rr, c), ch(rr, c2)
                if (a == "+" and b == "+" and rr > r + 1
                        and all(ch(rr, x) in "-+" for x in range(c + 1, c2))):
                    r2 = rr
                    break
                if a not in "|+" or b not in "|+":
                    break
            if r2 is None:
                continue
            struct.update({(r, c), (r, c2)})
            x = c + 1
            while x < c2:                                   # top edge: dash runs, not title hyphens
                if ch(r, x) == "-":
                    a = x
                    while x < c2 and ch(r, x) == "-":
                        x += 1
                    left, right = ch(r, a - 1), ch(r, x)
                    if left in "+- " or right in "+- ":
                        struct.update((r, y) for y in range(a, x))
                else:
                    x += 1
            for x in range(c + 1, c2):
                if ch(r, x) == "+" and ((r, x - 1) in struct or (r, x + 1) in struct):
                    struct.add((r, x))
            struct.update((r2, x) for x in range(c, c2 + 1))
            for rr in range(r + 1, r2):
                struct.update({(rr, c), (rr, c2)})
            break

    uni = lambda r, c: ch(r, c) in ARMS or ch(r, c) in HEADS
    is_s = lambda r, c: (r, c) in struct or uni(r, c)

    # 2) connectors grow outward from structure until nothing changes
    hruns, vruns = [], []
    for r in range(nrows):
        c = 0
        while c < ncols:
            if ch(r, c) == "-" and (r, c) not in struct:
                a = c
                while ch(r, c) == "-" and (r, c) not in struct:
                    c += 1
                hruns.append((r, a, c - 1))
            else:
                c += 1
    for c in range(ncols):
        r = 0
        while r < nrows:
            if ch(r, c) == "|" and (r, c) not in struct:
                a = r
                while ch(r, c) == "|" and (r, c) not in struct:
                    r += 1
                vruns.append((c, a, r - 1))
            else:
                r += 1
    pluses = [k for k, (t, _) in sorted(cells.items()) if t == "+" and k not in struct]
    heads = [k for k, (t, _) in sorted(cells.items()) if t in ASCII_HEADS and k not in struct]

    def head_ok(r, c):
        t = ch(r, c)
        if t not in ASCII_HEADS:
            return False
        if t in "v^" and (_alnum(ch(r, c - 1)) or _alnum(ch(r, c + 1))):
            return False
        return True

    def points_into(r, c):
        """Arrowhead at (r, c) points at structure (allowing one blank cell)."""
        dr, dc = DIRS[{"v": "D", "^": "U", ">": "R", "<": "L"}[ch(r, c)]]
        return is_s(r + dr, c + dc) or (ch(r + dr, c + dc) == " " and is_s(r + 2 * dr, c + 2 * dc))

    def tail_ok(r, c):
        t = ch(r, c)
        side = ASCII_TAIL[t]
        dr, dc = DIRS[side]
        n = (r + dr, c + dc)
        tn = ch(*n)
        if n in struct:
            return tn == "+" or (tn == "|" and side in "UD") or (tn == "-" and side in "LR")
        return tn in ARMS and OPP[side] in ARMS[tn]

    def compat(t, side):
        """Neighbour t (on `side` of a junction) can carry a line into the junction."""
        need = OPP[side]
        if t == "+":
            return True
        if side in "LR" and t == "-":
            return True
        if side in "UD" and t == "|":
            return True
        if t in ASCII_HEADS:
            return ASCII_TAIL[t] == need
        return t in ARMS and need in ARMS[t]

    changed = True
    while changed:
        changed = False
        for r, a, b in hruns:
            if (r, a) in struct:
                continue
            ends, ok = [], False
            for cc, want in ((a - 1, "<"), (b + 1, ">")):
                t = ch(r, cc)
                if is_s(r, cc):
                    ok = True
                    ends.append("S")
                elif t == "+" or t == " ":
                    ends.append("O")
                elif t == want and head_ok(r, cc):
                    ends.append(("A", cc))
                    if points_into(r, cc):
                        ok = True
                else:
                    ends.append("T")
            if "T" in ends or not ok:
                continue
            struct.update((r, x) for x in range(a, b + 1))
            for e in ends:
                if isinstance(e, tuple):
                    struct.add((r, e[1]))
            changed = True
        for c, a, b in vruns:
            if (a, c) in struct:
                continue
            ok, marks = False, []
            for rr, want in ((a - 1, "^"), (b + 1, "v")):
                t = ch(rr, c)
                if is_s(rr, c):
                    ok = True
                elif t == want and head_ok(rr, c):
                    marks.append((rr, c))
                    if points_into(rr, c):
                        ok = True
            if not ok:
                continue
            struct.update((x, c) for x in range(a, b + 1))
            struct.update(marks)
            changed = True
        for (r, c) in pluses:
            if (r, c) in struct:
                continue
            nb = {s: (r + DIRS[s][0], c + DIRS[s][1]) for s in "UDLR"}
            if any(_alnum(ch(*p)) for p in nb.values()):
                continue
            cand = [s for s, p in nb.items() if compat(ch(*p), s)]
            solid = [s for s in cand if is_s(*nb[s])]
            if solid and len(cand) >= 2:
                struct.add((r, c))
                changed = True
        for (r, c) in heads:
            if (r, c) not in struct and head_ok(r, c) and tail_ok(r, c):
                struct.add((r, c))
                changed = True

    # 3) arms -> the Unicode line character each ASCII cell stands for
    def conn(r, c, d, own):
        n = (r + DIRS[d][0], c + DIRS[d][1])
        t = ch(*n)
        back = OPP[d]
        perpendicular = (own == "-" and d in "UD") or (own == "|" and d in "LR")
        if n in struct:
            if t == "-":
                return d in "LR"
            if t == "|":
                return d in "UD"
            if t == "+":
                return not perpendicular
            if t in ASCII_HEADS:
                return ASCII_TAIL[t] == back
        if t in ARMS:
            return back in ARMS[t]
        if t in HEADS:
            return TAIL[t] == back
        return False

    drawn = {}
    for (r, c) in sorted(struct):
        t = ch(r, c)
        if t in ASCII_HEADS:
            drawn[(r, c)] = ASCII_HEADS[t]
            continue
        arms = set("LR" if t == "-" else "UD" if t == "|" else "")
        arms |= {d for d in "UDLR" if conn(r, c, d, t)}
        if arms:
            drawn[(r, c)] = SINGLE_OF[frozenset(arms)]

    # 4) diagonals: '/' and '\' only in a run of two or more along their own slope, and never
    #    touching a word ("yes/no", "TCP/IP", "C:\Users" and "\_/" stay text)
    def slash(r, c):
        return ch(r, c) in "/\\" and not _alnum(ch(r, c - 1)) and not _alnum(ch(r, c + 1))

    for (r, c) in sorted(cells):
        t = ch(r, c)
        if slash(r, c):
            dc = -1 if t == "/" else 1                      # where the line goes one row down
            if any(ch(r + k, c + k * dc) == t and slash(r + k, c + k * dc) for k in (-1, 1)):
                drawn[(r, c)] = DIAG_OF[t]
    kept = sum(1 for k, (t, _) in cells.items() if t in "|+" and k not in drawn)
    kept += sum(b - a + 1 for r, a, b in hruns if b > a and (r, a) not in drawn)
    return drawn, {"ascii_drawn_as_lines": len(drawn), "ascii_line_like_kept_as_text": kept}


# ─── rendering ───────────────────────────────────────────────────────────────
CW, CH, PAD, FS = 9, 18, 12, 14
GLOW_R, GLOW_N, GLOW_DY = 7.0, 14, 1.5
SHADOW = ((1.5, 0.18), (3.0, 0.13), (4.2, 0.09))
RADIUS = 4.0
TL, TR, BL, BR = set("┌╭╔"), set("┐╮╗"), set("└╰╚"), set("┘╯╝")
BOTTOM_OK = set("─┬┴┼═╪")

# hues: (tint for a box that contains boxes, tint for a leaf box)
THEMES = {
    "light": {"ink": "#1f2328", "bg": "#ffffff", "accent": "#0969da", "glow": "#000000", "glow_a": 0.02,
              "neutral": "#f6f8fa", "hover": "#e2edfc",
              "hues": [("#f1f8ff", "#dbeeff"), ("#f0fbf3", "#d4f5de"), ("#f8f4ff", "#ebdfff"),
                       ("#fff7f0", "#ffe6d1"), ("#fff4f9", "#ffdcec"), ("#effbfa", "#cef3ef")]},
    "dark": {"ink": "#e6edf3", "bg": "#0d1117", "accent": "#58a6ff", "glow": "#ffffff", "glow_a": 0.012,
             "neutral": "#151b23", "hover": "#1c2d45",
             "hues": [("#0f1a2b", "#15325a"), ("#0e1f16", "#16402a"), ("#1b1530", "#34245a"),
                      ("#23180e", "#4a2e14"), ("#241421", "#4a1f3a"), ("#0c2023", "#124042")]},
}
ANIMATIONS = ("none", "draw", "flow", "scroll")
FLOW_SPEED, FLOW_REST = 150.0, 0.9          # pulse speed along a connector (px/s), pause between pulses (s)


def find_boxes(get, nrows, ncols):
    boxes = []
    for r in range(nrows):
        for c in range(ncols):
            t = get(r, c)
            if t not in TL:
                continue
            side = set("║╟╢╪") if t == "╔" else set("│├┤┼")
            c2 = None
            for x in range(c + 1, ncols):
                tx = get(r, x)
                if tx in TR:
                    c2 = x
                    break
                if tx in TL or tx in "│║":
                    break
            if c2 is None:
                continue
            r2 = r + 1
            while get(r2, c) in side and get(r2, c2) in side:
                r2 += 1
            if r2 == r + 1 or get(r2, c) not in BL or get(r2, c2) not in BR:
                continue
            if all(get(r2, x) in BOTTOM_OK for x in range(c + 1, c2)):
                boxes.append((r, c, r2, c2))
    inside = lambda a, b: a != b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    return sorted(boxes, key=lambda b: (sum(inside(b, o) for o in boxes), b))


def box_tints(boxes):
    """Tint class per box. Each top-level group (a box directly inside the outermost
    container, or a lone box) gets its own hue; containers get the light shade, leaves the stronger one."""
    inside = lambda a, b: a != b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    parents = {b: [o for o in boxes if inside(b, o)] for b in boxes}
    has_kids = {b: any(inside(o, b) for o in boxes) for b in boxes}
    group = {}
    for b in boxes:
        depth = len(parents[b])
        if depth == 0:
            group[b] = None if has_kids[b] else b
        else:
            group[b] = b if depth == 1 else next(p for p in parents[b] if len(parents[p]) == 1)
    hue = {g: i % len(THEMES["light"]["hues"]) for i, g in enumerate(sorted({g for g in group.values() if g}))}
    return {b: "tn" if group[b] is None else f"t{hue[group[b]]}{'c' if has_kids[b] else 'l'}" for b in boxes}


def head_geometry(r, c, d, line_like):
    """Arrowhead at cell (r, c) pointing d: (shaft x1 y1 x2 y2, triangle points, tip)."""
    x0, y0 = PAD + c * CW, PAD + r * CH
    cx, cy = x0 + CW / 2, y0 + CH / 2
    if d == "D":
        tip = y0 + CH + (CH / 2 if line_like(r + 1, c) else 0)
        return (cx, y0, cx, tip - 6), ((cx - 4, tip - 8), (cx + 4, tip - 8), (cx, tip)), (cx, tip)
    if d == "U":
        tip = y0 - (CH / 2 if line_like(r - 1, c) else 0)
        return (cx, y0 + CH, cx, tip + 6), ((cx - 4, tip + 8), (cx + 4, tip + 8), (cx, tip)), (cx, tip)
    if d == "R":
        tip = x0 + CW + (CW / 2 if line_like(r, c + 1) else 0)
        return (x0, cy, tip - 6, cy), ((tip - 8, cy - 4), (tip - 8, cy + 4), (tip, cy)), (tip, cy)
    tip = x0 - (CW / 2 if line_like(r, c - 1) else 0)
    return (x0 + CW, cy, tip + 6, cy), ((tip + 8, cy - 4), (tip + 8, cy + 4), (tip, cy)), (tip, cy)


def box_border(boxes):
    border = set()
    for r1, c1, r2, c2 in boxes:
        border.update((r, c) for r in (r1, r2) for c in range(c1, c2 + 1))
        border.update((r, c) for c in (c1, c2) for r in range(r1, r2 + 1))
    return border


def trace_routes(get, heads, boxes, limit=200):
    """Every route that ends in an arrowhead: (head, cells from the head back to the source,
    kind, last step). kind is "box" when the route starts on a box edge, "open" when the line
    begins in open space.

    Walks backwards from each arrowhead along connector lines; branches that lead into another
    arrowhead are dropped. A ┼ / ╪ is a crossing: the route goes straight through, which is
    also how a connector passes through a box edge. Walking backwards, a route never steps down
    after stepping up: flow that climbs and then drops back down is a misreading of two branches
    of a fork (a loop that drops and then climbs, like a 'changes requested' arrow, is fine)."""
    border = box_border(boxes)
    out = []
    for r, c, d in heads:
        stack = [((r, c), OPP[d], [(r, c)], OPP[d] == "U")]
        while stack and len(out) < limit:
            (cr, cc), step, seq, climbed = stack.pop()
            if climbed and step == "D":
                continue
            n = (cr + DIRS[step][0], cc + DIRS[step][1])
            t, back = get(*n), OPP[step]
            if t in HEADS:
                continue                                        # leads into another arrow: not a source
            if t not in ARMS or back not in ARMS[t] or n in seq:
                if len(seq) > 1:                                # line starts in open space
                    out.append(((r, c, d), seq, "open", step))
                continue
            seq = seq + [n]
            crossing = len(ARMS[t]) == 4                       # ┼ ╪: lines pass straight through
            if n in border and not crossing:
                out.append(((r, c, d), seq, "box", step))       # starts on a box edge
                continue
            for a in ([step] if crossing else sorted(ARMS[t] - {back}, reverse=True)):
                stack.append((n, a, seq, climbed or a == "U"))
    return out


def flow_paths(get, heads, boxes, line_like, limit=200):
    """Every route that ends in an arrowhead, as points from its source to the tip."""
    centre = lambda r, c: (PAD + c * CW + CW / 2, PAD + r * CH + CH / 2)
    out = []
    for (r, c, d), seq, kind, step in trace_routes(get, heads, boxes, limit):
        tip = head_geometry(r, c, d, line_like)[2]
        pts = [centre(*k) for k in reversed(seq)] + [tip]
        if kind == "open":
            x, y = centre(*seq[-1])
            pts.insert(0, (x + DIRS[step][1] * CW / 2, y + DIRS[step][0] * CH / 2))
        out.append(pts)
    routes = []
    for pts in out:
        keep = [pts[0]]
        for i in range(1, len(pts) - 1):
            (ax, ay), (bx, by), (qx, qy) = keep[-1], pts[i], pts[i + 1]
            if (bx - ax) * (qy - by) != (by - ay) * (qx - bx):
                keep.append(pts[i])
        keep.append(pts[-1])
        if len(keep) >= 2 and keep not in routes:
            routes.append(keep)
    return routes


def _layout_css(mode, font=None):
    """mode: none | timed (plays on load) | scroll (a host page adds .a2s-on as things scroll into view)."""
    css = (".sgl{stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".dbl{stroke-width:5;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".dbl-gap{stroke-width:2;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".head{stroke-width:1;stroke-linejoin:round}"
           f"text{{font:{FS}px {font_stack(font)}ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
           "text-anchor:middle;white-space:pre}"
           ".blk{shape-rendering:crispEdges}.k3{fill-opacity:.75}.k2{fill-opacity:.5}.k1{fill-opacity:.28}"
           ".fill{transition:fill .25s}text,line,path,polygon,.blk{pointer-events:none}")
    if mode == "none":
        return css
    on = ".a2s-on" if mode == "scroll" else ""
    sel = lambda *names: ",".join(f"{on}{n}" if n.startswith(".") else f"{n}{on}" for n in names)
    ease = "cubic-bezier(.3,.7,.4,1)"
    css += ("@keyframes a2s-gap{0%{stroke-dasharray:1 2;stroke-dashoffset:1.01}"
            "60%,100%{stroke-dasharray:1 2;stroke-dashoffset:0}}"
            "@keyframes a2s-fade{0%{opacity:0}}"
            "@keyframes a2s-pop{0%{opacity:0;transform:scale(.2)}}"
            "@keyframes a2s-grow{0%{transform:scaleX(0)}}"
            f"{sel('.blk')}{{animation:a2s-grow .7s {ease} backwards}}"
            ".blk{transform-box:fill-box;transform-origin:left}"
            f"{sel('.sgl', '.dbl')}{{animation:a2s-draw .6s {ease} backwards}}"
            f"{sel('.dbl-gap')}{{animation:a2s-gap .6s {ease} backwards}}"
            f"{sel('.sgl.shaft')}{{animation:a2s-fade .3s ease-out backwards}}"
            f"{sel('.head')}{{animation:a2s-pop .45s cubic-bezier(.3,1.6,.5,1) backwards}}"
            ".head{transform-box:fill-box;transform-origin:center}"
            f"{sel('text')}{{animation:a2s-fade .5s ease-out backwards}}"
            f"{sel('.glow', '.shadow', '.fill', '.plate')}{{animation:a2s-fade .8s ease-out backwards}}"
            ".pulse .halo{fill-opacity:.28}")
    if mode == "scroll":
        css += ".a2s-off{opacity:0}.sgl,.dbl{transition:stroke .8s}"
    return css + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.pulse{display:none}}"


_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_FONT = re.compile(r"[\w\s,'\"-]+")


def check_style(accent=None, font=None, width=None):
    """Validate the style options (they end up inside the SVG's CSS). Raises ValueError."""
    if accent is not None and not _HEX.fullmatch(accent):
        raise ValueError(f"accent must be a hex colour like #0969da, not {accent!r}")
    if font is not None and not (_FONT.fullmatch(font) and font.strip()):
        raise ValueError("font must be font family names, e.g. 'JetBrains Mono' or \"Fira Code, monospace\"")
    if width is not None and not 16 <= width <= 20000:
        raise ValueError("width must be between 16 and 20000 pixels")


def font_stack(font):
    """'JetBrains Mono, Fira Code' -> "'JetBrains Mono','Fira Code'," (in front of the monospace stack)."""
    if not font:
        return ""
    names = [n.strip() for n in font.split(",") if n.strip()]
    return "".join((n if n[0] in "'\"" or " " not in n else f"'{n}'") + "," for n in names)


def _colour_css(t, color, anim):
    acc = t["accent"]
    css = (f".bg,.fill,.plate{{fill:{t['bg']}}}.sgl,.dbl{{stroke:{t['ink']}}}.dbl-gap{{stroke:{t['bg']}}}"
           f".head{{fill:{t['ink']};stroke:{t['ink']}}}text{{fill:{t['ink']}}}"
           f".glow{{fill:{t['glow']};fill-opacity:{t['glow_a']}}}.shadow{{fill:#000}}.blk{{fill:{t['ink']}}}")
    if color:
        css += (f".shaft{{stroke:{acc}}}.head{{fill:{acc};stroke:{acc}}}.blk{{fill:{acc}}}.fill.tn{{fill:{t['neutral']}}}"
                + "".join(f".fill.t{i}c{{fill:{a}}}.fill.t{i}l{{fill:{b}}}" for i, (a, b) in enumerate(t["hues"])))
    css += f".fill:hover{{fill:{t['hover']}}}"
    if anim:   # lines are sketched in the accent colour, then settle to ink
        css += (f"@keyframes a2s-draw{{0%{{stroke-dasharray:1 2;stroke-dashoffset:1.01;stroke:{acc}}}"
                f"60%{{stroke-dasharray:1 2;stroke-dashoffset:0;stroke:{acc}}}"
                f"100%{{stroke-dasharray:1 2;stroke-dashoffset:0}}}}.pulse circle{{fill:{acc}}}"
                f".a2s-live.sgl,.a2s-live.dbl{{stroke:{acc}}}")
    return css


def render_svg(cells, nrows, ncols, style="glow", square=False, title="ASCII diagram",
               theme="light", color=False, animate="none", accent=None, font=None, width=None):
    """cells: {(r, c): (text, width)} where line cells already hold Unicode line characters.

    Animation only ever starts from an earlier state and ends on the static drawing, so a
    renderer that ignores CSS/SMIL animation shows exactly what the self-check verified."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    segs = {"s": {"h": {}, "v": {}}, "d": {"h": {}, "v": {}}}
    curves, heads, texts, blocks = [], [], [], []
    diag = {"/": set(), "\\": set()}
    round_ok = not square and not any(t in ROUNDED for t, _ in cells.values())
    anim = animate != "none"
    timed = animate in ("draw", "flow")              # "scroll" leaves the timing to the host page
    span = max(nrows * CH, 1)
    sweep = min(2.0, 0.5 + 0.025 * nrows)          # seconds for the drawing front to reach the bottom
    speed = span / sweep

    def at(y):
        return sweep * min(max(y - PAD, 0.0), span) / span

    def timing(y, dur=None):
        if not timed:
            return ""
        s = f"animation-delay:{at(y):.2f}s"
        if dur is not None:
            s += f";animation-duration:{dur:.2f}s"
        return f' style="{s}"'

    grow = ' pathLength="1"' if anim else ""

    def add(st, d, key, a, b):
        segs[st][d].setdefault(key, []).append((a, b))

    for (r, c) in sorted(cells):
        t, w = cells[(r, c)]
        if w == 0 or t == " ":
            continue
        x0, y0 = PAD + c * CW, PAD + r * CH
        cx, cy = x0 + CW / 2, y0 + CH / 2
        if t in ARMS:
            arms = ARMS[t]
            st_h = "d" if (t in DOUBLE or t == "╪") else "s"
            st_v = "d" if t in DOUBLE else "s"
            corner = len(arms) == 2 and arms not in (frozenset("LR"), frozenset("UD"))
            if corner and (t in ROUNDED or round_ok):
                hx = cx + (RADIUS if "R" in arms else -RADIUS)
                vy = cy + (RADIUS if "D" in arms else -RADIUS)
                add(st_h, "h", cy, *((hx, x0 + CW) if "R" in arms else (x0, hx)))
                add(st_v, "v", cx, *((vy, y0 + CH) if "D" in arms else (y0, vy)))
                curves.append((st_h, f"M{hx:g} {cy:g}Q{cx:g} {cy:g} {cx:g} {vy:g}", y0))
                continue
            for a in sorted(arms):
                st = st_h if a in "LR" else st_v
                n = get(r + DIRS[a][0], c + DIRS[a][1])
                # meeting a straight line side-on (│───▶│): run on until the strokes meet, stopping
                # just short of that cell's centre so it still reads back as a plain │ / ─
                ext = ((CW if a in "LR" else CH) / 2 - (2.5 if n in DOUBLE else 0.7)) if touches(a, n) else 0
                if a == "L":
                    add(st, "h", cy, x0 - ext, cx)
                elif a == "R":
                    add(st, "h", cy, cx, x0 + CW + ext)
                elif a == "U":
                    add(st, "v", cx, y0 - ext, cy)
                else:
                    add(st, "v", cx, cy, y0 + CH + ext)
        elif t in HEADS:
            heads.append((r, c, HEADS[t]))
        elif t in DIAG:
            for s in DIAG[t]:
                diag[s].add((r, c))
        elif t in BLOCKS:
            blocks.append((r, c, t))
        else:
            texts.append((r, c, w, t))

    def merged(d):
        out = []
        for k in sorted(d):
            iv = sorted(d[k])
            cur = list(iv[0])
            for a, b in iv[1:]:
                if a <= cur[1] + 0.01:
                    cur[1] = max(cur[1], b)
                else:
                    out.append((k, *cur))
                    cur = [a, b]
            out.append((k, *cur))
        return out

    def lines(st, cls):
        o = [f'<path d="{d}" class="{cls}"{grow}{timing(y, 0.25)}/>' for s, d, y in curves if s == st]
        o += [f'<line x1="{a:g}" y1="{k:g}" x2="{b:g}" y2="{k:g}" class="{cls}"{grow}'
              f'{timing(k - CH / 2, min(max((b - a) / (1.5 * speed), 0.25), 0.8))}/>'
              for k, a, b in merged(segs[st]["h"])]
        o += [f'<line x1="{k:g}" y1="{a:g}" x2="{k:g}" y2="{b:g}" class="{cls}"{grow}'
              f'{timing(a, max((b - a) / speed, 0.25))}/>' for k, a, b in merged(segs[st]["v"])]
        return o

    # boxes: glow / shadow, then fill, then plates behind titles on the top edge
    under = []
    boxes = find_boxes(get, nrows, ncols)
    tints = box_tints(boxes) if color else {}
    is_text = lambda t: t not in (" ", "") and t not in ARMS and t not in HEADS and t not in DIAG and t not in BLOCKS
    for b in boxes:
        r1, c1, r2, c2 = b
        x1, y1 = PAD + c1 * CW + CW / 2, PAD + r1 * CH + CH / 2
        x2, y2 = PAD + c2 * CW + CW / 2, PAD + r2 * CH + CH / 2
        w, h = x2 - x1, y2 - y1
        rad = RADIUS if (round_ok or get(r1, c1) in ROUNDED) else 0
        tm = timing(y1 - CH / 2)
        if style == "glow":
            reach = GLOW_R                                  # shrink so glow never sits behind a label
            for rr in range(r1 - 1, r2 + 2):
                for cc in range(c1 - 2, c2 + 2):
                    t, tw = cells.get((rr, cc), (" ", 1))
                    if not is_text(t) or (rr == r1 and c1 < cc < c2):
                        continue
                    tx0, ty0 = PAD + cc * CW, PAD + rr * CH
                    tx1, ty1 = tx0 + tw * CW, ty0 + CH
                    if tx0 >= x1 and tx1 <= x2 and ty0 >= y1 and ty1 <= y2:
                        continue
                    room = max(x1 - tx1, tx0 - x2, (y1 - ty1) + GLOW_DY, (ty0 - y2) - GLOW_DY) - 0.5
                    reach = min(reach, room)
            if reach >= 1:
                for i in range(GLOW_N, 0, -1):
                    e = reach * i / GLOW_N
                    under.append(f'<rect x="{x1 - e:g}" y="{y1 - e + GLOW_DY:g}" width="{w + 2 * e:g}" '
                                 f'height="{h + 2 * e:g}" rx="{rad + e:g}" class="glow"{tm}/>')
        elif style == "shadow":
            for off, op in SHADOW:
                under.append(f'<rect x="{x1 + off:g}" y="{y1 + off:g}" width="{w:g}" height="{h:g}" '
                             f'rx="{rad:g}" class="shadow" fill-opacity="{op}"{tm}/>')
        if style != "flat" or color:
            cls = f"fill {tints[b]}" if color else "fill"
            under.append(f'<rect x="{x1:g}" y="{y1:g}" width="{w:g}" height="{h:g}" rx="{rad:g}" class="{cls}"{tm}/>')
            run = None
            for c in range(c1 + 1, c2 + 1):
                t = get(r1, c)
                line_cell = t in ARMS or t in HEADS or c == c2
                if not line_cell and run is None:
                    run = c
                if line_cell and run is not None:
                    under.append(f'<rect x="{PAD + run * CW:g}" y="{PAD + r1 * CH:g}" '
                                 f'width="{(c - run) * CW:g}" height="{CH:g}" class="plate"{tm}/>')
                    run = None

    def diagonals():
        """One stroke per run of ╱ or ╲, corner to corner. Where a ╱ and a ╲ end one cell apart on
        the same edge (the flat top and bottom of an ASCII diamond) a short cap joins them; an end
        that points at a line runs on to meet it. Caps and run-ons are marked `ext`."""
        o, ends = [], []
        for s, cellset in diag.items():
            dc = -1 if s == "/" else 1
            for (r, c) in sorted(cellset):
                if (r - 1, c - dc) in cellset:
                    continue                                # not the top of its run
                n = 1
                while (r + n, c + n * dc) in cellset:
                    n += 1
                if s == "/":
                    top, bot = (PAD + (c + 1) * CW, PAD + r * CH), (PAD + (c - n + 1) * CW, PAD + (r + n) * CH)
                    a, b = bot, top
                else:
                    top, bot = (PAD + c * CW, PAD + r * CH), (PAD + (c + n) * CW, PAD + (r + n) * CH)
                    a, b = top, bot
                o.append(f'<line x1="{a[0]:g}" y1="{a[1]:g}" x2="{b[0]:g}" y2="{b[1]:g}" class="sgl"{grow}'
                         f'{timing(top[1], max(n * CH / speed, 0.25))}/>')
                ends.append((s, "top", top, (r - 1, c - dc)))
                ends.append((s, "bot", bot, (r + n, c + n * dc)))
        at_end = {(s, e, p) for s, e, p, _ in ends}
        capped = set()
        for s, e, p, _ in ends:                            # left end of a flat top or bottom
            if (s, e) in (("/", "top"), ("\\", "bot")):
                q = (p[0] + CW, p[1])
                if ({"top": "\\", "bot": "/"}[e], e, q) in at_end:
                    o.append(f'<line x1="{p[0]:g}" y1="{p[1]:g}" x2="{q[0]:g}" y2="{q[1]:g}" class="sgl ext"'
                             f'{grow}{timing(p[1])}/>')
                    capped.update({p, q})
        for s, e, p, (br, bc) in ends:
            if p in capped or get(br, bc) not in ARMS:
                continue
            q = (PAD + bc * CW + CW / 2, PAD + br * CH + CH / 2)
            o.append(f'<line x1="{p[0]:g}" y1="{p[1]:g}" x2="{q[0]:g}" y2="{q[1]:g}" class="sgl ext"{grow}{timing(p[1])}/>')
        return o

    def block_rects():
        """Block elements as exact rectangles; a run of the same full-width block is one rectangle."""
        o, i = [], 0
        while i < len(blocks):
            r, c, t = blocks[i]
            n = 1
            if t in MERGEABLE:
                while i + n < len(blocks) and blocks[i + n] == (r, c + n, t):
                    n += 1
            shade, rects = BLOCKS[t]
            for x0, y0, x1, y1 in rects:
                x, y = PAD + c * CW + x0 * CW / 8, PAD + r * CH + y0 * CH / 8
                wd, ht = (n - 1) * CW + (x1 - x0) * CW / 8, (y1 - y0) * CH / 8
                o.append(f'<rect x="{x:g}" y="{y:g}" width="{wd:g}" height="{ht:g}" class="blk k{shade}"'
                         f'{timing(y)}/>')
            i += n
        return o

    body = under + block_rects() + lines("d", "dbl") + lines("d", "dbl-gap") + lines("s", "sgl") + diagonals()
    line_like = lambda r, c: get(r, c) in ARMS
    for r, c, d in heads:
        sh, pts, _ = head_geometry(r, c, d, line_like)
        tm = timing(PAD + r * CH + 0.15 * speed)
        body.append('<line x1="%g" y1="%g" x2="%g" y2="%g" class="sgl shaft"%s/>' % (*sh, tm))
        body.append('<polygon points="%s" class="head"%s/>' % (" ".join(f"{x:g},{y:g}" for x, y in pts), tm))
    for r, c, w, t in texts:                         # one delay per row (a class), not per character
        row_cls = f' class="r{r}"' if timed else ""
        body.append(f'<text x="{PAD + c * CW + w * CW / 2:g}" y="{PAD + r * CH + CH / 2 + 5:g}"'
                    f'{row_cls}>{html.escape(t, quote=False)}</text>')
    rows_css = "".join(f".r{r}{{animation-delay:{at(PAD + r * CH + 0.08 * speed):.2f}s}}"
                       for r in sorted({r for r, *_ in texts})) if timed else ""

    routes = flow_paths(get, heads, boxes, line_like) if animate in ("flow", "scroll") else []
    begin = "indefinite" if animate == "scroll" else f"{sweep + 0.9:.2f}s"      # scroll: the page starts them
    for pts in routes:
        length = sum(abs(bx - ax) + abs(by - ay) for (ax, ay), (bx, by) in zip(pts, pts[1:]))
        travel = max(length / FLOW_SPEED, 0.4)
        dur = travel + FLOW_REST
        f = travel / dur
        d = "M" + "L".join(f"{x:g} {y:g}" for x, y in pts)
        body.append(f'<g class="pulse" opacity="0"><circle r="5.5" class="halo"/><circle r="2.6"/>'
                    f'<animateMotion path="{d}" dur="{dur:.2f}s" begin="{begin}" repeatCount="indefinite" '
                    f'calcMode="linear" keyPoints="0;1;1" keyTimes="0;{f:.3f};1"/>'
                    f'<animate attributeName="opacity" values="0;1;1;0;0" '
                    f'keyTimes="0;{0.08 * f:.3f};{0.85 * f:.3f};{f:.3f};1" dur="{dur:.2f}s" begin="{begin}" '
                    f'repeatCount="indefinite"/></g>')

    tune = lambda t: dict(t, accent=accent) if accent else t
    pal = tune(THEMES["light" if theme == "auto" else theme])
    css = _layout_css("timed" if timed else animate if anim else "none", font) + rows_css + _colour_css(pal, color, anim)
    if theme == "auto":
        css += "@media (prefers-color-scheme:dark){" + _colour_css(tune(THEMES["dark"]), color, anim) + "}"
    W, H = ncols * CW + 2 * PAD, nrows * CH + 2 * PAD
    ow, oh = (width, round(H * width / W, 2)) if width else (W, H)      # --width scales; the viewBox stays
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" width="{ow:g}" '
           f'height="{oh:g}" role="img" data-cell="{CW}x{CH}" data-pad="{PAD}" '
           + ('data-reveal="scroll" ' if animate == "scroll" else "") +
           f'data-generator="ascii2svg {__version__}"><title>{html.escape(title)}</title>'
           f'<style>{css}</style><rect width="100%" height="100%" fill="{pal["bg"]}" class="bg"/>'
           + "".join(body) + "</svg>\n")
    return svg, {"boxes": len(boxes), "text_cells": len(texts), "arrowheads": len(heads), "flows": len(routes)}


# ─── web page (--html) ───────────────────────────────────────────────────────
# Scroll reveal, no dependencies. An SVG inside <img> cannot see the page scroll, and CSS
# scroll timelines don't drive SVG shapes, so the page does it: things fade and draw in as
# they reach the reader, long vertical connectors grow with the scroll, and flow pulses
# start once their route is on screen. Every step ends on the static, self-checked drawing.
REVEAL_JS = r"""(() => {
  const svg = document.querySelector('svg[data-reveal="scroll"]');
  if (!svg || !('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const q = s => [...svg.querySelectorAll(s)], n = (el, a) => +el.getAttribute(a);
  const grow = [], show = q('path.sgl,path.dbl,path.dbl-gap,.shaft,.head,text,.glow,.shadow,.fill,.plate,.blk');
  for (const el of q('line.sgl:not(.shaft),line.dbl,line.dbl-gap')) {
    if (n(el, 'x1') === n(el, 'x2') && n(el, 'y2') - n(el, 'y1') > 72) grow.push({el, y1: n(el, 'y1'), y2: n(el, 'y2'), f: 0});
    else show.push(el);
  }
  const pulses = q('g.pulse').map(g => {
    const ys = g.querySelector('animateMotion').getAttribute('path').match(/-?[\d.]+/g).filter((_, i) => i % 2);
    return {g, bottom: Math.max(...ys), go: false};
  });
  show.forEach(el => el.classList.add('a2s-off'));
  for (const g of grow) {
    Object.assign(g.el.style, {strokeDasharray: '1 2', strokeDashoffset: '1.01',
                               transition: 'stroke-dashoffset .45s ease-out, stroke .8s'});
    g.el.classList.add('a2s-live');
  }
  let first = true;
  const io = new IntersectionObserver(entries => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const el = e.target, top = e.boundingClientRect.top / innerHeight;
      io.unobserve(el);
      el.style.animationDelay = (first ? Math.min(Math.max(top, 0), 1) * 0.9 : 0).toFixed(2) + 's';
      if (el.tagName === 'line' && !el.classList.contains('shaft'))
        el.style.animationDuration = Math.min(Math.max((n(el, 'x2') - n(el, 'x1')) / 600, 0.3), 0.9) + 's';
      el.classList.replace('a2s-off', 'a2s-on');
    }
    first = false;
  }, {rootMargin: '0px 0px -8% 0px'});
  show.forEach(el => io.observe(el));
  let queued = false;
  const tick = () => {
    queued = false;
    const box = svg.getBoundingClientRect(), k = box.height / svg.viewBox.baseVal.height;
    const edge = innerHeight * 0.92;
    for (const g of grow) {
      if (g.f >= 1) continue;
      const f = Math.min(Math.max((edge - box.top - g.y1 * k) / ((g.y2 - g.y1) * k), 0), 1);
      if (f <= g.f) continue;
      g.f = f;
      g.el.style.strokeDashoffset = String(1 - f);
      if (f >= 1) setTimeout(() => {
        Object.assign(g.el.style, {strokeDasharray: '', strokeDashoffset: ''});
        g.el.classList.remove('a2s-live');
      }, 500);
    }
    for (const p of pulses) {
      if (p.go || box.top + p.bottom * k > edge) continue;
      p.go = true;
      setTimeout(() => p.g.querySelectorAll('animateMotion,animate').forEach(a => a.beginElement()), 900);
    }
  };
  const later = () => { if (!queued) { queued = true; requestAnimationFrame(tick); } };
  addEventListener('scroll', later, {passive: true});
  addEventListener('resize', later);
  requestAnimationFrame(tick);
})();"""


def to_html(svg, title="ASCII diagram", theme="light"):
    """A standalone page with the SVG inline (and the scroll reveal, when the SVG asks for it)."""
    bg = THEMES["light" if theme == "auto" else theme]["bg"]
    css = f"html{{background:{bg}}}body{{margin:0}}main{{padding:32px 16px 72px;display:flex;justify-content:center}}" \
          "main svg{max-width:100%;height:auto}"
    if theme == "auto":
        css += f"@media (prefers-color-scheme:dark){{html{{background:{THEMES['dark']['bg']}}}}}"
    script = f"<script>{REVEAL_JS}</script>" if 'data-reveal="scroll"' in svg else ""
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{css}</style></head>"
            f"<body><main>{svg.strip()}</main>{script}</body></html>\n")


# ─── self-check: read the SVG back into a grid ───────────────────────────────
def read_back(svg: str) -> dict:
    """Rebuild {(r, c): char} using only what is in the SVG."""
    cw, chh = map(float, re.search(r'data-cell="([\d.]+)x([\d.]+)"', svg).groups())
    pad = float(re.search(r'data-pad="([\d.]+)"', svg).group(1))
    arms: dict = {}
    out: dict = {}
    slopes: dict = {}
    pieces: dict = {}

    def arm(r, c, st, a):
        arms.setdefault((r, c), {"s": set(), "d": set()})[st].add(a)

    for hx, cy, qx, qy, vx, vy, cls in re.findall(
            r'<path d="M([\d.]+) ([\d.]+)Q([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)" class="([^"]+)"[^>]*/>', svg):
        if cls == "dbl-gap":
            continue
        hx, qx, qy, vy = map(float, (hx, qx, qy, vy))
        r, c, st = int((qy - pad) // chh), int((qx - pad) // cw), "d" if cls == "dbl" else "s"
        arm(r, c, st, "R" if hx > qx else "L")
        arm(r, c, st, "D" if vy > qy else "U")
    for x1, y1, x2, y2, cls in re.findall(
            r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" class="([^"]+)"[^>]*/>', svg):
        x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
        if cls == "sgl shaft":
            if x1 == x2:
                col = int((x1 - pad) // cw)
                out[(round((y1 - pad) / chh) - (0 if y2 > y1 else 1), col)] = "▼" if y2 > y1 else "▲"
            else:
                row = int((y1 - pad) // chh)
                out[(row, round((x1 - pad) / cw) - (0 if x2 > x1 else 1))] = "▶" if x2 > x1 else "◀"
            continue
        if cls in ("dbl-gap", "sgl ext"):
            continue
        if x1 != x2 and y1 != y2:                          # a diagonal run, one cell per row
            s = "/" if y2 < y1 else "\\"
            r0, c0 = round((min(y1, y2) - pad) / chh), round((x1 - pad) / cw)
            n = round(abs(y2 - y1) / chh)
            for k in range(n):
                cell = (r0 + k, c0 + n - 1 - k) if s == "/" else (r0 + k, c0 + k)
                slopes[cell] = slopes.get(cell, "") + s
            continue
        st = "d" if cls == "dbl" else "s"
        if y1 == y2:
            r = int((y1 - pad) // chh)
            for c in range(int((x1 - pad) // cw) - 1, int((x2 - pad) // cw) + 2):
                ccx = pad + c * cw + cw / 2
                if x1 - 0.01 <= ccx <= x2 + 0.01:
                    if x1 < ccx - 0.01:
                        arm(r, c, st, "L")
                    if x2 > ccx + 0.01:
                        arm(r, c, st, "R")
        else:
            c = int((x1 - pad) // cw)
            for r in range(int((y1 - pad) // chh) - 1, int((y2 - pad) // chh) + 2):
                ccy = pad + r * chh + chh / 2
                if y1 - 0.01 <= ccy <= y2 + 0.01:
                    if y1 < ccy - 0.01:
                        arm(r, c, st, "U")
                    if y2 > ccy + 0.01:
                        arm(r, c, st, "D")
    for k, v in arms.items():
        s, d = frozenset(v["s"]), frozenset(v["d"])
        if d and s:
            out[k] = "╪" if (d, s) == (frozenset("LR"), frozenset("UD")) else "?"
        elif d:
            out[k] = next((ch for ch in DOUBLE if ARMS[ch] == d), "?")
        else:
            out[k] = SINGLE_OF.get(s, "?")
    for k, s in slopes.items():
        out[k] = "?" if k in out else DIAG_OF.get("".join(sorted(s)), "?")
    for x, y, w, h, shade in re.findall(
            r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" class="blk k(\d)"', svg):
        x, y, w, h, shade = float(x), float(y), float(w), float(h), int(shade)
        r = int((y - pad) // chh)
        ry = pad + r * chh
        for c in range(int((x - pad) // cw), int((x + w - pad - 0.01) // cw) + 1):   # a run: one piece per cell
            cx0 = pad + c * cw
            e = lambda v, o, size: round((v - o) / size * 8)
            rect = (e(max(x, cx0), cx0, cw), e(y, ry, chh), e(min(x + w, cx0 + cw), cx0, cw), e(y + h, ry, chh))
            pieces.setdefault((r, c), []).append((shade, rect))
    for k, p in pieces.items():
        out[k] = BLOCK_OF.get(tuple(sorted(p)), "?")
    for x, y, t in re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>(.*?)</text>', svg):
        t = html.unescape(t)
        w = width_of(t)
        out[(round((float(y) - 5 - pad - chh / 2) / chh), round((float(x) - pad - w * cw / 2) / cw))] = t
    return out


def self_check(svg, drawn_cells, original_cells):
    """1:1 check. Returns a list of problems (empty = exact)."""
    problems = []
    got = read_back(svg)
    corner_family = {"┌": "╭", "┐": "╮", "└": "╰", "┘": "╯"}
    want = {k: t for k, (t, w) in drawn_cells.items() if w and t != " "}
    for k in sorted(set(got) | set(want)):
        g, w = got.get(k, " "), want.get(k, " ")
        if g != w and not (w in ROUNDED and corner_family.get(g) == w):
            problems.append({"row": k[0] + 1, "col": k[1] + 1, "expected": w, "svg_has": g})
    for k, (t, w) in original_cells.items():
        d = drawn_cells[k][0]
        if d != t and d not in CORR.get(t, ()):
            problems.append({"row": k[0] + 1, "col": k[1] + 1, "original": t, "drawn_as": d})
    return problems


def touches(a, n):
    """A line running toward `a` meets straight line `n` side-on, e.g. a sequence message │───▶│.
    Nothing to fix: the renderer runs the line up to `n` so they meet."""
    return n in ARMS and ARMS[n] == (frozenset("UD") if a in "LR" else frozenset("LR"))


def _near_miss(get, r, c, a, at):
    """A line at (r, c) runs toward a and hits empty space. Is its partner one cell off to the side?"""
    dr, dc = DIRS[a]
    nr, nc = r + dr, c + dc
    want_head = {"D": "v▼", "U": "^▲", "R": ">▶", "L": "<◀"}[a]
    for side, (sr, sc) in (("right", (0, 1)), ("left", (0, -1))) if a in "UD" else (("below", (1, 0)), ("above", (-1, 0))):
        t = get(nr + sr, nc + sc)
        if t in want_head or (t in ARMS and OPP[a] in ARMS[t]):
            what = "the arrowhead" if t in want_head else "the line"
            axis = "column" if a in "UD" else "row"
            return (f"{what} '{t}' at {at(nr + sr, nc + sc)} is one {axis} {side}; "
                    f"move one of them so they line up")
    return None


def _gap(get, r, c, a, at, reach=3):
    """A line at (r, c) runs toward a into empty space. Is there a line, box or arrowhead just ahead?"""
    dr, dc = DIRS[a]
    for k in range(2, reach + 2):
        t = get(r + k * dr, c + k * dc)
        if t == " ":
            continue
        if t in ARMS or t in HEADS:
            return (f"the line stops {k - 1} cell{'s' if k > 2 else ''} short of '{t}' at "
                    f"{at(r + k * dr, c + k * dc)}; extend it so they meet")
        return None                                     # text ahead: the line just ends near a label
    return None


def connector_warnings(cells, nrows, ncols, limit=50, origin=(0, 0)):
    """Line ends that look like mistakes - usually a misaligned diagram.

    Not warned: a line that ends at text (a label) or an arrowhead, meets a straight line side-on
    (│───▶│), or simply stops in open space (ticks, lifeline ends, stubs). Warned: a line whose
    partner is one cell off to the side, one that stops just short of a line or box, and a line
    that runs into a corner or junction without an arm toward it. One warning per character.
    Each has a stable `code`, 1-based `row`/`col`, the source `line`, and a concrete `hint`."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    at = lambda r, c: f"line {r + origin[0] + 1} col {c + origin[1] + 1}"      # where it is in the input
    rows = {}
    for (r, c), (t, _) in sorted(cells.items()):
        rows.setdefault(r, []).append(t)
    line = lambda r: "".join(rows.get(r, ())).rstrip()                        # only built for real warnings
    out, by_cell = [], {}
    for (r, c) in sorted(cells):
        t = get(r, c)
        if t not in ARMS:
            continue
        for a in sorted(ARMS[t]):
            dr, dc = DIRS[a]
            n, back = get(r + dr, c + dc), OPP[a]
            if n in ARMS:
                if back in ARMS[n] or touches(a, n):
                    continue
                fixed = SINGLE_OF.get(ARMS[n] | {back}) if n not in DOUBLE else None
                code, issue = "broken_join", f"line toward {a} meets '{n}' which doesn't connect back"
                hint = (f"use '{fixed}' instead of '{n}' at {at(r + dr, c + dc)}" if fixed
                        else f"'{n}' at {at(r + dr, c + dc)} has no arm toward this line")
            elif n != " ":
                continue                                  # an arrowhead, or a label: a fine place to end
            else:
                t2 = get(r + 2 * dr, c + 2 * dc)
                if t2 not in (" ", "") and t2 not in ARMS and t2 not in HEADS:
                    continue                              # a space, then a label: a title in a border, "──▶ HTTP 400"
                hint = _near_miss(get, r, c, a, at) or _gap(get, r, c, a, at)
                if not hint:
                    continue                              # a free end: a tick, a lifeline's end, a stub
                code, issue = "dangling_line", f"line toward {a} ends in empty space"
            if (r, c) in by_cell:                         # one warning per character
                by_cell[(r, c)]["issue"] += f"; also toward {a}"
                continue
            w = {"row": r + 1, "col": c + 1, "char": t, "line": line(r), "code": code, "issue": issue, "hint": hint}
            by_cell[(r, c)] = w
            out.append(w)
            if len(out) >= limit:
                return out
    return out


def box_warnings(cells, drawn, origin=(0, 0)):
    """ASCII boxes that start (+---+ with a wall below) but were never drawn because they don't close.
    Says exactly which wall or edge breaks, and where."""
    ch = lambda r, c: cells.get((r, c), (" ", 1))[0]
    at = lambda r, c: f"line {r + origin[0] + 1} col {c + origin[1] + 1}"
    nrows = max((r for r, _ in cells), default=-1) + 1
    out = []
    for (r, c) in sorted(cells):
        if ch(r, c) != "+" or (r, c) in drawn or ch(r, c + 1) != "-" or ch(r, c - 1) == "-":
            continue
        c2 = c + 1
        while ch(r, c2) == "-":
            c2 += 1
        if ch(r, c2) != "+" or c2 - c < 3 or ch(r + 1, c) not in "|+" or ch(r + 1, c2) not in "|+":
            continue
        why = None
        for rr in range(r + 1, nrows + 1):
            a, b = ch(rr, c), ch(rr, c2)
            if a == "+" and b == "+":
                bad = next((x for x in range(c + 1, c2) if ch(rr, x) not in "-+"), None)
                if bad is not None:
                    why = f"its bottom edge at {at(rr, bad)} is '{ch(rr, bad)}'"
                break
            broken = [(side, x, t) for side, x, t in (("left", c, a), ("right", c2, b)) if t not in "|+"]
            if broken:
                why = " and ".join(f"its {side} wall at {at(rr, x)} is '{t}'" if t.strip()
                                   else f"its {side} wall stops at {at(rr, x)}" for side, x, t in broken)
                break
        if why is None:
            continue                                      # closed after all; left as text for another reason
        out.append({"row": r + 1, "col": c + 1, "char": "+", "code": "unclosed_box",
                    "issue": f"the box starting at {at(r, c)} is not closed, so it stays plain text",
                    "hint": f"{why}; box walls need '|' (or '+' where a line joins) all the way down, "
                            f"and the bottom edge needs '+' at both corners"})
    return out


def input_warnings(raw, cells, info, drawn=None, origin=(0, 0)):
    """Input that renders 'successfully' but not as intended."""
    out = []
    body = raw.strip("\r\n")
    if "\n" not in body and "\\n" in body:
        out.append({"code": "escaped_newlines", "row": 1, "col": body.index("\\n") + 1,
                    "issue": "the input is one line containing literal \\n sequences",
                    "hint": "pass real newlines (write the diagram to a file or stdin), or add --unescape"})
    boxes = box_warnings(cells, drawn or {}, origin)
    out += boxes
    unicode_lines = any(t in ARMS or t in HEADS for t, _ in cells.values())
    if not boxes and not unicode_lines and not info["ascii_drawn_as_lines"] and re.search(r"\+-|-\+", raw):
        out.append({"code": "no_structure", "row": 1, "col": 1,
                    "issue": "ASCII box pieces (+-) were found but nothing was drawn as lines",
                    "hint": "close every box: '+' at all four corners, '-' along the top and bottom, "
                            "'|' down both sides, all in matching columns"})
    return out


# ─── repair (--repair): fix the misalignments LLM-drawn diagrams typically have ─
# Only line characters and spaces move or appear, and only into empty cells: text never changes.
# Every edit is reported, and the repaired text is returned so it can replace the original.
_VWALL = set("│║|├┤┼╟╢╪")
_TL, _TR, _BL, _BR = set("┌╭╔"), set("┐╮╗"), set("└╰╚"), set("┘╯╝")


class _Grid:
    def __init__(self, cells):
        self.cells = dict(cells)
        self.edits = []

    def ch(self, r, c):
        return self.cells.get((r, c), (" ", 1))[0]

    def free(self, r, c):
        return self.cells.get((r, c), (" ", 1)) == (" ", 1)

    def put(self, r, c, t):
        self.cells[(r, c)] = (t, 1)

    def note(self, r, c, fix):
        self.edits.append({"row": r + 1, "col": c + 1, "fix": fix})

    @property
    def nrows(self):
        return max((r for r, _ in self.cells), default=-1) + 1

    @property
    def ncols(self):
        return max((c + max(w, 1) for (_, c), (_, w) in self.cells.items()), default=0)


def _box_candidates(g):
    """Every box outline that starts cleanly (a top edge and a left wall down to a bottom-left
    corner), whatever state its right side is in: (top, left, top-right col, bottom, ascii)."""
    out = []
    for (r, c) in sorted(g.cells):
        t = g.ch(r, c)
        ascii_box = t == "+" and g.ch(r, c + 1) == "-" and g.ch(r, c - 1) != "-"
        if not (t in _TL or ascii_box):
            continue
        ct, x = None, c + 1
        while x < c + 400:
            tx = g.ch(r, x)
            if tx in _TL or tx in "│║|" or (tx == " " and g.ch(r, x + 1) == " " and g.ch(r, x + 2) == " "):
                break                                       # another box, a wall, or open space: no top edge
            if (not ascii_box and tx in _TR) or (ascii_box and tx == "+" and g.ch(r, x + 1) != "-"):
                ct = x
                break
            x += 1
        if ct is None or ct - c < 2:
            continue
        rb, drift = None, []
        wall = (lambda t: t in "|+") if ascii_box else (lambda t: t in _VWALL)
        for rr in range(r + 1, g.nrows + 1):
            lw = g.ch(rr, c)
            if (not ascii_box and lw in _BL) or (ascii_box and lw == "+" and g.ch(rr, c + 1) == "-"
                                                 and g.ch(rr + 1, c) not in "|+"):
                rb = rr
                break
            if not wall(lw):
                p = next((x for x in (c + 1, c - 1, c + 2, c - 2) if g.ch(rr, x) in ("|" if ascii_box else "│║")), None)
                if p is None:
                    break
                drift.append((rr, p))                       # the left wall drifted on this row
        if rb is not None and rb > r + 1 and len(drift) < (rb - r - 1):
            out.append((r, c, ct, rb, ascii_box, drift))
    return out


def _fix_edge(g, row, cur, target, corner, edge):
    """Move an edge's end corner from `cur` to `target`, extending or trimming the edge."""
    if target > cur:
        if not all(g.free(row, x) for x in range(cur + 1, target + 1)):
            return False
        for x in range(cur, target):
            g.put(row, x, edge)
        g.put(row, target, corner)
        g.note(row, target, f"extended the edge by {target - cur} so its corner '{corner}' lines up")
        return True
    if not all(g.ch(row, x) in "─═-" for x in range(target, cur)):
        return False
    g.put(row, target, corner)
    for x in range(target + 1, cur + 1):
        g.put(row, x, " ")
    g.note(row, target, f"shortened the edge by {cur - target} so its corner '{corner}' lines up")
    return True


def _repair_box_once(g):
    """Right side of one box: the top corner, each row's wall and the bottom corner vote on the
    column; the majority wins and the stragglers move. Returns True if something changed."""
    boxes = _box_candidates(g)
    claimed = {}                                            # (row, col) -> box, for every box's own walls
    for b in boxes:
        r, c, ct, rb = b[:4]
        for rr in range(r, rb + 1):
            claimed.setdefault((rr, c), b)
            claimed.setdefault((rr, ct), b)
    for b in boxes:
        r, c, ct, rb, ascii_box, drift = b
        wall_ok = (lambda t: t in "|+") if ascii_box else (lambda t: t in _VWALL)
        corner_ok = (lambda t: t == "+") if ascii_box else (lambda t: t in _BR)
        near = [ct - 1, ct + 1, ct - 2, ct + 2, ct - 3, ct + 3]
        rows = {}
        for rr in range(r + 1, rb):
            if wall_ok(g.ch(rr, ct)):
                rows[rr] = ct
                continue
            rows[rr] = next((p for p in near if wall_ok(g.ch(rr, p)) and claimed.get((rr, p), b) is b), None)
        pb = ct if corner_ok(g.ch(rb, ct)) else next((p for p in near if corner_ok(g.ch(rb, p))), None)
        votes = {}
        for p in [ct] + [p for p in rows.values() if p is not None] + ([pb] if pb is not None else []):
            votes[p] = votes.get(p, 0) + 1
        target = max(votes, key=lambda k: (votes[k], k == ct))
        changed = False
        for rr, p in drift:                                 # left walls first: they anchor the row
            lo, hi = sorted((p, c))
            if g.free(rr, c) and all(g.free(rr, x) for x in range(lo + 1, hi)):
                t = g.ch(rr, p)
                g.put(rr, p, " ")
                g.put(rr, c, t)
                g.note(rr, c, f"moved the left wall '{t}' {abs(c - p)} col {'right' if c > p else 'left'}")
                changed = True
        edge = "-" if ascii_box else ("═" if g.ch(r, c) == "╔" else "─")
        if ct != target:
            changed |= _fix_edge(g, r, ct, target, g.ch(r, ct), edge)
        for rr, p in rows.items():
            if p is None:
                if g.free(rr, target) and g.ch(rr, target - 1) == " ":
                    wall = "|" if ascii_box else ("║" if edge == "═" else "│")
                    g.put(rr, target, wall)
                    g.note(rr, target, f"added the missing right wall '{wall}'")
                    changed = True
            elif p != target:
                lo, hi = sorted((p, target))
                if g.free(rr, target) and all(g.free(rr, x) for x in range(lo + 1, hi)):
                    t = g.ch(rr, p)
                    g.put(rr, p, " ")
                    g.put(rr, target, t)
                    g.note(rr, target, f"moved the right wall '{t}' {abs(target - p)} col {'right' if target > p else 'left'}")
                    changed = True
        if pb is not None and pb != target:
            changed |= _fix_edge(g, rb, pb, target, g.ch(rb, pb), edge)
        if changed:
            return True
    return False


def _repair_connector_once(g):
    """One connector fix, then the caller re-analyses: a piece one cell off moves into line,
    a short gap before a line or box is filled, an arrowhead one cell short moves to touch."""
    cells, nrows, ncols = g.cells, g.nrows, g.ncols
    drawn, _ = interpret(cells, nrows, ncols)
    get = lambda r, c: drawn.get((r, c), cells.get((r, c), (" ", 1))[0])
    border = box_border(find_boxes(get, nrows, ncols))
    is_text = lambda t: t not in (" ", "") and t not in ARMS and t not in HEADS
    axis = {"U": "│", "D": "│", "L": "─", "R": "─"}
    for (r, c) in sorted(cells):
        t = get(r, c)
        if t not in ARMS:
            continue
        raw = g.ch(r, c)
        for a in sorted(ARMS[t]):
            dr, dc = DIRS[a]
            nr, nc = r + dr, c + dc
            if get(nr, nc) != " " or is_text(get(r + 2 * dr, c + 2 * dc)):
                continue
            # a piece one cell to the side that continues this line: move it into line
            want = {"D": "▼v", "U": "▲^", "R": "▶>", "L": "◀<"}[a]
            sides = (((0, 1), (0, -1), (0, 2), (0, -2)) if a in "UD"          # nearest first
                     else ((1, 0), (-1, 0), (2, 0), (-2, 0)))
            for sr, sc in sides:
                pr, pc = nr + sr, nc + sc
                p = get(pr, pc)
                straight = (p in ARMS and ARMS[p] == (frozenset("UD") if a in "UD" else frozenset("LR"))) \
                    or p == ("|" if a in "UD" else "-")
                if (p in want or straight) and (pr, pc) not in border and g.free(nr, nc) \
                        and g.cells.get((pr, pc), (" ", 1))[1] == 1:
                    q = g.ch(pr, pc)
                    g.put(pr, pc, " ")
                    g.put(nr, nc, q)
                    g.note(nr, nc, f"moved '{q}' {abs(sc)} col {'left' if sc > 0 else 'right'} to line it up"
                           if sr == 0 else f"moved '{q}' {abs(sr)} line {'up' if sr > 0 else 'down'} to line it up")
                    return True
            # a gap of one or two cells before a line, a box or an arrowhead: fill it
            for k in (2, 3):
                ahead = get(r + k * dr, c + k * dc)
                if ahead == " ":
                    continue
                if (ahead in ARMS or ahead in HEADS) and all(g.free(r + j * dr, c + j * dc) for j in range(1, k)):
                    fill = ("|" if a in "UD" else "-") if raw in "|-+" else \
                           (("║" if a in "UD" else "═") if t in DOUBLE else axis[a])
                    for j in range(1, k):
                        g.put(r + j * dr, c + j * dc, fill)
                    g.note(nr, nc, f"filled a {k - 1}-cell gap in the line with '{fill}'")
                    return True
                break
    for (r, c) in sorted(cells):                            # an arrowhead one cell short of its target
        t = get(r, c)
        if t not in HEADS:
            continue
        d = HEADS[t]
        dr, dc = DIRS[d]
        n1, n2 = (r + dr, c + dc), (r + 2 * dr, c + 2 * dc)
        tail = get(r - dr, c - dc)
        if g.free(*n1) and (get(*n2) in ARMS or n2 in border) and tail in ARMS and d in ARMS[tail]:
            raw = g.ch(r, c)
            shaft = ("|" if d in "UD" else "-") if raw in "v^<>" else ("│" if d in "UD" else "─")
            g.put(r, c, shaft)
            g.put(*n1, raw)
            g.note(n1[0], n1[1], f"moved '{raw}' one cell so it touches what it points at")
            return True
    return False


def grid_text(cells):
    """The text of a grid, one line per row (wide characters count once)."""
    rows = {}
    for (r, c), tw in cells.items():
        rows.setdefault(r, {})[c] = tw
    out = []
    for r in range(max(rows, default=-1) + 1):
        row, s, c = rows.get(r, {}), [], 0
        end = max(row, default=-1)
        while c <= end:
            t, w = row.get(c, (" ", 1))
            if w == 0:
                c += 1
                continue
            s.append(t)
            c += w
        out.append("".join(s).rstrip())
    return "\n".join(out)


def repair(cells, limit=200):
    """Fix typical misalignment. Returns (cells, edits); edits carry 1-based grid row/col."""
    g = _Grid(cells)
    for _ in range(limit):
        if not (_repair_box_once(g) or _repair_connector_once(g)):
            break
    return g.cells, g.edits


def unescape(text):
    r"""Turn literal \n, \t, \r, \" and \\ into the characters they stand for (for --unescape)."""
    return re.sub(r'\\(n|t|r|"|\\)', lambda m: {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}[m.group(1)], text)


# ─── structure: what the diagram says (--describe) ───────────────────────────
def describe(cells, nrows, ncols):
    """Boxes (with titles and text) and edges (which box each arrow connects), in reading order.

    Lets an agent check that the picture means what it intended, e.g. that an arrow really
    runs from "API" to "DB"."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    is_text = lambda t: t not in (" ", "") and t not in ARMS and t not in HEADS and t not in DIAG and t not in BLOCKS
    boxes = sorted(find_boxes(get, nrows, ncols))
    inside = lambda a, b: a != b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    ids = {b: f"b{i}" for i, b in enumerate(boxes, 1)}
    squash = lambda s: " ".join(s.split())

    def row_text(r, c1, c2, skip=()):
        out = []
        for c in range(c1, c2 + 1):
            t = get(r, c)
            if t == "":
                continue                                  # second half of a wide character
            out.append(t if is_text(t) and (r, c) not in skip else " ")
        return squash("".join(out))

    def text_run(r, c):
        """The words around (r, c) on one row, allowing single spaces between them."""
        a = b = c
        while is_text(get(r, a - 1)) or (get(r, a - 1) == " " and is_text(get(r, a - 2))):
            a -= 1
        while is_text(get(r, b + 1)) or (get(r, b + 1) == " " and is_text(get(r, b + 2))):
            b += 1
        return squash("".join(get(r, x) for x in range(a, b + 1)))

    info = {}
    for b in boxes:
        r1, c1, r2, c2 = b
        kids = {(r, c) for k in boxes if inside(k, b) for r in range(k[0], k[2] + 1) for c in range(k[1], k[3] + 1)}
        title = row_text(r1, c1 + 1, c2 - 1)
        text = [t for t in (row_text(r, c1 + 1, c2 - 1, kids) for r in range(r1 + 1, r2)) if t]
        parents = [p for p in boxes if inside(b, p)]
        parent = min(parents, key=lambda p: (p[2] - p[0]) * (p[3] - p[1])) if parents else None
        info[b] = {"id": ids[b], "name": title or (text[0] if text else ""), "title": title or None,
                   "text": text, "row": r1 + 1, "col": c1 + 1, "rows": r2 - r1 + 1, "cols": c2 - c1 + 1,
                   "parent": ids[parent] if parent else None}

    borders = {b: box_border([b]) for b in boxes}

    def on_border(cell):
        hits = [b for b in boxes if cell in borders[b]]
        return min(hits, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if hits else None

    def endpoint(cell, step):
        """What sits at `cell` (or one blank cell further along `step`)."""
        for k in (0, 1):
            r, c = cell[0] + k * DIRS[step][0], cell[1] + k * DIRS[step][1]
            b = on_border((r, c))
            if b:
                return {"box": ids[b], "name": info[b]["name"]}
            if is_text(get(r, c)):
                return {"text": text_run(r, c)}
            if get(r, c) != " ":
                break
        return {"cell": [cell[0] + 1, cell[1] + 1]}

    heads = [(r, c, HEADS[t]) for (r, c), (t, _) in sorted(cells.items()) if t in HEADS]
    edges, seen = [], set()
    for (r, c, d), seq, kind, step in trace_routes(get, heads, boxes):
        src = seq[-1]
        if kind == "box":
            b = on_border(src)
            frm = {"box": ids[b], "name": info[b]["name"]} if b else {"cell": [src[0] + 1, src[1] + 1]}
        else:
            frm = endpoint((src[0] + DIRS[step][0], src[1] + DIRS[step][1]), step)
        to = endpoint((r + DIRS[d][0], c + DIRS[d][1]), d)
        key = json.dumps([frm, to], sort_keys=True)
        if key not in seen:
            seen.add(key)
            edges.append({"from": frm, "to": to})
    return {"boxes": [info[b] for b in boxes], "edges": edges}


# ─── command line ────────────────────────────────────────────────────────────
PRESETS = {                                 # destination -> look; explicit flags still win
    "readme": {"theme": "auto", "color": True, "animate": "flow"},
    "slides": {"color": True, "animate": "draw"},
    "chat": {"color": True},
    "print": {"style": "flat", "square": True},
    "dark": {"theme": "dark", "color": True},
    "page": {"theme": "auto", "color": True, "animate": "scroll", "html": True},
}
LOOK_DEFAULTS = {"style": "glow", "square": False, "theme": "light", "color": False, "animate": "none",
                 "html": False}
EXIT_CODES = {0: "ok (warnings allowed)", 1: "bad input or usage (see error and hint)",
              2: "self-check failed: the output is not 1:1, do not use it",
              3: "--strict was given and there were warnings"}
WARNING_CODES = {
    "dangling_line": "a line ends in empty space; hint says where its partner is when it is one cell off",
    "broken_join": "a line meets a line character that has no arm toward it; hint names the right character",
    "escaped_newlines": "one-line input containing literal \\n; pass real newlines or add --unescape",
    "no_structure": "ASCII box pieces were found but no closed box, so everything stayed text",
    "unclosed_box": "an ASCII box starts (+---+) but never closes, so it stays text; hint names the broken wall",
}
REPORT_FIELDS = {
    "status": "ok | warnings | self_check_failed | bad_input | usage_error",
    "summary": "one sentence to pass on to the user",
    "exit_code": "see exit_codes",
    "ok": "true unless the self-check failed",
    "roundtrip": "exact when the output was read back and matches the input cell for cell",
    "warnings": "list of {code, row, col, issue, hint, ...}; row/col are 1-based",
    "tips": "suggestions, e.g. to use --animate scroll for a tall diagram",
    "normalized": "every clean-up applied to the input (tabs, odd spaces, code fence, indentation, ...)",
    "rows, cols, boxes, arrowheads, flows, text_cells": "what was found",
    "ascii_drawn_as_lines, ascii_line_like_kept_as_text": "how ASCII - | + v ^ < > were read",
    "style, theme, color, animate, html, preset": "the look that was rendered",
    "diagram": "with --describe: {boxes: [{id, name, title, text, row, col, rows, cols, parent}], "
               "edges: [{from, to}]}; an endpoint is {box, name}, {text} or {cell}",
    "svg / html, png": "output paths, or the markup itself when there is no -o (unless --brief or --check)",
    "source": "where the diagram came from: {input, block, line, info} (block/line for markdown code blocks)",
    "warnings[].source_line, source_col": "the warning's position in the input file itself (1-based); hints use these",
    "diagrams, skipped": "with several inputs or --all-blocks: one report per diagram, and the code blocks "
                         "skipped because they had no lines or boxes; status/summary/exit_code aggregate them",
    "self_check_problems": "only when roundtrip is not exact",
    "repair": "with --repair: {edits: [{line, col, fix}], text}; text is the corrected diagram (only when "
              "something changed); the 1:1 check then holds against that text",
}
STDIN_WAIT = 5.0                            # seconds to wait for implicit stdin before giving up

HELP_EPILOG = """\
examples:
  ascii2svg diagram.txt -o diagram.svg --json
  ascii2svg diagram.txt --check --describe  # validate + list boxes and arrows; writes nothing
  ascii2svg notes.md -o out.svg --preset readme   # a ```fenced``` block is unwrapped automatically
  ascii2svg d.txt -o d.html --preset page         # a page that reveals as you scroll
  ascii2svg README.md --all-blocks -o out/  # every diagram in a markdown file -> out/README-N.svg
  ascii2svg a.txt b.txt -o out/ --check     # several files, one report each
  ascii2svg d.txt -o d.svg --accent '#e8590c' --font 'JetBrains Mono' --width 800
  ascii2svg --schema                        # every option, preset, report field as JSON
  claude mcp add ascii2svg -- ascii2svg --mcp   # use it as an MCP server

presets (pick the destination; explicit flags still win):
  readme  --theme auto --color --animate flow     slides  --color --animate draw
  chat    --color (add --png for apps without SVG) print   --style flat --square
  dark    --theme dark --color                    page    --html --theme auto --color --animate scroll

looks (all optional, and all keep the 1:1 guarantee):
  --theme light|dark|auto   auto follows the viewer's light/dark setting
  --color                   tint boxes by group, colour the arrows
  --animate draw            the diagram draws itself once, top to bottom
  --animate flow            ...then pulses keep travelling along every arrow
  --animate scroll          web page only: parts appear as the reader scrolls to them
  --html / -o NAME.html     write a standalone web page with the diagram inline
  PNG output is always the finished drawing (auto theme -> light).

what gets drawn:
  Unicode lines ─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╪ and arrows ▼▲▶◀ are drawn as lines.
  ASCII + - | and v ^ < > are drawn only when they form a box or attach to one.
  Everything else (hyphens in words, a->b, user_id, markdown tables) stays text,
  in exactly the same cell. When unsure, it stays text.

for agents:
  Pass the diagram as a file (or '-' for stdin); --text breaks on escaped newlines.
  With --json every outcome is JSON on stdout, including usage errors. Read
  "status" and "summary" first; warnings carry a code and a concrete hint.

exit codes:
  0 ok (warnings allowed)   1 bad input or usage   2 self-check failed (output not 1:1)
  3 --strict was given and there were warnings
"""


class UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):                   # never exit 2 (that means "self-check failed")
        raise UsageError(message)


def build_parser():
    p = _Parser(
        prog="ascii2svg", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=HELP_EPILOG,
        description="Render an ASCII/Unicode box diagram as SVG. Every character keeps its exact "
                    "position (1:1); a built-in check verifies this on every run.")
    p.add_argument("input", nargs="*", help="diagram file(s), or '-' for stdin; a markdown file uses its first "
                                       "code block (see --all-blocks)")
    p.add_argument("--text", help="the diagram itself, instead of a file or stdin")
    p.add_argument("-o", "--output", help="write the SVG (or .html page) here (default: stdout, or inside the JSON)")
    p.add_argument("--preset", choices=list(PRESETS), help="a look for a destination; explicit flags still win")
    p.add_argument("--style", choices=["glow", "shadow", "flat"], help="box depth effect (default: glow)")
    p.add_argument("--square", action=argparse.BooleanOptionalAction, help="keep box corners square")
    p.add_argument("--theme", choices=["light", "dark", "auto"],
                   help="colours; auto follows the viewer's light/dark setting (default: light)")
    p.add_argument("--color", action=argparse.BooleanOptionalAction, help="tint boxes by group and colour the arrows")
    p.add_argument("--animate", nargs="?", const="flow", choices=list(ANIMATIONS),
                   help="draw: the diagram draws itself; flow: draw, then pulses travel along the "
                        "arrows (bare --animate = flow); scroll: web page that reveals as you scroll")
    p.add_argument("--html", action=argparse.BooleanOptionalAction,
                   help="write a standalone web page (implied by -o NAME.html); needed for --animate scroll")
    p.add_argument("--png", nargs="?", const="", metavar="PATH",
                   help="also write a PNG (default path: next to -o). Needs cairosvg")
    p.add_argument("--json", action="store_true", help="print a machine-readable report on stdout")
    p.add_argument("--check", action="store_true", help="validate only: print the JSON report, write nothing")
    p.add_argument("--all-blocks", action="store_true",
                   help="render every diagram in a markdown file (code blocks without lines or boxes are skipped)")
    p.add_argument("--block", type=int, metavar="N", help="render only the Nth code block of a markdown file")
    p.add_argument("--accent", metavar="#HEX", help="accent colour for arrows and animation (default #0969da)")
    p.add_argument("--font", metavar="FAMILY", help="font family to try first, e.g. \"JetBrains Mono\"")
    p.add_argument("--width", type=int, metavar="PX", help="scale the output to this width in pixels")
    p.add_argument("--describe", action="store_true",
                   help="add the diagram's structure to the report: boxes, and which box each arrow connects")
    p.add_argument("--brief", action="store_true", help="keep the JSON small: never embed the markup")
    p.add_argument("--strict", action="store_true", help="exit 3 if there are warnings")
    p.add_argument("--repair", action="store_true",
                   help="fix typical misalignment first (ragged walls, drifting connectors, short arrows); "
                        "only line characters move, text never changes; edits and fixed text are in the report")
    p.add_argument("--unescape", action="store_true", help=r"turn literal \n, \t, \" and \\ in the input into real characters")
    p.add_argument("--tab-size", type=int, default=4, help="tab stops for tab characters (default: 4)")
    p.add_argument("--title", default="ASCII diagram", help="accessible title stored in the SVG")
    p.add_argument("--max-rows", type=int, default=1000, help="refuse larger input (default: 1000)")
    p.add_argument("--max-cols", type=int, default=400, help="refuse wider input (default: 400)")
    p.add_argument("--schema", action="store_true", help="print every option, preset and report field as JSON, then exit")
    p.add_argument("--mcp", action="store_true",
                   help="run as an MCP server on stdin/stdout (tools: render_diagram, check_diagram)")
    p.add_argument("--version", action="version", version=f"ascii2svg {__version__}")
    return p


def resolve_look(args):
    """Fill the look options: explicit flag, else the preset, else the default."""
    preset = PRESETS.get(args.preset or "", {})
    if args.html is None:
        args.html = preset.get("html", False) or bool(args.output and args.output.lower().endswith((".html", ".htm")))
    for k, v in LOOK_DEFAULTS.items():
        if getattr(args, k) is None:
            setattr(args, k, preset.get(k, v))
    return args


def schema():
    """Everything an agent needs to call the CLI correctly, as data."""
    opts = []
    for a in build_parser()._actions:
        if a.dest in ("help", "version"):
            continue
        if isinstance(a, argparse.BooleanOptionalAction):
            kind = "boolean"
        elif a.nargs == 0:
            kind = "flag"
        elif a.choices:
            kind = "choice"
        elif a.type is int:
            kind = "integer"
        else:
            kind = "string"
        default = LOOK_DEFAULTS.get(a.dest, a.default)
        opts.append({"flags": a.option_strings or [a.dest], "dest": a.dest, "kind": kind,
                     "choices": list(a.choices) if a.choices else None, "default": default,
                     "optional_value": a.const if a.nargs == "?" and a.option_strings else None,
                     "help": a.help})
    return {"name": "ascii2svg", "version": __version__,
            "input": "file path(s), '-' for stdin, or --text; a markdown file uses its first code block, "
                     "or every diagram block with --all-blocks",
            "mcp": "ascii2svg --mcp serves tools render_diagram and check_diagram over stdio",
            "options": opts, "presets": PRESETS, "exit_codes": {str(k): v for k, v in EXIT_CODES.items()},
            "warning_codes": WARNING_CODES, "report_fields": REPORT_FIELDS,
            "library": "ascii2svg.render(text, **options) -> (markup, report)"}


def _read_stdin(explicit):
    """Read stdin. Implicit stdin (no input argument) gives up if nothing arrives within
    STDIN_WAIT seconds, so an agent that forgot the file gets an error instead of a hang."""
    if sys.stdin is None or sys.stdin.isatty():
        raise ValueError("no diagram given: pass a file path, '-' with stdin, or --text")
    if explicit:
        return sys.stdin.buffer.read()
    import os
    import threading
    got, parts, fd = threading.Event(), [], sys.stdin.fileno()

    def pull():                                  # raw fd reads: no buffer lock left held at exit
        chunk = os.read(fd, 65536)
        parts.append(chunk)
        got.set()
        while chunk:
            chunk = os.read(fd, 65536)
            parts.append(chunk)

    t = threading.Thread(target=pull, daemon=True)
    t.start()
    if not got.wait(float(os.environ.get("ASCII2SVG_STDIN_WAIT", STDIN_WAIT))):
        raise ValueError("no diagram given: nothing arrived on stdin. Pass a file path, "
                         "'-' to wait for stdin, or --text")
    t.join()
    return b"".join(parts)


def _sources(args):
    """[(label, text, notes, error)] for every input: --text, each file, or stdin."""
    if args.text is not None:
        return [("--text", args.text, [], None)]
    out = []
    names = args.input or [None]                          # None: implicit stdin
    for name in names:
        notes = []
        try:
            if name in (None, "-"):
                label, data = "stdin", _read_stdin(explicit=name == "-")
            else:
                label = name
                try:
                    data = open(name, "rb").read()
                except OSError as e:
                    raise ValueError(f"cannot read {name}: {e.strerror}")
        except ValueError as e:
            if len(names) == 1:
                raise
            out.append((name or "stdin", None, notes, str(e)))
            continue
        text = data.decode("utf-8", errors="replace")
        if "�" in text and b"\xef\xbf\xbd" not in data:
            notes.append({"change": "invalid UTF-8 bytes replaced with �"})
        out.append((label, text, notes, None))
    return out


def _jobs(args):
    """One job per diagram: every input, or every code block with --all-blocks / --block."""
    jobs = []
    for label, raw, notes, err in _sources(args):
        if err:
            jobs.append({"source": {"input": label}, "error": err})
            continue
        if not (args.all_blocks or args.block):
            jobs.append({"source": {"input": label}, "raw": raw, "notes": notes, "base": 0})
            continue
        blocks = code_blocks(raw)
        if args.block:
            if not 1 <= args.block <= len(blocks):
                jobs.append({"source": {"input": label},
                             "error": f"{label} has {len(blocks)} code block(s); --block {args.block} is out of range"})
                continue
            blocks = [blocks[args.block - 1]]
        if not blocks:                                     # --all-blocks on a plain file: the file is the diagram
            jobs.append({"source": {"input": label}, "raw": raw, "notes": notes, "base": 0})
        for b in blocks:
            src = {"input": label, "block": b["block"], "line": b["line"]}
            if b["info"]:
                src["info"] = b["info"]
            jobs.append({"source": src, "raw": b["text"], "notes": list(notes), "base": b["line"] - 1, "block": True})
    return jobs


def run_one(args, raw, notes, base=0):
    """Render one diagram. Returns (exit_code, report, svg, static_svg_for_png, is_diagram)."""
    notes = list(notes)
    if args.unescape:
        new = unescape(raw)
        if new != raw:
            raw = new
            notes.append({"change": "unescaped \\n, \\t, \\\" and \\\\ sequences"})
    lines, more, origin = prepare_ex(raw, args.tab_size)
    notes += more
    if not lines:
        raise ValueError("the diagram is empty")
    cells, nrows, ncols = build_grid(lines)
    if nrows > args.max_rows or ncols > args.max_cols:
        raise ValueError(f"diagram is {nrows} rows x {ncols} columns; limit is {args.max_rows} x "
                         f"{args.max_cols} (raise with --max-rows / --max-cols)")
    fixes = None
    if args.repair:
        fixed, edits = repair(cells)
        if edits:
            cells, nrows, ncols = build_grid(grid_text(fixed).split("\n"))
        fixes = {"edits": [{"line": base + origin["line"] + e["row"], "col": origin["col"] + e["col"],
                            "fix": e["fix"]} for e in edits]}
        if edits:
            fixes["text"] = grid_text(cells)
    drawn, info = interpret(cells, nrows, ncols)
    draw_cells = {k: ((drawn[k], w) if k in drawn else (t, w)) for k, (t, w) in cells.items()}
    style = dict(accent=args.accent, font=args.font, width=args.width)
    svg, stats = render_svg(draw_cells, nrows, ncols, args.style, args.square, args.title,
                            args.theme, args.color, args.animate, **style)
    problems = self_check(svg, draw_cells, cells)
    still = svg
    if args.png is not None and (args.animate != "none" or args.theme == "auto"):
        still = render_svg(draw_cells, nrows, ncols, args.style, args.square, args.title,
                           "light" if args.theme == "auto" else args.theme, args.color, **style)[0]
        problems += self_check(still, draw_cells, cells)
    where = (base + origin["line"], origin["col"])
    warnings = input_warnings(raw, cells, info, drawn, where) + connector_warnings(
        draw_cells, nrows, ncols, origin=(base + origin["line"], origin["col"]))
    for w in warnings:                                     # where to fix it in the file you were given
        w["source_line"] = base + origin["line"] + w["row"]
        w["source_col"] = origin["col"] + w["col"]
    report = {"ok": not problems, "rows": nrows, "cols": ncols, "style": args.style, "theme": args.theme,
              "color": args.color, "animate": args.animate, "html": args.html, "preset": args.preset,
              "boxes": stats["boxes"], "arrowheads": stats["arrowheads"], "flows": stats["flows"],
              "text_cells": stats["text_cells"],
              **info, "roundtrip": "exact" if not problems else "MISMATCH",
              "normalized": notes, "warnings": warnings, "tips": [], "width_source": WIDTH_SOURCE,
              "version": __version__}
    if nrows > 45 and args.animate in ("draw", "flow") and not args.html:
        report["tips"].append("tall diagram: the lower part finishes drawing before the reader scrolls "
                              "to it; for a web page use --animate scroll -o NAME.html (or --preset page)")
    if fixes is not None:
        report["repair"] = fixes
    if args.describe:
        report["diagram"] = describe(draw_cells, nrows, ncols)
    is_diagram = any(t in ARMS or t in HEADS or t in DIAG or t in BLOCKS for t, _ in draw_cells.values())
    if problems:
        report["self_check_problems"] = problems[:50]
        return 2, report, svg, still, is_diagram
    return (3 if args.strict and warnings else 0), report, svg, still, is_diagram


def run(args) -> tuple[int, dict, str, str]:
    """Core pipeline for a single diagram (kept for callers of earlier versions)."""
    (label, raw, notes, _), = _sources(args)
    code, report, svg, still, _ = run_one(args, raw, notes)
    return code, report, svg, still


def _finish(report, code, where=None):
    """Put status, summary and exit_code first, so a truncated report still says what happened."""
    w = report["warnings"]
    status = "self_check_failed" if code == 2 else "warnings" if w else "ok"
    what = (f"{report['boxes']} box{'es' if report['boxes'] != 1 else ''} and "
            f"{report['arrowheads']} arrow{'s' if report['arrowheads'] != 1 else ''} "
            f"({report['rows']}x{report['cols']})")
    fixed = len(report.get("repair", {}).get("edits", []))
    repaired = f"Repaired {fixed} misalignment{'s' if fixed != 1 else ''}. " if fixed else ""
    if code == 2:
        summary = f"Self-check FAILED: the output does not match the input 1:1; do not use it. Found {what}."
    else:
        summary = f"{repaired}Rendered {what}{' to ' + where if where else ''}; 1:1 self-check exact."
        if w:
            at = f"line {w[0]['source_line']} col {w[0]['source_col']}" if "source_line" in w[0] \
                else f"row {w[0]['row']} col {w[0]['col']}"
            summary += (f" {len(w)} warning{'s' if len(w) != 1 else ''}, first at {at} "
                        f"({w[0]['code']}): {w[0]['hint']}")
    return {"status": status, "summary": summary, "exit_code": code, **report}


def _failed(source, msg):
    return {"status": "bad_input", "summary": f"Nothing rendered: {msg}", "exit_code": 1, "ok": False,
            "error": msg, "source": source}


def render(text: str, *, preset: str | None = None, style: str | None = None, square: bool | None = None,
           theme: str | None = None, color: bool | None = None, animate: str | None = None,
           html: bool | None = None, accent: str | None = None, font: str | None = None,
           width: int | None = None, title: str = "ASCII diagram", tab_size: int = 4,
           describe: bool = False, unescape: bool = False, strict: bool = False,
           repair: bool = False) -> tuple[str, dict]:
    """Render a diagram. Returns (markup, report): an SVG, or a web page with html=True.

    Options match the CLI; unset look options come from `preset`, then the defaults
    (glow, light, no colour, no animation). The report is what the CLI prints with --json:
    check report["status"] ("ok" / "warnings"; "self_check_failed" means do not use the output).
    Raises ValueError for empty or oversized input and for invalid options.
    """
    args = build_parser().parse_args([])
    looks = {"preset": preset, "style": style, "square": square, "theme": theme, "color": color,
             "animate": animate, "html": html}
    allowed = {"preset": tuple(PRESETS), "style": ("glow", "shadow", "flat"), "theme": ("light", "dark", "auto"),
               "animate": ANIMATIONS}
    for name, value in looks.items():
        if value is not None and name in allowed and value not in allowed[name]:
            raise ValueError(f"{name} must be one of {', '.join(allowed[name])}")
        setattr(args, name, value)
    check_style(accent, font, width)
    args.accent, args.font, args.width = accent, font, width
    args.text, args.title, args.tab_size = text, title, tab_size
    args.describe, args.unescape, args.strict, args.repair = describe, unescape, strict, repair
    resolve_look(args)
    if args.animate == "scroll" and not args.html:
        raise ValueError("animate='scroll' needs html=True (an SVG shown as an image can't see the page scroll)")
    code, report, svg, _, _ = run_one(args, text, [])
    return (to_html(svg, args.title, args.theme) if args.html else svg), _finish(report, code)


# ─── MCP server (--mcp) ──────────────────────────────────────────────────────
# Model Context Protocol over stdio: one JSON-RPC message per line. No dependencies.
#   claude mcp add ascii2svg -- ascii2svg --mcp
MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
_DIAGRAM = {"type": "string",
            "description": "The diagram as plain text with real line breaks (a markdown code block is fine). "
                           "Boxes: +--+ / |  | / +--+ or ┌─┐ │ │ └─┘. Arrows end in v ^ < > or ▼ ▲ ▶ ◀ "
                           "touching (or one space from) the box they point at."}
MCP_TOOLS = [
    {"name": "render_diagram",
     "description": "Render an ASCII/Unicode box diagram as SVG (or a web page), keeping every character "
                    "in its exact cell. Writes output_path and returns a JSON report: read 'status' "
                    "(ok | warnings | self_check_failed | bad_input) and 'summary'. For warnings, apply each "
                    "'hint' (it names the row/col to fix) and render again. Pick 'preset' from where the "
                    "diagram is going. Run check_diagram first on a new diagram.",
     "inputSchema": {"type": "object", "required": ["diagram"], "properties": {
         "diagram": _DIAGRAM,
         "output_path": {"type": "string", "description": "File to write: .svg, or .html for a web page. "
                                                          "Prefer an absolute path. Omit to get the markup back."},
         "preset": {"type": "string", "enum": list(PRESETS),
                    "description": "readme: GitHub/docs, animated, follows dark mode · slides · chat · print · "
                                   "dark · page: a web page that reveals as you scroll (needs a .html path)"},
         "theme": {"type": "string", "enum": ["light", "dark", "auto"]},
         "color": {"type": "boolean", "description": "Tint boxes by group and colour the arrows"},
         "animate": {"type": "string", "enum": list(ANIMATIONS)},
         "style": {"type": "string", "enum": ["glow", "shadow", "flat"]},
         "square": {"type": "boolean", "description": "Square box corners"},
         "accent": {"type": "string", "description": "Accent colour for arrows and animation, e.g. #0969da"},
         "font": {"type": "string", "description": "Font family to try first, e.g. JetBrains Mono"},
         "width": {"type": "integer", "description": "Scale the output to this width in pixels"},
         "title": {"type": "string", "description": "Accessible title stored in the output"},
         "describe": {"type": "boolean", "description": "Also return boxes and edges (which box each arrow connects)"},
         "repair": {"type": "boolean", "description": "Fix typical misalignment first (ragged walls, drifting "
                                                      "connectors, short arrows); the fixed text is in report.repair.text"},
     }}},
    {"name": "check_diagram",
     "description": "Validate an ASCII/Unicode box diagram without writing anything. Returns 'status', "
                    "'summary', warnings with concrete 'hint's (e.g. 'the arrowhead v at row 5 col 5 is one "
                    "column right'), and the structure: boxes and edges (which box each arrow connects). "
                    "Use it to confirm a diagram means what you intended before rendering.",
     "inputSchema": {"type": "object", "required": ["diagram"], "properties": {
         "diagram": _DIAGRAM,
         "describe": {"type": "boolean", "description": "Include boxes and edges (default true)"},
         "repair": {"type": "boolean", "description": "Also fix typical misalignment; report.repair lists the "
                                                      "edits and report.repair.text is the corrected diagram"},
     }}},
]


def _mcp_call(name, a):
    """Run one tool call. Returns the report (never raises for bad input)."""
    import os
    diagram = a.get("diagram")
    if not isinstance(diagram, str):
        return _failed({"input": "diagram"}, "'diagram' must be a string with the diagram text")
    try:
        if name == "check_diagram":
            _, report = render(diagram, describe=a.get("describe", True), repair=bool(a.get("repair")))
            return report
        path = a.get("output_path")
        kw = {k: a[k] for k in ("preset", "style", "square", "theme", "color", "animate", "accent", "font",
                                "width", "title", "describe", "repair") if a.get(k) is not None}
        html_out = bool(path and path.lower().endswith((".html", ".htm")))
        if html_out or kw.get("preset") == "page" or kw.get("animate") == "scroll":
            kw["html"] = True
        markup, report = render(diagram, **kw)
    except ValueError as e:
        return _failed({"input": "diagram"}, str(e))
    kind = "html" if report["html"] else "svg"
    if path:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(markup)
        report[kind] = path
        report["summary"] = report["summary"].replace("; 1:1", f" to {path}; 1:1", 1)
    else:
        report[kind] = markup
    return report


def serve_mcp():
    """Serve MCP on stdin/stdout until stdin closes."""
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    names = {t["name"] for t in MCP_TOOLS}

    def send(msg):
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
        if mid is None:
            continue                                        # a notification: nothing to answer
        reply = {"jsonrpc": "2.0", "id": mid}
        try:
            if method == "initialize":
                asked = params.get("protocolVersion")
                reply["result"] = {
                    "protocolVersion": asked if asked in MCP_VERSIONS else MCP_VERSIONS[0],
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "ascii2svg", "version": __version__},
                    "instructions": "Render text box diagrams as SVG, 1:1. Draft the diagram, call check_diagram, "
                                    "apply the hints until status is ok and the edges are what you meant, then "
                                    "call render_diagram with a preset for the destination."}
            elif method == "ping":
                reply["result"] = {}
            elif method == "tools/list":
                reply["result"] = {"tools": MCP_TOOLS}
            elif method == "tools/call":
                if params.get("name") not in names:
                    reply["error"] = {"code": -32602, "message": f"unknown tool: {params.get('name')}"}
                else:
                    report = _mcp_call(params["name"], params.get("arguments") or {})
                    reply["result"] = {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False)}],
                                       "isError": report["status"] in ("bad_input", "usage_error", "self_check_failed")}
            else:
                reply["error"] = {"code": -32601, "message": f"method not found: {method}"}
        except Exception as e:                              # never let one request kill the server
            reply.pop("result", None)
            reply["error"] = {"code": -32603, "message": f"internal error: {e}"}
        send(reply)
    return 0


def _usage_hint(message):
    """A concrete suggestion for an argparse error, plus the valid choices when there are some."""
    import difflib
    flags = sorted({f for a in build_parser()._actions for f in a.option_strings})
    m = re.search(r"invalid choice: '([^']*)' \(choose from (.*)\)", message)
    if m:
        choices = [c.strip(" '") for c in m.group(2).split(",")]
        close = difflib.get_close_matches(m.group(1), choices, n=1)
        return (f"did you mean '{close[0]}'?" if close else f"use one of: {', '.join(choices)}"), choices
    m = re.search(r"unrecognized arguments: (.*)", message)
    if m:
        tips = []
        for tok in m.group(1).split():
            close = difflib.get_close_matches(tok.split("=")[0], flags, n=1, cutoff=0.6) if tok.startswith("-") else []
            tips.append(f"'{tok}': did you mean {close[0]}?" if close else f"'{tok}' is not an option")
        return "; ".join(tips) + " (ascii2svg --schema lists every option)", None
    return "run ascii2svg --schema (JSON) or --help for the options", None


def _out_name(job, i, ext, used):
    """out/NAME.svg for one diagram of several: the input's stem, plus -N for a code block."""
    import os
    src = job["source"]
    stem = "diagram" if src["input"] in ("stdin", "--text") else os.path.splitext(os.path.basename(src["input"]))[0]
    name = f"{stem}-{src['block']}" if "block" in src else stem
    if name in used:
        name = f"{name}-{i}"
    used.add(name)
    return name + ext


def main(argv=None) -> int:
    import os
    for stream in (sys.stdout, sys.stderr):              # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else list(argv)
    wants_json = any(a in ("--json", "--check") for a in argv)

    def emit(obj):
        print(json.dumps(obj))                            # ASCII-safe: decodes the same everywhere

    def fail(code, status, msg, hint=None, choices=None):
        if wants_json:
            err = {"status": status, "summary": f"Nothing rendered: {msg}", "exit_code": code,
                   "ok": False, "error": msg}
            if hint:
                err["hint"] = hint
            if choices:
                err["choices"] = choices
            emit(err)
        else:
            print(f"ascii2svg: error: {msg}" + (f"\nascii2svg: hint: {hint}" if hint else ""), file=sys.stderr)
        return code

    try:
        args = build_parser().parse_args(argv)
        check_style(args.accent, args.font, args.width)
    except (UsageError, ValueError) as e:
        return fail(1, "usage_error", str(e), *_usage_hint(str(e)))
    if args.schema:
        emit(schema())
        return 0
    if args.mcp:
        return serve_mcp()
    args.json = args.json or args.check
    resolve_look(args)
    if args.animate == "scroll" and not args.html:
        return fail(1, "usage_error", "--animate scroll needs a web page",
                    "add --html or use -o NAME.html (an SVG shown as an image can't see the page scroll)")
    try:
        jobs = _jobs(args)
    except ValueError as e:
        return fail(1, "bad_input", str(e))
    many = len(jobs) > 1 or args.all_blocks
    outdir = args.output if args.output and (args.output.endswith(("/", "\\")) or os.path.isdir(args.output)) else None
    writes = not args.check
    ext = ".html" if args.html else ".svg"
    if many and args.output and not outdir:
        return fail(1, "usage_error", "several diagrams need a directory for -o", "end it with a slash, e.g. -o out/")
    if many and writes and not args.output and not args.json:
        return fail(1, "usage_error", "several diagrams need -o DIR/ or --json", "e.g. -o out/")
    if many and args.png:
        return fail(1, "usage_error", "--png PATH names one file", "use --png alone: each PNG goes next to its SVG")
    if writes and args.png is not None:
        if not args.output and not args.png:
            return fail(1, "usage_error", "--png needs a path when -o is not given", "add -o NAME.svg or --png NAME.png")
        try:
            import cairosvg
        except ImportError:
            return fail(1, "usage_error", "--png needs cairosvg", "pip install cairosvg")
    if outdir and writes:
        os.makedirs(outdir, exist_ok=True)

    results, skipped, used = [], [], set()
    for i, job in enumerate(jobs, 1):
        if "error" in job:
            results.append((1, _failed(job["source"], job["error"]), None))
            continue
        try:
            code, report, svg, still, is_diagram = run_one(args, job["raw"], job["notes"], job["base"])
        except ValueError as e:
            if not many:
                return fail(1, "bad_input", str(e))
            results.append((1, _failed(job["source"], str(e)), None))
            continue
        if job.get("block") and args.all_blocks and not is_diagram:
            skipped.append({"source": job["source"], "reason": "no lines or boxes: not a diagram"})
            continue
        out = to_html(svg, args.title, args.theme) if args.html else svg
        target = os.path.join(outdir, _out_name(job, i, ext, used)) if outdir else args.output
        if writes and target:
            with open(target, "w", encoding="utf-8", newline="") as f:   # same bytes on every OS
                f.write(out)
            report["html" if args.html else "svg"] = target
        if writes and args.png is not None:
            png = args.png or re.sub(r"\.(svg|html?)$", "", target, flags=re.I) + ".png"
            cairosvg.svg2png(bytestring=still.encode(), write_to=png, scale=2)
            report["png"] = png
        report["source"] = job["source"]
        report = _finish(report, code, target if writes else None)
        if args.json and writes and not target and not args.brief:
            report["html" if args.html else "svg"] = out
        results.append((code, report, out))

    if not many:
        code, report, out = results[0]
        if args.json:
            emit(report)
        else:
            if not args.output:
                sys.stdout.write(out)
            print(f"ascii2svg: {report['summary']}", file=sys.stderr)
            if code == 2:
                print("ascii2svg: SELF-CHECK FAILED - the SVG does not match the input 1:1", file=sys.stderr)
        return code

    codes = [c for c, _, _ in results]
    code = 2 if 2 in codes else 1 if 1 in codes else 3 if 3 in codes else 0
    reports = [r for _, r, _ in results]
    if not reports:
        return fail(1, "bad_input", f"no diagrams found ({len(skipped)} code block(s) had no lines or boxes)")
    counts = {s: sum(r["status"] == s for r in reports) for s in ("ok", "warnings", "bad_input", "self_check_failed")}
    status = ("self_check_failed" if counts["self_check_failed"] else "bad_input" if counts["bad_input"]
              else "warnings" if counts["warnings"] else "ok")
    parts = [f"{n} {s.replace('_', ' ')}" for s, n in counts.items() if n]
    summary = (f"Rendered {len(reports)} diagram{'s' if len(reports) != 1 else ''}"
               f"{' to ' + outdir if outdir and writes else ''}: {', '.join(parts)}.")
    if skipped:
        summary += f" Skipped {len(skipped)} code block{'s' if len(skipped) != 1 else ''} with no diagram."
    agg = {"status": status, "summary": summary, "exit_code": code, "ok": code not in (1, 2),
           "diagrams": reports, "skipped": skipped, "version": __version__}
    if args.json:
        emit(agg)
    else:
        for r in reports:
            print(f"ascii2svg: {r['source']}: {r['summary']}", file=sys.stderr)
        print(f"ascii2svg: {summary}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
