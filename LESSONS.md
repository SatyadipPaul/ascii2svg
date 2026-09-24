# Lessons

How to look next time. Each lesson is about where to look, not whom to trust.

| # | Field | Lesson |
|---|---|---|
| 1 | Product / dev tools | When a feature list says "X stays as-is, to be safe" (here: `\|--` file trees, `tree` output), check whether X is also a use case worth supporting, not only a trap to avoid. Run the real outputs people already have (`tree`, `npm ls`, `git log --graph`) through the tool and read what it *understands*, not just what it draws. |
| 2 | Product / dev tools | Test structure, not just pixels: a diagram can render 1:1 and still be understood wrongly. Here the mind-map fan-out drew perfectly but `--describe` found 1 of its 3 links and none of its 9 leaves. |
| 3 | Rendering / SVG | When the output's structure changes, check it in every renderer it goes to (browser, cairosvg for PNG, design tools), not only the browser. A test that only checks "the PNG file exists" hides a broken PNG: text runs looked perfect in Chromium and were scrambled in cairosvg. |
| 4 | Product / dev tools | Before styling or changing behaviour on a new detector, run it over every existing fixture and example and list what it catches. Here the tree detector matched the README's flagship architecture diagram and two timelines. |
| 5 | Testing | Test with realistic data, not clean samples: real call trees carry notes (`× 3`, `312 ms`) after labels, and those kept folded rows open. |
| 6 | Testing | After adding tests, check the pass count went up. Tests appended after the file's `__main__` runner never ran, and the suite still printed "all passed". |
| 7 | Prompting / skills | Test guidance on a fresh model before calling it done. Examples it copies verbatim work; the gaps show where it has to improvise (merges, lifelines, sizing), and where it takes shortcuts to silence a warning (dropping a leader, cutting a question to "has ?"). |
| 8 | Diagrams | "The check passes" proves the drawing is exact, not that it is true. Review for meaning too: numbers to scale, notes on their subject, labels that don't cut lines, full-height lifelines. |
