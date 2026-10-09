# Charmander

A Quick Bricks model: 14 pieces, about 4 cm long (with the flame), 2 cm wide and 3 cm tall.
It is an orange Charmander on two round feet: a tan belly, two little cheese-slope arms, a head
made of a curved dome over a black eye band, and a tail that is a cone with a trans-orange
flame on its tip. The design is another builder's, SwordBricks (RSierra), Rebrickable
MOC-220190. It was taken in from the designer's BrickLink Studio file with `brickkit import`:
every part sits exactly where the designer put it. All 8 checks pass except stability, which is
switched off (see below).

## Source

- **From:** a BrickLink Studio file (Studio 2.25.4), `MOC-220190_SwordBricks_Charmander_RSierra_SwordBricks.io`,
  kept in `inbox/charmander/` (local only, never committed: the repo is public). It has no
  building steps, only the parts where they sit.
- **Designer / credit:** SwordBricks (RSierra), Rebrickable MOC-220190,
  https://rebrickable.com/mocs/MOC-220190/ (named in the file's name; the page itself was not
  opened while taking it in). Someone else's design: credit them wherever it is shown.
- **Saved in `reference/`:** nothing. The original is in `inbox/charmander/`, which is local
  only. Inside it, `unpacked/` is the `.io` opened up: `model.ldr` is the whole file as plain
  LDraw text (read it there), `thumbnail.png` is Studio's own picture of it (the orange figure
  in front, the red one behind it), and `model.ins` holds only Studio's page layout settings.
- **Taken in:** 2026-10-08. Imported with `brickkit import`, then made to pass the checks and
  written up (stages 2 and 3) by char-agent the same day.

### What else is in the Studio file

The file has 33 parts, and only the first 14 are this model:

- **The orange figure** is the sub-model "SubModel Group 1": 14 parts, the one imported.
- **A red figure**, loose in the main model: 15 parts, the same build in red with one more
  part (below). It is not a colourway, so it is not in `model.toml`.
- **Two tiny balls**, each two Plate Round 1 x 1 (6141) stacked: a red one on a white one (in
  front of the orange figure) and a blue one on a white one (in front of the red figure).
  They look like Poke Balls, but the file does not say. They float one plate (3.2 mm) above the
  table the figures stand on, and they are not joined to anything. Not part of this model.

**The red figure, piece for piece.** Laid over the orange one, every part is the same part in
the same place (checked by comparing all 14 with their twins), with these differences:

- every orange part is Red (colour 4): the feet, plates, jumper, slopes, dome and cone. The
  black, tan and trans-orange parts keep their colours, so it has the same flame;
- it has **one more Plate 1 x 2** (red) in the legs: feet, then two 1 x 2 plates, then the
  jumper, where the orange figure has feet, one plate, the jumper. Everything above that sits
  one plate (3.2 mm) higher, so it is 15 parts and 8 LDU taller.

Because of that extra plate it is a slightly different build, not the same one in red, so it
is described here and not added as a colourway. If it were wanted: add one 3023 plate under the
jumper (the `y` of the jumper and everything above it goes up by 8) and a `[variants.red]`
that sets `body = "Red"`.

## The plans, page by page

The Studio file has no pages, so the steps are ours: `design.py` has 8 steps, bottom to top,
one to two pieces each. Charmander faces one end of its long side; call that the front. Its tail
is the back; left and right are as you face it. Feet, legs and head are one stud wide front to
back, and two studs across (the feet side by side). In `design.py`'s frame the front is -X, and
`azimuth_offset = -90` turns the stills and the video round to it.

