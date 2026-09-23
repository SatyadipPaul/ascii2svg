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

__version__ = "1.1.0"

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


def flow_paths(get, heads, boxes, line_like, limit=200):
    """Every route that ends in an arrowhead, as points from its source to the tip.

    Walks backwards from each arrowhead along connector lines. A route starts at a box
    edge (or where the line begins in open space); branches that lead into another
    arrowhead are dropped. A ┼ / ╪ is a crossing: the route goes straight through,
    which is also how a connector passes through a box edge."""
    border = set()
    for r1, c1, r2, c2 in boxes:
        border.update((r, c) for r in (r1, r2) for c in range(c1, c2 + 1))
        border.update((r, c) for c in (c1, c2) for r in range(r1, r2 + 1))
    centre = lambda r, c: (PAD + c * CW + CW / 2, PAD + r * CH + CH / 2)
    out = []
    for r, c, d in heads:
        tip = head_geometry(r, c, d, line_like)[2]
        stack = [((r, c), OPP[d], [(r, c)])]
        while stack and len(out) < limit:
            (cr, cc), step, seq = stack.pop()
            n = (cr + DIRS[step][0], cc + DIRS[step][1])
            t, back = get(*n), OPP[step]
            if t in HEADS:
                continue                                        # leads into another arrow: not a source
            if t not in ARMS or back not in ARMS[t] or n in seq:
                if len(seq) > 1:                                # line starts in open space
                    x, y = centre(*seq[-1])
                    start = (x + DIRS[step][1] * CW / 2, y + DIRS[step][0] * CH / 2)
                    out.append([start] + [centre(*k) for k in reversed(seq)] + [tip])
                continue
            seq = seq + [n]
            crossing = len(ARMS[t]) == 4                       # ┼ ╪: lines pass straight through
            if n in border and not crossing:
                out.append([centre(*k) for k in reversed(seq)] + [tip])   # starts on a box edge
                continue
            for a in ([step] if crossing else sorted(ARMS[t] - {back}, reverse=True)):
                stack.append((n, a, seq))
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


