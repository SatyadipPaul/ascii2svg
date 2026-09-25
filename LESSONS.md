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
| 9 | Prompting / skills | Re-test fixed guidance on a *different* request than the one that exposed the gaps (the old one is now a copyable recipe). Compare warnings on the first check and misleading content in the final version, not only whether the final passes. |
| 10 | Testing | A test that starts a Python process and reads its output must set `PYTHONIOENCODING=utf-8` and decode the bytes itself: Windows consoles default to cp1252, which can't encode box-drawing characters. Reproduce locally with `PYTHONIOENCODING=cp1252`. |
| 11 | Release | Dry-run a release exactly as the workflow runs it: same order (tests, then build), same folders (`dist/`), same commands (`twine check dist/*`). Building into a separate folder hid that a test left a file in `dist/`, and the real publish failed on it. Tests must never write into build output folders. |
| 12 | Docs / launch | When a feature ships, list every place a visitor first meets the project (landing page, README top, playground picker, npm page, skill) and check each one shows it. The 1.16 folding trees were in the README and playground but not on the website's front page. Also prove "it's interactive" with a real click in a browser, clicking where a user would click. |
| 13 | Interactivity | Look at the *folded* state of every tree shape, not only the open one, and not only counts of visible labels. A `┬` joint left a stub under a folded `npm ls` branch through a whole release, because the tests counted labels and the screenshots showed trees open. |
| 14 | Testing / browser | When a browser check says "nothing happened", look at the screenshot before blaming the product. Twice the test clicked in the wrong place: frame element boxes are already page coordinates, and on a phone the result sits below the fold (scroll it into view first). |
| 15 | Web / mobile | Measure horizontal scroll at phone width on every page touched, and compare with `main` to tell old bugs from new. The playground's example picker pushed a 390 px page sideways before this change; it had never been measured. |
