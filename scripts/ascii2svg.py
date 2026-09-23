#!/usr/bin/env python3
"""ascii2svg - turn an ASCII or Unicode box diagram into an SVG, 1:1.

Every character keeps its exact grid cell. Box-drawing characters, and ASCII
+ - | v ^ < > that form a box or attach to one, are drawn as real lines.
Everything else is drawn as the same text in the same place.

Built for LLM agents:   cat diagram.txt | ascii2svg -o diagram.svg --json
No required dependencies (uses `wcwidth` for character widths if installed).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata

__version__ = "1.0.0"

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
    notes: list[dict] = []
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
    while out and not out[-1]:
        out.pop()
    indent = min((len(l) - len(l.lstrip(" ")) for l in out if l), default=0)
    if indent:
        out = [l[indent:] for l in out]
        notes.append({"change": "removed common indentation", "columns": indent})
    return out, notes


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
# 1:1 contract: an ASCII character may be drawn only as the line it stands for
CORR = {"-": set("─┬┴┼"), "|": set("│├┤┼"), "+": set("┌┐└┘├┤┬┴┼─│"),
        "v": {"▼"}, "^": {"▲"}, ">": {"▶"}, "<": {"◀"}}
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
    kept = sum(1 for k, (t, _) in cells.items() if t in "|+" and k not in drawn)
    kept += sum(b - a + 1 for r, a, b in hruns if b > a and (r, a) not in drawn)
    return drawn, {"ascii_drawn_as_lines": len(drawn), "ascii_line_like_kept_as_text": kept}


# ─── rendering ───────────────────────────────────────────────────────────────
CW, CH, PAD, FS = 9, 18, 12, 14
INK, BG = "#1f2328", "#ffffff"
GLOW_R, GLOW_N, GLOW_A, GLOW_DY = 7.0, 14, 0.02, 1.5
SHADOW = ((1.5, 0.18), (3.0, 0.13), (4.2, 0.09))
RADIUS = 4.0
TL, TR, BL, BR = set("┌╭╔"), set("┐╮╗"), set("└╰╚"), set("┘╯╝")
BOTTOM_OK = set("─┬┴┼═╪")


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


def render_svg(cells, nrows, ncols, style="glow", square=False, title="ASCII diagram"):
    """cells: {(r, c): (text, width)} where line cells already hold Unicode line characters."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    segs = {"s": {"h": {}, "v": {}}, "d": {"h": {}, "v": {}}}
    curves, heads, texts = [], [], []
    round_ok = not square and not any(t in ROUNDED for t, _ in cells.values())

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
                curves.append((st_h, f"M{hx:g} {cy:g}Q{cx:g} {cy:g} {cx:g} {vy:g}"))
                continue
            for a in sorted(arms):
                st = st_h if a in "LR" else st_v
                if a == "L":
                    add(st, "h", cy, x0, cx)
                elif a == "R":
                    add(st, "h", cy, cx, x0 + CW)
                elif a == "U":
                    add(st, "v", cx, y0, cy)
                else:
                    add(st, "v", cx, cy, y0 + CH)
        elif t in HEADS:
            heads.append((r, c, HEADS[t]))
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
        o = [f'<path d="{d}" class="{cls}"/>' for s, d in curves if s == st]
        o += [f'<line x1="{a:g}" y1="{k:g}" x2="{b:g}" y2="{k:g}" class="{cls}"/>' for k, a, b in merged(segs[st]["h"])]
        o += [f'<line x1="{k:g}" y1="{a:g}" x2="{k:g}" y2="{b:g}" class="{cls}"/>' for k, a, b in merged(segs[st]["v"])]
        return o

    # boxes: glow / shadow, then fill, then plates behind titles on the top edge
    under = []
    boxes = find_boxes(get, nrows, ncols)
    is_text = lambda t: t not in (" ", "") and t not in ARMS and t not in HEADS
    for r1, c1, r2, c2 in boxes:
        x1, y1 = PAD + c1 * CW + CW / 2, PAD + r1 * CH + CH / 2
        x2, y2 = PAD + c2 * CW + CW / 2, PAD + r2 * CH + CH / 2
        w, h = x2 - x1, y2 - y1
        rad = RADIUS if (round_ok or get(r1, c1) in ROUNDED) else 0
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
                                 f'height="{h + 2 * e:g}" rx="{rad + e:g}" class="glow"/>')
        elif style == "shadow":
            for off, op in SHADOW:
                under.append(f'<rect x="{x1 + off:g}" y="{y1 + off:g}" width="{w:g}" height="{h:g}" '
                             f'rx="{rad:g}" class="shadow" fill-opacity="{op}"/>')
        if style != "flat":
            under.append(f'<rect x="{x1:g}" y="{y1:g}" width="{w:g}" height="{h:g}" rx="{rad:g}" class="fill"/>')
            run = None
            for c in range(c1 + 1, c2 + 1):
                t = get(r1, c)
                line_cell = t in ARMS or t in HEADS or c == c2
                if not line_cell and run is None:
                    run = c
                if line_cell and run is not None:
                    under.append(f'<rect x="{PAD + run * CW:g}" y="{PAD + r1 * CH:g}" '
                                 f'width="{(c - run) * CW:g}" height="{CH:g}" class="plate"/>')
                    run = None

    body = under + lines("d", "dbl") + lines("d", "dbl-gap") + lines("s", "sgl")
    line_like = lambda r, c: get(r, c) in ARMS
    for r, c, d in heads:
        x0, y0 = PAD + c * CW, PAD + r * CH
        cx, cy = x0 + CW / 2, y0 + CH / 2
        if d == "D":
            tip = y0 + CH + (CH / 2 if line_like(r + 1, c) else 0)
            sh, pts = (cx, y0, cx, tip - 6), ((cx - 4, tip - 8), (cx + 4, tip - 8), (cx, tip))
        elif d == "U":
            tip = y0 - (CH / 2 if line_like(r - 1, c) else 0)
            sh, pts = (cx, y0 + CH, cx, tip + 6), ((cx - 4, tip + 8), (cx + 4, tip + 8), (cx, tip))
        elif d == "R":
            tip = x0 + CW + (CW / 2 if line_like(r, c + 1) else 0)
            sh, pts = (x0, cy, tip - 6, cy), ((tip - 8, cy - 4), (tip - 8, cy + 4), (tip, cy))
        else:
            tip = x0 - (CW / 2 if line_like(r, c - 1) else 0)
            sh, pts = (x0 + CW, cy, tip + 6, cy), ((tip + 8, cy - 4), (tip + 8, cy + 4), (tip, cy))
        body.append('<line x1="%g" y1="%g" x2="%g" y2="%g" class="sgl shaft"/>' % sh)
        body.append('<polygon points="%s" class="head"/>' % " ".join(f"{x:g},{y:g}" for x, y in pts))
    for r, c, w, t in texts:
        body.append(f'<text x="{PAD + c * CW + w * CW / 2:g}" y="{PAD + r * CH + CH / 2 + 5:g}">'
                    f'{html.escape(t, quote=False)}</text>')

    W, H = ncols * CW + 2 * PAD, nrows * CH + 2 * PAD
    css = (f".sgl{{stroke:{INK};stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round;fill:none}}"
           f".dbl{{stroke:{INK};stroke-width:5;stroke-linecap:round;stroke-linejoin:round;fill:none}}"
           f".dbl-gap{{stroke:{BG};stroke-width:2;stroke-linecap:round;stroke-linejoin:round;fill:none}}"
           f".head{{fill:{INK};stroke:{INK};stroke-width:1;stroke-linejoin:round}}"
           f".glow{{fill:#000;fill-opacity:{GLOW_A}}}.shadow{{fill:#000}}.fill,.plate{{fill:{BG}}}"
           f"text{{fill:{INK};font:{FS}px ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',"
           f"monospace;text-anchor:middle;white-space:pre}}")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" width="{W:g}" '
           f'height="{H:g}" role="img" data-cell="{CW}x{CH}" data-pad="{PAD}" '
           f'data-generator="ascii2svg {__version__}"><title>{html.escape(title)}</title>'
           f'<style>{css}</style><rect width="100%" height="100%" fill="{BG}"/>' + "".join(body) + "</svg>\n")
    return svg, {"boxes": len(boxes), "text_cells": len(texts), "arrowheads": len(heads)}


