# Porygon

A Quick Bricks model: 19 pieces, 4 studs (3.2 cm) long, 4 studs across its feet and 2.9 cm
tall, about 9 g. A pink head and body, a blue beak, chest, feet and tail, and a round printed
eye on each side of its head. The design is another builder's: QSKSw's Porygon, Rebrickable
MOC-31400. It was read from a LEGO Digital Designer file, part by part.

All 8 checks pass, and `brickkit status porygon --check` says the build is `clean`.

## Source

- **From:** a LEGO Digital Designer (LDD) file, `MOC-31400_QSKSw_Porygon.lxf`. It is a zip of
  two files: `IMAGE100.LXFML` (XML: every part with its design number, LEGO colour number
  and a position) and `IMAGE100.PNG` (a 128 x 128 picture of the finished model, seen from
  its front right).
- **Designer / credit:** QSKSw, on Rebrickable: MOC-31400, "Porygon"
  (https://rebrickable.com/mocs/MOC-31400/). The design is theirs; the build order, the
  captions and this write-up are ours.
- **Saved in `reference/`:** nothing. The original file and its two unpacked files are in
  `inbox/porygon/` (`inbox/porygon/unpacked/`), which is local only and never committed.
  Nothing was downloaded.
- **Taken in:** 2026-10-08 by porygon-agent.

## The plans, step by step

The file has no plans of the designer's, so there is one row per step of our build order,
from the base up. Columns run left to right as you face the beak: x = -30, -10, 10, 30. The
body is the middle two; the feet are the outer two. Rows run front to back: the beak
(z = -30), the chest and head (z = -10), the back (z = 10) and the tail (z = 30).

| Step | Pieces | Where |
|---:|---|---|
| 1 | 1x Plate 2 x 4 (3020), Dark Azure | The base, its long side across: all four columns, the chest and back rows. |
| 2 | 1x Brick 1 x 2 (3004), Dark Azure, and 1x Brick 2 x 2 (3003), Dark Pink | The blue brick across the middle two studs of the chest row. The pink brick behind it on the middle two studs of the back row; its back half hangs over the plate's edge (the tail row). |
| 3 | 2x Slope 30 1 x 1 x 2/3 "cheese" (54200), Dark Azure | On the plate's two outer studs in the chest row, falling forward: the front of the feet. |
| 4 | 2x Slope 30 1 x 1 x 2/3 "cheese" (54200), Dark Azure | On the two outer studs in the back row, falling backward. Each foot is a little ridge, high in the middle. |
| 5 | 1x Plate 2 x 2 (3022), Dark Azure, and 2x Plate 1 x 1 (3024), Dark Pink | The 2 x 2 plate on the blue brick, its front half hanging forward (the beak row). The two 1 x 1 plates on the pink brick's front studs. |
| 6 | 1x Slope 30 1 x 2 x 2/3 (85984), Dark Azure | On the pink brick's two back studs, its high edge behind: the tail. |
| 7 | 2x Brick 1 x 1 with Stud on 1 Side (87087), Dark Pink | On the back studs of the 2 x 2 plate, side studs facing out, left and right: the head. |
| 8 | 1x Slope 30 1 x 2 x 2/3 (85984), Dark Azure | On the front studs of the 2 x 2 plate, falling forward: the beak. |
| 9 | 1x Plate 1 x 2 (3023), Dark Pink, and 1x Slope 30 1 x 2 x 2/3 (85984), Dark Pink | The plate across the two 1 x 1 plates, the slope on it, falling backward: the back of the head. |
| 10 | 1x Tile 1 x 2 (3069b), Dark Pink | On the two head bricks. |
| 11 | 2x Tile Round 1 x 1 with Eye (98138pb007; Rebrickable 98138pr0008, LDraw 98138p07), White | One on each side stud of the head. |

## How the file was read

- **Colours.** LDD gives LEGO's own colour numbers (`materials`). Three are used:

  | LEGO number | LEGO name | Name here (Rebrickable) | LDraw code |
  |---:|---|---|---:|
  | 1 | White | White | 15 |
  | 221 | Bright Purple | Dark Pink | 5 |
  | 321 | Dark Azure | Dark Azure | 321 |

- **Part numbers.** `designID` is the LDraw number, except:
  - 50746 is LDD's number for the cheese slope, 54200;
  - 3069 and 3023 are today's moulds, 3069b (tile with a groove) and 3023b;
  - 98138 with a `decoration` is the printed eye (see below).
- **Positions.** LDD's frame is Y up, 0.8 to a stud and 0.32 to a plate. The beak points along
  LDD's +x. Here the front is -Z, so a position converts as
  `X = -(z - 0.8) * 25`, `Y = 8 - y * 25`, `Z = -x * 25`. That is a turn, not a mirror.
- **Where LDD puts a part's origin.** On the part's underside, at the middle of one corner
  stud. From there, in the part's own frame:
  - the 2 x 4 plate runs four studs along +x and two along -z; the 2 x 2 plate and brick
    two along +x and two along -z;
  - the 1 x 2 plate, brick and tile run along +x;
  - the 1 x 2 slope (85984) runs along -z, and its low edge faces +x;
  - the cheese slope's low edge faces +z;
  - the 1 x 1 brick's side stud faces +z, 0.56 up (10 LDU below its top);
  - the round tile's origin is the middle of its underside.

  The file's own joints confirm the side studs and the eyes on them. Placed this way all 19
  parts meet stud to stud with no overlaps (26 stud connections), which is the proof.
- **The parts as read**, in the file's order (positions in our frame, LDU, as placed in
  `design.py`):

  | Ref | LDD part | LEGO colour | Part here | Where |
  |---:|---|---:|---|---|
  | 0, 4 | 98138, printed | 1 | 98138p07 | the eyes, x = 28 and -28 |
  | 1, 3 | 87087 | 221 | 87087 | the head, x = 10 and -10 |
  | 2 | 3069 | 221 | 3069b | on top of the head |
  | 5, 7, 11, 12 | 50746 | 321 | 54200 | the feet |
  | 6 | 3020 | 321 | 3020 | the base |
  | 8 | 3003 | 221 | 3003 | the body, back and tail rows |
  | 9 | 85984 | 321 | 85984 | the tail |
  | 10 | 3004 | 321 | 3004 | the chest |
  | 13 | 85984 | 221 | 85984 | the back of the head |
  | 14 | 3023 | 221 | 3023b | under it |
  | 15, 16 | 3024 | 221 | 3024 | under that |
  | 17 | 85984 | 321 | 85984 | the beak |
  | 18 | 3022 | 321 | 3022 | under the head and the beak |
  | 19 | 85984 | 221 | (left out) | loose on the ground, behind the left back corner |
  | 20 | 3021 | 321 | (left out) | loose on the ground, about 11 studs behind |

