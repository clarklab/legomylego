# VHS Cassette: design notes

A life-size (1:1) VHS video cassette in real LEGO, with a working dust door and two reels
that spin on their pins. 348 parts, 66 part/colour lines, 81 steps.

## Size

| | Real VHS | Model | Difference |
|---|---|---|---|
| Width | 187 mm | 184.0 mm (23 studs) | -3.0 mm |
| Depth | 103 mm | 104.0 mm (13 studs) | +1.0 mm |
| Height | 25 mm | 25.6 mm (8 plates) | +0.6 mm |

`check_dimensions` (an `extra_checks` entry, reported by the mechanism check) fails the build
if any outer dimension drifts more than 5 mm from the real cassette. Mass is about 288 g
(a real T-120 weighs about 230 g).

## Structure

- **Bottom half** (157 parts): a floor of big plates tied by smooth floor tiles and the
  first wall course; walls of plate / brick / plate (8 + 24 + 8 LDU); the front beam that
  carries the tape; the door hinge mounts. The top face of every wall is bare studs for
  the top half.
- **Dust door** (30 parts): built flat, then mounted studs-forward (SNOT): 2-wide plates
  with 1x and 2x tiles on the outside, filler plates along its top edge, two hinge tops.
- **Reels** (14 parts each): identical hardware, only the tape differs.
- **Top half** (161 parts): a plate layer with a smoked window sheet, a tile layer with
  window glass, the white face label recess, grip ridges and moulded arrows; the reel pins
  and both reels hang in it.

The plate and tile layers are laid out by a small packer (`kit.py`) that picks each tile to
join as many still-separate groups of plates below as possible, then tries layout variants
until every build phase joins into one piece. A few floor plates near the corners and under
the front beam are fixed by hand (`FIXED_FLOOR`) because the edge structure needs them to
reach the floor tiles.

### Build order (for the booklet)
Steps are generated per phase: floor slab (plates, screws, floor tiles, spindle rims, first
wall course), walls and front corners, tape path, the tape itself, top course, hinge mounts,
hinge bases. Each step is a local cluster of up to six parts that joins onto what is already
built, the lowest layer first; a step gets a caption only when it introduces something new.
The door and reels are hand-sequenced. The top half is built face up; its last steps turn
it over, push in the reel pins and slide the reels on, and then it is lowered onto the
bottom half with the reels hanging in it.

## Mechanisms

### Dust door (`flap`)
Real VHS doors hinge at the top-front and swing up and outwards to expose the tape. Any
flap hinged inside the body sweeps its upper edge backwards into the top shell, so the
geometry was worked out first:

- Two classic click hinges (`3937` base + `6134` 2x2 top) are mounted **sideways**: the
  bases sit on the side studs of `99206` (2x2x2/3 plate with two side studs), so the hinge
  top faces forwards and becomes the back of the door. Opening is `rot(x = -90 t)` about
  the axis y = -50, z = -104 (along X): the door's bottom swings forwards and up until the
  door lies flat as a visor at t = 1.
- With the hinge top 10 LDU below the door top and 26 LDU behind its face, every door point
  behind the axis stays above the door's own top face, so nothing hits the top half. The
  side-stud height (6 below the top of a 2/3 plate) puts the door strip 4 LDU (1.6 mm) below
  the top surface - a VHS-style recessed door top.
- Between the hinges, filler plates behind the door fill the top strip and swing up with
  it; a 3.2 mm groove remains between them and the top half.
- The hinges sit at x = +-30: further out, the mount's back half would overhang the full
  reel and the top half could not be lowered on.

### Reels (`reel_l`, `reel_r`)
Each reel turns on a fixed **half pin** (`4274`) that hangs from a black 2x2 round plate
with axle hole (`4032a`) in the window's plate layer. From below:

1. `30565` x4: the white lower flange (a true 8 x 8 circle).
2. `11833` (4x4 round with 2x2 opening) as the hub core, with the tape pack around it:
   `79393` 3x3 macaroni tiles (r 40-60) and `27507` 4x4 macaroni tiles (r 60-80).
