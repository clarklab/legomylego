# The Caldwell County Courthouse: design notes

The 1894 Second Empire courthouse in Lockhart, Texas (Alfred Giles), as a LEGO display
model: buff stone walls with red trim, slate mansards with iron cresting, four corner
pavilions with round windows under crested slate mansards, gabled attics, a columned
portico and the central clock tower with its bell-shaped slate dome, red ribs, Texas star
medallions, red finial and arrow weather vane.
**The four clocks are real**: a quartz clock insert (bought, not LEGO) sits behind each
dial, and the dome lifts off to set them.

- **2,933 LEGO pieces** in 133 part/colour lines, plus **4 quartz clock inserts** (not LEGO).
- **30.4 x 30.4 cm** base (38 x 38 studs, lawn and walks included), **45.9 cm** to the tip
  of the weather vane; the building is 28 x 28 studs (22.4 cm). About 3.2 kg (estimated).
- **Price**: roughly $112-$389 for the LEGO parts (price bands, `out/price_estimate.md`)
  plus roughly $20-$60 for the four clock inserts (`out/hardware.csv`): about $132-$449.
- Every check passes (`out/report.html`): real elements, connections, collisions,
  buildability, stability, the mechanism sweep (hands turning, dome lifting), electrics
  (none) and technique. Colourway: reddish brown trim (`out/variants/brownstone/`).

## Build order (booklet sections)

1. **Base**: two layers of plates, green lawn, grey walks with tiles, shrubs.
2. **Tower columns** (x4): 2 x 2 grey columns from the base to the roof deck, under the
   tower's corners. The tower's weight goes straight down to the base.
3. **Walls**, as segments that stand on the base: a **corner pavilion** (an L of two 8-stud
   faces, x4), a recessed **wing** (4 studs, x8) and a **centre pavilion** (4 studs, x4).
   Tan courses on a plinth, a red band and a red belt course; tall ground-floor windows
   (1 x 2 x 3 under a 1 x 2 x 2 transom) and first-floor windows, each under a red 1 x 4 arch;
   the pavilions have pairs of windows under a 1 x 6 x 2 arch whose opening is a lunette.
4. **Roof deck and cornice**: two layers of plates over the whole building (tan then red at
   the edge) tie the segments together; red inverted slopes, plates and tiles make the
   overhanging cornice.
5. **Mansards, attics, flat roof**: 75-degree slate slopes over the wings, each with a dormer
   and black ornamental fence as cresting; gabled attics over the centre pavilions (window,
   red arch, red pediment, slate roof, finial); slate grey tiles on the flat roof.
6. **Pavilion towers** (x4): a tan stage with a round red window (oculus, built flat and
   pressed onto side studs) on each outer face, a red cornice, a steep slate mansard with red
   corners and a flat top with iron cresting (railings and corner posts).
7. **Belfry**: 10 x 10 walls with a pair of arched windows on each side, over the columns.
8. **Clock stage** with its four **clock faces** (built flat) and the **clock inserts**.
9. **Lift-off top**: tan frieze, red cornice, the bell-shaped dome with red ribs and a star
   medallion on each face, a red finial and the weather vane.
10. **Portico** (front), **live oaks**, **flagpoles**.

## The clocks

### What to buy

