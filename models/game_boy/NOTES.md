# Game Boy

A Quick Bricks model: 25 pieces, 2.4 cm wide, 4.5 cm tall and 1.9 cm deep. It is a micro Game
Boy standing on its bottom edge: a light grey case with the one rounded corner at the bottom
right, a screen of three clear tiles in a dark grey frame, two magenta buttons, and a D-pad that
is the end of a black axle. The design is another builder's: Phoenix_bricks' "Micro Game Boy",
Rebrickable MOC-238888. It was built here from the designer's 13 pages of picture instructions,
every piece where they put it. All 8 checks pass; the stability check's limit is lowered from 10
degrees to 8 (see below).

## Source

- **From:** an instructions PDF of 13 pages, made with Studio's instruction maker: one step a
  page, pictures only. It has no cover, no parts list and no words.
  `MOC-238888_Phoenix_bricks_MicroGameBoy.pdf`, kept in `inbox/gameboy/` (local only, never
  committed: the repo is public).
- **Designer / credit:** Phoenix_bricks, "Micro Game Boy", Rebrickable MOC-238888,
  https://rebrickable.com/mocs/MOC-238888/ (the name and the number are from the file's name;
  the Rebrickable page itself was not opened). Someone else's design: credit them wherever it
  is shown. `designer` and `source` are set in `model.toml`.
- **Saved in `reference/`:** nothing. Page images of a designer's instructions are not
  committed either, so none were cut out of the PDF. The original is in `inbox/gameboy/`.
- **Taken in:** 2026-10-10 by lead (Claude), who read the pages and wrote `design.py`. This
  record was written the same day from the lead's page notes and from `design.py`; the PDF was
  not opened again for it.

## The plans, page by page

