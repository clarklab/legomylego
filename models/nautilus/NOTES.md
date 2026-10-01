# Nautilus: design notes

Captain Nemo's Nautilus as Harper Goff designed it for Walt Disney's *20,000 Leagues Under the
Sea* (1954): a riveted iron fish of a submarine with a ram at the bow, a toothed crest arching
from the wheelhouse down to the bow, a saw keel, a shark's dorsal fin, the big salon window on
each side ringed with lights, and a swept fish tail with a propeller and rudder. It floats on two
clear posts over a low block of sea with rolling waves. The salon windows light up (Power
Functions); the propeller spins, the rudder swings and the four dive planes tilt. Two
colourways: **rusty iron** (default) and **steel**.

- **1,305 LEGO pieces** in 136 part/colour lines (1,306 placed: the two lamp heads count as one
  8870 light unit), 350 instruction steps, about 1.46 kg (estimated).
- **Price**: roughly $60-$185 for the parts (price bands, `out/price_estimate.md`); the light
  unit and battery box are bought used (Power Functions was discontinued in 2018).
- Every check passes (`out/report.html`); the one warning is that the Power Functions battery
  box was last in a set in 2015 (as for the Baby Metroid Lamp).

## Size (1 LDU = 0.4 mm)

| | model | from the profile photo |
|---|---|---|
| Length, tail tip to the ram's point | 1,156 LDU = **46.2 cm** (18.2 in) | 1,140 LDU target |
| Hull, deck to keel amidships | 160 LDU = 6.4 cm | 150 |
| Crest top to the keel fins | 275 LDU = 11.0 cm | 241 |
| Beam over the side keels | 200 LDU = **8 cm** (7.7 cm over the windows, 11.2 cm over the dive planes) | judged from the 3/4 photos |
| On the stand: overall height | 19.0 cm; the keel fins 3.8 cm above the sea's deck | |
| Stand | 44 x 14 studs = 35.2 x 11.2 cm, 4.5 cm deep plus waves up to 1.3 cm | |

The side profile was traced from the profile photo of a finished display model
(`naut_shape.py`: deck line, belly line, chine, tail lobes, crest arch, dorsal fin, keel fins,
saw keel, wheelhouse and window positions in photo pixels, at 1,140 LDU for the photo's
1,775 px), and the build was checked against it by overlaying an orthographic render on the
photo's silhouette in model units: the hull, the crest, the fins, the saw keel and the tail
lobes sit within about a stud of the traced lines.

## Structure (booklet order)