Four **"mini" quartz clock inserts** of the kind sold for a **1-3/8 inch (35 mm) hole**
(press-in / fit-up inserts for woodworking and photo frames, often called "1-7/16 inch
mini clock insert" after the bezel). Search for "1-3/8 inch mini clock insert" or "35 mm
clock insert": clock-making and woodworking suppliers (Klockit, Rockler, Woodcraft), craft
stores, Amazon or eBay; roughly $5-$15 each. Choose a **white dial with black numerals**
(Roman numerals match the courthouse). The bezel colour doesn't matter much: only a thin
ring of it shows round the dial (black looks best). Each needs a button cell, usually
included (SR626SW / 377 or LR44).

### How to check the size

Measure before you buy (or check the listing):

| | fits | the model was drawn with |
|---|---|---|
| body (the part behind the bezel) | 35 mm across or less | 35 mm |
| bezel | 34-40 mm across | 38 mm |
| depth, front of the bezel to the back of the body | 22 mm or less | 17.6 mm |
| setting knob | may stick out a few mm more | 2.4 mm (20 mm overall) |
| dial | shows whole up to about 31 mm | 30.4 mm |

Lay the insert face down on the table and measure how high the back of the body stands.

### How they fit

Each clock face is a SNOT panel: plates with their studs outward, carrying a red ring (four
4 x 4 macaroni tiles) round a white ring (four 3 x 3 macaroni tiles) with a **32 mm round
window**. Behind the window the plates leave a 4 x 4 stud (32 mm) square hole. The insert's
bezel is bigger than that, so it sits **behind** the plates and only the dial shows through
the window, framed by the white and red rings, like the real clock faces.

Behind each face the clock stage has a **slot open to the top**: the insert slides down it
face first, its bezel behind the face plates, its body resting on **two tile rails 16 mm
apart**. A round body on two rails centres itself, so a 35 mm body sits within half a
millimetre of the window's centre (a smaller one sits a little lower). The slot is 48 mm
wide and the floor under the bezel leaves room for bezels up to 40 mm. The four inserts sit back to back: their faces are 40 mm
from the tower's axis, which leaves room for four bodies up to 22 mm deep before they would
meet in the corners, and a 45 mm square shaft between their backs.

The **lift-off top** (frieze, cornice, dome, vane) sits on four single studs, one on top of
each corner column of the clock stage, and covers the four slots, so the inserts can't lift
out while it is on. Lift it straight up: the backs of all four inserts, with their setting
knobs and battery covers, face the open middle of the tower. Set the time with a fingertip
or a pencil's eraser; to change a battery lift the insert straight out of its slot. If an
insert slides back in its slot when the model is handled, a small square of foam tape
behind it keeps its bezel against the face.

### In the model and the checks

The inserts are stand-in parts from brickkit's new non-LEGO hardware support
(`docs/brickkit-guide.md`, "Non-LEGO hardware"): `bk-clock-insert-35mm` (bezel, white dial
with hour marks, 35 mm body, setting knob, drawn at the largest size the slots take) with
separate `bk-clock-hand-hour` and `bk-clock-hand-minute`, all under
`brickkit/data/ldraw/parts/` (made by `tools/hardware_parts.py`). They show in the renders,
the booklet and the viewer; the collision check sees them (the slots, rails and faces
really have room); `model.press_fit` makes the connections and buildability checks treat
each insert as held by what it touches (rails and face plates) and each hand as held on its
insert's spindle. They are not on the LEGO parts lists; `out/hardware.csv`, the price
estimate's "Not LEGO" section and the booklet's "You will need" list them with where to
buy them. The eight hands are moving groups and the top is a `lifts_off` group: pose(t)
turns the hands from 10:10 to 12:10 and lifts the dome 8 cm from t = 0.35.

## Techniques

- **Walls** are one stud thick, courses bonded with staggered joints; the corners of an L
  alternate between its two walls course by course. Window frames stand in the courses;
  their glass clicks in from behind. 60602 (glass for the 1 x 2 x 3 window) had no LDCad
  snap, so `brickkit/data/shadow/parts/60602.dat` gives it the finger its frame's glazing
  slot expects.
- **SNOT**: the clock faces, oculi and star medallions are built lying flat and pressed onto
  bricks with studs on the side (1 x 4, 1 x 1 and 1 x 1 on two adjacent sides). The clock
  faces' columns of plates overhang the tower's core by one stud at their right-hand end,
  pinwheel fashion, so each corner is covered by exactly one face.
- **Round shapes from macaroni tiles**: 4 x 4 and 3 x 3 macaroni tiles for the clock rings,
  2 x 2 macaroni tiles and quarter tiles for the oculi; quarter tiles tangent to the ring
  fill the face corners.
- **Star medallions**: a jumper plate on two side studs puts a single stud in the middle of
  each dome face; a tan 2 x 2 dish sits on it and a red star on the dish's stud.
- **Bell dome**: each stage of slopes steps in one stud all round, so its toe sits on the
  previous stage's back row and the slopes run on without ledges: a 45-degree flare at the
  foot, two 75-degree stages, two 45-degree stages and a 75-degree point (concave at the
  foot, swelling to the point), with red double-convex corners up every corner as ribs. A
  red cone threaded on the vane's bar is the finial.
- **Pavilion roofs**: 75-degree mansards (red corners) with a flat top, iron cresting of
  1 x 4 x 2 railings and round corner posts with cones.
- **Cornices**: red inverted slopes on the wall top, plates over them and the overhang,
  tiles on the edge; the convex corners are covered by cantilevered plates.
- **Colours**: the trim is Dark Red, chosen by rendering Dark Red, Reddish Brown, Red and
  Dark Orange against the photos (Reddish Brown reads brown, Red too bright, Dark Orange
  orange-brown); the colourway keeps Reddish Brown. The walls are Tan. The slate is Black:
  Dark Bluish Gray rendered mid-grey next to the photos' charcoal slate. Cresting, spikes
  and the vane are Black too.

## Known limits

- **Not built with real bricks.** The checks cover part existence, connections,
  collisions, every insertion, balance and the mechanism sweep, not clutch or handling.
  The model is heavy (about 3.2 kg) on a two-layer plate base: lift it from underneath.
- **Clock inserts vary.** The slots take the range in the table above; the stand-in is the
  largest insert of that kind. Nothing but friction and the lift-off top keeps an insert
  forward in its slot (see the foam tip). The dial sits about 7.5 mm behind the face of the
  red ring, set back like a porthole.
- **The clock stage is 11.6 studs (9.3 cm) across its faces, not 10.** Four inserts up to
  20 mm deep back to back need their faces at least 3.5 cm from the axis, plus the face
  plates and tiles in front.
- **Simplified plan.** The four facades are the same (the real building's differ in
  detail); the portico is only on the front, the other centre pavilions have arched
  doorways. The pavilions have one pair of windows per face under a 1 x 6 x 2 arch (Dark
  Red has no 1 x 6 raised arch). The belfry under the clock stage is mostly hidden behind
  the attics and pavilion roofs. The dome's bell curve is made of straight 45- and
  75-degree slopes, and its red ribs are two studs wide (corner slopes), bolder than the
  real thin ribs; the pediments under the dome were left out to keep its flared foot.
- The flags are plain (red, blue, dark blue) wavy flags, no prints. Proportions follow the
  photos, not a survey.
- Interior: hollow, with the four tower columns inside; the windows show dark rooms.
