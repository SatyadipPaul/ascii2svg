# 1.16.1: trees that fold, SVGs half the size, a skill that composes the whole picture

Trees and mind maps that fold, SVGs half the size, and a skill that composes the whole picture. This is the first published release of the 1.16 work: the 1.16.0 build stopped before uploading anything, so this release carries all of it.

```bash
pip install -U ascii2svg
npm install @satyadip28/asciitosvg@1.16.1
```

## New in 1.16

- **Trees and mind maps that fold.** Call trees, file trees, `npm ls` / `cargo tree` output, left-to-right mind maps and boxes fanning out are read as a hierarchy. With `--interactive` (or `--preset explore`), click a node, or Tab to it and press Enter, to fold its branch; Shift folds the whole branch, and rows left empty close up. `--fold N` starts folded at depth N. As an `<img>` (GitHub, most docs sites) it is the full, self-checked drawing. [Open the example](https://satyadippaul.github.io/ascii2svg/mindmap.svg).
- **A colour per branch.** `--color` on a tree with no arrows gives each main branch its own colour, tinted pills for the main labels, and the root on a dark pill; boxes take their branch's tint.
- **ASCII trees** as `tree` and `cargo tree` print them (`|--`, `` `-- ``) are drawn as lines. Markdown tables and look-alikes stay text.
- **`--describe` reports the tree** (`diagram.tree`) and every parent → child as a `branch` edge.
- **SVGs about half the size.** A `<text>` per word instead of per letter (every character still in its own cell), one path per line style, a lighter glow: the architecture example goes from 87 KB to 36 KB, 50 KB to 16 KB flat. `--portable` keeps one `<text>` per character for design tools such as Inkscape or Figma; PNG output always uses it.
- **The Claude skill composes the whole picture.** A new guide, `references/composing.md`, has models take stock of what the information holds, pick from a catalog of 16 notations (sequences, trees, tables, bars, timelines, swimlanes, ER, callouts and more), combine them around one reading path, and review for mistakes the checker can't see, such as numbers not drawn to scale. Seven worked recipes; every diagram in it renders with no warnings. [Download the skill](https://github.com/SatyadipPaul/ascii2svg/releases/download/v1.16.1/ascii2svg.skill).
- **`--repair` no longer ping-pongs** when a line and its corner are both one column off.
- **Playground:** a Fold toggle, the `explore` preset, new examples, and a Clear button for the editor.

## Fixed in 1.16.1

- The test suite no longer writes the Claude skill into `dist/`, which stopped the 1.16.0 publish at its package check.
- The publish workflow can also run by hand from `main`: it creates the tag and the release, then publishes as usual.

77 tests over 36 test diagrams, plus the npm package's parity tests (245 renders byte-identical to Python). CI covers Python 3.9–3.13 and Node 20/24 on Linux, Windows and macOS.
