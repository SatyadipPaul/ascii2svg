# Lessons

How to look next time. Each lesson is about where to look, not whom to trust.

| # | Field | Lesson |
|---|---|---|
| 1 | Product / dev tools | When a feature list says "X stays as-is, to be safe" (here: `\|--` file trees, `tree` output), check whether X is also a use case worth supporting, not only a trap to avoid. Run the real outputs people already have (`tree`, `npm ls`, `git log --graph`) through the tool and read what it *understands*, not just what it draws. |
| 2 | Product / dev tools | Test structure, not just pixels: a diagram can render 1:1 and still be understood wrongly. Here the mind-map fan-out drew perfectly but `--describe` found 1 of its 3 links and none of its 9 leaves. |
