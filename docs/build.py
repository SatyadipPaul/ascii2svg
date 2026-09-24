"""Regenerate every image the README shows, and the playground's files:  python3 docs/build.py"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "scripts", "ascii2svg.py")
LIVE = ["--theme", "auto", "--color", "--animate", "flow"]
IMAGES = [
    ("docs/examples/banner.txt", "docs/banner.svg",       # docs/make_banner.py writes it; static, so it
     ["--theme", "auto", "--color", "--title", "ascii2svg"]),  # shows even where animation never starts
    ("docs/examples/timeline.txt", "docs/timeline.svg", LIVE + ["--title", "ascii2svg, release by release"]),  # make_timeline.py
    ("docs/examples/roadmap.txt", "docs/roadmap.svg", LIVE + ["--title", "ascii2svg roadmap"]),   # docs/make_roadmap.py
    ("docs/examples/how-it-works.txt", "docs/how-it-works.svg", LIVE),
    ("docs/examples/workflow.txt", "docs/workflow.svg", LIVE),
    ("tests/fixtures/complex_unicode.txt", "docs/architecture.svg", LIVE),
    ("tests/fixtures/complex_unicode.txt", "docs/architecture.html",
     ["--theme", "auto", "--color", "--animate", "scroll", "--title", "Order platform architecture"]),
    ("docs/examples/llm-output.txt", "docs/llm-before.svg", ["--theme", "auto", "--color"]),
    ("docs/examples/llm-output.txt", "docs/llm-after.svg", ["--theme", "auto", "--color", "--repair"]),
    ("docs/examples/decision-flow.txt", "docs/decision-flow.svg", LIVE + ["--title", "Checkout decision flow"]),
    ("docs/examples/pivot-table.txt", "docs/pivot-table.svg", ["--theme", "auto", "--color", "--title", "Revenue pivot"]),
    ("docs/examples/swimlanes.txt", "docs/swimlanes.svg", LIVE + ["--title", "Incident response swimlanes"]),
    ("docs/examples/mermaid/flowchart-decision.txt", "docs/diamond-flow.svg", LIVE + ["--title", "Sign-up decision"]),
    ("docs/examples/mermaid/gantt.txt", "docs/gantt.svg",
     ["--theme", "auto", "--color", "--animate", "draw", "--title", "Release plan"]),
    ("docs/examples/mermaid/class.txt", "docs/uml-class.svg", ["--theme", "auto", "--color", "--title", "Class diagram"]),
    ("tests/fixtures/er_crowsfoot.txt", "docs/er.svg", ["--theme", "auto", "--color", "--title", "Orders ER diagram"]),
    ("docs/examples/mermaid/c4-dashed-boundary.txt", "docs/c4.svg", LIVE + ["--title", "C4 container view"]),
    ("docs/examples/mermaid/state.txt", "docs/state.svg", LIVE + ["--title", "Publishing states"]),
    ("docs/examples/cache-sequence.txt", "docs/cache-sequence.svg", LIVE + ["--title", "Cache lookup"]),
    ("docs/examples/mermaid/sequence.txt", "docs/sequence.svg", LIVE + ["--title", "Create an order"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/default.svg", []),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/color.svg", ["--color"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/dark.svg", ["--theme", "dark", "--color"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/flat.svg", ["--style", "flat", "--square"]),
    ("tests/fixtures/ascii_fanout.txt", "docs/looks/flow.svg", LIVE),
]
# playground: name shown in the picker -> source file (or the text itself)
EXAMPLES = [
    ("LLM output: press Fix alignment", "docs/examples/llm-output.txt"),
    ("Checkout: flow, decision tree, flow", "docs/examples/decision-flow.txt"),
    ("Pivot table with a callout", "docs/examples/pivot-table.txt"),
    ("Incident swimlanes", "docs/examples/swimlanes.txt"),
    ("Sequence into a decision, back to a reply", "docs/examples/cache-sequence.txt"),
    ("Roadmap: timeline into mind maps", "docs/examples/roadmap-tree.txt"),
    ("Mermaid-style: flowchart with a decision", "docs/examples/mermaid/flowchart-decision.txt"),
    ("Mermaid-style: sequence", "docs/examples/mermaid/sequence.txt"),
    ("Mermaid-style: class", "docs/examples/mermaid/class.txt"),
    ("UML: composition, aggregation, realization", "tests/fixtures/uml.txt"),
    ("UML in plain ASCII: <|  <>  *", "tests/fixtures/uml_ascii.txt"),
    ("Dashed and dotted ASCII lines", "tests/fixtures/dashed_ascii.txt"),
    ("Rounded ASCII corners and bends: .--.  '--'", "tests/fixtures/rounded_ascii.txt"),
    ("ER diagram with crow's feet", "tests/fixtures/er_crowsfoot.txt"),
    ("Mermaid-style: state", "docs/examples/mermaid/state.txt"),
    ("Mermaid-style: C4 with a dashed boundary", "docs/examples/mermaid/c4-dashed-boundary.txt"),
    ("Mermaid-style: mind map", "docs/examples/mermaid/mindmap-tree.txt"),
    ("Mermaid-style: kanban", "docs/examples/mermaid/kanban.txt"),
    ("Mermaid-style: git graph", "docs/examples/mermaid/gitgraph.txt"),
    ("Mermaid-style: user journey", "docs/examples/mermaid/journey-table.txt"),
    ("Mermaid-style: timeline", "docs/examples/mermaid/timeline.txt"),
    ("Mermaid-style: Gantt", "docs/examples/mermaid/gantt.txt"),
    ("Mermaid-style: bar chart", "docs/examples/mermaid/bar-chart.txt"),
    ("Mermaid-style: XY line chart", "docs/examples/mermaid/xy-line-chart.txt"),
    ("Mermaid-style: quadrant", "docs/examples/mermaid/quadrant.txt"),
    ("Release timeline", "docs/examples/timeline.txt"),
    ("This project's roadmap", "docs/examples/roadmap.txt"),
    ("Workflow (plain ASCII)", "docs/examples/workflow.txt"),
    ("How ascii2svg works", "docs/examples/how-it-works.txt"),
    ("Fan-out (plain ASCII)", "tests/fixtures/ascii_fanout.txt"),
    ("Architecture (72 rows)", "tests/fixtures/complex_unicode.txt"),
    ("Misaligned: see a hint", "+---------+     +---------+\n|  web    |---->|  api    |\n+----+----+     +---------+\n"
                               "     |\n      v\n+---------+\n|   db    |\n+---------+\n"),
]

os.makedirs(os.path.join(ROOT, "docs", "looks"), exist_ok=True)
for src, out, args in IMAGES:
    code = subprocess.call([sys.executable, CLI, os.path.join(ROOT, src), "-o", os.path.join(ROOT, out), *args])
    if code:
        sys.exit(f"{src}: exit {code}")

play = os.path.join(ROOT, "docs", "playground")
os.makedirs(play, exist_ok=True)
shutil.copyfile(CLI, os.path.join(play, "ascii2svg.py"))            # the exact released module
examples = {}
for name, src in EXAMPLES:
    path = os.path.join(ROOT, src)
    examples[name] = open(path, encoding="utf-8").read() if os.path.exists(path) else src
with open(os.path.join(play, "examples.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(examples, f, ensure_ascii=False, indent=1)
    f.write("\n")
