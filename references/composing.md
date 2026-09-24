# Composing a diagram: the whole picture

Diagram languages make you pick one chart type first: a flowchart, *or* a sequence, *or* a table.
Real information is never one shape. A system has parts, and a request moving through them, and a
slow step, and a number that matters. ascii2svg draws whatever you put on the character grid, and
every notation below can sit next to, inside, or across any other. So don't pick a diagram type.
**Look at the information, then compose the picture that shows all of it.**

Work through the six steps below every time you draw from scratch. Don't jump to the first box.

## 1. Take inventory

Before drawing anything, write down (in your reply, or where you plan your work) what the
information contains. Go through every kind and note what you have:

| Kind of information | Look for |
|---|---|
| Things | services, people, teams, stores, files, concepts |
| Groups | clusters, boundaries, teams, layers, phases |
| Connections | who calls, feeds, owns or depends on whom, and *how* (protocol, event, data) |
| Order in time | steps, messages, handshakes, dates, durations |
| Choices | conditions, branches, retries, fallbacks |
| Hierarchy | parts of a whole, call trees, folders, ideas and sub-ideas |
| Numbers | amounts, percentages, latencies, counts, progress |
| Comparison | the same fields across options, regions or versions |
| States | the life of one thing: created, paid, shipped |
| Emphasis | the one risk, anomaly, decision or takeaway the reader must not miss |

Most real questions contain four or more of these. A diagram that shows only one kind leaves the
rest of the picture out.

## 2. Match each kind to a notation

| Kind | Draw it as (catalog number) |
|---|---|
| Things | boxes (1) |
| Groups | containers (1), swimlanes (12) |
| Connections | arrows between boxes, lines between words (2), fan-out (3), ER (14) |
| Order in time | sequence (5), timeline (11), Gantt (10), numbered flow |
| Choices | decision (4) with every way out labelled |
| Hierarchy | tree (6), mind map (7), boxes fanning out (3) |
| Numbers | bar chart (9), numbers inside boxes or after tree labels, a table column |
| Comparison | table (8), bars side by side (9) |
| States | state machine (13) |
| Emphasis | callout (15); bold wording in a box; the one colour-coded branch |

## 3. Choose the spine, then place the rest

The **spine** is what the reader follows first: usually the flow of time, of a request, or of
work. Everything else attaches to the part of the spine it explains: a call tree under the service
it profiles, a table beside the step it measures, a callout pointing at the anomaly. Sketch the
layout as regions before drawing details:

```text
┌─ spine: the request, top to bottom ──┐  ┌─ beside it ─────────────┐
│ sequence: Client · API · Cache       │  │ table: latency by step  │
│ decision: hit?                       │  └─────────────────────────┘
│ outcomes: reply now · price engine   │  ╭┄ note ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╮
└──────────────────────────────────────┘  ┆ 1 in 5 requests miss    ┆
                                          ╰┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╯
```
### 3b. Map the columns before you draw

Most redrawing comes from columns that don't line up. Before drawing, write down where every
vertical thing goes: each lifeline, each box's left edge and width, each branch. Size a box to its
longest label plus two spaces. For example:

| Part | Column | Width |
|---|---|---|
| User lifeline | 4 | |
| Auth service box / lifeline | 28 / 35 | 16 |
| Mail service box / lifeline | 60 / 67 | 16 |

Then draw the vertical lines first, run `--check`, and only then add the labels and messages
between them. A generated diagram (a script that prints the text) is fine for anything regular:
many boxes in a row, a timeline, bars.

## 4. Say the plan

In two to four lines, tell the user what the picture will contain and how it is arranged, e.g.
*"The request as a sequence down the left, turning into the cache decision; a table of latency
per step on the right; a note on the miss rate."* This is the moment to catch a missing piece.

## 5. Draw region by region, checking as you go

Draw one region, run `--check`, fix what the hints say, then add the next. Keep a connector's
column (or row) identical from start to arrowhead. When branches join again, the join is **one
row**: the arrowhead, then `┴` where each branch lands, `┘` at the far end (see 3 and recipe B).
Finish with `--repair --check --describe`.

**`status: ok` means the drawing is exact, not that it is right.** Read `diagram.edges`: each end
should name the box you meant (`{"box": ..., "name": "Orders"}`). In a sequence, messages between
lifelines are reported by position (`{"cell": [row, col]}`) for now; check those rows against your
plan instead. Read `diagram.tree` for a hierarchy. Then go through the list below.

