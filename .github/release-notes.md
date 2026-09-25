# 1.17.0: paste any text tree, and it folds

Paste what `tree`, `npm ls`, `cargo tree`, `pipdeptree`, `mvn dependency:tree`, `gradle dependencies`, `pstree` or Windows `tree` print, exactly as printed, and get a tree whose branches fold, with a colour per branch. No JSON, no special syntax.

```bash
pip install -U ascii2svg
npm install @satyadip28/asciitosvg@1.17.0
```

## New

- **Maven trees.** `mvn dependency:tree` output (`+- name`, `\- name`, with or without the `[INFO]` prefix) is now read as a tree. The one-dash branch counts only after `+` or `\`, so text such as `|- x` or `a +- b` stays text.
- **Playground: paste any text tree.** A new picker group has 9 real outputs from 8 tools. Pasting a tree, or picking one of these examples, turns on Fold and Colour by itself, with a short note; typing, flowcharts and shared links are left as they are. [Try it](https://satyadippaul.github.io/ascii2svg/playground.html).
- **Website:** the front page shows a mind map you can fold right on the page.

## Fixed

- **No stub left behind when an `npm ls` branch folds.** In `├─┬ express`, the `┬` stays on express's row, but its stroke down to express's children now folds away with them.
- **Playground on phones:** the example picker no longer makes the page scroll sideways.

79 tests over 43 test diagrams, plus the npm package's parity tests (every render byte-identical to Python). CI covers Python 3.9–3.13 and Node 20/24 on Linux, Windows and macOS.
