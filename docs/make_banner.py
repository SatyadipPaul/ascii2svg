"""Write docs/examples/banner.txt: the README banner, as plain text for ascii2svg to render.

A block-letter wordmark with a shaded drop shadow, and the pipeline it stands for underneath.
Everything in it is ordinary text: block elements, box lines and arrows.
"""
import os

FONT = {                     # 5 x 5 pixels per letter; each pixel is two cells wide, so it comes out square
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "S": [".####", "#....", ".###.", "....#", "####."],
    "C": [".####", "#....", "#....", "#....", ".####"],
    "I": ["#####", "..#..", "..#..", "..#..", "#####"],
    "2": ["####.", "....#", ".###.", "#....", "#####"],
    "V": ["#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "G": [".####", "#....", "#..##", "#...#", ".###."],
}


def wordmark(word, gap=1):
    rows = [""] * 5
    for i, ch in enumerate(word):
        for r in range(5):
            rows[r] += FONT[ch][r] + ("." * gap if i < len(word) - 1 else "")
    h, w = len(rows), len(rows[0])
    on = lambda r, c: 0 <= r < h and 0 <= c < w and rows[r][c] == "#"
    out = []
    for r in range(h + 1):                                     # one extra row for the shadow
        line = ""
        for c in range(w + 1):
            line += "██" if on(r, c) else "░░" if on(r - 1, c - 1) else "  "
        out.append(line.rstrip())
    return out


STEPS = [("your text diagram", "(or your AI's)", ""),
         ("ascii2svg", "repair · draw ·", "self-check"),
         ("SVG, exactly 1:1", "animated, light", "and dark")]
W = 20                                                         # inside width of each box


def pipeline():
    edge = lambda l, r: "        ".join(l + "─" * W + r for _ in STEPS)
    rows = [edge("┌", "┐")]
    for i in range(3):
        cells = ["│" + s[i].center(W) + "│" for s in STEPS]
        link = "├───────▶│" if i == 1 else "│        │"
        rows.append(cells[0][:-1] + link + cells[1][1:-1] + link + cells[2][1:])
    return rows + [edge("└", "┘")]


PIPE = pipeline()

if __name__ == "__main__":
    mark = wordmark("ASCII2SVG", gap=2)
    width = max(len(s) for s in mark + PIPE)
    block = lambda rows: [(" " * ((width - max(map(len, rows))) // 2) + s).rstrip() for s in rows]   # one offset per block
    lines = block(mark) + [""] + block(PIPE)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "banner.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(out)
