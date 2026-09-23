"""Regenerate every image the README shows:  python3 docs/build.py"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "scripts", "ascii2svg.py")
LIVE = ["--theme", "auto", "--color", "--animate", "flow"]
IMAGES = [
    ("docs/examples/how-it-works.txt", "docs/how-it-works.svg", LIVE),
    ("docs/examples/workflow.txt", "docs/workflow.svg", LIVE),
    ("tests/fixtures/complex_unicode.txt", "docs/architecture.svg", LIVE),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/default.svg", []),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/color.svg", ["--color"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/dark.svg", ["--theme", "dark", "--color"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/flat.svg", ["--style", "flat", "--square"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/flow.svg", LIVE),
]

os.makedirs(os.path.join(ROOT, "docs", "looks"), exist_ok=True)
for src, out, args in IMAGES:
    code = subprocess.call([sys.executable, CLI, os.path.join(ROOT, src), "-o", os.path.join(ROOT, out), *args])
    if code:
        sys.exit(f"{src}: exit {code}")
