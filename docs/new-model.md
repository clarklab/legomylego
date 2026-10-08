# Taking in a new model

How a small model gets from something pasted into a chat (a set of instructions, or just a
picture) to a checked 3D model, parts lists, an instruction booklet, a build video and a page
on the site. It is written for an agent or a person who has never seen this repo.

The work is in six stages. Each one leaves files behind, so you can stop after any stage and
someone else can pick it up later. `brickkit status` shows where every model is and what to
do next.

| Stage | You need | You make | Done when | GPU |
|---|---|---|---|---|
| 1. Take it in | what was pasted | `models/SLUG/` with `reference/` and `NOTES.md` | NOTES.md has no TODO left | no |
| 2. Model it | stage 1 | `design.py`, `model.toml` | `brickkit all SLUG` passes every check | no |
| 3. Parts lists | stage 2 | `out/parts.csv`, `pick_a_brick.csv`, `bricklink_wanted.xml`, price | every part has a LEGO element ID | no |
| 4. Instructions | stage 2 | `out/booklet.pdf` | you have read every page in order | a few minutes |
| 5. Video | stage 2 | `out/SLUG-1080x1920.mp4` | no `quick:` warnings, and you have looked at it | about 100 minutes |
| 6. Site | stages 3 to 5, and the owner's go-ahead | pages under `site/quick/SLUG/` | the live page plays the video | no |

Stages 1 to 3 are quick and need no GPU. Do them for every new model first; stages 4 and 5
can wait and be queued.

```bash
.venv/bin/python -m brickkit status            # the Quick Bricks models: one row each
.venv/bin/python -m brickkit status --check    # also audits each one's video plan
```

## Before you start

- Setup is in the [README](../README.md). Use `.venv/bin/python`. The engine's full reference
  is [brickkit-guide.md](brickkit-guide.md); this page is the order to do things in.
- The rules in [AGENTS.md](../AGENTS.md) apply: one Blender render at a time, no LEGO
  instruction PDFs in the repo, nothing published without the owner's say.
- A slug is lower case with underscores, the model's plain name: `bat`, `birthday_cake`.

## Stage 1: Take it in

The goal is a record good enough that someone else could build the 3D model from it later
without the chat.

```bash
.venv/bin/python -m brickkit new SLUG --quick --name "The Name"
```

That makes `models/SLUG/` with `model.toml`, `design.py`, a `NOTES.md` to fill in and an
empty `reference/`.

1. **Save the source** in `reference/`, in page order: `page_01.png`, `page_02.png`, or
   `picture_01.jpg`. Save what was pasted. Do not add LEGO's own instruction PDFs or zips of
   them (the repo is public). Scans of pages from an official LEGO booklet: ask the owner
   first.
2. **Fill in `NOTES.md`.** Its headings are the standard:
   - *Source*: where it came from, who designed it (credit the designer if it is not ours),
     and what each saved file shows.
   - *The plans, page by page*: one row per page, with the pieces (quantity, name, part
     number, colour) and where they go. Say how you name the columns and rows.
   - *What had to be worked out*: everything the source did not show plainly, and how sure
     you are of each.
3. **Name the parts for real.** `brickkit find "plate 1 x 2" --color Black` searches real LEGO
   parts and shows which exist in that colour. Colours use Rebrickable's names ("Light Bluish
   Gray", "Reddish Brown").

Stop here if you like: the model is taken in.

## Stage 2: Model it

Write `design.py`: one `m.step("caption")` per page of the plans, and one `m.place(...)` per
piece. The frame is LDraw's: a stud is 20 units, a plate 8, a brick 24; **-Y is up**; the
front faces -Z. `models/dracula/design.py` and `models/bat/design.py` are good small examples;
`models/dinosaur/design.py` shows sub-assemblies (`model.submodel`, `m.use`).

```bash
.venv/bin/python -m brickkit inspect 87087      # a part's box and where its studs are
.venv/bin/python -m brickkit all SLUG           # build, run the 8 checks, write the parts lists
.venv/bin/python -m brickkit render SLUG --size 700 --samples 48    # stills in out/renders/
```

- Fix every FAIL in `out/report.html`. Switch a check off in `model.toml` only with a comment
  saying why (the bat cannot stand, so it has no stability check).
- Look at the renders next to the source. Fix what differs, or write the difference down in
  NOTES.md.
- Fill in `model.toml`: `description` (one sentence for the site), `[palette]`, and
  `[booklet]` `subtitle` and `intro`.
- Tag the pieces a close-up should land on (`tag="eyes"`), for the video later.

## Stage 3: Parts lists and price

`brickkit all` already wrote them in `out/`: `parts.csv`, `pick_a_brick.csv` (upload to LEGO
Pick a Brick), `bricklink_wanted.xml` (upload to BrickLink) and `price_estimate.md`.