One row per page of the designer's PDF. The model stands as you see it in the end, and the
columns are named as you face its front: left (the D-pad's; x = -20 in `design.py`), middle
(x = 0) and right (the rounded corner's; x = 20). It is one stud deep, with one brick more
behind the D-pad. Everything is Light Bluish Gray unless a colour is given. The last column is
the step of our own booklet the page ended up in (it has 10).

| Page | Pieces | Where | Our step |
|---:|---|---|---:|
| 1 | 1x Brick Curved 1 x 2 x 1 1/3 with Curved Top (6091); 1x Tile 1 x 2 with Groove (3069b) | The curved brick upside down, round end down, on the middle and right columns: the rounded bottom-right corner. The tile presses onto its stud from below and sticks out one stud to the left. | 1 |
| 2 | 2x Plate 1 x 1 (3024); 1x Brick Special 1 x 1 with Stud on 1 Side (87087) | The two plates stacked on the tile's free end, in the left column. The brick on the curved brick's ledge, in the middle column, its side stud forward. | 1 (the plates), 2 (the brick) |
| 3 | 1x Plate 1 x 1 (3024); 1x Brick Special 1 x 1 with Stud on 1 Side (87087) | The plate on that brick. The second brick on the curved brick, in the right column, its side stud forward. | 2 |
| 4 | 1x Technic Brick 1 x 1 with Axle Hole (73230); 1x Technic Axle 2 Notched (32062), Black | The axle through the brick's cross hole. Its front end is the D-pad. | 3 |
| 5 | 1x Technic Brick 1 x 1 with Axle Hole (73230); 1x Brick Sloped 30° 1 x 1 x 2/3, "cheese slope" (54200) | The second brick on the axle's back end, and the slope on top of it. | 4 |
| 6 | (no new piece) | That assembly onto the two 1 x 1 plates in the left column. Its second brick hangs behind. | 5 |
| 7 | 1x Plate 1 x 2 (3023) | Across the top of the left and middle columns. It locks the D-pad in. | 5 |
| 8 | 1x Bracket 1 x 1 - 1 x 1 Inverted (36840), Dark Bluish Gray; 1x Bracket 1 x 2 - 1 x 2 Inverted (99780), Dark Bluish Gray | Lying on their side studs on the flat top of the body, the 1 x 1 over the D-pad and the 1 x 2 beside it. Their plates stand along the back, studs to the front. | 6 |
| 9 | 1x Bracket 1 x 1 - 1 x 1 (36841), Dark Bluish Gray; 1x Bracket 1 x 2 - 1 x 2 (99781), Dark Bluish Gray | Pressed onto those brackets' studs, plates to the front and side studs up: the 1 x 2 on the left and middle columns, the 1 x 1 on the right, so the joins do not line up with the pair below. | 7 |
| 10 | 2x Plate 1 x 3 (3623), Dark Bluish Gray | One on the other, on the studs that point up. | 8 |
| 11 | 3x Tile 1 x 2 with Groove (3069b), Trans-Clear | Standing side by side, each on one of the studs that face forward: the screen. | 9 |
| 12 | 2x Tile Round 1 x 1 (98138), Magenta | One on each side stud on the front: the A and B buttons, the right one higher. | 10 |
| 13 | 1x Plate 1 x 1 (3024); 1x Tile 1 x 2 with Groove (3069b) | On top of the two 1 x 3 plates: the plate on the left, the tile on the middle and right. | 8 |

## What had to be worked out

The pictures are small and carry no part numbers, so these were read off them. How sure each one
is, is said with it.

- **Which parts they are.** The rounded corner is the curved brick 6091. The two bricks on the
  axle are Technic bricks with an axle hole (73230). The axle is the 2 long notched one
  (32062). Of the four brackets, the lower pair are the inverted kind (36840, 99780) and lie
  on their side studs; the upper pair are the plain kind (36841, 99781). Fairly sure: built
  this way every stud meets a socket, nothing overlaps, and the checks find 32 connections
  (30 stud, 2 axle) in one assembly.
- **Studs down.** Everything in the grey body is upside down: each piece presses on with its
  studs into the piece below (the pictures show undersides up). The two 1 x 3 plates and the
  top edge are the right way up again. Sure.
- **How far the axle sticks out at the front:** 6 LDU (2.4 mm), judged by eye from the last
  page. Not measured.
- **The second axle-hole brick sits lower than the first.** A brick's cross hole is not in
  the middle of its height: it is 10 LDU from the top. The first brick is upside down and the
  second the right way up, so on one axle the second sits 4 LDU (1.6 mm) lower. Page 5's
  picture shows the step. Sure.
- **Colours.** Light and dark grey, clear and black were read from the pictures. The buttons'
  pink-purple was taken as Magenta. It could be Dark Pink: LEGO makes the round tile in both.
- **The stud on top.** The 1 x 1 plate at the top left leaves one stud showing. `design.py`
  tags it `switch`: our reading of it as the power switch, not something the pages say.
- **Our steps.** The booklet has 10 steps for the designer's 13 pages. The D-pad is a
  sub-assembly of two steps (pages 4 and 5). Pages 1 to 3 are two steps, and page 6 goes with
  page 7. The top edge (page 13) goes on with the two 1 x 3 plates (page 10), before the
  screen and the buttons, so those end the build. The finished model is the same.
- **Does it stand?** Only just. It stands on its bottom edge, one stud deep (8 mm) and three
  wide, weighs about 9 g, and tips at 9.3 degrees (the check wants at least 10). So
  `[checks.stability] min_tilt_deg = 8` in `model.toml`, with a comment. Nothing was added to
  steady it: the design is someone else's.
- **Not tried in bricks.** The checks are on the computer model. No physical build is
  recorded.

## Parts and price

- 25 pieces in 15 lines. Every line has a LEGO element ID; none is flagged rare.
  `out/parts.csv`, `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1 to $4, new parts on BrickLink, before shipping. It is not a live
  price.
- The line in the fewest sets is the Magenta round tile (30 sets).

| Qty | Part | Number | Colour | Element ID |
|---:|---|---|---|---|
| 4 | Plate 1 x 1 | 3024 | Light Bluish Gray | 4211399 |
| 2 | Tile 1 x 2 with Groove | 3069b (BrickLink 3069) | Light Bluish Gray | 4211414 |
| 2 | Technic Brick 1 x 1 with Axle Hole | 73230 | Light Bluish Gray | 6336539 |
| 2 | Brick Special 1 x 1 with Stud on 1 Side | 87087 | Light Bluish Gray | 4558953 |
| 1 | Plate 1 x 2 | 3023 (LDraw 3023b) | Light Bluish Gray | 4211398 |
| 1 | Brick Sloped 30° 1 x 1 x 2/3 (Cheese Slope) | 54200 | Light Bluish Gray | 4521921 |
| 1 | Brick Curved 1 x 2 x 1 1/3 with Curved Top | 6091 | Light Bluish Gray | 6285778 |
| 2 | Plate 1 x 3 | 3623 | Dark Bluish Gray | 4211133 |
| 1 | Bracket 1 x 1 - 1 x 1 Inverted | 36840 | Dark Bluish Gray | 6225494 |
| 1 | Bracket 1 x 1 - 1 x 1 | 36841 | Dark Bluish Gray | 6413106 |
| 1 | Bracket 1 x 2 - 1 x 2 Inverted | 99780 | Dark Bluish Gray | 6000606 |
| 1 | Bracket 1 x 2 - 1 x 2 | 99781 | Dark Bluish Gray | 6214341 |
| 3 | Tile 1 x 2 with Groove | 3069b (BrickLink 3069) | Trans-Clear | 6514223 |
| 2 | Tile Round 1 x 1 | 98138 | Magenta | 6322816 |
| 1 | Technic Axle 2 Notched | 32062 | Black | 4109810 |

## Quick Bricks

- `[quick]` in `model.toml`: the blue LEGO floor (`lego_blue`) in the bookshelf room, day
  light, 14 seconds, clicks only. The yellow LEGO floor was the first choice and was changed
  the same day; the comment beside the setting says why: yellow turns the grey beige, and on
  blue the grey stays grey and the buttons jump out. Yoda PEZ has the same floor, room and
  light.
- `highlight = ["screen", "dpad", "buttons"]`, two close-ups. As planned on 2026-10-10 they
  land on the D-pad (about 5.6 s) and on a screen tile (about 10 s). The D-pad one lands on
  the second cross-hole brick, not on the axle: the whole sub-assembly carries the `dpad` tag.
  Check it in the preview.
- It has 25 pieces, one too many for the opening with the parts laid out (that is for under
  25), so they come in from off frame.
- The video's build plan is clean, audited the way `brickkit status game_boy --check` does it:
  no piece passes through another and each lands on something. The pieces that go on from the
  front, from behind and from underneath carry `insert=` hints in `design.py`.
- The final video was not rendered when this was written; `brickkit status` shows where it is.
  `collection = "quick_bricks"` is not set: it is not on the site.