def _layout_css(mode):
    """mode: none | timed (plays on load) | scroll (a host page adds .a2s-on as things scroll into view)."""
    css = (".sgl{stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".dbl{stroke-width:5;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".dbl-gap{stroke-width:2;stroke-linecap:round;stroke-linejoin:round;fill:none}"
           ".head{stroke-width:1;stroke-linejoin:round}"
           f"text{{font:{FS}px ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
           "text-anchor:middle;white-space:pre}"
           ".fill{transition:fill .25s}text,line,path,polygon{pointer-events:none}")
    if mode == "none":
        return css
    on = ".a2s-on" if mode == "scroll" else ""
    sel = lambda *names: ",".join(f"{on}{n}" if n.startswith(".") else f"{n}{on}" for n in names)
    ease = "cubic-bezier(.3,.7,.4,1)"
    css += ("@keyframes a2s-gap{0%{stroke-dasharray:1 2;stroke-dashoffset:1.01}"
            "60%,100%{stroke-dasharray:1 2;stroke-dashoffset:0}}"
            "@keyframes a2s-fade{0%{opacity:0}}"
            "@keyframes a2s-pop{0%{opacity:0;transform:scale(.2)}}"
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


def _colour_css(t, color, anim):
    acc = t["accent"]
    css = (f".bg,.fill,.plate{{fill:{t['bg']}}}.sgl,.dbl{{stroke:{t['ink']}}}.dbl-gap{{stroke:{t['bg']}}}"
           f".head{{fill:{t['ink']};stroke:{t['ink']}}}text{{fill:{t['ink']}}}"
           f".glow{{fill:{t['glow']};fill-opacity:{t['glow_a']}}}.shadow{{fill:#000}}")
    if color:
        css += (f".shaft{{stroke:{acc}}}.head{{fill:{acc};stroke:{acc}}}.fill.tn{{fill:{t['neutral']}}}"
                + "".join(f".fill.t{i}c{{fill:{a}}}.fill.t{i}l{{fill:{b}}}" for i, (a, b) in enumerate(t["hues"])))
    css += f".fill:hover{{fill:{t['hover']}}}"
    if anim:   # lines are sketched in the accent colour, then settle to ink
        css += (f"@keyframes a2s-draw{{0%{{stroke-dasharray:1 2;stroke-dashoffset:1.01;stroke:{acc}}}"
                f"60%{{stroke-dasharray:1 2;stroke-dashoffset:0;stroke:{acc}}}"
                f"100%{{stroke-dasharray:1 2;stroke-dashoffset:0}}}}.pulse circle{{fill:{acc}}}"
                f".a2s-live.sgl,.a2s-live.dbl{{stroke:{acc}}}")
    return css


def render_svg(cells, nrows, ncols, style="glow", square=False, title="ASCII diagram",
               theme="light", color=False, animate="none"):
    """cells: {(r, c): (text, width)} where line cells already hold Unicode line characters.

    Animation only ever starts from an earlier state and ends on the static drawing, so a
    renderer that ignores CSS/SMIL animation shows exactly what the self-check verified."""
    get = lambda r, c: cells.get((r, c), (" ", 1))[0]
    segs = {"s": {"h": {}, "v": {}}, "d": {"h": {}, "v": {}}}
    curves, heads, texts = [], [], []
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
    is_text = lambda t: t not in (" ", "") and t not in ARMS and t not in HEADS
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

    body = under + lines("d", "dbl") + lines("d", "dbl-gap") + lines("s", "sgl")
    line_like = lambda r, c: get(r, c) in ARMS
    for r, c, d in heads:
        sh, pts, _ = head_geometry(r, c, d, line_like)
        tm = timing(PAD + r * CH + 0.15 * speed)
        body.append('<line x1="%g" y1="%g" x2="%g" y2="%g" class="sgl shaft"%s/>' % (*sh, tm))
        body.append('<polygon points="%s" class="head"%s/>' % (" ".join(f"{x:g},{y:g}" for x, y in pts), tm))
    for r, c, w, t in texts:                         # one delay per row (a class), not per character
        body.append(f'<text x="{PAD + c * CW + w * CW / 2:g}" y="{PAD + r * CH + CH / 2 + 5:g}"'
                    f'{f" class=\"r{r}\"" if timed else ""}>{html.escape(t, quote=False)}</text>')
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

    pal = THEMES["light" if theme == "auto" else theme]
    css = _layout_css("timed" if timed else animate if anim else "none") + rows_css + _colour_css(pal, color, anim)
    if theme == "auto":
        css += "@media (prefers-color-scheme:dark){" + _colour_css(THEMES["dark"], color, anim) + "}"
    W, H = ncols * CW + 2 * PAD, nrows * CH + 2 * PAD
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" width="{W:g}" '
           f'height="{H:g}" role="img" data-cell="{CW}x{CH}" data-pad="{PAD}" '
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
  const grow = [], show = q('path.sgl,path.dbl,path.dbl-gap,.shaft,.head,text,.glow,.shadow,.fill,.plate');
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
  ascii2svg d.txt -o d.svg --theme auto --color --animate flow   # for a GitHub README
  ascii2svg d.txt -o d.html --color --animate scroll            # a page that reveals as you scroll

looks (all optional, and all keep the 1:1 guarantee):
  --theme light|dark|auto   auto follows the viewer's light/dark setting
  --color                   tint boxes by group, colour the arrows
  --animate draw            the diagram draws itself once, top to bottom
  --animate flow            ...then pulses keep travelling along every arrow
  --animate scroll          web page only: parts appear as the reader scrolls to them,
                            long connectors grow with the scroll (best for tall diagrams)
  --html / -o NAME.html     write a standalone web page with the diagram inline
  Viewers without animation support show the finished drawing. PNG output is
  always the finished drawing (auto theme -> light).

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
    p.add_argument("--theme", choices=["light", "dark", "auto"], default="light",
                   help="colours; auto follows the viewer's light/dark setting (default: light)")
    p.add_argument("--color", action="store_true", help="tint boxes by group and colour the arrows")
    p.add_argument("--animate", nargs="?", const="flow", choices=list(ANIMATIONS), default="none",
                   help="draw: the diagram draws itself; flow: draw, then pulses travel along the "
                        "arrows (bare --animate = flow); scroll: web page that reveals as you scroll")
    p.add_argument("--png", nargs="?", const="", metavar="PATH",
                   help="also write a PNG (default path: next to -o). Needs cairosvg")
    p.add_argument("--html", action="store_true",
                   help="write a standalone web page (implied by -o NAME.html); needed for --animate scroll")
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


def run(args) -> tuple[int, dict, str, str]:
    """Core pipeline. Returns (exit_code, report, svg, static_svg_for_png)."""
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
    svg, stats = render_svg(draw_cells, nrows, ncols, args.style, args.square, args.title,
                            args.theme, args.color, args.animate)
    problems = self_check(svg, draw_cells, cells)
    still = svg
    if args.png is not None and (args.animate != "none" or args.theme == "auto"):
        still = render_svg(draw_cells, nrows, ncols, args.style, args.square, args.title,
                           "light" if args.theme == "auto" else args.theme, args.color)[0]
        problems += self_check(still, draw_cells, cells)
    warnings = connector_warnings(draw_cells, nrows, ncols)
    report = {"ok": not problems, "rows": nrows, "cols": ncols, "style": args.style, "theme": args.theme,
              "color": args.color, "animate": args.animate,
              "boxes": stats["boxes"], "arrowheads": stats["arrowheads"], "flows": stats["flows"],
              "text_cells": stats["text_cells"],
              **info, "roundtrip": "exact" if not problems else "MISMATCH",
              "normalized": notes, "warnings": warnings, "tips": [], "width_source": WIDTH_SOURCE,
              "version": __version__}
    if nrows > 45 and args.animate in ("draw", "flow") and not args.html:
        report["tips"].append("tall diagram: the lower part finishes drawing before the reader scrolls "
                              "to it; for a web page use --animate scroll -o NAME.html")
    if problems:
        report["self_check_problems"] = problems[:50]
        return 2, report, svg, still
    return (3 if args.strict and warnings else 0), report, svg, still


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):              # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    args.html = args.html or bool(args.output and args.output.lower().endswith((".html", ".htm")))

    def fail(code, msg):
        if args.json:
            print(json.dumps({"ok": False, "error": msg, "exit_code": code}))
        else:
            print(f"ascii2svg: error: {msg}", file=sys.stderr)
        return code

    if args.animate == "scroll" and not args.html:
        return fail(1, "--animate scroll needs a web page: add --html or use -o NAME.html "
                       "(an SVG shown as an image can't see the page scroll)")
    try:
        code, report, svg, still = run(args)
    except ValueError as e:
        return fail(1, str(e))
    if args.png is not None:
        if not args.output and not args.png:
            return fail(1, "--png needs a path when -o is not given")
        try:
            import cairosvg
        except ImportError:
            return fail(1, "--png needs cairosvg: pip install cairosvg")
    kind = "html" if args.html else "svg"
    out = to_html(svg, args.title, args.theme) if args.html else svg
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:   # same bytes on every OS
            f.write(out)
        report[kind] = args.output
    if args.png is not None:
        png = args.png or re.sub(r"\.(svg|html?)$", "", args.output, flags=re.I) + ".png"
        cairosvg.svg2png(bytestring=still.encode(), write_to=png, scale=2)
        report["png"] = png
    report["exit_code"] = code
    if args.json:
        if not args.output:
            report[kind] = out
        print(json.dumps(report, ensure_ascii=False))
    else:
        if not args.output:
            sys.stdout.write(out)
        where = args.output or "stdout"
        print(f"ascii2svg: {where}  {report['rows']}x{report['cols']}  {report['boxes']} boxes  "
              f"style={report['style']}  theme={report['theme']}  animate={report['animate']}  "
              f"round-trip={report['roundtrip']}  "
              f"warnings={len(report['warnings'])}", file=sys.stderr)
        if code == 2:
            print("ascii2svg: SELF-CHECK FAILED - the SVG does not match the input 1:1", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
