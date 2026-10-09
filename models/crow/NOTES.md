# Crow

A Quick Bricks model: 34 pieces, 7 cm from beak to tail, 4.3 cm tall and 3.7 cm across the
wings. A little black crow with a pointed beak, half-closed eyes, wings and tail feathers on
clips, and yellow feet. The design is another builder's: Rebrickable MOC-165060 by
Qrys.And.Reading. It was imported from the designer's BrickLink Studio file, so every part is
where the designer put it (one, under the belly, to within 0.25 LDU).

All checks pass except stability, which is switched off: the crow only balances on its feet
(see *What had to be worked out*). The eye print is rare, which the parts check warns about.

## Source

- **From:** a BrickLink Studio file, `MOC-165060_Qrys.And.Reading_crow.io`: 34 parts in 12
  steps, no sub-models.
- **Designer / credit:** Qrys.And.Reading, Rebrickable MOC-165060
  (https://rebrickable.com/mocs/MOC-165060/). Someone else's design; credit them wherever
  the model is shown.
- **Saved in `reference/`:** nothing. The original file is in `inbox/crow/`, which is local
  only and never committed (the repo is public). The designer's picture of the finished model
  is `inbox/crow/unpacked/thumbnail.png`: the crow from its left side, head to the left.
- **Taken in:** 2026-10-08 with `brickkit import`; checked and written up by crow-agent.

## The plans, step by step

The crow looks to the left as you face the model (along -X) and its tail points right (+X).
"Front", "back" and the "front, middle and back studs" follow the crow: front is the beak
end. "Near side" is the side facing you (-Z, the crow's left), "far side" the other. The body
leans back 5 degrees on its feet, so "up" for the body is tipped 5 degrees towards the tail.

`design.py` has 13 steps for the crow: the designer's 12 in the designer's order, with step
7 split in two (see below). The beak and brow of step 8 are a sub-assembly with two short
steps of its own, so `brickkit all` counts 15.

| Step | Designer's step | Pieces | Where |
|---:|---:|---|---|
| 1 | 1 | 1x Plate 2 x 3 (3021), Dark Bluish Gray, and 1x Plate 1 x 2 with Clips Horizontal (60470b), Black | The grey plate is the belly, long side front to back. The clip plate goes across its two back studs, clips pointing back, for the tail. |
| 2 | 2 | 2x Plate 1 x 1 with Clip Vertical (4085c), Black | On the two middle studs of the belly, one clip out to each side, for the wings. |
| 3 | 3 | 1x Plate 1 x 2 (3023), Black, and 1x Plate 2 x 2 (3022), Dark Bluish Gray | The black plate across the two front studs of the belly. The grey plate on top of the three clip plates. |
| 4 | 4 | 1x Bracket 1 x 2 - 1 x 2 (99781), Black, and 1x Slope 30 1 x 2 x 2/3 (85984), Black | The bracket on the black plate, its side plate hanging down in front. The slope on the bracket's two forward studs, thin edge down: the chest. |
| 5 | 5 | 1x Brick Curved 2 x 2 x 2/3 with Two Studs and Curved Slope End (47457), Black, and 1x Jumper Plate 1 x 2 with 1 Stud (15573), Black | The curved brick on the grey 2 x 2 plate, studs to the front, curving down to the tail: the back. The jumper plate on the bracket. |
| 6 | 6 | 1x Jumper Plate 1 x 2 with 1 Stud (15573), Dark Bluish Gray, and 1x Plate 1 x 1 (3024), Black | The grey jumper plate on the curved brick's two studs, and the 1 x 1 plate on its stud: the neck. |
| 7 | 7 | 1x Brick 1 x 1 with Studs on 2 Sides (47905), Black | On the front jumper plate's stud, its side studs out to the near and far sides: the head. |
| 8 | 7 | 1x Jumper Plate 1 x 2 with 1 Stud (15573), 1x Plate 1 x 1 with Tooth (49668) and 1x Brick Curved 1 x 2 x 1 1/3 with Curved Top (6091), all Black | The beak and the brow, stacked in the hand first: the tooth plate on the jumper plate's stud, its point to the front, and the curved brick on the tooth plate's stud. The curved brick's tall curved end is over the tooth plate; its other end, a ledge with a stud, sticks out behind. Then the stack is pressed down onto the head: that ledge goes on the head brick's stud, and the jumper plate comes to rest on the chest, in front of the head. |
| 9 | 8 | 1x Slope Curved 2 x 1 (11477), Black | Its thick end on the stud of the brow's curved brick, its thin end on the 1 x 1 plate of the neck, curving down to the back: the back of the head. |
| 10 | 9 | 2x Jumper Plate 1 x 2 with 1 Stud (15573), Black, and 2x Tile Round 1 x 1 with Half Open Eye print (98138p8f), White | A jumper plate on each side stud of the head brick, flat against the head and reaching forward beside the brow, its own stud facing out. An eye on each of those studs. |
| 11 | 10 | 2x Plate 1 x 2 with Handle on End (60478), Black, 2x Tile Round 1 x 1 Quarter (25269), Dark Bluish Gray, and 2x Slope Curved 2 x 1 (11477), Black | The tail feathers. The two handle plates go in the two clips at the back, side by side, the near one tipped up 20 degrees and the far one 10. On each, a quarter tile on the stud next to the body, and a curved slope with its thick end on the end stud. Its thin end reaches one stud past the end of the plate, level with the plate's underside. |
| 12 | 11 | 2x Plate 1 x 1 Rounded with Handle (26047), Black, and 2x Slope Curved 2 x 1 (11477), Black | The wings. A handle plate in the clip on each side, standing on edge with its stud facing out, and a curved slope with its thick end on that stud, its thin end pointing back. The far wing is swung out 20 degrees, the near one 15. |
| 13 | 12 | 1x Shield Rectangular with 4 Studs and Handle (30166), Dark Bluish Gray, and 2x Plate 1 x 2 with Top Clip (92280), Yellow | The shield goes up under the belly, its four studs in the underside of the 2 x 3 plate, its handle down and running from side to side. The two feet clip onto the handle side by side, flat on the table, their studs to the front. |

## What was changed from the designer's file, and why

No part was moved. The whole model was shifted so its feet stand on y = 0; apart from that,
33 of the 34 parts are within 0.002 LDU of their places in the file. The 34th is the shield
under the belly: Studio's copy of that part has another origin and another way up than
LDraw's, so the import seated LDraw's part in the same place by its shape. That left it a
quarter of an LDU low (see *What had to be worked out*).

**Parts and colours** (done at import, before this write-up):

- **The eyes** are LDraw's `98138p8f`, Tile Round 1 x 1 with Half Open Eye print. The Studio
  file calls the same print `98138pb098`, its BrickLink number. Nothing changed but the name.
- **Five jumper plates:** the file has the old mould, 3794a (no groove). They are the
  current one, 15573, which is the one you can buy.
- **The clip plate for the tail:** the file has the old mould 60470a; it is 60470b now.
- **The shield under the belly (30166)** is Black in the file. That part was never made in
  Black, so it is Dark Bluish Gray, which 73 sets used. It is under the body: only its handle
  shows, as the legs.
- **The feet (92280)** are Medium Orange in the file. That part was never made in Medium
  Orange, so they are Yellow (13 sets).

**The build order** (done here):

- **Step 7 is split in two, and the beak and brow are a small sub-assembly** (`brow` in
  `design.py`). In the file's step 7 the jumper plate under the beak has nothing to click
  onto: it lies on the chest, and is held only once the tooth plate and the curved brick
  above it are on. By then nothing can reach it: the tooth plate cannot come up from below
  (the chest is 8 LDU under it) and the jumper plate would have to pass through the chest. So
  the three are stacked first and pressed on as one, which is how you would do it in the
  hand. `brickkit ways crow` now keeps the steps' order and finds a clear way for every
  piece.
- **Three `insert=` hints** tell the buildability check which way a piece goes on. They move
  nothing. The bracket of step 4 goes on from above; without the hint the check set the
  slope down first and then found the bracket blocked by it. The two wing handle plates of
  step 12 push into their clips from the side, for the same reason (the check tried each
  wing's slope first).

**In `model.toml` and `design.py`** (done here): the palette roles were renamed (`feather`,
`grey`, `shield`, `feet`, `eye`), the captions rewritten in plain words, and the eyes, beak,
tail, wings, legs and feet tagged for the video.

## What had to be worked out

- **Does it stand?** Only just, so the stability check is switched off in `model.toml`. It
  stands on its two feet, a patch of 2 x 2 studs. The check puts the whole crow at about 14 g,
  with its centre of mass 3 LDU (about 1 mm) in front of the back edge of the feet, 53 LDU
  up: it stands on a level table as posed, and tips back onto its tail at 3.2 degrees. That is
  the designer's pose, and no parts were added to change it. The body turns on the feet's
  clips: leaning it forward 5 degrees, to level, would put the centre of mass 6.5 LDU inside
  the edge (tipping at about 7 degrees). The model is left at the designer's 5 degrees.
- **The eye print is rare.** `98138p8f` came in one set, last in 2019 (LEGO elements 6258840
  and 6287770), so the parts check warns about it. It is the designer's print and it is kept.
  If it cannot be found, the standard eye, `98138p07` (Tile Round 1 x 1 with Offset Black Eye
  Print, in over 350 sets), fits the same studs; the crow then looks wide awake instead of
  sleepy. Rebrickable also lists a partly closed eye in 60 sets, 98138pr0027, which would be
  closer to the look; it has not been tried here.
- **The two eyes are turned differently** on their studs in the file: the far one is 30
  degrees round from where a plain copy of the near one would be. That makes its slant the
  mirror image of the near eye's, so both read the same from their own side in the renders.
  They are left as the designer set them.
- **The shield is 0.25 LDU (0.1 mm) low.** As imported, at (-22.288, -13.751, 0), its studs
  are 0.25 LDU short of fully home in the belly plate and its handle is 0.25 LDU above the
  middle of the feet's clips. Moved 0.25 LDU up along the body's own up, to
  (-22.266, -14, 0), both would be exact, with no collision: that is where the designer had
  it, and the difference comes from matching Studio's copy of the part to LDraw's by shape.
  Connections and collisions pass as it is and it cannot be seen, so it was not moved. It is
  a one-line change in `design.py` if wanted.
- **Against the designer's picture:** the renders (`out/renders/front.png` is the same view)
  match it part for part. Two colours differ, both from the substitutions above: the feet
  are yellow where the picture has orange, and the legs (the shield's handle) are dark grey
  where the picture has black.

## Parts and price

- 34 pieces in 21 lines; every part has a LEGO element ID.
- One line is rare: the two printed eyes (see above).
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1-$4. Prices have not been checked live.

## Quick Bricks

- `[quick]` in `model.toml`: the green cutting mat in the white studio, morning light, 14
  seconds, clicks only.
- 34 pieces, so they fly in one at a time; the grid of laid-out parts is for models under 25.
- Close-ups are asked for on an eye and on the beak (`highlight = ["eye", "beak"]`). The beak
  lands while the beak and brow are being stacked beside the model, before they are joined to
  the head. Look at that close-up in the preview, and take `"beak"` out if it does not read.
- The beak and brow are built beside the model and joined as one. For the last step the
  build is lifted and set down on its legs and feet. `brickkit status crow --check` says
  `clean`.
- The front of the model for the camera is the crow's left side, the designer's view; the
  video starts and ends on the three-quarter view, which shows the face.
- `collection` is still commented out: the crow is not on the site, and no booklet or video
  has been made yet.
