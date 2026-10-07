# Nautilus: design notes

Captain Nemo's Nautilus as Harper Goff designed it for Walt Disney's *20,000 Leagues Under the
Sea* (1954), at minifigure scale: an iron fish of a submarine with a ram, a toothed crest arching
from an alligator-head wheelhouse, a saw keel, a shark's dorsal fin, the big salon window on each
side ringed with lights, and a swept fish tail with a propeller and rudder. The port side of the
salon swings up like a gull wing on Nemo's salon and its crew; the salon lights up (Power
Functions), the propeller spins and the rudder swings. It rides a breaking sea on two clear posts.
One colourway, the film's: **rusty iron** (Reddish Brown plating on a Dark Bluish Gray iron
frame). (A steel one, Dark Bluish Gray on Black, was dropped: the model stays movie-accurate.)

- **7,126 LEGO pieces** in 408 part/colour lines (7,154 placed with the minifigures' parts and the
  two lamp heads), 1,492 instruction steps, about 7.9 kg with its stand (estimated).
- **Price**: roughly $284-$973 for the parts (price bands, `out/price_estimate.md`); the
  Power Functions light unit, extension wire and battery box are bought used.
- Every check passes (`out/report.html`); the warnings are rare parts: the
  battery box, the diver's helmet and some crew heads and torsos, and the squid's Red tentacle.

## Scale and size (1 LDU = 0.4 mm)

The scale comes from the salon window: in the profile photo of a finished display model its glass
is 80 px across, and here it is LEGO's biggest clear bubble (50747, a 6 x 6 half sphere, 120
LDU), so 1 px = 1.5 LDU: about **1:52**, and a minifigure stands at the window at eye height.

| | model |
|---|---|
| Length, tail tips to the ram's point | 2,660 LDU = **106 cm** (42 in) |
| Beam over the side keels | 480 LDU = 19 cm (20 cm over the windows' bubbles) |
| Hull, deck to keel strip amidships | 344 LDU = 14 cm |
| On its stand: overall height | 36 cm; the side keels 22 cm over the table |
| Stand (the sea) | an oval about 94 x 27 cm, 4 cm deep plus its waves |

The shape is traced from the profile photo (`naut_shape.py`: deck and belly lines, chine, tail
lobes, crest arch, dorsal fin, keel fins, saw keel, wheelhouse, window and the stand's posts, in
photo pixels).

## Structure (booklet order)

The hull frame: the side keels (the chine) centred on y = 0, the bow toward -X, the port side
toward the front (-Z). Cells are studs: column i is x in [20 i, 20 i + 20].

1. **Side keels** (`naut_frame`): the waterline flange, two plates, 24 studs across amidships and
   tapering 1:6, 1:4 and 1:3 (wedge plates) to the ram and the tail stock; two sub-assemblies
   (the salon's windows cut it in two), each laid out until it holds together.
2. **Salon windows** (`naut_window`): on bricks with side studs on the side keels, a raised boss
   built flat (a rectangle filling the gap in the side panels), the bubble on two click hinges,
   a brass ring of four macaroni tiles, eight yellow lights; open behind the bubble, so the salon
   shows through it.
3. **Core** (`naut_relief.core_batch`): a wall two studs wide on the side keels up to the deck and
   hanging under them down to the keel, with courses of bricks with side studs the hull sides hang
   on; a Technic brick at the tail stock's end is the propeller's bearing.
4. **Bars** for the side panels on the side keels, and **a rail** of plates and tiles along the
   midbody's chine (hiding the slot under the upper panels' lower edges).
5. **Hull sides of the tapers** (`naut_relief`), built flat and pushed onto the core's side studs:
   rows of studs-out plates (rows 20 LDU, layers 8 LDU) as deep as the hull is wide there. The
   section blends from the midbody's lens to a rounded superellipse toward the ends, so the
   hull narrows to its top and bottom like a cone. Each row is laid out as a **chain of curved
   slopes** along the hull (`fit_chain`: a dynamic programme choosing tiles, cheese slopes, 2 x 1
   and 3 x 1 curved slopes so every step toward the ends is under a curve); between rows, cheese
   and curved slopes. Plates over the hollow inside are pushed up from below; where one would be
   held by nothing but its caps, the shell is thickened there.
6. **Keel strip, salon floor, Nemo's salon** (`naut_salon`: the organ, the library, the aquarium,
   the table, the settee, lamps, the crew at the window and the organ), the **deck strip** over it
   with the bars the upper panels clip onto, the salon's two lamps under the deck.