## 6. Review, then render

### Mistakes the checker can't see

The check proves every character is where you put it. It can't tell whether the picture is true.
Look for these yourself:

- **Numbers not to scale.** A bar's length is its value divided by the largest value, times the
  bar width, rounded. `░` is only ever the rest of a target, never a value; a value under one cell
  gets `▏` or `▌`, not an empty bar. (310 of 12,400 on a 20-cell bar is `▌`, not `░░░░░…`.)
- **A note pointing at the wrong thing.** The leader ends on what the note is about: that box's
  edge, or a `◀┄┄` pointing at the label. A note about a step never points at a number.
- **A cut-down question.** `has ?` means nothing. Write the question beside the diamond (4), or
  use a box that ends in `?`.
- **A label that cuts a line.** Text written across a lifeline or connector breaks it into two
  pieces, silently. Keep every label between the lines it sits between; shorten it or add a row.
- **A lifeline that stops early.** Every lifeline runs from its box to the bottom of the sequence.
  Show a choice as a guard on the message, `[email known] send link`, not a diamond that swallows
  the lifeline (recipe G).
- **A sequence inside a container.** The container becomes every message's end in `--describe`.
  Put the title as plain text above a sequence instead of framing it.

### Checklist

- [ ] Every item from the inventory is in the picture, or left out on purpose.
- [ ] Every line says what it carries (a label, or a legend entry).
- [ ] One reading direction: top to bottom or left to right, not both at once.
- [ ] At least two spaces (or one empty row) between regions; nothing touches by accident.
- [ ] More than two kinds of line or box? Add a legend (16).
- [ ] At most about 100 columns wide, so it reads on a laptop and scales down on a phone.
- [ ] Numbers are to scale; every note points at its subject; every label reads on its own.
- [ ] `status` is `ok`, and `diagram.edges` / `diagram.tree` say what you meant. Then render with the preset for where it's going
  (a tree or mind map on its own: `--preset explore`, so its branches fold).

## When to split instead

One picture is for one question. Split into several diagrams (several code blocks, rendered with
`--all-blocks -o DIR/`) when the parts answer different questions, when it would pass about 100
columns or 60 rows, or when two spines would compete (a request flow *and* a delivery plan). Give
each diagram a title on its top container, and repeat a box name exactly where the diagrams meet.

---

## Catalog

Every example below renders exactly, with no warnings. Copy, then adapt.

### 1. Boxes and containers

**Use it for** things that exist: services, teams, stores, people. A container (title on its top edge) groups what belongs together: a cluster, a team, a trust boundary.  
**Watch out:** Close every box. One space between words and the wall. Two lines of text beat one long line.

```text
┌─ Payments (k8s ns: pay) ──────────────────┐
│  ┌──────────────┐      ┌──────────────┐   │
│  │ Checkout API ├─────▶│ Ledger       │   │
│  │ Go · 3 pods  │      │ Postgres 16  │   │
│  └──────────────┘      └──────────────┘   │
└───────────────────────────────────────────┘
```

### 2. Lines between words

**Use it for** a quick chain where boxes would be heavy. The word set into the line (`--HTTPS-->`) says *how*.  
**Watch out:** Leave a space between a word and the line, and end in an arrowhead that points at a word.

```text
Browser --HTTPS--> Gateway --gRPC--> Orders
```

### 3. Fan-out and fan-in

**Use it for** one thing feeding several (or several feeding one).  
**Watch out:** Split at a `┴` or `┬` on one row; every branch keeps its column down to its arrowhead.
Joining is the same in reverse, and also **one row**: each branch ends in `└` or `┘` on the join
row, with a `┬` where the joined line leaves (below). Don't add a separate bridge row.

```text
        ┌──────────┐
        │ Gateway  │
        └────┬─────┘
      ┌──────┴──────┐
      ▼             ▼
┌──────────┐  ┌──────────┐
│ Orders   │  │ Search   │
└──────────┘  └──────────┘
```

```text
┌────────┐   ┌────────┐
│ Card   │   │ Wallet │
└───┬────┘   └───┬────┘
    └─────┬──────┘
          ▼
    ┌──────────┐
    │ Receipt  │
    └──────────┘
```

### 4. Decision

**Use it for** a question whose answer changes the path. Label every way out (`yes` / `no`).  
**Watch out:** The diamond's rows must mirror each other, and its middle rows hold about three
characters (`hit`, `>70`, `?`). Never cut the question down to fit: put a `?` inside and write the
question beside it (below), or use a box whose text ends in `?`.

