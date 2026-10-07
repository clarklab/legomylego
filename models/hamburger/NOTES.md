# Hamburger: design notes

A life-size cheeseburger in six layers that are built separately and click together: bottom
bun, patty, cheese, lettuce, tomato and a domed sesame top bun. 590 pieces in 98 part/colour
lines, about 530 g. Rough price $27-$90 on BrickLink (estimate bands, not a live quote); every
line has a LEGO element ID, so `out/pick_a_brick.csv` covers the whole set.

An earlier version (767 pieces, square-stepped discs) was replaced by this one. The top bun has
been rebuilt twice since. First from a 29 mm stepped disc (a curved edge under three flat round
steps, 56 round tiles on the stud grid) to a 42 mm dome with 22 tan seeds. Then, after "I'd
take smoother and white seeds", to the one described here: the same height, the rim's upright
wall cut from about 10 mm to about 6, the flat stepped crown replaced by curved slopes round a
4 x 4 plate with quarter-circle corners, every curved slope seated at both ends, and 18 white
seeds.

## Size

| | Across | Tall | Pieces |
|---|---|---|---|
| Whole burger | 125 mm (4.9 in), the lettuce and cheese tips | 96 mm (3.8 in) | 590 |
| Bottom bun | 112 mm (14 studs across the flats) | 16 mm | 105 |
| Patty | 112 mm | 13 mm | 94 |
| Cheese | 125 mm tip to tip (a 90 mm square laid diamond-wise) | 6 mm | 83 |
| Lettuce | 121 mm | 13 mm | 46 |
| Tomato | 112 mm (two 64 mm slices) | 6 mm | 33 |
| Top bun | 112 mm | 42 mm (41.6: 38.4 to the crust, two seeds stand 3.2 proud; 0.37 of its width) | 229 |

## How the layers click together

Every layer under the top bun has the same 4 x 4 plate of studs in the middle of its top (cells
-2..1), and every layer above the bottom bun has plain plates under the middle of its bottom.
Nothing else rises above a layer's top face or hangs below its bottom inside the next layer's
footprint, so the four fillings sit on each other and between the buns in any order, in any
quarter turn. Joints hold 16 studs; lettuce to tomato holds 28 (the rosettes' own studs engage
the slices). `pose(t)` lifts each layer 90 LDU above the one below (five `lifts_off` groups),
the exploded stack in `out/hero_open/`.

The top bun is the lid. Its underside is the same as before (the 12-stud octagon of pale crumb,
plain plates in the middle), but its top is a dome of slopes, tiles and seeds with no free studs,
so nothing clicks on top of it. That was already so: the old crown was tiled all over.

All 24 orders of the four fillings between the buns were stacked and checked, again with the
new top bun: every order connects as one piece. The cheese's tips are
set at 30 degrees, which only clears the patty (it dips under each tip); in the 18 orders where
the cheese sits on something else the checks see the tips touching the layer below. In real
bricks the tips are friction clips and simply ride up.

## Construction

- **The octagon.** Buns and patty are octagons 14 studs across the flats, 15.2 across the
  corners. Wedge plates (6106) give the 45 degree flats but have stud notches along the cut edge,
  so they are only used in base layers, inset (12-stud octagon) or low on the patty. Above them
  the four diagonal flats are separate faces turned 45 degrees (kit.py `Face`, design.py
  `Diagonals`): each stands on smooth tiles and is pinned through one anti-stud by a round 1 x 1
  plate or a 2 x 2 jumper (87580) on a grid corner, chosen so the face moves 2-4 LDU at most;
  the on-grid sides beside it keep it straight.
- **Bottom bun.** Medium Nougat crust round a tan cut face: a base, a floor, and 2 x 2 curved
  slopes all round so the crust curves in under the patty.
- **Patty.** Reddish brown with dark brown seared edges and grill marks on top. The middle of
  each side is a pair of curved slopes set a plate low, so the cheese's tip can hang over it.
- **Cheese.** Bright Light Orange, |x| + |z| <= 8 studs with triangle tiles on its edges. Each
  tip is a sub-assembly (a clip plate 60470b, a plate and two triangle tiles) clipped onto the
  handles of two 60478 plates 5.5 studs out, so it hinges along the line and hangs at 30 degrees.