7. **Teeth** along the side keels' forward edges; the deck's planking and grilles (tiles).
8. **Side panels** (`naut_panels`): over the midbody, each side four big tiled panels on clip and
   bar hinges, a chain in the hull's cross-section closed by its geometry (side keels' bar, facet
   A, seam, facet B, deck's bar; and under the side keels C and D to the keel strip): seen
   head-on the hull is a lens, the upper facets at 72 and 31 degrees, the lower at 71 and 30.
   Each panel has a one-stud lip over its hinge lines; over a hinge the lip is just tiles
   bridging from either side (on the seam, a 2 x 2 tile put on after the next panel clips on).
   On the port side the salon's upper panels are one hinged piece, the **gull wing**.
9. **On deck**: the wheelhouse (an alligator's head of bricks and slopes, curved slopes sweeping
   down its back, two bubble eyes on side studs, the searchlight), the **crest arch** (a band of
   plates one stud wide hung between the wheelhouse's peak and the deck, a chain of curved and
   cheese slopes along its top following the photo's arch, two big spikes and two small raked
   ones), the **dorsal fin** (built sideways, below), the raised after deck, the hatch; the
   **bow's ridge** (a spine with a chain of curved slopes and spikes down to the ram) and the
   **stern's ridge**.
10. **Under the hull**: the **saw keel** (a blade under the core, its underside a chain of
    inverted curved slopes and steps, a tooth at every fourth pair of columns), the stern's keel,
    the two **keel fins** (built sideways, below; each hangs from plates 1 x 2 in the keel strip's
    underside, their pins in jumpers' open studs, and ends in a keel of jumpers the after post
    plugs into), and **inverted 2 x 2 tiles** under the keel strip, the fins' keels, the keels'
    flats and the side keels' edges, so the underside is smooth.
11. **Tail** (`naut_tail_new`): the stock (the bow's cone turned round, to x 1000: the narrow
    wrist between the afterbody's pillows and the fin, its top tiles and a curved slope 4 x 2) and the
    **fish tail**, a fin built sideways in two halves over and under the side keels' strip (the
    shaft line, running on to the window): the upper lobe's leading edge 1:2 in wedge plates
    2 x 2, its trailing edge 1:6; the lower lobe's leading edge 1:3, 1:2, 1:4, its trailing edge
    1:4. In the window between them a brass **guard ring** hangs on an axle from a round brick
    under the upper half, the propeller turns on an axle in a Technic brick in the lower half's
    core, and the rudder swings on a bar post on the window's floor.

**Fins built sideways** (`naut_fin`: the dorsal fin, the keel fins, the fish tail), as LEGO's
sets build fins: a core one stud thick (bricks with studs on both sides, 47905, every other row
of side studs, bonded by plates), on each side a face of plates and **wedge plates** on those
studs (their diagonals make the swept edges: 1:2, 1:3, 1:4, 1:6 and 45 degrees), tiles over
them; a part on a row without core studs is held by the tile over it and its neighbour. The fins
are 52 LDU thick. Along a swept edge the core's top is capped with cheese slopes or tiles just
under the faces' diagonal; the dorsal fin has three claws up its leading edge for spikes.
12. The last tiles; Conseil and the diver on the after deck; the **stand** (`naut_stand_big`).

## The bow and tail modules

