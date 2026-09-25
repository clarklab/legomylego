# Ferret — design notes

A life-size ferret mid-bounce: the long, tubular body bent into the running "hunch" (back
arched high in the middle, front and hind legs closer together), head low and forward and
turned towards the viewer, thick tail tapering to a point. Three colourways of the same build:
**sable** (default), **albino** and **cinnamon**.

## Dimensions (as built)

| | mm | LDU / studs |
|---|---|---|
| Nose tip to tail tip | 513 | 1283 LDU ≈ 64 studs |
| Head and body (nose to rump) | 403 | |
| Tail (root to tip) | 112 | |
| Height at the top of the arch | 150 | 15.6 bricks |
| Body width | 80 | 10 studs incl. curved edges |
| Overall width (ears, whiskers, turned head) | 93 | |

Target was a real adult ferret: 35–40 cm head+body, 10–13 cm tail, 10–15 cm at the arch. The
brief's "≈120–130 studs" does not match its own millimetre target (50 cm is ≈ 63 studs of 8 mm),
so the millimetre target was followed.

About 890 parts, ≈ 820 g, 187 instruction steps. Centre of mass sits over the four feet with
97 % margin; the model tips at 14°.

## Construction

The model is five sub-assemblies plus four legs, joined in four main steps:

1. **Chest** with both **front legs** — built upside down from the top of the chest down to the
   shoulders; the legs plug into 2 x 2 sockets underneath.
2. **Hips** with both **hind legs** — the same way.
3. **Arched back** (neck, the whole arch, the rump and the throat shelf) — lowered onto chest and
   hips at once; it spans the gap between them, which is what holds the arch up.
4. **Head** — set on a 2 x 2 turntable in the throat, turned 20° to look at you.
5. **Tail** — plugged onto eight side studs at the rump.

### Body: a brick sculpture sampled from a shape

`ferret_shape.py` describes the ferret as a tube swept along an arched spine (18 nodes: centre
height, half width, half height) plus four limb capsules. `design.py` samples it on the stud grid
in brick-high courses (8 mm x 8 mm x 9.6 mm cells), then:

* **Sections** (`sections_of`): everything from course 8 up is the back; below it, the islands
  holding the leg sockets are the chest and the hips. A one-course fringe under the back hangs
  from it instead.
* **Bond-aware packing** (`ferret_sculpt.pack_section`): each section's courses are packed in
  build order. Rim cells with no course above or below them are covered first, by a brick that
  also reaches a bonded cell (most constrained first). Every other brick is chosen to join the
  most still-separate clusters of the course before, and a repair pass re-packs locally until
  every junction between clusters is spanned. The result is that every sub-assembly holds
  together as one piece at every step. Hidden cells are Light Bluish Gray `core`. Where only a
  one-colour brick could bond a corner, one stud of colour may bleed across an edge (rump
  corners, the tail root).
* **Curved-slope caps** on every exposed top: plate + cheese slope (1 stud), plate + 11477
  (2 studs), 50950 (3 studs), all exactly one brick high against the course above. Where nothing
  is behind the high end (the ridge of the back), lower 2-plate caps are used instead so no
  fins stick up. Cap directions prefer falling to the sides, since the body is a tube along z.
* **Build planner** (`plan_steps`): each step holds up to 8 parts of one course and one kind
  (bricks or edge slopes). Every part sits on, or hangs from, what earlier steps built, or sits
  on a part placed earlier in the same step, and slides in along its studs without hitting
  anything. No part is ever chosen if it would shut another part in (built both above and below
  it). Steps continue a course while it has parts left, and follow each other around it.

### Head: finer, plate-high sculpture with SNOT details (`ferret_head.py`)

Cranium, brow, muzzle, jaw and cheeks are unioned ellipsoids, sampled in plate-high layers so
the profile is three times finer than the body, and rounded with cheese slopes and tiles.
Colour zones give the sable face: a white muzzle, chin and cheeks, the dark **bandit mask** band
straight across the eyes and nose bridge, and a body-coloured crown.

* **Eyes**: glossy 2 x 2 dishes (4740) on round 1 x 1 plates with a side bar (32828). A round
  plate sits on a single stud, so it can be turned to any angle without its corners hitting its
  neighbours. The bars point 45° outwards from straight ahead, like a real ferret's eyes, so the
  eyes read from the front, the three-quarter and the side view. The space the dishes need is
  sampled and kept clear.