- **Lettuce.** A green octagon with twelve leaf rosettes (15469) round the edge, each on a 2 x 2
  plate so its leaves droop clear of the base; the base is cut back between the side pairs.
- **Tomato.** Two slices 4 studs in radius (four 30565 each), red skin and flesh rings (27507,
  79393) round a coral middle (27925, 14769), joined by the stud plate over their inner quarters.
- **Top bun.** A dome in four bands over the tan cut face, so the outline turns over from
  upright to flat like a quarter of an ellipse 112 mm wide and 42 mm tall. Rim, slope and ring
  are eight flats each (four on the stud grid, four turned to the diagonals); the crown is
  square to the grid with round corners:

  | Band | From the axis | Rises to | Parts |
  |---|---|---|---|
  | Rim | 6-7 studs | 19 mm | one plate (3.2 mm upright), then a quarter-round brick (37352) |
  | Slope | 5-6 studs | 26 mm | 30 degree slopes (85984) on a brick |
  | Ring | 3-5 studs | 32 mm | 2 x 2 and 2 x 1 curved slopes (15068, 11477) |
  | Crown | 0-3 studs | 38 mm, two seeds to 42 mm | curved slopes round a 4 x 4 plate, quarter-circle corners (5852) |

  Each band starts with a 2 mm lip (the thin end of its slopes); nothing else steps. The floor
  stops a stud short of the rim all the way round, so the bun's edge tucks in underneath: 6 mm
  of pale crumb and crust floor, then the rim overhanging on a 2 x 4 plate (a 1 x 1 plate is
  pressed up under each end of each side's quarter-round bricks to fill the corner). The rim
  and the slope share one set of turned corners (a 2 x 4 plate, two quarter-round bricks in
  front, a 1 x 4 brick and the slope behind), pinned as on the bottom bun. The middle is solid:
  a layer of bricks, one of plates, and a deck of plates with smooth tiles where the ring's
  corners stand.
- **Curved slopes sit on two levels.** The underside of a curved slope (11477, 15068, 5852; the
  3-long 50950 and 24309 too) is cut back by a plate under its high end: the low end's stud
  holes are at the bottom, the high end's a plate higher (LDraw's geometry and LDCad's snap
  data agree). On a flat plate only the low end clutches and the high end hangs 3.2 mm clear.
  So in the ring and the crown every slope straddles a plate edge: the ring's on-grid slopes
  stand on a 2 x 2 plate with a 1 x 2 on its inner half, its turned corners on a 2 x 3 with a
  1 x 3 on the inner row (three 2 x 1 slopes across both, pinned by the middle of the inner row
  on the diagonal's own stud, cell 2, 2); the crown's stand on a round 6 x 6 plate (11213)
  with their high ends on the edge of a 4 x 4 plate. Every one of them now holds by both ends.
  (The bottom bun's and the patty's 2 x 2 curved slopes still stand on flat plates and hold by
  their two low studs; they were not part of this change.)
- **The crown** is the 4 x 4 plate with a 2 x 2 curved slope (or two 2 x 1) over each side and
  a quarter-circle curved slope (5852) on each corner, a cushion 6 studs across and 6.4 mm
  high whose top is level with the tiles in its middle: no step, where the old crown was a flat
  disc standing 3.2 mm proud. The 5852's high corner has a 1 x 1 cutout that sits on the
  plate's corner stud; its two low cells would take studs from the level below, but the round
  plate has none there, so each corner holds by one stud, lies flat on the round plate and is
  locked between the slopes on either side. The engine had no connection data for 5852; it is
  in `brickkit/data/shadow/parts/5852.dat` (three stud holes, read from the part's LDraw mesh).
- **Sesame seeds.** 18 white 1 x 1 tiles in three shapes (9 quarter-round 25269, the teardrop;
  5 half-round 24246; 4 round 98138), every one on a stud: 5 on the crown, 5 on the ring, 3 in
  the ring's gaps and 5 on the slope, none on the rim, so they thin out toward the edge. Two of
  the crown's sit on 1 x 2 jumper plates, half a stud off the grid and a plate proud, turned to
  their own angles (a 1 x 1 tile on a lone stud turns freely); the third lies flush in the
  middle. Everywhere else a seed takes the place of the top of one lane of slope: a 1 x 1 slope
  (54200) below it and the seed on the upper plate's stud, level with the slopes' tops (on the
  slope band, on the bare stud beside a 1 x 1 slope, level with its middle). On the turned
  corners that puts them at 45 degrees to the rest. Between each of the ring's on-grid slopes
  and the turned corner beside it is a wedge-shaped gap, filled by a round 1 x 1 plate and a
  quarter tile level with the slope beside it; three of those are seeds. The layout is the
  tables at the top of the top bun's section in `design.py` (`SLOPE_SEEDS`, `RING_SEEDS`,
  `GAPS`, `CROWN_*`), picked by polar angle so that no three near each other line up. With
  white on the nougat crust 18 read as plenty (22 tan ones were hard to see).

## Known limits

- The bun and patty edges are octagons with curved slopes, not true circles: LEGO makes no round
  part between 10 and 20 studs across in these colours. Where a turned face meets a straight side
  there is a narrow V-shaped gap in the curved edge.
- Each turned face is held by one stud and wedged between its neighbours, not clutched on all
  its studs; it can be knocked sideways a little until the layer above is on. The top bun has
  eight (four rim corners, four ring corners), as before, and the crown's four quarter-circle
  corners hold by one stud each, though those are square to the grid and locked in.
- The top bun's dome is still made of bands: a 2 mm lip where each begins, a flat 30 degree
  facet for the slope band, and the seams and V-shaped gaps of the octagon. The rim stands
  upright for about 6 mm before it turns over. It is not a moulded dome.
- Parts that could go further were looked at and left out. The quarter-rounds 1 2/3 bricks tall
  (5907, 7527) would turn the rim over from its very bottom, but they are two studs deep, which
  doubles the V-shaped gaps at the octagon's corners (a ring of rectangles leaves 2 pi times
  its depth of gap round the outside: 126 LDU for one stud, 251 for two). The 3 x 3
  quarter-circle 76797 makes a seamless round cap 6 studs across but has no studs, so the crown
  would carry no seeds. The inverted curved slopes (24201, 32803) would round the rim's
  underside; they have studs on top and, in LDraw's file, no stud hole underneath (the pocket
  there is 14 LDU wide and under 4 deep), so they can only hang from the part above, and a
  turned corner built on them has nothing left to be pinned through. None of the three needed
  new connection data to rule out; their stud holes were read the same way as 5852's (5907:
  front 0, 40, -20 and back 0, 16, 0; 7527: the same at x = -10 and 10; 76797: the corner cell
  0, 16, 0 and four more at y = 24) and can be added when a model wants them.