| Step | Pieces | Where |
|---:|---|---|
| 1 | 2x Plate Round 1 x 1 with Solid Stud (6141), Orange | Side by side across the width, touching: the feet. |
| 2 | 1x Plate 1 x 2 (3023), Orange, and 1x Plate Special 1 x 2 with 1 Stud with Groove and Inside Stud Holder, "jumper" (15573), Orange | The plate lies across both feet, its two studs on theirs. The jumper goes on it the same way: its one stud is in the middle, between the feet. Together, the legs. |
| 3 | 1x Brick Special 1 x 1 with Studs on 4 Sides (4733), Black | On the jumper's middle stud: the body. Its four side studs face front, back, left and right. |
| 4 | 1x Tile 1 x 2 with Groove (3069b), Tan, and 1x Plate 1 x 2 (3023), Orange | Both stand on their ends (long side up and down) against the black brick's side studs, their top hole over the stud. The tile is on the front stud: the belly, hanging down in front of the legs. The plate is on the back stud, its two studs facing backward. |
| 5 | 2x Slope 30 1 x 1 x 2/3, "cheese slope" (54200), Orange | One on each side stud of the black brick: the arms, the slope's high edge at the top against the body, falling away outward and down. |
| 6 | 1x Cone 1 x 1 [Top Groove] (59900), Orange, and 1x Flame / Headwear Accessory Plume / Feather, Triple Point (64647), Trans-Orange | The cone, narrow end out, onto the lower of the back plate's two studs: the tail, straight back. The flame's pin goes into the cone's narrow end. |
| 7 | 1x Plate 1 x 2 (3023), Orange, and 1x Plate 1 x 1 (3024), Black | The plate on the black brick's top stud, its other stud sticking out in front: the snout. The black plate on its back stud. |
| 8 | 1x Brick Curved 2 x 1 No Studs [1/2 Bow] (11477), Orange | The dome. Its low end is on the snout's front stud, its high end over the black plate, which shows as a black band under it: the eyes. |

## What had to be worked out

- **The build order.** Studio gave only positions, so `brickkit import` worked out one piece
  per step. Those were grouped into the 8 steps above, in the same order but for one swap, in
  "Changes" below.
- **Which part is which.** From the render beside the thumbnail: the black band under the
  dome is the little black plate (3024), not a printed part; the belly is the tan tile; the
  arms are the two cheese slopes on the body brick's side studs. The black brick (4733) is
  mostly hidden: it shows only as the dark sliver at the neck and sides. Sure of all of it.
- **The black band as eyes** is my reading of the picture; the file only has a black 1 x 1
  plate. It is called `eyes` in the palette.
