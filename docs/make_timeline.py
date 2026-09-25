"""Write docs/examples/timeline.txt: the release timeline for the README, as a text diagram.

A vertical spine with a box for each release, newest at the top. Each release reaches out to one
side with a dotted leader that ends in a diamond marker under its label; the sides alternate. What's
planned sits above, dashed, with hollow markers. Edit RELEASES / NEXT and run this script, then
docs/build.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_roadmap import Canvas  # noqa: E402

TITLE = "ascii2svg, release by release"
RELEASES = [  # oldest first: (version, side, label lines, leader length)
    ("1.0", "R", ["first release: CLI,", "Claude skill, 1:1 check"], 14),
    ("1.1", "L", ["colour, light / dark,", "draw and flow animation"], 10),
    ("1.2", "R", ["on PyPI, library API,", "MIT licence"], 22),
    ("1.3", "L", ["agent CLI: JSON reports,", "hints, --describe"], 18),
    ("1.4", "R", ["browser playground,", "MCP server"], 10),
    ("1.5", "L", ["--repair for", "LLM-drawn diagrams"], 24),
    ("1.6", "R", ["block charts, diagonals,", "diamonds"], 18),
    ("1.7", "L", ["dashed lines,", "dashed boxes"], 12),
    ("1.8", "R", ["UML heads,", "ER crow's feet"], 24),
    ("1.9", "L", ["ER crow's feet", "running up and down"], 14),
    ("1.10", "R", ["ASCII UML heads <|  <>  *,", "dashed  - - ->  and dotted  ...>"], 16),
    ("1.11", "L", ["ASCII rounded corners", "and rounded bends"], 14),
    ("1.12", "R", ["arrows between plain words,", "labels set into lines"], 16),
    ("1.13", "L", ["ASCII UML heads up and down:", "/_\\   <>   *"], 12),
    ("1.14", "R", ["bigger repairs: boxes grow,", "split lines join up"], 16),
    ("1.15", "L", ["on npm: the same module", "in WebAssembly"], 14),
    ("1.16", "R", ["trees and mind maps fold,", "SVGs half the size"], 14),
]
NEXT = [("R", ["your idea next?", "open an issue"], 16)]
S = 44                                    # the spine's column
HALF = 4                                  # a version box spans S-HALF .. S+HALF


def event(k, row, side, lines, length, dashed=False):
    """A leader from the box wall at `row`, a marker at its end, the label centred above it."""
    lead = "╌" if dashed else "┈"
    mark = "◇" if dashed else "◆"                   # joined by the leader, so drawn as a diamond on it
    if side == "R":
        start = S + HALF + 1
        end = start + length
        k.text(row, start, lead * (end - start))
        k.chars[(row, end)] = mark
        k.arm(row, S + HALF, "R")                      # the wall becomes ├
    else:
        end = S - HALF - 1
        start = end - length
        k.chars[(row, start)] = mark
        k.text(row, start + 1, lead * (end - start))
        k.arm(row, S - HALF, "L")                      # the wall becomes ┤
    mc = end if side == "R" else start
    for i, s in enumerate(lines):                      # label rows sit just above the leader
        c = mc - len(s) // 2
        c = max(c, S + HALF + 2) if side == "R" else min(c, S - HALF - 2 - len(s))
        k.text(row - len(lines) + i, c, s)


def timeline():
    k = Canvas()
    k.text(0, S - len(TITLE) // 2, TITLE)
    # the future: an arrowhead, a dashed spine, a dashed "next" box
    k.chars[(2, S)] = "▲"
    k.v(S, 3, 6)
    k.dashed |= {(r, S) for r in range(3, 6)}
    k.box(6, S - HALF, 8, S + HALF, ["next"], dashed=True)
    for side, lines, length in NEXT:
        event(k, 7, side, lines, length, dashed=True)
    # releases, newest first, each box joined to the next by the spine
    row = 8
    for version, side, lines, length in reversed(RELEASES):
        top = row + 3
        k.v(S, row, top)                               # spine from the box above into this one,
        k.chars[(row + 1, S)] = "▲"                    # pointing up: pulses run from old to new
        k.box(top, S - HALF, top + 2, S + HALF, [version])
        event(k, top + 1, side, lines, length)
        row = top + 2
    k.v(S, row, row + 2)
    k.chars[(row + 1, S)] = "▲"
    k.chars[(row + 3, S)] = "●"                        # where it all started
    return k.render()


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "timeline.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(timeline())
    print(out)
