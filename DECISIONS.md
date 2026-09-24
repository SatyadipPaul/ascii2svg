# Decisions

| Decision | Field | Score | Replaces | Why the old way was chosen | Overridden |
|---|---|---|---|---|---|
| Position against Mermaid by leading with "any text tree becomes a collapsible, linked diagram, no rewriting" (call trees, dependency trees, file trees, mind maps), then architecture path-highlighting. Not a new DSL. *Status: approved by the owner (goal set); built in 1.16.* | Product strategy | 7/10 (accept with fix list) | Positioning as "faithful 1:1 box diagrams for READMEs and LLM output" | The first goal was fixing and rendering diagrams that already exist (LLM output, READMEs) with a provable 1:1 result | no |
| Text as one `<text>` per word run with an x per character (default); `--portable` gives one per character; PNG frames always use one per character | SVG output | 8/10 | One `<text>` per character | Simplest exact 1:1 mapping, and every renderer places it right | no |
| Glow drawn with 7 layers instead of 14, same total density | SVG output | 8/10 | 14 layers | Smoothness; 7 is visually the same (checked by screenshot) | no |
| Still drawings write one `<path>` per line style (and fold group); animated ones keep a `<line>` per segment | SVG output | 9/10 | A `<line>` per segment always | Per-segment timing for animation | no |
| ASCII trees (`\|--` … `` `-- ``) are drawn as lines, only in the exact shape `tree` / `cargo tree` print | Parsing | 7/10 | `\|--` file trees always stay text | Fail-safe: when unsure, stay text. Kept: a strict shape rule, and markdown tables and look-alikes stay text (tested) | no |
| Folding is opt-in (`--interactive`, `--fold`, preset `explore`); the default SVG has no script | Interactivity | 8/10 | – (new) | Scripts don't run in `<img>` (GitHub), and some platforms strip them | no |
| Branch colours only on pure trees (no arrowheads anywhere); arrowed diagrams keep their colours | Styling | 8/10 | – (new) | Avoid restyling flowcharts such as the README's architecture diagram | no |
