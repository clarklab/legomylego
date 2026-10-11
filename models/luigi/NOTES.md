# Luigi

A Quick Bricks model: 62 pieces, 13.3 cm tall, 6.4 cm wide across the arms and 4.8 cm deep. It
is the same build as Mario (`models/mario`) with the red swapped for green: a green cap with a
peak, a green shirt and a green stand, with the same brown moustache, tan face, blue overalls,
yellow buttons and white gloves. The build is JellsaTheBobJeffCreator's Mario, Rebrickable
MOC-249307; the colour swap is ours, not the designer's. All 8 checks pass, with the same
lowered stability limit as Mario.

## Source

- **From:** the same BrickLink Studio file as Mario,
  `MOC-249307_JellsaTheBobJeffCreator_mario.io`, kept in `inbox/mario/` (local only, never
  committed: the repo is public). There is no Luigi in it: this model is that build in other
  colours.
- **Designer / credit:** the build is by JellsaTheBobJeffCreator, Rebrickable MOC-249307,
  https://rebrickable.com/mocs/MOC-249307/ (from the file's name; the page itself was not
  opened). Credit them wherever it is shown, and say that the green is our change.
  `model.toml` carries this as `credit` ("The build is JellsaTheBobJeffCreator's Mario; we
  swapped his red for Luigi's green.") with `source` linking the original. It has no
  `designer` line: the booklet and the page show that sentence in place of "Designed by ...",
  which would not be true of a version the designer did not make.
- **Saved in `reference/`:** nothing. The original is in `inbox/mario/`.
- **Taken in:** 2026-10-10 by lead (Claude), the same day as Mario.

## The plans, page by page

The same 15 steps as Mario, piece for piece: see the table in
[models/mario/NOTES.md](../mario/NOTES.md). `design.py` calls the same `build_plumber`
(`brickkit/designs/mario.py`); only this model's palette differs. Wherever Mario's table says
Red, read Green:

| Steps | Pieces | Colour here |
|---:|---|---|
| 1 | 2x Plate 2 x 4 (3020); 2x Brick 2 x 4 (3001): the stand | Green |
| 5, 6 | 4x Brick 2 x 2 Corner (2357): the shirt | Green |
| 7, made twice | 2x Brick 2 x 2 (3003); 1x Plate 2 x 4 (3020): the sleeve and the plate of an arm | Green |
| 8 | 1x Brick 2 x 4 (3001): the shoulders | Green |
| 14, 15 | 3x Brick 2 x 4 (3001); 4x Plate 2 x 4 (3020): the cap | Green |

That is 22 pieces in 4 lines. The other 40 are the colours they are on Mario.

## What had to be worked out

- **Which pieces turn green.** The palette roles `shirt` (the cap, the shirt, the arms) and
  `stand` are Green in `model.toml`; on Mario both are Red. Nothing else changes: `stand_top`,
  `overalls`, `skin`, `hair`, `glove`, `button` and `eye` are the same.
- **It is a colour swap and no more.** No brick was moved to make him more like Luigi: he is
  the same height and width as Mario and has the same moustache.
- **The green parts are real.** All four exist in Green with LEGO element IDs, and
  `real_elements` flags none as rare. The one in the fewest sets is the corner brick (2357 in
  Green, 56 sets).
- **Does he stand?** As Mario does: about 83 g, tipping backwards at 8.2 degrees, so
  `[checks.stability] min_tilt_deg = 7`, with a comment. See Mario's notes for why.
- Everything else that was decided on the way in (which way he faces, the steps, the arm as a
  sub-assembly, the yellow buttons) is in Mario's notes and holds here too.

## Parts and price

- 62 pieces in 23 lines. Every line has a LEGO element ID; none is flagged rare.
  `out/parts.csv`, `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $2 to $7, new parts on BrickLink, before shipping. It is not a live
  price.
- By colour: 22 Green, 16 Tan, 11 Reddish Brown, 7 Blue, 2 White, 2 Black, 2 Yellow.

## Quick Bricks

- `[quick]` in `model.toml`: the red LEGO floor (`lego_red`: his brother's colour, and
  green's opposite) in the studio room, day light, 16 seconds, clicks only.
- `highlight = ["eyes", "moustache", "buttons", "cap"]`, two close-ups. As planned on
  2026-10-10 they land on the moustache (about 9.6 s) and on an eye (about 11.4 s), as on
  Mario.
- The video's build plan is clean, audited the way `brickkit status luigi --check` does it.
- The final video was not rendered when this was written; `brickkit status` shows where it is.
  `collection = "quick_bricks"` is not set: he is not on the site.