```text
    ┌───────────────┐
    │ Score order   │
    └───────┬───────┘
            │
            ▼
           / \
          /   \
         / >70 \
         \  ?  /
          \   /
           \ /
     yes    │     no
    ┌───────┴───────┐
    ▼               ▼
┌────────┐     ┌─────────┐
│ Review │     │ Approve │
└────────┘     └─────────┘
```

```text
        ┌──────────────┐
        │ Reset asked  │
        └──────┬───────┘
               ▼
              / \
             /   \      does the email
            /  ?  \     belong to an account?
            \     /
             \   /
              \ /
      yes      │      no
       ┌───────┴───────┐
       ▼               ▼
┌────────────┐  ┌────────────┐
│ Send link  │  │ Do nothing │
└────────────┘  └────────────┘
```

### 5. Sequence

**Use it for** who talks to whom, in what order: requests, handshakes, protocols.  
**Watch out:** A message runs lifeline to lifeline (`│───▶│`) with its label on the row above,
fitting *between* the two lifelines. Every lifeline runs to the bottom; a message that passes a
lifeline crosses it with `┼`. Show a choice as a guard, `[email known] send link`. Don't wrap a
sequence in a container (see recipe G for all of this at once).

```text
┌────────┐          ┌─────────┐          ┌────────┐
│ Client │          │   API   │          │   DB   │
└───┬────┘          └────┬────┘          └───┬────┘
    │   POST /orders     │                   │
    │───────────────────▶│                   │
    │                    │  INSERT order     │
    │                    │──────────────────▶│
    │                    │        ok         │
    │                    │◀──────────────────│
    │   201 Created      │                   │
    │◀───────────────────│                   │
```

### 6. Tree (call tree, file tree, dependencies)

**Use it for** hierarchy: calls, folders, packages, org charts. Notes after a label (`× 3`, `312 ms`) stay with it. Folds with `--preset explore`.  
**Watch out:** No arrowheads in a tree; `├──` for every child, `└──` for the last.

```text
checkout()
├── validate(cart)
│   └── Sku.lookup(sku)   × 3
├── charge(card)          312 ms
└── publish(OrderPlaced)
```

### 7. Mind map

**Use it for** a topic and its parts, read left to right; the leaves can carry numbers. Folds, and gets a colour per branch.  
**Watch out:** Split on one column: `╭──` first, `├──` middle, `╰──` last, `┼` or `┤` where the parent line joins.

```text
                ╭── Latency ─── p99 < 300 ms
Service goals ──┼── Uptime ──── 99.95 %
                ╰── Cost ────── < $4k / month
```

### 8. Table

**Use it for** anything compared across the same fields: options, regions, versions, before and after.  
**Watch out:** `┬ ┼ ┴` where the rules cross; `↑ ↓` (not `▲ ▼`, which are arrowheads) for trends.

```text
┌─────────┬────────┬────────┬─────────┐
│ Region  │ Q1     │ Q2     │ Trend   │
├─────────┼────────┼────────┼─────────┤
│ EU      │ 1.2 M  │ 1.5 M  │ ↑ 25 %  │
│ APAC    │ 0.8 M  │ 0.7 M  │ ↓ 12 %  │
└─────────┴────────┴────────┴─────────┘
```

### 9. Bar chart

**Use it for** quantities side by side. Put the number at the end of each bar.  
**Watch out:** Scale the longest bar to about 20 cells and every other bar in proportion
(value ÷ largest × 20, rounded). `█` is the value; `░` only for what's left of a target (progress);
a value under one cell is `▏` or `▌`, never an empty bar.

```text
Build time by stage (s)
  lint     ██████                 12
  test     ████████████████████   41
  package  █████████              18
```

### 10. Gantt

**Use it for** work over time: `█` done or planned, `░` slack or risk.  
**Watch out:** A header row with the time scale; each character is the same slice of time.

```text
            W1   W2   W3   W4
Design      ████████░░
Build            ███████████░░░
Launch                     ████
```

### 11. Timeline

**Use it for** moments in order: releases, an incident, a history. Times above the spine, events below.  
**Watch out:** `●` on the spine, labels centred on it.

```text
 09:02          09:07          09:15          09:40
   ●──────────────●──────────────●──────────────●───▶
 alert         paged          rollback       resolved
```

### 12. Swimlanes