The hull frame has the side keels (the chine) at y = 0, the bow toward -X and the port side
toward the front (-Z); on the stand the side keels are 12.5 cm above the table
(`design.Y_HULL`, set by the posts' height).

1. **Side keels** (`naut_frame.build_frame`): the hull's base, a flange two plates thick at the
   waterline, a pointed lens in plan: ten studs across amidships, tapering 1:6 (12 x 3 wedge
   plates) then 1:4 (4 x 2 wedge plates) to two studs at the bow tip and the tail stock. The
   lower layer is narrower, so the edge reads as a thin keel line. Its layout is searched until
   it holds together as one piece (plates across every join between the stretches, then a
   repair pass that merges plates across any join still open).
2. **Core** (`naut_relief.core_batch`): plates two studs wide standing on the side keels up to
   the deck and pushed up under them down to the keel, in steps from the side keels outward;
   a course of bricks with side studs on the side keels and one under them; 18-degree slopes
   carry the bow's ridge up to the deck; under the bow the core runs on down as the saw keel's
   blade, stepping up toward the ram, an inverted 4 x 1 curved slope under each step. A Technic
   brick at the tail stock's end is the propeller's bearing.
3. **Hull sides** (`naut_relief`), four sub-assemblies (upper and lower, each side), each built
   flat and pushed onto the core's side studs: rows of plates turned studs-out, as many layers
   deep as the hull is wide at that stud row (a lens from the side keels to the deck's edge and
   to the keel) and shortening with the side keels' taper toward the bow and stern. Every row's
   outer layer is capped: cheese slopes rise to the row nearer the side keels (the rows join
   into one smooth side) or along the taper; elsewhere tiles. Rivet lines run down the plate
   seams every seven studs (Dark Brown round tiles), with short diagonals of round tiles in the
   hull's colour hinting at the plating's triangles; grilles along the lower hull are the
   vents; on each side a ladder of three handle tiles climbs to the hatch.
4. **Deck strip**, the **ram** (a jumper, an open-stud round plate, a 3L bar and a cone on the
   bow's tip brick), the **wheelhouse** (an alligator's head: low, its sides sloping in, an
   18-degree slope up to the brow, two clear dish eyes on round plates on its front brick's
   side studs) and the **breathers** behind it (grille slopes).
5. **Crest arch** (`naut_details.crest_arch`), built flat and pushed onto a side stud at the
   wheelhouse's brow and one at the bow: five plates standing on edge in two layers, each
   turned on the single studs it shares with its neighbours (solved so the chain follows the
   traced crest), tiles along its studs, and tooth plates raking back. The searchlight eyes go
   on the wheelhouse after it.
6. **Salon windows** (one per side, `naut_details.salon_window`): the hull side is raised to a
   flat boss six studs square with cut corners (its face Dark Brown), centred on a stud-grid
   corner so the frame's anti-studs land on the hull's stud rows above and below the side
   keels, which are cut back under it and run into it. On the boss: a round 4 x 4 plate with a
   pin hole (Pearl Gold: the iris ring, Pearl Gold round tiles on its studs), a Power Functions
   lamp pushed into its centre hole from behind, a clear jumper plate and a clear dish; round
   it eight Trans-Yellow round tiles on Yellow round plates (two over, one each side, four
   under, as on the photo model) and Dark Brown rivets.
7. **Dive planes**, two pairs: a plate with a side handle on a riser on the side keel's edge is
   the hinge bar; the plane (a plate with a clip on its end and a tile) clips onto it.
8. **Dorsal fin** (plate levels stepping up aft, a cheese slope on each step's front so the
   leading edge is a row of teeth, a tooth plate raking aft at the top), the round **hatch**
   and the **skiff** on the after deck.
9. **Tail**: the lower lobe pushed up under the stock (inverted curved slopes under its steps),
   the propeller (Pearl Gold, on a smooth Technic pin) pushed into the bearing from astern, the
   **guard's post** behind it (a bar in a round brick on a jumper), the **rudder** clipped to
   the post by two vertical clips, then the upper lobe on the stock (cheese slopes up its
   leading edge). Both lobes sweep back past the rudder to pointed tips.
10. **Keel fins** (two, built upside down and pushed up under the core: the forward one's tip
    hooked back), the **saw teeth** (tooth plates in the deep ends of the keel's curved slopes
    and under the side keels' tip, curving down and out) and **teeth along the side keels'**
    forward third (in free anti-studs under their edge).
11. **Tiles** over every stud left bare: the side keels' stud rows alternate Dark Brown round
    tiles (rivets) and square tiles; the deck's middle two rows are grilles.
12. **Stand** (`naut_stand.py`): the **sea base** (a floor of plates, open where the battery
    box stands on the table; walls three bricks tall in Dark Blue lightening to Dark Azure, a
    slot in the back wall at the box's button), the **sea's top** (built flat: two crossed
    layers of Medium Azure plates; long rolling waves - a 3 x 1 or 2 x 1 curved front rising
    to a crest of plates with white round-plate foam, a curved back - ripples round the posts,
    the calm sea in tiles of Dark Azure, Medium Azure and Trans-Light Blue, a hole by the front
    post for the leads, a blank black 2 x 6 nameplate at the front left) and **two clear
    posts** of round 2 x 2 bricks, plugged into the keel fins.

The Nautilus lifts off the posts; unplug the lights' leads at the battery box first.

## Techniques

- **A sideways relief on a lens of side keels.** The hull's sides are heightfields of plates on
  the core's side studs, the same idea as a sculpted terrain turned on its side: rows (20 LDU)
  up and down, columns (20 LDU) along, layers (8 LDU) out. Each side is packed so it holds
  together by itself, trying layouts until it does.
- **A step planner** (`naut_kit.Batch.emit`) orders every sub-assembly's parts so each one
  can really go in: parts standing on the table or on parts already built go in first,
  nothing goes in between parts already built above and below it, and hanging parts (the core
  under the side keels, the tail's lower lobe) are built top down, each pushed up under what is
  already there. Sub-assemblies built flat (the hull sides, the crest) have their own frames.
- **Placing by free connections** (`naut_kit.exposed_studs`, `free_sockets`): the bare studs
  to tile and the free anti-studs under the side keels' edge for the teeth are found from the
  built model's own connectors.
- **Weathering** (`naut_kit.weather_role`): a few scattered small visible parts (one or two
  studs; about one in twenty) are Dark Brown, darkened with age, and a very few Dark Orange,
  rust; chosen by a hash of their position, never in patches. A part only takes a colour LEGO
  makes it in (in every colourway), otherwise it keeps the base colour. The steel colourway is
  Dark Bluish Gray with Black rivets and spines.
- **Colours checked for every colourway**: the packers only use plate/tile/slope sizes that
  exist in every colour their role takes (`naut_kit.Avail`).

## Mechanism

- `prop`: the propeller turns about its shaft; it sits on a smooth pin, so a flick spins it.
- `rudder`: swings about the guard's post (its clips turn on the bar), 22 degrees each way.
- `dive_fwd_port` / `_stbd`, `dive_aft_port` / `_stbd`: each plane tilts on its bar, 15 degrees.
- `pose(t)` turns the propeller once, puts the rudder hard over and tilts the planes (forward
  pair one way, after pair the other); the mechanism check sweeps 24 poses with no collisions
  and nothing coming apart.
- For the showreel's cold open (`[video.cold_open]`: the deep sea, a glide),
  `meta["performance"]` spins the propeller (three turns a loop), eases the rudder to and fro
  and tilts the dive planes in turn; `meta["performance_info"]` hides the stand (tag `stand`),
  gives the bow direction (-X), the keel fins' height and a 4 s loop.

## Lights and wiring

- One Power Functions light unit (8870): one lamp behind each salon window, pushed into the
  window frame's centre pin hole from behind; it shines through a clear jumper plate and a
  clear dish. The lights round the window glow in lit renders only (they are not lit).
- Each lead goes up from its lamp into the open cell beside it under the frame, in to the core
  and down a shaft left in the core just aft of the window's middle (the side keels hold
  together round it), out under the hull behind the forward keel fin, down beside the front
  post, through the hole in the sea and to the battery box's plug. The electrics check's
  longest run needs 19 cm of the 40 cm budgeted per lamp (as for the Baby Metroid Lamp, the
  8870's 50 cm lead is budgeted at 40 cm per lamp, since where it splits could not be
  confirmed).
- The battery box (Power Functions AAA, set 88000) stands on its back on the table inside the
  base, boxed in by the floor's opening and the walls; its green button is behind a slot in
  the back wall. It switches itself off after two hours unless held for three seconds when
  switched on. To change the batteries, lift the sea's top off.
- The wheelhouse's eyes and searchlights are not lit: there was no clean way to put a light
  behind a side stud without a transparent side-stud brick, which LEGO doesn't make.

## Checks

`brickkit all nautilus`: real elements (one warning, the battery box), connections (one
piece; the battery box is a press fit), collisions, buildability (1,244 insertions, every step
of every sub-assembly), stability (100 % margin, tips at 36 degrees), mechanism (24 poses, six
moving groups), electrics and technique all pass; the steel colourway passes real elements
and technique with the same warning.

## Known limits

- Not built in real bricks. The checks cover part existence, connections, collisions, every
  insertion, balance, the mechanism sweep and lead lengths; they cannot judge clutch, the
  posts' stiffness or how much the hull sides flex. The posts are round 2 x 2 bricks: firm in
  compression, but nudge the Nautilus gently.
- The hull is still a LEGO relief: seen head-on its taper shows as small slopes and steps.
- The rivets are 1 x 1 round tiles, far larger than the photo model's; so they read as rivet
  lines rather than patches only a few seams carry them. The side keels' edges show the wedge
  plates' stud notches.
- The salon window's boss is a square with cut corners, not the photo's flared lozenge, and the
  clear jumper under the dish is square.
- The forward keel fin's hooked tip ends a stud short of the photo's (the lights' shaft comes
  out just behind it). The skiff sits on the after deck rather than in a recess. The guard is
  a single post behind the propeller, without the photo model's hoop and struts.
- The dive planes are this model's (the photo model has none showing); they stand out a stud
  and a half from the side keels.
- Power Functions is discontinued; the Powered Up light and hub have different plugs and a
  different box size and have not been checked in this design.

## Files

- `design.py`: assembly order, the hull's height on the stand, mechanism, video hooks,
  electrics.
- `naut_shape.py`: the shape traced from the profile photo (photo pixels to LDU), the side
  keels' plan and the salon windows' layout.
- `naut_frame.py`: the side keels and the deck strip.
- `naut_relief.py`: the core and the hull sides (rows, layers, caps, rivets, the windows'
  bosses).
- `naut_details.py`: wheelhouse, breathers, crest arch, ram, tail (lobes, propeller, guard,
  rudder), keel fins, saw teeth, dorsal fin, hatch, skiff, salon windows, dive planes.
- `naut_stand.py`: the sea base, the sea's top with its waves, the posts.
- `naut_kit.py`: part tables, availability per colour role, orientation helpers, packing, the
  step planner, weathering, finding free studs and anti-studs.