- The `real_elements` check must pass: every part exists in its colour and has an element ID.
  If a part does not, pick another with `brickkit find`, or record it in NOTES.md.
- Put the piece count, the number of lines and the price range in NOTES.md.
- Never put anything in a cart or buy anything.

## Stage 4: Instructions

```bash
.venv/bin/python -m brickkit booklet SLUG       # out/booklet.pdf (pictures in out/booklet/)
```

Read every page in order. Each step should add what its caption says, and nothing should
appear from nowhere. If a step is too crowded, split it in `design.py`.

## Stage 5: Video

Set `[quick]` in `model.toml`: a surface, a room and a light, and `highlight` tags for the
close-ups. Pick a workshop the last few models did not use: `brickkit status` lists each
model's in its `scene` column. Under 25 pieces the parts start laid out on the table.

```bash
.venv/bin/python -m brickkit quick SLUG --preview    # about 5 minutes: out/quick_preview.mp4
.venv/bin/python -m brickkit quick SLUG              # the final: about 100 minutes
```

- **It has to build for real.** The planner checks every piece against what is already built.
  If it prints a `quick:` line (a piece with no clear way in, a part that passes through
  another), fix that before rendering: usually an `insert=(x, y, z)` hint on the piece, the
  way it comes in from. `brickkit status --check` should say `clean`.
- Look at the preview before the final. Check the close-ups land on the right pieces.
- Sound is clicks only by default. A sound of the model's own (`ending`, `[[quick.sound]]`)
  is optional; see the guide.
- Renders take turns on one GPU. Queue finals one after another; do not start two.

## Stage 6: Site

Only when the owner says to publish.

1. In `model.toml`, set `collection = "quick_bricks"`.
2. Export and refresh the site's files:

```bash
.venv/bin/python tools/quick_site.py
.venv/bin/python tools/site_assets.py
```

3. Run the tests: `.venv/bin/python -m pytest -q`. Every tagged model is held to the build
   audit automatically.
4. Preview the site locally (`.venv/bin/python -m http.server 4401 --directory site`), open
   `/quick/` and the model's page, and check the video plays.
5. Commit only the files of this model and the site files that changed, then push. Netlify
   deploys `site/` from `main`. Check the live page.

## From a picture only

There are no steps to copy, so the record matters more.

1. Save the picture. In NOTES.md, list what you can see and what you cannot.
2. **Find the scale.** Count studs along one edge you can see clearly; everything else is
   measured against that.
3. **Name the visible parts**, most certain first. Printed parts (eyes, smiles) pin the scale
   and the colours down.
4. **Decide the hidden structure** the simplest way that holds together, and say so in *What
   had to be worked out*.
5. Model it, render the same view (`brickkit render SLUG --views front,three_quarter`), and
   put the render beside the picture. Repeat until they agree.
6. Write the build order yourself: bottom to top, each piece landing on something. In
   NOTES.md the table has one row per layer instead of per page.
7. Show the owner the render beside the picture before spending GPU time on a video.

## Several models at once

Take them all in first (stage 1), then model them (stages 2 and 3). None of that needs the
GPU, so it can be done in any order or in parallel, one model per folder. Then queue the
booklets and the videos one after another. Five videos are about nine hours of rendering.

Other sessions may be working in the same checkout. Commit only the files you made, by name.

## Things that catch people out

- A plate's, brick's or tile's origin is its **top**. A cheese slope's (54200) is its bottom.
  When in doubt: `brickkit inspect PART`.
- The side stud of a 1 x 1 brick with a stud on its side is 10 units below the brick's top.
- Some part numbers are old moulds that are hard to buy. `brickkit find` ranks parts by how
  many sets used them; prefer the common one (3665b, not 3665).
- A piece that goes on from the side or from underneath needs nothing special: the video
  planner finds its way in. Give an `insert=` hint only if it reports a problem.
- A model whose lowest piece goes on last (a stick under a lolly) is built on the table and
  lifted for that piece. You do not have to build it upside down.
- `brickkit status` says "stale" when `design.py` is newer than a file made from it.

## Where things are

| Path | What |
|---|---|
| `models/SLUG/reference/` | what was pasted: the source |
| `models/SLUG/NOTES.md` | the record: source, parts page by page, what was worked out |
| `models/SLUG/design.py`, `model.toml` | the model, and its colours, texts and video settings |
| `models/SLUG/out/` | everything made from it: report, parts lists, booklet, videos |
| `site/quick/SLUG/`, `site/models/SLUG/` | its page and files on the site |
| `brickkit/templates/quick/` | what `brickkit new --quick` copies |