**Use it for** who does what: steps in a lane per team or system, arrows crossing lanes when work is handed over.  
**Watch out:** Lanes are rows of one container; a crossing arrow passes the lane rule with `┼`.

```text
┌─ On-call ────┬─────────────────────────────────────────┐
│              │  ┌─────────┐      ┌──────────┐          │
│              │  │ Triage  ├─────▶│ Rollback │          │
│              │  └────┬────┘      └──────────┘          │
├─ Support ────┼───────┼─────────────────────────────────┤
│              │       ▼                                 │
│              │  ┌───────────────┐                      │
│              │  │ Notify users  │                      │
│              │  └───────────────┘                      │
└──────────────┴─────────────────────────────────────────┘
```

### 13. State machine

**Use it for** the life of one thing: an order, a ticket, a document. Label each move with its event.  
**Watch out:** A loop back goes under the boxes, labelled below.

```text
┌───────┐  submit  ┌───────────┐ approve ┌───────────┐
│ Draft ├─────────▶│ In review ├────────▶│ Published │
└───────┘          └─────┬─────┘         └───────────┘
    ▲                    │
    └────────────────────┘
       changes requested
```

### 14. Data model (ER)

**Use it for** entities and how many of each relate: `||` one, `o<` zero or many, `|<` one or many.  
**Watch out:** The crow's foot touches the wall: `o<┤`, not `o<─┤`.

```text
┌──────────┐        ┌──────────┐        ┌──────────┐
│ CUSTOMER ├──||──o<┤ ORDER    ├──||──|<┤ LINE     │
└──────────┘        └──────────┘        └──────────┘
```

### 15. Callout

**Use it for** the one thing the reader must notice: an anomaly, a risk, a decision. A dotted box, and a dotted leader to what it's about.  
**Watch out:** The leader starts on a wall or a line (`┴`), never in open space, and ends on the
thing the note is about. To point at a label (a tree branch, a table cell), end the leader in an
arrowhead one space from it, on the same row (below).

```text
┌──────────────┐      ┌──────────────┐
│ Cache        ├─────▶│ Database     │
└──────────────┘      └──────┬───────┘
                             ┆
                  ╭┄┄┄┄┄┄┄┄┄┄┴┄┄┄┄┄┄┄┄┄┄┄╮
                  ┆ hot spot: 80 % of    ┆
                  ┆ reads miss the cache ┆
                  ╰┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╯
```

```text
Payments revamp (Nov)
├── Apple Pay
├── Google Pay     ◀┄┄ blocked: backend API not ready
└── receipts
```

### 16. Legend

**Use it for** whenever you use more than two kinds of line or box. Show each one between words, as it appears.  
**Watch out:** Sample lines need a word at both ends (`A ───▶ B`), or they read as broken lines.
Only use samples like these (no `├──` or corners), and keep the legend one empty row and two
columns away from everything else, so its samples can't line up with real lines.

```text
╭─ Legend ─────────────────────────────╮
│ A ───▶ B    A calls B and waits      │
│ A ╌╌╌▶ B    A sends B an event       │
│ ╭┄┄┄┄╮      a note, not a system     │
│ ╰┄┄┄┄╯                               │
╰──────────────────────────────────────╯
```

**Plain characters that stay text:** `✓ ✗ · • → ← ↑ ↓ × %` are safe for status and values. Emoji
and CJK characters take two columns: count them as two, or run `--repair`. `▼ ▲ ▶ ◀` and `v ^ < >`
next to a line are arrowheads, not text.

---

## Recipes: several notations in one picture

Each recipe starts from an inventory and combines notations from the catalog. Every one renders
exactly, with no warnings.

### A. System at a glance

**Inventory:** services, where they run, how they talk, the path that matters, one problem.  
**Notations:** containers (1) + labelled lines (2) + the hot path as a call tree with timings (6) + a callout (15).

```text
                     ┌──────────────┐
                     │ Mobile · Web │
                     └──────┬───────┘
                            │ HTTPS
┌─ Order platform ──────────┼──────────────────────────────────────────┐
│                           ▼                                          │
│                   ┌───────────────┐   gRPC    ┌───────────────┐      │
│                   │ API gateway   ├──────────▶│ Orders        │      │
│                   │ auth · limits │           │ Java · 6 pods │      │
│                   └───────────────┘           └───────┬───────┘      │
│                                                       │ events       │
│                                                       ▼              │
│  ┌───────────────┐   reads      ┌─────────────────────────────────┐  │
│  │ Search        │◀─────────────┤ Kafka  orders.v1                │  │
│  └───────────────┘              └─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

 Hot path: Orders.place(cmd)              ╭┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╮
 ├── Inventory.reserve(items)    41 ms    ┆ p99 is 380 ms; the budget  ┆
 ├── Pricing.quote(items)        18 ms    ┆ is 300 ms: Payments is the ┆
 ├── Payments.charge(card)      290 ms    ┆ place to look first        ┆
 └── Kafka.publish(OrderPlaced)   6 ms    ╰┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╯
```