* **Ears**: the same mount at 55° on top of the skull, with a white dish and a pink round tile
  on the dish's centre stud as the inner ear.
* **Nose**: a 1 x 2 half-circle tile on a brick with two side studs; below it a coral half-circle
  tile is the tongue tip ("blep").
* **Whiskers**: 3L bars in clip tiles on the whisker pads.
* **Turntable**: the head is built on a 3679 turntable top, which drops into the 3680 base on the
  throat shelf (hidden, fixed colours). The rest of the shelf is tiled white, so the head slides
  over it. The head is posable: the mechanism check sweeps it from 15° one way to 30° the other
  without collisions.

### Tail: built along its own axis (`ferret_tail.py`)

The tail is a sub-assembly built standing up, so each brick-high slice is a round cross-section
of the tail. Curved slopes on each slice's exposed rim taper it smoothly from a 45 mm root to the
tip. It plugs onto the eight side studs of two 1 x 2 x 1⅔ bricks (22885) set side by side into
the rump, under a 1 x 4 plate; their stud rows are 20 LDU apart, matching the tail's grid, where
a stack of ordinary side-stud bricks would be 24 apart. A 2 x 4 brick at the tail's root takes
all eight studs.

### Legs

2 x 2 brick columns on plate paws: a 2 x 3 front paw with a cheese-slope toe row, and a long
2 x 4 hind foot with rounded toes (a curved 2 x 2 slope). The upper legs, shoulders and thighs are
part of the sculpted body (dark `dark` colour where the limb capsules meet the surface, as on a
real sable).

## Colourways

Palette roles, with every part checked to exist in every colour its role takes (≥ 3 sets, still
in sets since 2016; `design.Avail` restricts the packer to such sizes):

| role | sable (default) | albino | cinnamon |
|---|---|---|---|
| coat (body, crown) | Tan | White | Medium Nougat |
| belly (underside) | Tan | White | Tan |
| dark (legs, shoulders, thighs, tail) | Dark Brown | White | Reddish Brown |
| mask (band over the eyes) | Dark Brown | White | Reddish Brown |
| face (muzzle, cheeks, throat, ears) | White | White | White |
| nose | Reddish Brown | Bright Pink | Dark Pink |
| eye | Black | Red | Black |
| ear_inner | Bright Pink | Bright Pink | Bright Pink |
| tongue | Coral | Coral | Coral |
| whisker | Black | White | Black |
| core (hidden) | Light Bluish Gray | = | = |

Fixed colours shared by all colourways, all hidden or nearly so: eye mounts Black (32828),
turntable base Black (3680) and top Light Bluish Gray (3679, its only colour), tail socket
Light Bluish Gray (22885).

Dark Brown only comes in 1 x 1, 1 x 2 and 2 x 2 bricks (plus plates and curved slopes), so the
legs and tail use those; Medium Nougat has no 2 x 3 or 2 x 8 bricks, so the coat avoids them.

## Checks

`brickkit all ferret`: every check passes for the default palette (real elements, connections,
collisions, buildability, stability, mechanism with the 24-pose head sweep, electrics,
technique), and real elements + technique pass for albino and cinnamon, with **no warnings**.
The cinnamon nose had been Coral, which is rare on the 1 x 2 half-circle tile (1 set), so it
became Dark Pink. The albino's eyes were Trans-Red at first; once the head became posable the
technique check warned about transparent parts in a moving group (clear plastic is the brittle
kind), so they are opaque Red.

## Known limitations

* A brick sculpture at this scale is stepped: flanks show brick courses, and the underside of the
  belly steps up to the arch (no inverted slopes underneath).
* The whiskers are straight bars sticking out sideways; they can't fan out.
* The eye and ear mounts each hold on one stud, and the head turns on friction; nudge them back
  if knocked.
* From the side view the turned head shows its back three-quarter: the head looks towards the
  front three-quarter camera.
* The tail sticks straight out: it plugs into side studs, so it can't be raised at an angle
  without a hinge.

## Files

* `design.py`: build entry; body sections, colours, legs, head/tail assembly, captions, pose.
* `ferret_shape.py`: the body and limb shape (millimetres).
* `ferret_sculpt.py`: grid pieces, caps, bond-aware packer and the step planner (model-local
  helpers, no engine changes).
* `ferret_head.py`, `ferret_tail.py`: the head and the tail.