- **Does it stand? Only just, so its stability check is switched off.** It is about 4 g on two
  round 1 x 1 plates, one stud wide front to back. The centre of mass is over them (it is 1 mm
  behind the feet's centre line, towards the tail, and 13 mm up), but the part of the feet
  that touches the table is only about 6 mm wide, so it tips at about 9 degrees (the check wants
  at least 10). On a flat, level table it balances; a nudge or a tilt topples it. No
  parts were added to fix that, because the design is someone else's. The designer's picture
  shows it standing. I had no brick to try it on: this is from the numbers and the picture.
  The reason is written beside the switch in `model.toml`.
- **The cone's mould.** The designer's Cone 1 x 1 [No Top Groove] (4589) in Orange is in only
  5 sets, the last one in 2007 (`real_elements` warned: rare). It was swapped for the current
  Cone 1 x 1 [Top Groove] (59900, BrickLink 4589b, in 147 sets in Orange). In LDraw's data it
  has the same outline and top stud as the old one, and `connections` still finds the same 15
  joins, the flame's included. In the designer's file the flame sits on the old cone; that it
  sits on the top-groove cone the same way is what LDraw's connection data says. I could not try
  it on real bricks, so: fairly sure.
- **Colours.** Studio's Orange, Tan, Black and Trans-Orange are the same names LEGO uses
  (LDraw colours 25, 19, 0, 57). Nothing needed a substitute.

## Changes from the designer's file

Nothing was moved: all 14 parts sit where the Studio file puts them (checked part by part
against `model.ldr`: no point of any part is off by even 0.001 LDU), up to one plain sideways
shift of the whole figure along x (about 9.5 LDU) that `brickkit import` made. Colours are the
file's too, except the cone's mould (below). These are all the changes:

1. **Cone 4589 to 59900** (the current mould, same colour), as above, because 4589 in Orange
   is rare (5 sets, last in 2007).
2. **The black plate (3024) goes on before the dome (11477).** In the order the importer
   worked out the dome went on first, and the `buildability` check found no way to put the
   plate in after it: the dome's high end sits right on the plate's stud. Built the other way
   round (plate, then dome pressed down over both studs) both go on straight from above. The
   finished model is the same.
3. **The steps** are grouped and have captions, and the pieces a close-up should land on are
   tagged: the flame (`flame`), the dome and black plate (`face`), plus `tail` on the cone and
   `belly` on the tile.
4. **`azimuth_offset = -90`** in `design.py`: the designer built it facing -X, not -Z, so this
   turns the stills and the video round to its face.
5. **The palette roles** have names (`body`, `belly`, `flame`, `core`, `eyes`) in place of the
   importer's colour names.
6. **The stability check is switched off**, with a comment (see above).

## Parts and price

- 14 pieces in 10 lines; every part has a LEGO element ID. `out/pick_a_brick.csv` and
  `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $0.46 to $1.76 (shown as $0-$2); Pick a Brick and BrickLink prices
  were not checked live.

| Qty | Part | Number | Colour | Element ID |
|---:|---|---|---|---|
| 3 | Plate 1 x 2 | 3023 (LDraw 3023b) | Orange | 4177932 |
| 2 | Plate Round 1 x 1 with Solid Stud | 6141 | Orange | 4157103 |
| 2 | Brick Sloped 30 1 x 1 x 2/3 (Cheese Slope) | 54200 | Orange | 4504371 |
| 1 | Plate Special 1 x 2 with 1 Stud with Groove and Inside Stud Holder (Jumper) | 15573 | Orange | 6092599 |
| 1 | Brick Curved 2 x 1 No Studs [1/2 Bow] | 11477 | Orange | 6055069 |
| 1 | Cone 1 x 1 [Top Groove] | 59900 (BrickLink 4589b) | Orange | 4518029 |
| 1 | Brick Special 1 x 1 Studs on 4 Sides | 4733 | Black | 473326 |
| 1 | Plate 1 x 1 | 3024 | Black | 302426 |
| 1 | Tile 1 x 2 with Groove | 3069b (BrickLink 3069) | Tan | 4114026 |
| 1 | Flame / Headwear Accessory Plume / Feather, Triple Point | 64647 | Trans-Orange | 6314353 |

## Compared with the thumbnail

`out/renders/` has the three stills (`three_quarter`, `front`, `side`), made from this
model, put beside the orange figure in `inbox/charmander/unpacked/thumbnail.png`. The shape
matches: the dome with its black band under the high end, the tan belly, the two arms, the cone
with its flame, and the round feet. Differences, none of them in the parts:

- the thumbnail looks from behind and from the side of the tail, so it hardly shows the
  belly (only a sliver of tan behind the arm) and not the face; the stills look from the front;
- the Trans-Orange flame renders paler and clearer here than the beige-orange glass of
  Studio's picture;
- the orange is a little duller in the stills than the thumbnail's bright Studio orange: the
  same colour, different lighting.

## Quick Bricks

- `[quick]` in `model.toml`: a kraft surface in the workbench room, in day light, 14 seconds,
  clicks only (no music). Under 25 pieces, so the video opens with all 14 parts laid out on
  the table, then they float in one at a time.
- The close-ups are set to `highlight = ["flame", "face"]`: the flame as it goes on the tail,
  then the dome and its black band.
- `azimuth_offset` makes the camera start on Charmander's face.
- `brickkit status charmander --check` says `clean`: no `quick:` warning, so every piece has a
  way in. The cone and flame slide on from the back, along the stud's line, and the planner
  finds that way itself; no `insert=` hint is needed.
- The booklet and the video have not been made. `collection = "quick_bricks"` is not set: it is
  not on the site.