### B. The story of one request

**Inventory:** actors, messages in order, a branch point, what each branch costs.  
**Notations:** sequence (5) turning into a decision (4) and fan-out (3), timings inside the outcome boxes, the reply drawn back to the first lifeline.

```text
┌────────┐           ┌──────────┐           ┌──────────┐
│ Client │           │ API      │           │ Cache    │
└───┬────┘           └────┬─────┘           └────┬─────┘
    │  GET /price/42      │                      │
    │────────────────────▶│   GET price:42       │
    │                     │─────────────────────▶│
    │                     │      hit or miss     │
    │                     │◀─────────────────────│
    │                     │
    │                     ▼
    │                    / \
    │                   /   \
    │                  / hit \
    │                  \  ?  /
    │                   \   /
    │                    \ /
    │           yes       │        no
    │         ┌───────────┴───────────┐
    │         ▼                       ▼
    │  ┌──────────────┐       ┌──────────────┐
    │  │ Reply now    │       │ Price engine │
    │  │ 4 ms         │       │ 120 ms       │
    │  └──────┬───────┘       └──────┬───────┘
    │         │                      │
    │◀────────┴──────────────────────┘
    │  200 { price }
```

### C. A plan

**Inventory:** dates, milestones, progress, the tasks under each.  
**Notations:** timeline (11) as the spine, a box per milestone (1) with a progress bar (9) inside, its tasks as a tree (6) hanging below.

```text
 Q1 2027            Q2 2027            Q3 2027
   ●──────────────────●──────────────────●───────────────▶
   │                  │                  │
┌──┴──────────┐    ┌──┴──────────┐    ┌──┴──────────┐
│ Beta        │    │ GA          │    │ Teams       │
│ ██████████  │    │ ██████░░░░  │    │ ░░░░░░░░░░  │
│ done        │    │ 60 %        │    │ planned     │
└──┬──────────┘    └──┬──────────┘    └──┬──────────┘
   ├── invite codes   ├── billing        ├── SSO
   └── feedback form  ├── docs site      └── roles
                      └── status page
```

### D. A numbers report

**Inventory:** the same fields across groups, a comparison, one outlier and why.  
**Notations:** a table (8) and a bar chart (9) in one container (1), a callout (15) whose leader points at the outlier.

```text
┌─ Revenue by region ───────────────────────────┐
│ ┌────────┬─────────┬─────────┬──────────────┐ │
│ │ Region │ Q2      │ Q3      │ Change       │ │
│ ├────────┼─────────┼─────────┼──────────────┤ │
│ │ EU     │ 1.20 M  │ 1.31 M  │ ↑  9 %       │ │
│ │ US     │ 2.05 M  │ 2.10 M  │ ↑  2 %       │ │
│ │ APAC   │ 0.64 M  │ 0.98 M  │ ↑ 53 %  ◀┄┄┄┄┼┄┼┄┄┐
│ └────────┴─────────┴─────────┴──────────────┘ │  ┆
│                                               │  ┆
│  EU    █████████████             1.31 M       │  ┆
│  US    █████████████████████     2.10 M       │  ┆
│  APAC  ██████████                0.98 M       │  ┆
└───────────────────────────────────────────────┘  ┆
                                ╭┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┴┄┄┄┄┄┄╮
                                ┆ APAC: new Tokyo region, ┆
                                ┆ live since 2 August     ┆
                                ╰┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╯
```

### E. An incident

**Inventory:** what happened when, who did what, hand-overs.  
**Notations:** a timeline (11) on top, swimlanes (12) below, arrows across lanes for hand-overs.