3. `60474` (4x4 round with pin hole): the raised white hub; its ring of studs reads as the
   hub's drive teeth.

The pin passes through the hub and its flared tip ends in the core's round opening, so it
never sits in a same-size hole. The reel slides on the smooth floor tiles, located by the
pin. Through the round spindle hole underneath you see (and can push) the white flange.

`pose(t)` turns both reels the same way, as when playing: the supply reel 270 degrees and
the take-up reel 360 degrees, a 4 : 3 ratio because the small pack must spin faster for the
same tape speed.

## VHS details

Included:
- Black top and bottom halves, smooth tiled top, smooth brick sides, tile-faced door.
- Smoked window (`Trans-Brown`, LEGO's transparent brown) showing both reels; black bore
  holders over the white hubs.
- **Nearly full supply reel** (64 mm pack) and **nearly empty take-up reel** (48 mm pack
  with the white flange showing). Supply on the left in VHS terms (label up, door away).
- Tape (`Reddish Brown`) running across the mouth between two **white guide rollers**, with
  **silver guide pins** behind them; visible when the door is up.
- **Door release button** (grey headlight brick) on the right side near the front.
- **Light-path holes**: a Technic hole straight through each front corner, where the VCR's
  end sensors look through.
- **Write-protect tab** (dark grey) at the lower left of the spine.
- **Spine label** (white band in the back wall) and **face label recess** (white tiles).
- **Five screw heads** (flat silver round plates) in the bottom.
- **Spindle (drive) holes** with round rims and the white reel flange inside; **lamp hole**
  and **reel-lock release hole** (round open-stud plates) in the bottom.
- **Open mouth** underneath, where the head drum enters.
- **Moulded insert arrows** (pentagon tiles, black) pointing at the door and **grip ridges**
  (grille tiles) on the front corners.

Not included / approximations:
- No clear upper reel flanges, no reel brake levers (only the release hole) and no tape run
  from the reels to the corner guides inside.
- The hub is 32 mm (real 26 mm). The full pack is 64 mm, a full T-60 rather than a T-120's
  81 mm: an 80 mm pack fits the 13-stud depth only without the front beam, and the round
  plate that would close its outer ring leaves visible studs.
- The tape is an 8 mm tile strip on backing bricks (real tape is 12.7 mm and the mouth is
  hollow behind it).
- The window is two layers of transparent plates and tiles, so the reels look softened
  through the stud pattern - honest LEGO glass.
- The door top sits 1.6 mm below the top surface, with a 3.2 mm groove behind it and the
  hinge bases visible in it.
- The spindle holes are 4x4 openings in the floor plates; the round 32 mm rim sits one plate
  up.

## Colourways

- `clear_window`: `Trans-Clear` window (shows the reels more clearly).
- `white`: white shell with grey label areas and a clear window, like a head-cleaner tape.

Both pass `real_elements` with no rare parts.

## Checks

`brickkit all vhs_tape`: every check passes with no warnings - real elements (66
combinations, 0 rare), connections (1 piece), collisions (0), buildability, stability,
mechanism (24 poses, 3 moving groups, plus the size check), electrics (none), technique
(0 notes).

## Engine changes made for this model

- `engine: buildability lets clips and click hinges snap on` - interlocked hinges such as
  3937 + 6134 can't be separated by any straight slide, so the parts a unit clips or hinges
  onto no longer block its insertion path.
- `engine: buildability lets Technic pins click into holes` - a pin's split, flared tip
  always collided while sliding through a hole, so even one pin in a Technic brick failed.
- `engine: cache path test honours the BRICKKIT_CACHE override` - the paths test could not
  pass in a git worktree.

## Renders

`out/renders/`: `three_quarter.png` (final build), `open.png` (door up, reels turned, tape
across the mouth), `back.png` (spine label and write-protect tab) and `clear_window.png`
(window close-up in the clear colourway). The last three were rendered a few commits
earlier, when the pin holders over the hubs were still light grey; nothing else visible
has changed. Further renders were skipped because the shared machine was saturated.

The stock `low` view (elevation -8) sits below the ground plane for a model this flat, so
it only shows the ground; an underside view needs `render_model(..., ground=False)`.
