# Frankenstein

A Quick Bricks model: 17 pieces in 12 lines, a 2 x 2 stud base, 3.2 cm across the arms and about
4.5 cm tall. It is a flat-topped grey monster with sleepy white eyes, a grey brow bar, two white
neck bolts and grey arms, standing on a black body and base. The design is Agosami Brickworks'
MOC-215912 (see Source); this repo's model is built from its two pages of plans.

`design.py` has one step per numbered step 1-11 of the plans; the plans' step 12 is the finished
figure. All 8 checks pass and `brickkit status --check` says the build is `clean`.

## Source

- **From:** pasted instructions: a 2-page PDF, 12 numbered steps, each with a parts callout.
  Rebrickable MOC-215912, <https://rebrickable.com/mocs/MOC-215912/>.
- **Designer / credit:** Agosami Brickworks. This is their design, not ours; the model here only
  rebuilds it in code from their instructions.
- **Saved in `reference/`:** nothing, on purpose. The repo is public and these are the designer's
  own instructions, so the originals stay local, in `inbox/frankenstein/` (git ignores it):
  - `MOC-215912_Agosami Brickworks_Frankenstein.pdf`, the designer's instructions;
  - `pages/page_01.png` (steps 1-6) and `pages/page_02.png` (steps 7-12), the PDF's two pages
    rendered as pictures.
- **Taken in:** 2026-10-08 by frank-agent.

## The plans, page by page

Each page holds six numbered steps, so the rows below are the plans' steps, not pages. Left and
right are as you face him; the front is the side with the eyes (the plans draw him from the front
and a little from his right, so the right end is the one you see). Every piece of the body is one
stud deep; the base is two.

| Step | Pieces | Where |
|---:|---|---|
| 1 | 1x Plate 2 x 2 with 2 Studs on One Edge (33909), Black | The base. Its two studs run along the back edge, so the front row is a bare ledge. |
| 2 | 1x Plate 1 x 2 (3023), Black | On the two studs: the legs. |
| 3 | 2x Brick 1 x 1 with Headlight (4070), Black | Side by side on the 1 x 2 plate, each with its side stud facing out to its own side, so the two studs face away from each other. |
| 4 | 2x Plate 1 x 1 (3024), Black | One on each side stud, its own stud facing out. |
| 5 | 2x Tile Round 1 x 1 Half Circle (24246), Light Bluish Gray | One on each of those studs: the arms. The flat edge is at the top and the round end hangs down. |
| 6 | 1x Brick 1 x 2 x 1 2/3 with 8 Studs on 3 Sides (67329), Light Bluish Gray | On the two headlight bricks: the head. Its four-stud face is the front; each end has two studs, one above the other. |
| 7 | 2x Plate Round 1 x 1 with Solid Stud (6141), White | One on the lower stud at each end of the head, its stud facing out: the neck bolts. |
| 8 | 1x Plate 1 x 2 with 1 Stud (Jumper) (15573), Light Bluish Gray | Across the two lower front studs, its own stud facing front: the mouth. |
| 9 | 2x Tile Round 1 x 1 with Black Eye with Central Pupil Partially Closed Print (98138pr9976), White | On the two upper front studs: the eyes. The black half is at the bottom, with a white half-circle in it. |
| 10 | 1x Brick 1 x 2 with 2 Studs on 1 Side (11211), Light Bluish Gray | On the head's top studs, its two side studs facing front. |
| 11 | 1x Tile 1 x 2 (3069b), Black, and 1x Tile Special 1 x 2 with Sloped Walls, "gold bar" (99563), Light Bluish Gray | The tile on the two top studs of the step 10 brick: the flat top. The bar on its two front studs, its flat face with two dents out: the brow. |
| 12 | (finished) | |

