# Chicken

A blocky white chicken, the Minecraft one, in 30 pieces, about 5 cm tall: a printed face, an orange
beak over a red wattle, a 2 x 2 wing on each side and yellow legs. zeldar's design, built the way
zeldar's instructions build it.

## Source

- **From:** the owner's link, https://brickit.app/ideas/1ff0b486-ec13-474b-b23a-42492bd06964
  ("Chicken by @zeldar", 30 bricks), and 9 phone screenshots of the Brickit app, pasted in chat on
  2026-11-04: the model's picture, its parts list (two screens) and the instruction pages, four to
  a screen (the last screen's top row repeats pages 19 and 20).
- **Designer / credit:** zeldar. `source` in model.toml.
- **Saved in `reference/`:** `hero.png` the Brickit page's large picture (og:image, 1864 x 1908,
  much sharper than the phone's); `screen_01.png` the app's picture; `screen_02.png`,
  `screen_03.png` the parts list (shapes and part numbers, no colours); `screen_04.png` to
  `screen_09.png` the 22 instruction pages, new pieces outlined in red.
- **Taken in:** 2026-11-04 by lead.

## How it was read

Each page was cut out of the screenshots and a render of the model, built to the same step, laid
over it from the app's camera (orthographic, 45 degrees round, 30 up; fitted on page 1). Pages 2 to
4 show the plate turned over, underside forward; they were rendered turned the same way. Every page
overlaps 93-95% (the drawings' black outlines are the rest), and the zoomed overlays agree piece for
piece. Things only the overlays settled:

- **The headlight brick is in the middle of the front row** (page 7: 0.94 there, 0.86-0.91 in the
  other places), so page 8's two plates are the front corners.
- **The wings are centred on their side studs** (page 10: 0.94, against 0.85-0.88 a half stud
  off). A 2 x 2 plate's tube is hollow, a stud's width inside, so one stud goes up into it.
  LDCad's snap for the tube only has its outside; `brickkit/data/shadow/parts/3022.dat` adds the
  stud hole in the middle.
- **The left wing shows only as a strip** along the top of the body's left edge: it is the same as
  the right one, 2 LDU proud of the top.
- **The head:** a 47905 on the headlight brick's recessed front stud, its own top stud forward; a
  2 x 2 plate on its left side stud; the second 47905 a stud higher and a stud further forward, in
  that plate's front upper hole (page 13: 0.945, against 0.935 straight above it).
- **The two 1 x 1 tiles are the backs of the legs** (page 4), not part of the face. Only that way
  do the pages add up to the app's list: the seven 1 x 1 plates are two on page 8, two on page 14
  and one each on pages 15, 17 and 18, each of which needs a stud.
- **The eyes are a printed tile:** LDraw 3069bpx3, Tile 1 x 2 with 2 Black Squares (keywords
  "Chicken, Eyes, Minecraft"), Rebrickable 3069bpr0250, element 6252683 in White. The app's list
  says only 3069B. Squares at the bottom (page 20), centred (0.937 against 0.92 half a stud off).
- **Colours from the large picture:** White, Yellow legs, Orange beak, Red wattle.

## The plans, page by page

| Page | Pieces | Where |
|---:|---|---|
| 1 | 11212 White | the 3 x 3 plate |
| 2 | 2 x 36841 Yellow | turned over: a bracket under each side of the middle row, flange on the plate |
| 3 | 2 x 73825 Yellow | the legs, each on its bracket's side stud by its upper stud; their plates the feet |
| 4 | 2 x 3070b Yellow | a tile on each leg's lower stud, at the back |
| 5 | 2 x 87087 White | the middle row, side studs out to the sides |
| 6 | 2 x 3622 White | front and back rows |
| 7 | 4070 White | the headlight brick, front middle, headlight forward |
| 8 | 2 x 3024 White | the front corners |
| 9 | 3021 White | behind them |
| 10 | 2 x 3022 White | the wings, centred on the side studs |
| 11 | 47905 White | the head's lower brick, on the headlight's stud |
| 12 | 3022 White | the head's left side |
| 13 | 47905 White | the head's upper brick, a stud higher and further forward (here with page 14's plates, a sub-assembly) |
| 14 | 2 x 3024 White | upright behind the upper brick, filling the gap to the headlight brick |
| 15 | 3024 White | on the lower brick's stud |
| 16 | 36840 Red | the wattle: its plate on that stud, its other plate flat underneath |
| 17 | 3024 Red | upside down under it, its stud showing below |
| 18 | 3024 White | on the red bracket's stud |
| 19 | 3022 White | the head's right side |
| 20 | 3069bpx3 White | the face (here half a stud to the right) |
| 21 | 15573 Orange | the beak: a jumper on the white plate's stud |
| 22 | 3069b Orange | a tile on the jumper's hollow stud |

## Not exactly as the app, and open questions

- **The face tile is half a stud to the right.** zeldar centres the 1 x 2 face tile on the upper
  47905's top stud, which is solid. A real 1 x 2 tile has a pin in the middle of its underside,
  as the 1 x 2 plate has (LDraw draws it on the 1 x 3 and 1 x 4 tiles; its 1 x 2 tile is older
  and leaves it out), so a solid stud cannot go in there: the tile has nothing to grip. The owner
  chose (2026-11-05) the nearest real fix with the same pieces: the tile half a stud to the right,
  on one of its own stud places (`EYE_X` in design.py). The face sits 4 mm off centre.
- **Pages 13 and 14 are one sub-assembly.** zeldar puts the upper 47905 on, then slides the two
  1 x 1 plates in behind it: they have to come in from the side and then press forward 4 LDU onto
  the brick (the headlight brick's top stud is right behind them), a two-part move neither the
  buildability check nor the video planner can make. Here the plates go on the brick's bottom
  first and the three go on together, from the right, into the left side plate's upper front
  hole. Every piece ends where zeldar's is.
- **Stability:** the head reaches out in front of 1 x 1 feet: it tips forward at about 3 degrees.
  zeldar's design: the check is set to 2 degrees in model.toml.

## Parts and price

30 pieces in 16 lines, every one with a LEGO element ID. BrickLink $2.85, Pick a Brick $2.47 with 1
line not sold there (the printed face tile: rare, one set, 2019), 2026-11-05, before shipping.

## Quick Bricks

Video made and on the site 2026-11-05. `[quick]`: the green mat, the window room, morning light; close-ups on the face
and the beak.