Forward of x = -800 (`naut_shape.BOW_STATION`) and aft of x = +880 (`TAIL_STATION`) the hull can
be replaced by separate modules, `naut_bow.build_bow(model, parent)` and
`naut_tail_new.build_tail(model, parent)`, each one sub-assembly in the hull frame pushed on
along X. When a module's file defines its build function, the hull built here stops at the
station plane (the bulkheads' solid walls there are its end faces) and the core's last column
carries the joint: in each brick course a 1 x 2 brick with two side studs (11211) facing out of
the station at z = -10 and +10 (`JOIN_STUD_Y`: 12 studs at the bow, 10 at the tail). The
section the hull ends with is `naut_relief.station_section("bow" | "tail")`. The tail module
tags its propeller "prop" and its rudder "rudder" and gives `PROP_AXIS` and `RUDDER_AXIS`; the
mechanism uses them. Without the modules the hull runs on to the ram and the tail as described
above, so the model always builds.

## The quarters module

Between the midbody's panels and the stations - the forebody x -800 .. -480 and the afterbody
360 .. 880 (`naut_shape.QUARTERS`) - the hull's skin can come from a module too,
`naut_quarters.build_quarters(model, parent)`. When its file defines that function the stepped
shells there are left out; the core gets 1 x 4 / 1 x 2 / 1 x 1 bricks with side studs in every
brick course of every column along both faces there (studs at z = -20 and +20, facing out), and
the side keels' studs there are left bare for the skins (the last tiles cover what they leave).
The deck, side keels, keel strip, saw and stern keels, wheelhouse, crest, dorsal fin and after
deck stay here. `naut_relief.quarter_interface()` lists it all: the studs, the core's and
deck's extents, the side keels' widths, the keel line, and the panels' end section.

- **Afterbody, over the side keels: the pillows** (`naut_quarters.PILLOWS["p"]`). Each side is
  one rounded body tapering from the midbody (x 360) to a point by the after deck's end: a rigid
  panel ten rows wide on clips on the side keels' studs (on two spacer plates) along a line
  converging 1:4 on the tail, parallel to the side keels' edge, leaning in at 60 degrees until
  its top row rests on the deck strip. The deck strip narrows under it from x 360 to 600, from
  eight studs to two (its upper layer's edge 1:4 in wedge plates 4 x 2, 41769 / 41770, each on a
  plate under its row and the next, a plate 2 x 4 across the middle at each segment's start
  bonding the strip: `naut_shape.AFT_DECK_EDGE`, `naut_frame.aft_deck_wedges`), and the raised
  after deck is two studs wide between the pillows' top edges. The panel's section is an arch: on its carrier,
  curved slopes 4 x 2 (93606) along both edges, their high ends inward, and two plates and tiles
  over the middle rows at their height. Its end is a lens: two big curved wedges (41749 /
  41750, 8 x 3 x 2 open) on rows 3 and 4 (their roots three rows each), tall edges together,
  closing it 48 LDU over eight studs to tips at x ~780, clear of the core; a curved slope 2 x 2
  falls aft beside their roots from the top band's end. From above the two pillows close in on
  the after deck like a fish's body on its tail; from astern they are round shoulders over the
  side keels. (`AFT_UPPER = "ab"` brings back the pass-1 faceted a and b panels with the stern's
  sweeps.)
- **Afterbody, under the side keels**: the midbody's lower facets run on as long thin panels (a
  carrier layer, tiles on it) on clips: c under the side keels along a 1:4 line, d on the
  core's side studs along a keel line rising 2:9, d lapping over c along a straight 1:4 edge (a
  run of wedge plates on top, flush with the tiles, their studs a row of rivets), its free
  edges fitted by a dynamic programme (`fit_edge`). Each c panel ends at the station in a
  curved wedge 6 x 2 (41747 / 41748) sweeping in under the side keels toward the lower lobe.
  Aft of the after deck the stern's top is two studs wide on the core between the lenses: tiles
  at y -144, a curved slope 2 x 2 rolling down to the stock, whose top (tiles, then a curved
  slope 4 x 2) runs down to the fin's top edge.
