# Chainsaw Face: design notes

Chainsaw Face, a masked slasher from 1970s horror, as a brick-built, posable figure on a
display stand, in the spirit of LEGO's big football figures (43015/43016): a bulky man in a
white short-sleeved shirt, black tie, big yellow butcher's apron, dark blue jeans and black
shoes, a Tan skin mask with dark eyes and bared teeth, messy dark brown hair, and the chainsaw
raised high overhead in both fists. Every joint poses with real LEGO joints, and the model's
`pose(t)` swings the saw from overhead (t = 0, the static model) down across his hips (t = 1).

Colourways: the default (`Blood-spattered`: Dark Red splatter on the apron) and **clean**
(the `splatter` role set to the apron's Yellow). A grey shirt was tried and dropped: the neck's
39789 brick and the ball socket brick 67696 were never made in Light Bluish Gray.

## Dimensions (as built)

1 LDU = 0.4 mm (stud 8 mm, plate 3.2 mm, brick 9.6 mm).

| | model | real | at 1:6.6 |
|---|---|---|---|
| Soles to top of the hair | 740 LDU = **29.6 cm** | a 193 cm (6 ft 4) man | 29.2 cm |
| Overall, stand to top of the hair | 788 LDU = 31.5 cm (12.4 in) | | |
| Overall with the saw raised | 940 LDU = 37.6 cm | | |
| Torso block | 10 x 6 studs (8.0 x 4.8 cm), 12.4 studs across the shoulder balls | | |
| Across the upper arms | about 20 studs (16.6 cm) | | |
| Head, chin to crown (with hair) | 138 LDU = 5.5 cm; 8 studs (6.4 cm) across the hair | about 23 cm | 3.5 cm |
| Chainsaw, rear handle to bar tip | 320 LDU = **12.8 cm** | a 1970s saw with a 50 cm bar, about 85 cm | 12.9 cm |
| Stand | 16 x 14 studs (12.8 x 11.2 cm), deck 1.9 cm high | | |

The body follows the football figures' proportions rather than a real man's: a big head, a
barrel chest, 4-stud-thick arms and 4 x 4 legs. The head and shoulders are about 1.5 times
true scale; height and the saw are to scale.

809 parts in 189 lines, about 996 g, 138 steps. Rough cost $30-$109 (`out/price_estimate.md`).

## Construction

Built from the ground up (`design.py` puts it together; one module per body part):

1. **Stand** (`stand.py`): a black base 16 x 14 studs, a plate deck with exposed studs where
   the shoes go, dark wooden floorboards (1 x N tiles in two browns, joints staggered), a
   raised black nameplate at the front (blank, for a sticker) and a black support post behind
   the figure.
2. **Shoes** (`legs.py`): black, 4 x 7 studs, on the deck's studs; a ball socket brick over
   the instep takes the ankle ball, a rounded toe cap.
3. **Legs**: thigh and shin, 4 x 4 studs of jeans each, with the knee joint in the inner middle
   column; each leg goes in as one assembly, its ankle ball popping into the shoe. The shin's
   knee cap (a brick, plates and smooth tiles round the disk's slot) steps down from front to
   back under the bent thigh, closing the knee's gap to 8 LDU at the front so the disks hide
   inside and no studs show.
4. **Hips** (`body.py`): a 10 x 6 block of jeans with both hip sockets in its bottom course,
   two Technic bricks at the back for the post's pins, a front column of bricks with studs on
   the side that carries the **apron skirt** (built flat and turned to face forward), and a
   4 x 4 turntable base in the top. Two long pins go through the post into the back of the
   hips.
5. **Torso**: a 10 x 6 white block on the turntable, its four vertical corners rounded with
   columns of 1 x 1 round bricks and plates (a barrel chest), with a belly row of side-stud
   bricks that carries the **bib** (built flat), the shirt front, the black tie and the
   apron's straps. Below the chest the belly row and the whole front row are Yellow, so the
   apron wraps round the front corners to the sides;
   the shoulder axles and balls in its top course, a collar of cheese slopes, rounded
   trapezius slopes, the straps running over the shoulders, and the neck ball on top.
6. **Head** (`head.py`): a ball socket brick in the back half of the head (where a neck joins
   a skull), side-stud bricks at the front for the **mask**: a 4 x 6 Tan panel of smooth tiles
   built flat (a rounded jaw, bared White teeth in a dark open snarl, black eye holes either
   side of the nose, a heavy brow). Ears: round plates on bricks with a side stud. The Dark
   Brown hair is a shaggy mop: the crown's plates reach a stud past the head all round,
   curved slopes fall over every edge (a fringe over the brow), four more tumble every which
   way on a raised middle, and bricks of different lengths hang under the overhang down the
   sides (behind the ears) and the back.
7. **Arms** (`arms.py`): upper arm (the white short sleeve with a rounded shoulder cap and
   deltoid, bare Tan skin below it), bare Tan forearm (built upside down from the elbow end,
   with a grey bracelet band on the left wrist) and a fist (the ball socket brick, a plate
   under the palm, the clip plate for the fingers and a curved slope for the knuckles). Each
   arm is one assembly whose socket clicks onto its shoulder ball.
8. **Chainsaw** (`saw.py`): a yellow engine (bricks in a brick + 2 plate rhythm), a grey guide
   bar built flat and turned on edge along the engine's left side (black plates for the chain's
   edge under grey tiles, black grille tiles for the chain along the top edge, a rounded nose),
   and two black bar handles held out from the engine's top on clip plates: one across the
   front, one across the back, 16 cm apart as on a real saw. The handles clip into the fists
   last.

Flat panels (skirt, bib, face, guide bar) are laid out by `kit.panel_parts` so that every tile
sits across plate joints: each panel holds together as one piece before it's turned and
pressed onto its side studs (checked by the connections check).

## Joints

| Where | Joint | Moves |
|---|---|---|
| Neck | Technic ball 53585 on a 2L axle in the torso's 39789 brick, in a wide ball socket brick 67696 in the head | nods (-14° back to +10° down before the collar), turns, tilts |
| Shoulders | Technic ball 53585 on a 3L axle through two 1 x 2 Technic bricks in the torso; wide ball socket brick 67696 in the top of the upper arm | flexion all the way round (the socket turns about the axle through its slot), abduction 2°-85° in the slot, twist ±16° |
| Elbows | Technic rotation joint disks 44224 + 44225 (LEGO's big ratchet joint), each disk's beam pinned into its segment | 0°-100°, clicking in steps |
| Wrists | Technic ball on a 2L axle out of a round plate at the end of the forearm, in the fist's ball socket brick | spin, flex, sideways |
| Waist | 4 x 4 locking turntable (61485 + 60474) sunk into the hips | turns (no lean) |
| Hips | Technic ball on a 2L axle in the top of each thigh, in wide ball socket bricks facing out from the hips | flexion, abduction |
| Knees | Rotation joint disks 44224 + 44225, as the elbows | bend, clicking |
| Ankles | Technic ball on a 2L axle under the shin, in a ball socket brick in the shoe | all ways |
| Fists | Clip plate 11476 (the curled fingers) round the saw's bar handles (30374) | the handle turns and slides in the fist |

`kin.py` is the skeleton: forward kinematics for every segment (the right limbs are mirror
images of the left, so the same angles give mirror poses), inverse kinematics for the legs
(the hips' height and the shoes' studs fix them) and for both arms (each fist's clip exactly
on its handle bar, the fist pointing away from the engine, the arms kept out of the saw, body
and head).

**Engine support for ball joints.** Before this model, `find_connections` matched LDCad's
generic snaps only when their axes were parallel, so a ball in a socket at any other angle
showed as disconnected. Snaps with a spherical bounding (`[bounding=sph R]`) now connect in
any orientation when their centres meet and radii match (kind `ball`, which the buildability
check treats like clips and hinges). Shadow overlays for 53585 and 67696 in
`brickkit/data/shadow/parts/`, tests in `tests/test_match.py` and `tests/test_buildability.py`,
a note in `docs/brickkit-guide.md`.

## Poses

The static model is **t = 0, chainsaw raised**: the saw's engine centred 35 cm above the stand,
just to his right of his head, the bar pointing out to his right and up 15°, 29 LDU (1.2 cm) above
his hair; the right fist on the front handle, the left fist on the rear handle, the head
thrown back. `poses.hero()` solves both arms by inverse kinematics (exact grips).

**t = 1, chainsaw lowered**: both shoulder axles lie on one line across the chest, so turning
both arms by the same angle about it carries both fists and the saw as one rigid body: both
grips stay exact without solving anything. From t = 0 to 1 the arms swing 120° forward and
down (shoulder flexion 147°/157° to 27°/37°), the saw coming down across his hips with the
bar still pointing to his right; the waist turns 12° to his right and the head drops to look
at the saw. Legs and shoes don't move. In the real model the pose is set the same way: turn
both arms together at the shoulders.

`meta`: `mechanism_name = "Pose"`, labels "chainsaw raised" / "chainsaw lowered",
`turntable = {"cycles": 1}`.

Checks along the way: the mechanism check sweeps 24 poses (no collisions, nothing comes
apart), and `design.check_balance` (an extra check) sweeps 13 poses for the centre of mass:
it stays 76 %-89 % of the way from the edge of the base to its centre (the static model is
89 %, tipping at 17°).

## The chainsaw dance (`meta["performance"]`)

For the showreel: a sunset chainsaw dance, the figure swinging the roaring chainsaw
overhead on an empty road. `performance(u)` returns pose deltas in the same format as `pose(t)`
(`{group: 4x4}` applied on top of the static model), looping over u in [0, 1) (u = 0 and 1
identical), one loop meant to take 2.5 s:

* the waist twists the raised saw from 40° to one side to 40° to the other and back;
* the arms, fists and saw swing together about the shoulder line (the same rigid trick as the
  poses, so both fists stay exactly on their handles): high overhead as the saw passes his
  face, swung 40° forward and down at each side, so the saw draws a big arc over his head;
* the head is thrown back (12° ± 2°) and turns after the saw (a quarter of the waist's turn:
  any more and the shaggy hair meets the raised arms);
* the hips drop 4 LDU at the low end of each arc and both legs are re-solved so the ankles
  stay in the shoes: a small knee bend; the shoes stay planted.

Every angle is within the joints' real ranges. There is no whole-body spin (the video adds it).
`meta["performance_info"] = {"hide_tags": ["stand"], "ground_y": -48, "pivot": [0, 0],
"cycle_s": 2.5}`: the stand (base, floorboards, post and its pins, all tagged `stand`) is
hidden for the dance, the soles are at y = -48 LDU, and the figure's vertical axis is x = z = 0.

Checked at 24 and 48 values of u: no collisions between any parts (moving groups against
each other and against the shoes), and the loop closes exactly. The knee bend is small because
the shins meet the shoes and the thighs the hips beyond about 5 LDU; the head can't go much
further back than 14° before the back of the head meets the collar.

The build video (`model.toml` `[video]`) uses the `grindhouse` theme and opens cold on the
dance: `[video.cold_open]` scene `sunset_road`, 7 s, `motion = "performance"`, 1.5 spin turns.

## Checks

All eight pass with `.venv/bin/python -m brickkit all chainsaw_face`: real elements (169
part/colour lines, none rare), connections (one piece: 3,133 connections, 9 of them ball
joints), collisions (none among 809 parts), buildability (736 insertions, every step
reachable and connected), stability (996 g, 89 % margin, tips at 17°), mechanism (24 poses,
plus the balance sweep), electrics, technique. The `clean` colourway passes too.

## Known limits

* **The elbows still show their grey disks** in the elbow's gap, from the inside and the
  front: the rotation joint disks only come in Dark Bluish Gray and Light Bluish Gray, and
  the gap has to stay open for the elbow to bend 0°-100°. The upper arm's outer column hangs
  down over the outside of the elbow. A matching inner column was tried and dropped: it hits
  the torso's front corners as the arms come down (t = 0.7 to 1). The knees are closed down
  to an 8 LDU gap at the front (the knee is bent 15°, so the gap can't close further without
  locking the knee); a sliver of disk shows there from the side.
* **Pins**: no bright blue left. Black 2L friction pins in the knees, tan 3L pins in the bare
  skin, light grey 2L pins in the white sleeves. The support post's two long pins are tan (a
  black 3L friction pin that fits isn't in current production); only their ends show, at the
  back of the post.
* **Wrists**: the black 2L axle under each wrist ball shows between forearm and fist (2L
  axles only come in black).
* **The shoulder joint shows** between the torso and the sleeve's cap: the black ball on its
  grey axle. The arms need that room to swing overhead and down.
* **The face is a flat panel of smooth tiles**, not a sculpted mask: eye holes, nose, teeth,
  a snarl and a brow, meant to be painted or stickered with the mask's stitches and wrinkles.
* **Fists, not hands**: a ball socket brick, a palm plate, a clip plate and a curved slope
  each. No fingers or thumb: a thumb or a second knuckle slope hits the engine next to the
  right fist or blocks the saw's handles going into the clips.
* **Blocky**: 4-stud arms and a 10 x 6 torso read as a big man in the football-figure style,
  but the curves are only curved slopes at the shoulders, hair, toes and jaw.
* **Arms move as a pair**: with both fists on the saw, one arm can't move alone. Take the saw
  out of a fist to pose the arms separately.
* **Friction**: the raised saw (about 50 g) is held up by the shoulder and wrist ball joints'
  friction and the fists' clips. The checks can't judge clutch; real bricks might sag over
  time. The ratchet elbows won't.
* **Shoulder twist is ±16°**: beyond that the upper arm's socket brick meets the torso's
  axle bricks. The waist turns but can't lean.
* The splatter is 11 Dark Red tiles and small slopes in two clusters on the skirt and one on
  the bib; the clean colourway swaps them all for Yellow.

## Files

`design.py` (assembly, meta, balance check), `kin.py` (skeleton, IK), `poses.py` (hero pose,
pose(t), dance), `kit.py` (grid, courses, bonded panels, mirroring), `stand.py`, `legs.py`,
`body.py`, `head.py`, `arms.py`, `saw.py`. Renders: `out/renders/` (three_quarter, front,
side, back; `t1/` for t = 1), `out/hero/`, `out/hero_open/`.