## What had to be worked out

- **The file has 21 parts; the model is 19.** Parts 19 and 20, a Dark Pink 1 x 2 slope
  (85984) and a Dark Azure 2 x 3 plate (3021), are not part of the model as the file has it,
  and are left out here:
  - each lies flat on the ground on its own, joined to nothing: one two studs behind the
    back left corner, the other about 11 studs away;
  - the designer's own group in the file holds parts 0 to 18 only;
  - the model has no free stud for them: every top is a tile or a slope. They could only go
    underneath;
  - the picture shows a finished Porygon without them. Both lie straight behind the model
    from the picture's camera, so it cannot show whether they were there.

  They look like spares set aside while designing. Rebrickable's page may still count 21:
  it was not checked (nothing was downloaded). Quite sure, but it is the owner's call. If
  they belong, they need a place the file does not give.
- **Which way the slopes face.** LDD does not say which edge of a slope is the low one. It
  was settled from the picture, and it is the only way round that makes sense. Sure.
  - The beak falls forward and the slope behind the head falls backward (they are half a
    turn apart in the file).
  - The tail is turned the same way as the beak, so its high edge is behind: it sticks up
    at the back. The picture shows this at its right edge.
  - The feet: the picture's near foot is plainly a ridge, high in the middle.
- **Mirrored or not.** Apart from the eye prints the model is the same left and right, so
  it hardly matters. The picture is taken from LDD's +x, -z side; that is our front right,
  and `three_quarter_right.png` matches it: the beak on the left, the eye facing right.
- **The eye print.** The file gives LDD's decoration 603159, which could not be looked up.
  The picture shows a white round tile with a big black pupil and a small light dot in it.
  That is taken to be the usual printed eye, 98138pb007 (the one Dracula has). Fairly sure.
- **How the eyes are turned.** That print's pupil sits off-centre, and how LDD turns its
  print could not be carried over. Both eyes are turned so the pupil is up and forward. The
  glint is in front of the pupil on the right eye, as in the picture, and on top on the
  left eye. A guess.
- **The build order is ours.** The file's only steps are LDD's automatic guide: the two
  loose parts first, then the model in five groups of three or four parts, worked out by
  the program. Ours goes from the base up in 11 steps of one to three pieces, each piece
  landing on something. The eyes go on last.
- **Nothing is hidden.** Every part's place comes from the file, so the structure is not a
  guess.

## Compared with the picture

Renders are in `out/renders/`; `three_quarter_right.png` is the picture's view.

- The shapes agree: the beak, the head with its tile, the ridge of the near foot, the tail
  behind the body.
- The colours are the same LEGO colours but look different. LDD draws Bright Purple as a
  strong magenta and Dark Azure as a greyer blue; our renders show Dark Pink lighter and
  Dark Azure brighter, as the real bricks are.
- The picture's pupil is nearly centred. The real print's is a little off-centre.
- The two loose spare pieces are not in the renders (see above).

## Parts and price

- 19 pieces in 12 lines. Every part exists in its colour and has a LEGO element ID; none is
  rare (the `real_elements` check passes).
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1-$2 (`out/price.json`: $0.75 to $2.39). It is not live market
  data, and Pick a Brick prices haven't been checked.

## Quick Bricks

- `[quick]` in `model.toml`: a green cutting mat in front of the bookshelf, in daylight,
  14 seconds, clicks only. Close-ups on an eye and the beak (the tags `eye` and `beak`).
- Under 25 pieces, so the video will start with every piece laid out in a grid.
- The build audit is clean: no piece needed an `insert=` hint. The beak's plate and the
  pink brick each hang over the base by a stud, and the eyes go on sideways.
- No booklet or video has been made yet, and `collection` is not set: it is not on the site.