LDraw has a model of every part above (the eye is `98138p2l`, Rebrickable's `98138pr9976`).

## What had to be worked out

The plans are drawn pictures, not part lists with numbers, so every part was matched by its shape
(`brickkit find`, `brickkit inspect`, and LDraw's own parts to compare prints). How sure each is:

- **Step 1, the base (33909): fairly sure.** A flat 2 x 2 with two studs along one edge; nothing
  else is that shape. The studs are at the back: step 2 puts the 1 x 2 plate on them and leaves a
  bare ledge in front, and the finished picture shows that ledge.
- **Step 3, the headlight bricks (4070): sure.** Each has a ring-like side stud with a small ledge
  under it. The plans only show the right one's stud; the left brick's must face the other way
  (the one next to it would be in the way), and the left arm in the later pictures confirms it.
- **Steps 4 and 5, the arms: sure.** A 1 x 1 plate on each headlight stud, then a half-round tile
  (24246) on the plate's stud. In LDraw the headlight brick's face is set back 4 units above a
  bottom ledge, so the plate sits on the set-back face with its top level with the brick's top.
- **Step 6, the head (67329): fairly sure.** The callout shows a 1 x 2 brick, 1 2/3 bricks tall,
  with four studs on one long face and two on the visible end; the other end is hidden in the
  picture. Step 7 puts a bolt on the left end too, so both ends have studs, which is 67329's
  "8 studs on 3 sides". 80796 ("8 studs on 2 sides") is the other brick like it, but has no studs
  on one end.
- **Step 7, the neck bolts (6141): the least sure part.** The callout is a stack of discs: three
  ridge lines round the base and a two-step stud on top, with a small sparkle in its corner that
  the plans do not explain. It has a solid top, so I took the plain round plate with a solid
  stud, in White. 85861 (round plate with an *open* stud) would show a hole. The ridges may be
  how the plans' drawing program shows this part's rim, as the render of 6141 is a plain plate
  with a stud. The bolt goes on the lower of the two stud rows on each end of the head, the same
  height as the mouth; the upper end studs stay bare, as in the finished picture.
- **Step 8, the mouth (15573): fairly sure.** A 1 x 2 plate with one stud in the middle. 15573
  is the current mould (used by more sets than 3794a or 3794b, which look the same in the
  picture). It goes on the lower two of the head's four front studs.
- **Step 9, the eyes (98138pr9976): fairly sure.** A white round tile printed with a black half
  disc (flat edge up) and a white half-circle inside it. Of the LDraw eye prints only
  `98138p2l` ("Half Circle Within a Black Half Circle", Rebrickable `98138pr9976`, BrickLink
  `98138pb366`) looks like that; the other half-closed eyes (`98138pr0027`, `98138pr0082`) have a
  curved lid line and a round pupil. The plans show the glint left of centre in both eyes; the
  print is symmetrical, so that is the drawing's angle. The tile is turned so the black half is
  at the bottom. Only 16 sets use it in white; the real_elements check still passes.
- **Step 11, the grey brow (99563): fairly sure.** The callout is a chamfered 1 x 2 piece, one
  plate thick, with two rectangular dents over the stud positions: that is the "gold bar" tile
  (LDraw `99563`, an alias of `96910`). It goes on the 11211's side studs with its dented face out,
  and fills the brick's front except for a 4-unit strip at the bottom, as in the finished
  picture. The black tile on top is the plain 1 x 2 tile 3069b (3069a looks the same).
- **The twelfth step.** It has no parts: it is the finished figure, so `design.py` stops at step
  11, as the Dracula model does with its page 12.
- **Colours.** Light Bluish Gray for the grey (the plans' grey is light and bluish; Dark Bluish
  Gray would be too dark). Black for the base, body, the small plates under the arms and the
  tile on top. White for the bolts and the eyes. Everything else is as drawn.
- **Size.** 40 x 40 units for the base (1.6 cm), 80 units across the arms (3.2 cm), 112 units tall
  (4.5 cm).

What does not match the plans' finished picture: nothing I can see. The renders (front and three
quarter) show the same head, eyes, bolts, brow bar, arms and base. Only the bolts' ridged look is
not reproduced (see step 7).

## Parts and price

- 17 pieces in 12 lines; every part has a LEGO element ID (the Pick a Brick list has all 12).
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1-$2 ($0.52 to $1.77 in `out/price.json`): from price bands, not live
  BrickLink prices, which haven't been checked.
- The eye print (98138pr9976 in White, 16 sets) and the 99563 bar are the least common parts.

## Quick Bricks

- `[quick]` in `model.toml`: the kraft surface, the night room and the evening light, 14 seconds,
  clicks only (no music). `collection` is left commented out: it is not for the site yet.
- Close-ups are tagged: `eyes` (the two eye tiles) and `bolts` (the two neck bolts).
- `brickkit status --check` says the build is `clean`: every piece goes on without passing through
  another, with no `insert=` hints needed. No preview or video has been rendered yet.