```text
  09:02         09:07         09:15          09:40
    ●─────────────●─────────────●──────────────●────▶
  alert         paged         rollback       resolved

┌─ On-call ─────┬──────────────────────────────────────────────┐
│               │ ┌───────────┐    ┌───────────┐               │
│               │ │ Triage    ├───▶│ Roll back ├──────┐        │
│               │ └─────┬─────┘    └───────────┘      │        │
├─ Support ─────┼───────┼─────────────────────────────┼────────┤
│               │       ▼                             ▼        │
│               │ ┌───────────┐              ┌─────────────┐   │
│               │ │ Status    │              │ All clear   │   │
│               │ │ page      │              │ email       │   │
│               │ └───────────┘              └─────────────┘   │
└───────────────┴──────────────────────────────────────────────┘
```

### F. A data model and its life cycle

**Inventory:** entities, fields, cardinality, the states of the main entity.  
**Notations:** ER (14) on top, a state machine (13) in a container titled after the field, joined by a dotted leader.

```text
┌────────────┐          ┌────────────┐          ┌────────────┐
│ CUSTOMER   │          │ ORDER      │          │ LINE_ITEM  │
│ id  PK     ├──||────o<┤ id  PK     ├──||────|<┤ order_id   │
│ email      │          │ status     │          │ sku        │
└────────────┘          └─────┬──────┘          └────────────┘
                              ┆ status
┌─ ORDER.status ──────────────┴───────────────────────────────────────┐
│ ┌─────────┐  pay  ┌─────────┐  ship  ┌─────────┐  deliver  ┌──────┐ │
│ │ created ├──────▶│ paid    ├───────▶│ shipped ├──────────▶│ done │ │
│ └────┬────┘       └────┬────┘        └─────────┘           └──────┘ │
│      │ timeout         │ refund                                     │
│      ▼                 ▼                                            │
│ ┌───────────┐     ┌──────────┐                                      │
│ │ cancelled │     │ refunded │                                      │
│ └───────────┘     └──────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### G. A flow with rules, numbers and a warning (password reset)

**Inventory:** actors, messages in order, two conditions, a security rule, last month's numbers.  
**Notations:** sequence (5) with guards for the conditions, a crossing message (`┼`), a callout (15)
hanging from the lifeline it is about, scaled bars (9) including a sub-cell value.

A first attempt at this one put each condition in a diamond: the Auth lifeline stopped at the
first one, the questions were cut to `has ?`, 310 expired links drew as a full empty bar, and the
note pointed at the numbers. Guards keep the sequence whole:

```text
┌────────┐                  ┌──────────────┐                ┌──────────────┐
│ User   │                  │ Auth service │                │ Mail service │
└───┬────┘                  └──────┬───────┘                └──────┬───────┘
    │  reset(email)                │                               │
    │─────────────────────────────▶│                               │
    │                              │  [email known] token, 30 min  │
    │                              │──────────────────────────────▶│
    │  "check your inbox"          │                               │
    │◀─────────────────────────────│                               │
    │  (same reply if unknown)     │                               │
    │                              │                               │
    │  link with token             │                               │
    │◀─────────────────────────────┼───────────────────────────────│
    │  open link                   │                               │
    │─────────────────────────────▶│                               │
    │  [fresh, unused] form        │                               │
    │◀─────────────────────────────│                               │
    │  new password                │                               │
    │─────────────────────────────▶│  sign out other sessions      │
    │  done                        │                               │
    │◀─────────────────────────────│                               │
                                   ┆
     ╭┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┴┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╮
     ┆ tokens are single-use and expire after 30 minutes ┆
     ╰┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄╯

 Last month   requested  ████████████████████  12,400
              completed  ███████████████        9,100
              expired    ▌                        310
```

### More combinations to consider

- **Architecture + deployment:** containers per environment, each service box carrying its replica
  count and version; a table of what differs between environments.
- **Before and after:** two versions of the same picture side by side under one container, the
  changed boxes called out.
- **Onboarding map:** a mind map of the codebase (7) whose leaves name the file to read first,
  with a short numbered flow of a first change.
- **Algorithm walk-through:** a table of the data at each step (8), with arrows between the
  columns that change, and a decision (4) for the loop condition.
- **Cost breakdown:** a tree of cost centres with amounts (6), and bars (9) for the top five.

## Anti-patterns

- Every piece of information forced into a box-and-arrow flowchart.
- Arrows with no labels, so the reader has to guess what flows.
- Two reading directions fighting in one picture.
- A table drawn as a grid of boxes joined by arrows.
- Decoration that carries no information (borders around borders, emoji as bullets).
- Leaving out the numbers, the risk or the "why" because they didn't fit the chosen diagram type.