- **A lower pillow** (`PILLOWS["q"]`, `AFT_LOWER = "q"` in place of c and d) was tried: ten rows
  hung under the side keels converging 1:6, its far edge tucked over the keel strip. It rounds
  the belly's forward half, but being rigid and level it cannot follow the belly rising to the
  tail (it must end by x 480, leaving the core's striped sides bare aft of it), and it needs the
  keel strip narrowed under its far edge; c and d stay.
- **Forebody**: the bow's E and C carry a lip, a row of tiles past their crease over A's and
  c's stepped edges (A's and c's studs under it stay bare: `naut_bow.GRID_LIP`).
- **Joints**: where panels on different grids meet (x -640, -480 and 360) the converging
  panels' first or last column leaves a tapering slot; a rib on the straight panel's end
  (plates in its tiles' layer, tiles two studs wide reaching a stud over the other panel, a
  plate proud) covers it (`naut_panels.build_panel` `ribs`; the ribs' tiles go on last).
- Plates under the deck's port edge along the gull wing, low walls on the side keels inside
  the salon's side panels and the chine rail along the salon keep the lit salon's light in;
  tiles cover the core's bare side studs where they show by the stern.

## Colours

The hull is built in one role, `hull`; `naut_weather.py` recolours its outside once it is built
(`design.build`, before the stand), so the colours follow the shape whatever the modules build:

- **The iron frame** (`frame_iron`, Dark Bluish Gray / Black): the side keels' edges and their
  teeth, the deck's walkway from the wheelhouse aft, the keel strip and the saw keel - long
  lines that pick out the hull's structure, as a LEGO set would block it.
- **No darker plates**: Dark Brown plates were tried as single parts in patches (dots), as
  bands along a panel (stripes, where a panel's tiles run across the bands) and as whole panels
  (patchy: the tiles over the hinges belong to the hull, and wedge plates and inverted tiles
  aren't made in Dark Brown, so they stay Reddish Brown). `naut_weather` still has the strake
  machinery (`hull_dark`), unused by "iron_frame".
- The superstructure, the fins, the tail and the window bosses stay plain; the deck's vent
  grilles are `grille` (Dark Bluish Gray / Black).
- A part takes a colour only if it is made in it in both colourways (`naut_kit.AV`).
- Chosen from three looks rendered side by side: "weathered" (no frame; mottled dark, rust and
  bare-metal plates, read as camouflage), "two_tone" (the frame and a Dark Brown lower hull:
  patchy, as many curved and wedge parts aren't made in Dark Brown) and "iron_frame". They're
  still in `naut_weather.SCHEMES`; `NAUT_SCHEME=weathered` builds another for a test.

## Mechanism

- `salon`: the gull wing turns about the deck's bars on the port side, 105 degrees open.
- `prop`: the propeller turns on its smooth pin; `rudder`: swings about its post, 22 degrees.
- `pose(t)` opens the salon, turns the propeller once and puts the rudder over; the mechanism
  check sweeps 24 poses with nothing colliding or coming apart. `meta["performance"]` spins the
  propeller and eases the rudder for the video's cold open.

## Lights and wiring

- One Power Functions light unit (8870): a lamp under the salon's ceiling by each window, its nub
  in a Technic brick hanging from the deck strip. The leads run along the ceiling, down the
  hull's side past the salon floor, forward along the bottom of the hull to a shaft in the core
  over the front post, and down the post's clear tube to the battery box in the sea; an 8871
  extension wire (50 cm) joins the unit's plug to the box. The longest run needs 78 of the
  90 cm budgeted.
- The lights round the windows (Trans-Yellow) glow in lit renders only.

## Checks

`brickkit all nautilus`: real elements (warnings for rare parts only), connections (one piece),
collisions, buildability (8,193 insertions, every step of every sub-assembly), stability
(100 % margin, tips at 40 degrees), mechanism (24 poses, three moving groups), electrics and
technique all pass.

## Known limits

- Not built in real bricks: the checks cover part existence, connections, collisions, every
  insertion, balance, the mechanism sweep and lead lengths, not clutch or how much the long
  panels and shells flex.
- The tapers are still a LEGO relief: rows of plates whose steps are capped by curved slopes,
  not a smooth cone; the bow and tail modules replace them forward and aft of their stations.
- Along the gull wing's hinge on the deck's edge there is a slot (the wing can't carry a lip
  over its own hinge): plates under the deck's edge close the view into the salon except at
  the wing's hinge plates and the lamp under it, where a little light still shows.
- The bow's panels' wedge-plate edges step in their tiles' layer (the edge is straight a
  plate down, the tiles over it a staircase); the afterbody's are straight but show a row of
  studs. The quarters' joints with
  the midbody are covered by raised ribs, not flush; the bow's ridge and keel edges still
  show stepped V's head-on.
- The afterbody's top and sides are one rounded pillow a side, but it is a rigid panel: its
  arch keeps one section from x 360 to its lens, so the taper is in plan (1:4) and in the lens,
  not in height; its front is a rounded end face proud of the midbody's flat panels at x 360.
  Aft of the lenses (x ~780 .. 880) the core's sides over the side keels show courses of side
  tiles and bare brick (stripes) and a row of Technic holes over the side keels. Under the side
  keels the afterbody is still the faceted c and d (d's riveted edge to x 840).
- The photo model's rivets and plate seams are left out.
- Power Functions is discontinued; Powered Up has different plugs and has not been checked.

## Files

- `design.py`: assembly order, the hull's height on the stand, the modules' hooks, the deck's and
  belly's tiles, mechanism, video hooks, electrics.
- `naut_shape.py`: the shape traced from the photo, the side keels' plan, the panel chains, the
  salon, and the bow and tail modules' stations and joint.
- `naut_frame.py`: side keels, chine rail, panel bars, deck and keel strips.
- `naut_relief.py`: the core, the tapers' shells (section, fit_chain), the stations' sections.
- `naut_panels.py`: the midbody's panel chains and panels.
- `naut_window.py`: the salon windows. `naut_salon.py`: Nemo's salon.
- `naut_body.py`: the wheelhouse, the crest arch, the dorsal fin, the bow's ridge, bands capped
  with chains of slopes (`chain_band`, `keel_band`).
- `naut_keel.py`: keel fins, saw keel, stern ridge and keel, after deck, hatch.
- `naut_fin.py`: fins built sideways (core, faces of plates and wedge plates, tiles).
- `naut_tail_new.py`: the tail module (stock, fish tail, guard ring, propeller, rudder);
  `naut_tail.py` the older tail the hull falls back on without it.
- `naut_stand_big.py`: the sea stand and its posts.
- `naut_kit.py`: part tables, availability per colour role, packing, the step planner, free studs
  and anti-studs.
- `naut_weather.py`: the colours on the hull's outside (the iron frame, the darker plates).