# ─── self-check: read the SVG back into a grid ───────────────────────────────
def read_back(svg: str) -> dict:
    """Rebuild {(r, c): char} using only what is in the SVG."""
    cw, chh = map(float, re.search(r'data-cell="([\d.]+)x([\d.]+)"', svg).groups())
    pad = float(re.search(r'data-pad="([\d.]+)"', svg).group(1))
    arms: dict = {}
    out: dict = {}

    def arm(r, c, st, a):
        arms.setdefault((r, c), {"s": set(), "d": set()})[st].add(a)

    for hx, cy, qx, qy, vx, vy, cls in re.findall(
            r'<path d="M([\d.]+) ([\d.]+)Q([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)" class="([^"]+)"/>', svg):
        if cls == "dbl-gap":
            continue
        hx, qx, qy, vy = map(float, (hx, qx, qy, vy))
        r, c, st = int((qy - pad) // chh), int((qx - pad) // cw), "d" if cls == "dbl" else "s"
        arm(r, c, st, "R" if hx > qx else "L")
        arm(r, c, st, "D" if vy > qy else "U")
    for x1, y1, x2, y2, cls in re.findall(
            r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" class="([^"]+)"/>', svg):
        x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
        if cls == "sgl shaft":
            if x1 == x2:
                col = int((x1 - pad) // cw)
                out[(round((y1 - pad) / chh) - (0 if y2 > y1 else 1), col)] = "▼" if y2 > y1 else "▲"
            else:
                row = int((y1 - pad) // chh)
                out[(row, round((x1 - pad) / cw) - (0 if x2 > x1 else 1))] = "▶" if x2 > x1 else "◀"
            continue
        if cls == "dbl-gap":
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
    for x, y, t in re.findall(r'<text x="([\d.]+)" y="([\d.]+)">(.*?)</text>', svg):
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


def connector_warnings(cells, nrows, ncols, limit=50):
    """Line ends that don't meet anything - usually a misaligned diagram."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    out = []
    for (r, c) in sorted(cells):
        t = get(r, c)
        if t not in ARMS:
            continue
        for a in sorted(ARMS[t]):
            dr, dc = DIRS[a]
            n, back = get(r + dr, c + dc), OPP[a]
            if n in ARMS:
                if back not in ARMS[n]:
                    out.append({"row": r + 1, "col": c + 1, "char": t, "issue": f"line toward {a} meets '{n}' which doesn't connect back"})
            elif n in HEADS:
                continue
            elif t in "─═" or (a == "U" and n.strip()):
                continue                                  # a line may end at text; a tree may hang from a label
            else:
                out.append({"row": r + 1, "col": c + 1, "char": t, "issue": f"line toward {a} ends in empty space"})
            if len(out) >= limit:
                return out
    return out


# ─── command line ────────────────────────────────────────────────────────────
HELP_EPILOG = """\
examples:
  cat diagram.txt | ascii2svg -o diagram.svg --json
  ascii2svg notes.md -o out.svg            # a ```fenced``` block is unwrapped automatically
  ascii2svg --text "$(cat d.txt)" --json   # no -o: the SVG markup is returned inside the JSON
  ascii2svg d.txt -o d.svg --png           # also writes d.png (needs: pip install cairosvg)

what gets drawn:
  Unicode lines ─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╪ and arrows ▼▲▶◀ are drawn as lines.
  ASCII + - | and v ^ < > are drawn only when they form a box or attach to one.
  Everything else (hyphens in words, a->b, user_id, markdown tables) stays text,
  in exactly the same cell. When unsure, it stays text.

exit codes:
  0 ok (warnings allowed)   1 bad input or usage   2 self-check failed (SVG not 1:1)
  3 --strict was given and there were warnings
"""


def build_parser():
    p = argparse.ArgumentParser(
        prog="ascii2svg", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=HELP_EPILOG,
        description="Render an ASCII/Unicode box diagram as SVG. Every character keeps its exact "
                    "position (1:1); a built-in check verifies this on every run.")
    p.add_argument("input", nargs="?", help="diagram file, or '-' for stdin (default: stdin)")
    p.add_argument("--text", help="the diagram itself, instead of a file or stdin")
    p.add_argument("-o", "--output", help="write the SVG here (default: stdout, or inside the JSON)")
    p.add_argument("--style", choices=["glow", "shadow", "flat"], default="glow",
                   help="box depth effect (default: glow)")
    p.add_argument("--square", action="store_true", help="keep box corners square")
    p.add_argument("--png", nargs="?", const="", metavar="PATH",
                   help="also write a PNG (default path: next to -o). Needs cairosvg")
    p.add_argument("--json", action="store_true", help="print a machine-readable report on stdout")
    p.add_argument("--strict", action="store_true", help="exit 3 if there are connector warnings")
    p.add_argument("--tab-size", type=int, default=4, help="tab stops for tab characters (default: 4)")
    p.add_argument("--title", default="ASCII diagram", help="accessible title stored in the SVG")
    p.add_argument("--max-rows", type=int, default=1000)
    p.add_argument("--max-cols", type=int, default=400)
    p.add_argument("--version", action="version", version=f"ascii2svg {__version__}")
    return p


def _read(args) -> tuple[str, list[dict]]:
    notes = []
    if args.text is not None:
        return args.text, notes
    if args.input and args.input != "-":
        try:
            data = open(args.input, "rb").read()
        except OSError as e:
            raise ValueError(f"cannot read {args.input}: {e.strerror}")
    else:
        if sys.stdin is None or sys.stdin.isatty():
            raise ValueError("no diagram given: pass a file, '-' with stdin, or --text")
        data = sys.stdin.buffer.read()
    text = data.decode("utf-8", errors="replace")
    if "\ufffd" in text and b"\xef\xbf\xbd" not in data:
        notes.append({"change": "invalid UTF-8 bytes replaced with \ufffd"})
    return text, notes


def run(args) -> tuple[int, dict, str]:
    """Core pipeline. Returns (exit_code, report, svg)."""
    text, notes = _read(args)
    lines, more = prepare(text, args.tab_size)
    notes += more
    if not lines:
        raise ValueError("the diagram is empty")
    cells, nrows, ncols = build_grid(lines)
    if nrows > args.max_rows or ncols > args.max_cols:
        raise ValueError(f"diagram is {nrows} rows x {ncols} columns; limit is {args.max_rows} x "
                         f"{args.max_cols} (raise with --max-rows / --max-cols)")
    drawn, info = interpret(cells, nrows, ncols)
    draw_cells = {k: ((drawn[k], w) if k in drawn else (t, w)) for k, (t, w) in cells.items()}
    svg, stats = render_svg(draw_cells, nrows, ncols, args.style, args.square, args.title)
    problems = self_check(svg, draw_cells, cells)
    warnings = connector_warnings(draw_cells, nrows, ncols)
    report = {"ok": not problems, "rows": nrows, "cols": ncols, "style": args.style,
              "boxes": stats["boxes"], "arrowheads": stats["arrowheads"], "text_cells": stats["text_cells"],
              **info, "roundtrip": "exact" if not problems else "MISMATCH",
              "normalized": notes, "warnings": warnings, "width_source": WIDTH_SOURCE,
              "version": __version__}
    if problems:
        report["self_check_problems"] = problems[:50]
        return 2, report, svg
    return (3 if args.strict and warnings else 0), report, svg


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    def fail(code, msg):
        if args.json:
            print(json.dumps({"ok": False, "error": msg, "exit_code": code}))
        else:
            print(f"ascii2svg: error: {msg}", file=sys.stderr)
        return code

    try:
        code, report, svg = run(args)
    except ValueError as e:
        return fail(1, str(e))
    if args.png is not None:
        if not args.output and not args.png:
            return fail(1, "--png needs a path when -o is not given")
        try:
            import cairosvg
        except ImportError:
            return fail(1, "--png needs cairosvg: pip install cairosvg")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(svg)
        report["svg"] = args.output
    if args.png is not None:
        png = args.png or re.sub(r"\.svg$", "", args.output) + ".png"
        cairosvg.svg2png(bytestring=svg.encode(), write_to=png, scale=2)
        report["png"] = png
    report["exit_code"] = code
    if args.json:
        if not args.output:
            report["svg"] = svg
        print(json.dumps(report, ensure_ascii=False))
    else:
        if not args.output:
            sys.stdout.write(svg)
        where = args.output or "stdout"
        print(f"ascii2svg: {where}  {report['rows']}x{report['cols']}  {report['boxes']} boxes  "
              f"style={report['style']}  round-trip={report['roundtrip']}  "
              f"warnings={len(report['warnings'])}", file=sys.stderr)
        if code == 2:
            print("ascii2svg: SELF-CHECK FAILED - the SVG does not match the input 1:1", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