- The seeds are 8 mm tiles, about twice the size of real sesame seeds, and there are 18 of them
  where a real bun has a hundred or more.
- Some base studs of the lettuce show between the rosettes, under their leaves; each tomato
  slice's inner quarter is the shared stud plate, so its pale middle reads as a C.
- Computer-checked only: clutch, clip friction and how the turned faces feel need a real build.
- Part popularity on Pick a Brick was not checked; every part is a common one in 3 or more sets
  since 2016 in its colour (`real_elements`: 0 rare).

## Checks

`brickkit all hamburger`: all eight pass. real_elements (98 combinations, 0 not real, 0 rare),
connections (1942; one piece), collisions (0), buildability (521 insertions, 96 steps of at most
8 parts), stability (tips at 47.6 degrees), mechanism (24 poses, 5 lift-off groups), electrics
(none), technique (0 notes).

## Files

`design.py` builds the six layers, the pose and the step splitting; `kit.py` holds the grid
helpers (octagon layers, rectangle packing that keeps two plate layers bonded, turned faces).
Renders: `out/hero/hero.png`, `out/hero_open/hero.png` (exploded), `out/renders/side.png`,
`out/renders/top.png`, `out/renders/three_quarter.png`.
Outside this folder the model needs one engine data file,
`brickkit/data/shadow/parts/5852.dat` (the stud holes of the crown's quarter-circle corners);
without it those four parts are not seen to connect and the connections check fails.
