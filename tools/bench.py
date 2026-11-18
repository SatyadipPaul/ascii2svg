#!/usr/bin/env python3
"""Speed benchmark: ascii2svg against an earlier version of itself.

    python tools/bench.py                 # this checkout against main
    python tools/bench.py --base v1.17.0  # against any git revision
    python tools/bench.py --base v1.17.0 --quick --min-speedup 1.5   # CI: fail on a slow-down

Every case runs several times; the best time counts (the least disturbed by the machine).
Both versions run on the same machine in the same run, so the ratio holds on any CI runner where a
fixed time budget would not. The outputs are compared too: a speed-up that changes a drawing fails."""
from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def grid(rows, cols):
    """A synthetic diagram: rows x cols boxes, each with an arrow to its right-hand neighbour."""
    box = ["┌────────┐   ", "│ node   │──▶", "└────────┘   "]
    return "\n".join("".join(b for _ in range(cols)) for _ in range(rows) for b in box)


def best(fn, repeat):
    times = []
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return min(times)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="main", help="git revision to compare against (default: main)")
    p.add_argument("--repeat", type=int, default=5)
    p.add_argument("--min-speedup", type=float, metavar="X",
                   help="exit 1 if the typical diagrams are not X times as fast as --base, or any output differs")
    p.add_argument("--quick", action="store_true", help="skip the large synthetic diagrams")
    a = p.parse_args()

    new = load(os.path.join(ROOT, "scripts", "ascii2svg.py"), "a2s_new")
    old = None
    try:
        src = subprocess.run(["git", "show", f"{a.base}:scripts/ascii2svg.py"], cwd=ROOT,
                             capture_output=True, check=True).stdout
        with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as f:
            f.write(src)
        old = load(f.name, "a2s_old")
        os.unlink(f.name)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"(no git revision {a.base!r}: timing this checkout only)")

    files = sorted(glob.glob(os.path.join(ROOT, "tests", "fixtures", "*.txt"))
                   + glob.glob(os.path.join(ROOT, "docs", "examples", "*.txt")))
    texts = [open(f, encoding="utf-8").read() for f in files]
    cases = [(f"{len(texts)} typical diagrams, default look", texts, {}),
             (f"{len(texts)} typical diagrams, preset readme", texts, {"preset": "readme"}),
             (f"{len(texts)} typical diagrams, repair + describe", texts, {"repair": True, "describe": True})]
    if not a.quick:
        for r, c in ((10, 16), (40, 30)):
            cases.append((f"{r * c} boxes, render", [grid(r, c)], {}))
            cases.append((f"{r * c} boxes, repair + describe", [grid(r, c)], {"repair": True, "describe": True}))

    def run(mod, inputs, kw):
        return [mod.render(t, **kw) for t in inputs]

    print(f"{'case':44} {'before':>10} {'after':>10} {'faster':>8}  same output")
    failed = []
    for label, inputs, kw in cases:
        run(new, inputs[:2], kw)                            # warm caches the same way for both
        if old is None:
            t_new = best(lambda: run(new, inputs, kw), a.repeat)
            print(f"{label:44} {'':>10} {t_new * 1000:8.1f}ms")
            continue
        run(old, inputs[:2], kw)
        t_new = t_old = float("inf")
        for _ in range(a.repeat):                           # taking turns: both meet the same machine noise
            t_old = min(t_old, best(lambda: run(old, inputs, kw), 1))
            t_new = min(t_new, best(lambda: run(new, inputs, kw), 1))
        stamp = lambda svg: re.sub(r'data-generator="ascii2svg [^"]*"', "", svg)   # the version stamp differs
        same = all(stamp(x[0]) == stamp(y[0]) and {k: v for k, v in x[1].items() if k != "version"}
                   == {k: v for k, v in y[1].items() if k != "version"}
                   for x, y in zip(run(new, inputs, kw), run(old, inputs, kw)))
        print(f"{label:44} {t_old * 1000:8.1f}ms {t_new * 1000:8.1f}ms {t_old / t_new:7.1f}x  {'yes' if same else 'NO'}")
        if a.min_speedup and (not same or ("typical" in label and t_old / t_new < a.min_speedup)):
            failed.append(label)
    if a.min_speedup and old is None:
        print(f"cannot check --min-speedup without {a.base!r}")
        return 1
    for label in failed:
        print(f"FAIL: {label} (needs {a.min_speedup}x and the same output)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
