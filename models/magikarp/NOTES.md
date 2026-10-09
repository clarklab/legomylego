# Magikarp

A Quick Bricks model: 43 pieces in 22 lines, 6.5 cm from mouth to tail, 6.4 cm from fin tip to
fin tip and 2.6 cm across the eyes (the red body alone is 4.8 x 3.5 x 2.2 cm). A red Magikarp
with round white eyes, an open lavender mouth, a white forked tail, a white triangle fin at each
side and a yellow fin on its back and under its belly. It is someone else's design (see Source),
built here from their instructions: 14 numbered steps on 9 pages. It is built sideways off two
brackets. `design.py` follows the plans step by step, and each step was rendered and laid beside
the plans' drawing of that step before going on. The seven checks that are on pass
(`real_elements` with one warning: the mouth is a rare part); the stability check is off,
because the fish balances on its belly fin (see *Things to know when building it for real*).

This is the second modelling of it. The first (same day, by karp-agent) passed the checks but
was not the model in the plans: see *What the first attempt got wrong* at the end.

## Source

- **From:** the designer's instructions, a 9-page PDF: 14 numbered steps with parts call-outs
  (two of them with a boxed sub-build), the finished fish on page 8, and a parts list with LEGO
  element IDs on page 9.
- **Designer / credit:** **Redverse**, "Pokemon Magikarp", Rebrickable MOC-182443
  (https://rebrickable.com/mocs/MOC-182443/). This is their design, not ours; the model here is
  a re-drawing of it in code from their instructions. Credit them wherever it is shown
  (`designer` and `source` are set in `model.toml`).
- **Saved in `reference/`:** nothing, on purpose. The repo is public and the designer's
  instruction pages are not ours to publish. The originals stay in **`inbox/magikarp/`** (local
  only, git ignores it): `MOC-182443_Redverse_pokemon_magikarp.pdf` and `pages/page_01.png` to
  `page_09.png`. Each PDF page is one picture 1684 pixels wide; read it at that size, the
  1400-pixel copies in `pages/` are too small for the small parts.
- **Taken in:** 2026-10-08 by karp-agent; modelled again from the plans the same day by
  karp2-agent.

## The plans, page by page

How things are named. **Top** is the fish's back, **belly** its underside, **tail end** and
**head end** its two ends, a **side** is where an eye is. The plans turn the model over after
step 4 (steps 5 to 8 are drawn belly up), back after step 8, and round to its other side after
step 11; this table always says top and belly as in the finished fish. Rows of studs are
counted along the fish from the tail end: the **tail row**, the **fin row**, the **eye row**
and the **head row**, a stud apart. Part numbers are LDraw/Rebrickable numbers; page 9's
element IDs are in *Parts and price*.

| Step | Page | Pieces | Where |
|---:|---:|---|---|
| 1 | 1 | 2x Plate 2 x 2 (3022), Red; 1x Bracket 1 x 2 - 1 x 2 (99781), Red | The two plates stacked. The bracket on their tail row of studs, its wall hanging down over the plates' tail end, its two side studs facing the tail. The plates' other row of studs stays free. |
| 2 | 1 | 1x Bracket 1 x 2 - 1 x 2 (99781), Red; 1x Plate 2 x 4 (3020), Red | Both **upside down**. The 2 x 4 lies under the two plates, its hollow underside against theirs, level with them at the tail end and reaching two studs further towards the head. The bracket is on the 2 x 4's tail row of studs (they point down); its wall stands up over the end of the 2 x 4 and of the lower 2 x 2 plate, straight under the first bracket's wall. The two walls make a square of four side studs facing the tail. Nothing holds these two pieces to the first three yet. |
| 3 | 1 | 2x Slope 45 2 x 1 with 2/3 cutout (15672), Red | One on each side, standing on end against the two walls: its underside takes an upper and a lower side stud, and that locks the two halves together. Its stud end is at the top (the stud faces the tail), its wedge below, sloping down and in towards the belly. |
| 4 | 2 | 2x Plate 1 x 2 with pin hole underneath (18677), Red; 2x Technic Pin 1/2 without friction (4274), Blue; 1x Bar 3L (87994), Black | Boxed sub-build: (1) a pin pushed into the hole under a plate from outside; (2) the second plate beside the first, its pin from the other side; (3) the bar through both pins, sticking out the same at each end. The assembly goes on the free row of studs of step 1 (the fin row), its holes hanging over the hollow of the 2 x 4 a row further on (the eye row): the eye axle, across the fish. |
| 5 | 3 | 1x Plate 1 x 2 (3023), Red; 1x Plate 1 x 2 with 1 stud, "jumper" (15573), Red | On the two slopes' studs, facing the tail: the plate across both, then the jumper on the plate. Its face is level with the tips of the slopes' wedges. |
| 6 | 3 | 1x Slope inverted 45 3 x 1 double (18759), White; 2x Slope 30 1 x 1 x 2/3, "cheese" (54200), White | The 3 x 1 slope on the jumper's stud by its middle, upright, its three studs facing the tail: it flares from the body out. A cheese slope on its top stud and on its bottom stud, thick ends outwards: the forked tail. |
| 7 | 4 | 2x Bracket 1 x 1 - 1 x 1 inverted (36840), Red; 1x Plate 1 x 2 (3023), Red | Under the belly. A bracket on each stud of the 2 x 4's fin row (the row next to the big bracket), its wall on the outside, its side stud facing out. The plate across the two brackets' studs, between their walls. |
| 8 | 4 | 1x Plate 1 x 2 with 1 stud, jumper (15573), Red; 1x Slope 30 1 x 2 x 2/3 (85984), Red | Under the belly. The jumper on that plate; its stud points down, for the belly fin. The slope on the upside-down bracket's two studs (tail row), its thick end against the jumper and level with it, falling towards the tail. |
| 9 | 5 | 1x Plate 1 x 2 (3023), Red; 1x Technic Brick 1 x 2 with hole (3700), Red | On top: the plate on the axle plates' fin-row studs. The head: the brick **upside down** at the head end, lying on the hollow side of the 2 x 4 with its two studs pressed down into it (head row); its hole faces forward, its hollow underside is up, level with the top of the core. |
| 10 | 5 | 1x Technic Pin 1/2 with friction (89678), Red; 1x Plate 1 x 2 with 1 stud, jumper (15573), Red; 1x Plate 1 x 1 (3024), Red | The pin in the head's hole from the front, its stud forward. On the plate of step 9: the jumper, and the 1 x 1 plate on its stud. That makes a tower three plates high with one stud on top. |
| 11 | 6 | 1x Dish 2 x 2 inverted (4740), White; 1x Tile 2 x 2 triangular (35787), White | The eye: the dish on the blue pin's stud, the bar's end in its middle. The side fin: the triangle on the small bracket's side stud, held by the one stud holder at its square corner and turned so that the square corner points forward and the long edge stands upright behind it. |
| 12 | 7 | 1x Dish 2 x 2 inverted (4740), White; 1x Tile 2 x 2 triangular (35787), White | The same on the other side. |
| 13 | 7 | 1x Dish rectangular, from the Friends kitchen implements (97785), Lavender; 3x Brick curved 2 x 2 with lip, no studs (30602), Red | The mouth: the dish on the red pin's stud, opening forward, its long side upright. One curved brick on the first bracket's studs (tail row, on top), high end against the tower, falling to the tail, its lip over the root of the tail. One on the axle plates' eye-row studs, lying over the head brick, high end against the tower, falling to the mouth. One upside down under the 2 x 4's eye and head rows, high end against the belly jumper, falling to the mouth. |
| 14 | 8 | 2x Brick 1 x 1 with studs on 2 opposite sides (47905), Yellow; 6x Slope 30 1 x 1 x 2/3, cheese (54200), Yellow | Boxed sub-build, made twice: (1) the brick; (2) a slope on each side stud with its thick end up, and one on top, falling to the front. One goes on the tower's stud, its side slopes fore and aft: the dorsal fin. The other goes upside down on the belly jumper's stud. Page 8 is also the finished picture. |

Page 9 is the parts list: 21 lines with element IDs, and the lavender dish with none.

## What had to be worked out

The plans are small isometric line drawings and no 3D file was available. Every step was read
from the picture, placed with the engine's connection data, rendered from the plans' camera and
laid beside the drawing; where a drawing was hard to read, distances were measured in it (a
plate is about 25 pixels high on page 1).

- **Step 2, how the 2 x 4 plate is held (sure).** The side of the step 2 drawing shows **five**
  layers one plate high: the first bracket, the two 2 x 2 plates, the 2 x 4, and under it the
  second bracket's plate. The 2 x 4 is drawn hollow side up, with its studs showing as bumps
  underneath, so the second bracket must be upside down on those studs, wall upwards. The two
  walls together measure 40 units in the drawing, which only fits that way round. So the 2 x 4
  hangs on **real studs**: its two tail-end studs are in the second bracket, the second
  bracket's two side studs are in the lower ends of the step 3 slopes, and the slopes' upper
  ends are on the first bracket's side studs. The undersides of the 2 x 4 and of the lower 2 x 2
  plate only touch. There is no `press_fit` and no `allow_contact` in the model.
- **Steps 2 and 3 are one step here (a real difference in the order, not in the model).** In
  the plans, step 2 leaves the 2 x 4 and its bracket held by nothing; you hold them until step
  3's slopes are on. The checks want every step to end in one piece, so `design.py` builds the
  2 x 4 with its bracket apart ("Belly plate", the right way up), then one step turns it over,
  holds it under the stack and presses the two slopes on.
- **Step 3, which way up the slopes go (sure).** The drawings of steps 3 and 4 show their studs
  in the upper row and the wedges below; step 5's plate and jumper sit on those studs, level
  with the wedge tips, exactly as drawn.
- **Step 7 (sure).** The foot of the small brackets' walls is drawn level with the 2 x 4's stud
  face, and the plate's studs one plate above the upside-down bracket's: so the brackets are on
  the 2 x 4 and the plate lies across the brackets, not the other way round. The render of this
  step matches the drawing stud for stud, and the side fins of step 11, which hang on these
  brackets, come out at the drawn height.
- **Step 9, the head (sure).** The brick is drawn hollow side up and level with the top of the
  core: it is upside down on the hollow side of the 2 x 4, studs in the 2 x 4's stud holders.
  The plate of step 9 is on the fin row, so the tower of step 10 has **three** layers, as
  drawn.
- **Steps 11 and 12, the side fins (sure).** The triangle holds on one stud, so it can turn;
  its angle and which of its three stud holders is used were measured in the step 11 drawing.
  The long edge is upright (within a degree or two) and 14 units behind the stud, where the
  model has it; the square corner points forward. That is the corner holder, the tile turned
  45 degrees. Placed as the plans draw it, not turned to make the fish stand.
- **Step 13, the mouth (sure of the part, the colour and which way round).** Page 9
  gives it no element ID. It is drawn as a rounded-square tub with a thick rim, walls that lean
  out, and a small notch at the foot of one wall, in a very pale purple. Looking through
  everything the catalogue lists in Lavender found **97785, the rectangular dish of the Friends
  "Kitchen Implements" kit (93082)**: 35 x 30 units at the rim, 15 high, one stud holder in the
  middle of its base, a notch at the foot of each short wall (where it was cut from its
  sprue). It matches the drawing down to the notch, and it sits centred on the pin. The drawn
  colour (#ECDEF8) is Lavender (#E1D5ED) made a little lighter, the same way the plans draw
  their yellow. It has no element ID because LEGO only makes it as one of nine implements on a
  sprue: the ID belongs to the whole kit (in Lavender: 6284047 or 6299790). The catalogue has
  the dish in Lavender in one set, last in 2019, so `real_elements` warns that it is rare. The
  plans show the notch on the dish's upper wall (pages 7 and 8), so its long side is upright;
  a close render of the mouth from page 8's camera matches the drawing. Its upper wall
  then sits just under the front curved brick's lip and its base touches that brick's end
  face; nothing overlaps (the collision check finds none even at a tenth of its usual
  tolerance), but it is the tightest fit in the model.
- **Step 13, the curved bricks (sure).** Element 6247388 is 30602 in Red, the right part. Their
  places follow from the studs left free: the first bracket's two on top, the axle plates' two
  on the eye row, and the 2 x 4's last four underneath. With the tower three plates high they
  meet it flush on both sides, and the three of them give the smooth ellipse of page 8.
- **Step 14, the fins (sure).** The slopes are as the boxed sub-build and page 8 draw them: side
  slopes fore and aft with their thick ends away from the body, the end slope falling to the
  front. The belly fin is the same sub-build turned over about the fish's length, so its end
  slope falls to the front too: both ways round were rendered from page 8's camera, and only
  this one gives the drawn outline (thick at the tail side). Nothing collides: the fins' side
  slopes clear the curved bricks by 4 units or more.
- **Colours (sure).** From page 9's element IDs: Red, White, Yellow, Blue pins, a Black bar.

### What still differs from the plans

- The order only: the plans' steps 2 and 3 are one step, with the 2 x 4 and its bracket as a
  sub-assembly (above). Every piece is where the plans put it.
- Nothing else that could be found. The three-quarter render (`out/renders/three_quarter.png`)
  and a line render from page 8's own camera were compared with page 8: the outline, the
  centred mouth with its notch on top, both yellow fins, the eye and the side fin agree.

### Things to know when building it for real

- The fish **does not stand**: it touches the table with the tip of its belly fin only. The
  stability check is switched off in `model.toml` for that reason; the model was not changed
  to make it stand.
- The side fins and the mouth each hold on one stud and can turn: set the fins with the long
  edge upright and the mouth with its long side upright.
- The upper and lower halves are joined only by the two slopes at the tail (four studs).
  Elsewhere they just lie against each other, so pick it up by the body, not by the head.

## Parts and price

- **43 pieces in 22 lines** (`out/parts.csv`), the same 22 lines and quantities as page 9 of
  the plans.
- **Element IDs:** 19 of page 9's 21 IDs are the same in `out/parts.csv`. Two differ in number
  only, same part and colour (LEGO has more than one ID for them and the parts list picks the
  newest): Bar 3L in Black is 6185316 here, 6093525 in the plans; Plate 2 x 2 in Red is 4613974
  here, 302221 in the plans.
- **The mouth has no element ID**, here as in the plans (see step 13 above). It is therefore
  not in `out/pick_a_brick.csv`. `out/bricklink_wanted.xml` lists it as 97785 in Lavender;
  BrickLink sells the kit's pieces under its own lettered numbers (LDraw's file for this part
  cites BrickLink 93082c: not checked on bricklink.com), so fix that line by hand when
  uploading. If Lavender cannot be found, the same dish was also made in Bright Light Orange
  (7 sets), Medium Blue (4), Red (2) and Yellow (1).
- `real_elements`: 22 part and colour pairs, all real, 1 rare (the mouth).
- The rough estimate is **$2 to $10** (not live prices; no BrickLink keys were used).
- Nothing was bought or put in a cart.

## Quick Bricks

- `[quick]` in `model.toml`: a blue cutting mat by the window in morning light, 14 seconds,
  clicks only. Close-ups, the face first: the tags `eye` (the two dishes), `mouth` (the dish)
  and `dorsal_fin` (the fin on its back). Other tags: `belly_fin`, `side_fin`, `tail`.
- `brickkit status magikarp --check` says the build is `clean`: every piece has a clear way in
  and lands on something. The belly plate is built beside the model and slid in underneath
  (the stack is lifted and set down on it), then the slopes lock it; pieces under the belly go
  on from below.
- Three `insert=` hints in `design.py`, each the way the piece really goes on: the belly plate
  from below; the tail before its two slopes; the two small brackets before the plate across
  them (without the hints the buildability check tried the later piece first).
- `collection = "quick_bricks"` is commented out in `model.toml`: it is not on the site until
  the owner says so. No booklet or video has been made of this version.

## What the first attempt got wrong

For whoever compares the two: the first attempt's trouble all came from step 2.

1. It put the 2 x 4 plate under the second bracket and held it with `press_fit`. In the plans
   it is between the 2 x 2 plates and the second bracket, which is upside down on its studs.
2. So its slopes went on the lower bracket only and its tail plates on the upper bracket, and
   the 2 x 4 with everything on it (the head, the mouth, the belly) sat a plate too low.
3. Its tower had two layers instead of three: the plate of step 9 was a row too far forward,
   under the front curved brick, which lifted that brick a plate too high. That is why the body
   read as blocky, and why the fins hit the curved bricks and were turned sideways.
4. Its mouth was a square grey box (35700), half a stud off centre; the part is 97785 in
   Lavender, centred.
5. Its side fins were turned 18 degrees to make the fish stand on three points.
