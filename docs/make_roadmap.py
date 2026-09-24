"""Write docs/examples/roadmap.txt: the README roadmap, as a text diagram for ascii2svg to render.

Shipped milestones snake through a solid container with arrows (flow pulses follow them); the
planned ones sit in a dashed container, reached by a dashed arrow. A block-character bar on top
shows how far along it is. Every line is placed by coordinates, so the result is aligned by
construction; edit the lists below and run this script, then docs/build.py.
"""
import os

SHIPPED = [("1.0 – 1.2 foundations", "boxes, arrows, 1:1", "colour · themes · motion"),
           ("1.3 agent CLI", "JSON reports · hints", "--describe · --schema"),
           ("1.4 everywhere", "browser playground", "MCP server · skill"),
           ("1.5 repair", "--repair for LLMs", "Fix alignment button"),
           ("1.6 – 1.7 shapes", "block charts, diamonds", "dashed lines"),
           ("1.8 – 1.12 notation", "UML, ER, curves, dashes", "arrows between words")]
NEXT = [("vertical ASCII", "UML heads"), ("bigger repairs", "(3+ cells off)"),
        ("JS / npm port", ""), ("Firefox, Safari", "and cairo checks")]


class Canvas:
    def __init__(self):
        self.arms, self.chars, self.dashed = {}, {}, set()

    def arm(self, r, c, d):
        self.arms.setdefault((r, c), set()).add(d)

    def h(self, r, c1, c2):
        for c in range(c1, c2 + 1):
            if c > c1:
                self.arm(r, c, "L")
            if c < c2:
                self.arm(r, c, "R")

    def v(self, c, r1, r2):
        for r in range(r1, r2 + 1):
            if r > r1:
                self.arm(r, c, "U")
            if r < r2:
                self.arm(r, c, "D")

    def text(self, r, c, s):
        for i, ch in enumerate(s):
            self.chars[(r, c + i)] = ch

    def box(self, r1, c1, r2, c2, lines=(), title=None, dashed=False, center=True):
        self.h(r1, c1, c2), self.h(r2, c1, c2), self.v(c1, r1, r2), self.v(c2, r1, r2)
        if dashed:                                     # the edges dash; corners and junctions stay solid
            self.dashed |= {(r, c) for r in (r1, r2) for c in range(c1 + 1, c2)}
            self.dashed |= {(r, c) for c in (c1, c2) for r in range(r1 + 1, r2)}
        if title:
            self.text(r1, c1 + 2, f" {title} ")
        inner = c2 - c1 - 1
        for i, s in enumerate(lines):
            assert len(s) <= inner - 2, (s, inner)
            self.text(r1 + 1 + i, c1 + 1 + ((inner - len(s)) // 2 if center else 1), s)

    def arrow(self, r1, c1, r2, c2, head):            # a straight run ending in an arrowhead cell
        (self.h(r1, c1, c2) if r1 == r2 else self.v(c1, r1, r2))
        self.chars[head[0]] = head[1]

    def render(self):
        solid = {"LR": "─", "DU": "│", "DR": "┌", "DL": "┐", "RU": "└", "LU": "┘", "DRU": "├", "DLU": "┤",
                 "DLR": "┬", "LRU": "┴", "DLRU": "┼", "L": "─", "R": "─", "U": "│", "D": "│"}
        cells = {}
        for k, a in self.arms.items():
            ch = solid["".join(sorted(a))]
            cells[k] = {"─": "╌", "│": "╎"}.get(ch, ch) if k in self.dashed else ch
        cells.update(self.chars)
        rows = max(r for r, _ in cells) + 1
        out = []
        for r in range(rows):
            width = max((c for rr, c in cells if rr == r), default=-1) + 1
            out.append("".join(cells.get((r, c), " ") for c in range(width)).rstrip())
        return "\n".join(out) + "\n"


def roadmap():
    k = Canvas()
    W, GAP, X0 = 28, 6, 3                               # box width, gap between boxes, left inset
    cols = [X0 + i * (W + GAP) for i in range(3)]
    right = cols[-1] + W - 1 + 3
    # progress: one block of bar per 1/24th, full blocks for what shipped
    done = len(SHIPPED) / (len(SHIPPED) + len(NEXT))
    bar = "█" * round(24 * done) + "░" * (24 - round(24 * done))
    k.text(0, 1, f"progress  {bar}  {len(SHIPPED)} shipped · {len(NEXT)} next")

    # shipped: a snake, left to right, then down, then right to left
    k.box(2, 0, 18, right, title="Shipped")
    order = [(4, c) for c in cols] + [(11, c) for c in cols[::-1]]
    for (r, c), (title, a, b) in zip(order, SHIPPED):
        k.box(r, c, r + 4, c + W - 1, [title, a, b])
    mid = 6
    for c in cols[:-1]:                                 # ──▶ between the top row
        k.arrow(mid, c + W - 1, mid, c + W + GAP - 2, ((mid, c + W + GAP - 1), "▶"))
    cx = cols[-1] + W // 2                              # down from the last top box
    k.arrow(8, cx, 9, cx, ((10, cx), "▼"))
    mid2 = 13
    for c in cols[1:][::-1]:                            # ◀── along the bottom row
        k.arrow(mid2, c - GAP + 1, mid2, c, ((mid2, c - GAP), "◀"))

    # next: dashed, reached by a dashed arrow from the last shipped milestone
    top = 21
    k.box(top, 0, top + 12, right, title="Next, in no particular order", dashed=True)
    nx = cols[0] + W // 2
    k.arrow(15, nx, top - 2, nx, ((top - 1, nx), "▼"))
    k.dashed |= {(r, nx) for r in range(16, top - 1) if r != 18}
    k.text(19, nx + 2, "next")
    for i, (a, b) in enumerate(NEXT):
        r = top + 2 + (i // 3) * 5
        k.box(r, cols[i % 3], r + 3, cols[i % 3] + W - 1, [a, b], dashed=True)

    k.text(top + 14, 1, "── shipped    ╌╌ planned    the arrows run in the order things shipped")
    return k.render()


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "roadmap.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(roadmap())
    print(out)
