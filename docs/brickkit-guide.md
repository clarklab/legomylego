# brickkit — model authoring guide

brickkit turns a model written in Python into a real, checked LEGO build: an LDraw file,
a verification report, parts lists, renders (and, as they land, an instruction booklet, a
build video and a viewer page). The engine knows nothing about any particular model.

## Setup
```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m brickkit fetch          # LDraw library, LDCad snap data, Rebrickable catalogue -> .cache/
.venv/bin/python -m pytest -q               # engine tests
```
Blender 5.x must be at `/Applications/Blender.app` (override with `BRICKKIT_BLENDER`).
The cache location can be overridden with `BRICKKIT_CACHE` (useful in git worktrees).

## Commands
| Command | What it does |
|---|---|
| `brickkit new SLUG --name "Name"` | scaffold `models/SLUG/` (model.toml + design.py) |
| `brickkit build SLUG` | run design.py, write `out/SLUG.mpd` |
| `brickkit verify SLUG` | run all checks, write `out/report.{json,html}`; exit 1 on any FAIL |
| `brickkit bom SLUG` | `out/parts.csv`, `out/bricklink_wanted.xml`, `out/pick_a_brick.csv`, `out/price_estimate.md` and `out/price.json`: live BrickLink prices dated today when API keys are in `~/.config/brickkit/bricklink.env` (see `brickkit/bom/live_price.py`), else a rough range from `brickkit/data/price_bands.json` |
| `brickkit all SLUG` | build + verify + bom, then each colourway (variant) |
| `brickkit render SLUG [--views a,b] [--size N] [--samples N] [--pose T] [--lights] [--variant V]` | Blender stills in `out/renders/` |
| `brickkit booklet SLUG [--no-render]` | instruction booklet `out/booklet.pdf` (pictures in `out/booklet/`) |
| `brickkit viewer SLUG` | export `site/models/SLUG/` (GLB + model.json + files) for the viewer site |
| `brickkit turntable SLUG [--preview]` | `out/turntable.mp4`: a 12 s photoreal (Cycles) orbit with the mechanism and lights working, muted and seamless; the site plays it where WebGL is missing (`meta["turntable"]`: `program` tap/swing/lights, `cycles`, `taps`) |
| `brickkit sizzle [SLUG ...] [--stills F,F] [--preview]` | `showreel/sizzle.mp4`: one quick brand reel of several models cut on the music's beats, from their showreels' footage (config `showreel/sizzle.toml`; see Video) |
| `python tools/hero.py SLUG` | hero stills: `out/hero/`, `out/hero_lit/` (lights), `out/hero_open/` (pose 1) |
| `brickkit find "words" [--color C]` | search real LEGO parts by name, ranked by how many sets used them in that colour |

Views: `front, three_quarter, three_quarter_right, side, back, top, low`.

## Units and axes
LDraw units (LDU): 1 stud = 20, 1 plate = 8, 1 brick = 24, 1 LDU = 0.4 mm. **-Y is up.**
A part placed at `y=0` has its top face at `y=0` (studs poke up to `y=-4`); a brick stacked on
it goes at `y=-24`, a plate at `y=-8`. A 2x4 brick `3001` spans x ±40, z ±20 around its origin.
"Front" is -Z. Rotations: `from brickkit.ldraw.matrix import rot` → `rot(x=, y=, z=)` degrees,
applied X then Y then Z.

## model.toml
```toml
[model]
name = "Baby Metroid Lamp"
design = "design.py"

[palette]            # role -> real colour name (Rebrickable/BrickLink naming)
dome = "Trans-Light Blue"
fang = "White"

[variants.sable]     # optional colourways: override any roles
title = "Sable"
coat = "Reddish Brown"

[booklet]           # optional text for the instruction booklet
subtitle = "One line under the title on the cover"
intro = "A paragraph for 'Before you start' and 'About this model'"
you_will_need = ["Things besides the bricks, e.g. batteries"]
notes = ["Extra tips"]
works = [{ title = "Fangs that bite", text = "...", image = "hero_open/hero.png" }]  # under out/

[checks]
enabled = ["real_elements", "connections", "collisions", "buildability", "stability",
           "mechanism", "electrics", "technique"]
[checks.stability]
min_margin = 0.25
min_tilt_deg = 10
[checks.connections]
allow_separate_tags = []   # tags of parts allowed to be loose (e.g. a separate accessory)
```

## design.py
```python
from brickkit.ldraw.matrix import rot, translate

def build(model):
    leg = model.submodel("leg", "Leg")          # sub-assembly (built once, used many times)
    leg.place("3005", "body")                   # part, palette role or colour, pos, rot
    leg.step("Add the foot")                    # new instruction step (optional caption)
    leg.place("3024", "body", (0, 24, 0), tag="foot")

    main = model.main
    main.place("3001", "body")
    main.step()
    main.use(leg, (-30, 24, 0), tag="leg_l")    # place a sub-assembly
    main.use(leg, (30, 24, 0), rot(y=180), tag="leg_r", insert=(0, 1, 0))
```
- Part names are LDraw file names without `.dat` (aliases like `4073` are followed to `6141`).
- `tag=` labels a placement or sub-assembly. Tag paths join with `/` (e.g. `leg_l/foot`) and
  are used by mechanisms, lights and cables.
- `insert=(dx, dy, dz)` tells the buildability check which way a part slides in when it isn't
  simply pushed along its studs/pins (e.g. slid in sideways under an overhang).
- Keep steps small (1–8 parts), use sub-assemblies for anything repeated or built apart.

### Mechanisms
```python
model.moving_group("flap", "flap")                     # group name -> tag
model.pose = lambda t: {"flap": hinge_matrix(t)}       # t in [0,1] -> {group: 4x4 WORLD transform}
model.gear_pair("gear_a", "gear_b", "spur")            # spur | worm | bevel ; tags of the gears
model.extra_checks.append(lambda ctx: [])              # return issue dicts {"problem": "..."}
```
A pose transform is applied on top of each part's rest position (`M' = T @ M`). Build 4x4s
with `brickkit.ldraw.matrix.transform(pos, rot3)` / `translate`, e.g. rotation about a hinge
axis through point P: `translate(*P) @ R @ translate(*-P)`. The mechanism check sweeps 24 poses,
fails on collisions or on the model falling apart, and checks gear spacing (LEGO gears are
module 1: pitch radius = 1.25 LDU per tooth).

```python
model.moving_group("body", "*", exclude={"stand", "hub"})  # catch-all: every other part
model.allow_contact("tube", "battery", "presser pushes the button")  # may touch/overlap
model.captive("tube", "slides in the stand's top plate")   # held by a guide, not studs
```
A catch-all group moves everything not in another group and not under an excluded tag (a whole
body sliding on a fixed stand). `allow_contact` exempts pairs of tagged parts from the collision
and mechanism checks, for contact the part geometry can't show (a presser on a spring-loaded
button, a push rod riding on a lever). `captive` tells the buildability check that parts under
a tag are held without studs (a slider in its guide); the whole model must still join them up.
The Baby Metroid Lamp's tap mechanism (`models/baby_metroid/core.py`, `stand.py`) uses all three.

### Electrics and lights
```python
model.light("nucleus_1", "nucleus_l/led", color="#FF3A1A", power=1.5,
            offset=(0, 0, -70))            # render light 70 LDU along the part's -Z
model.cable("led_run", "nucleus_l/led", "battery", length=1000, route=[(x, y, z), ...])
model.glow("nucleus_l", strength=2.0)     # parts under this tag glow in `--lights` renders
model.extra("62501c01", "led", 2, "8870 light unit")   # on the parts lists, not placed in 3D
```
Cable ends are tag paths (a part's tags joined by `/`, matched at the end). The electrics check
adds up the straight segments lamp → route points → end and compares with `length` (LDU).
Use `model.extra` for bought items whose geometry is only partly placed (a light unit's lead
and plug); `data/part_map.json` sets `"bom": false` on the placed head so nothing counts twice,
and `"bricklink_type": "S"` for items BrickLink sells as sets.

## The checks
| Check | Fails when |
|---|---|
| real_elements | a part/colour pair LEGO never made (suggests substitutes); warns when rare (<3 sets or none since 2016) |
| connections | any part/sub-assembly not attached (studs, pins, axles, clips, hinges, balls via LDCad snap data) |
| collisions | two parts overlap by more than ~0.5 LDU |
| buildability | a part can't slide into place in its step, or a step leaves loose pieces |
| stability | centre of mass outside the footprint of the lowest parts, or tips over under 10° |
| mechanism | moving parts collide / disconnect across the pose sweep; gear spacing wrong |
| electrics | cable runs longer than the cable |
| technique | warnings: clips on transparent parts, moving transparent parts, uncertified geometry |

Connection points come from the LDCad shadow library. When a part has none there (for example
74611 Plate Round 8 x 8 with hole, whose underside would otherwise connect to nothing), add a
file with the same name under `brickkit/data/shadow/parts/` (or `parts/s/`) holding
`0 !LDCAD SNAP_*` lines in the part's own frame. These overlay files are read after the
library's file for that part, so they add to it; they never remove its snaps.

**Ball joints.** LDCad describes balls and their sockets as `SNAP_GEN [bounding=sph R]`
(towballs, Technic balls). A ball turns in its socket, so these connect at any orientation:
same centre (within 1 LDU), same radius (within 0.6), same group, opposite genders. They are
reported as `ball` connections, and the buildability check treats them like clips and hinges
(the socket's jaws flex as the ball pops in, so the socket never blocks the part carrying the
ball). Overlays add the Technic ball snaps LDCad lacks: 53585 (Technic Ball Joint with through
axle hole) gets the `techBallJnt` group its twin 32474 has, and 67696 (Brick 2 x 2 with wide
ball socket, the football figures' shoulder joint) gets its socket, where 92013's is. The
67696 socket's jaws leave a slot in the brick's own x-y plane: the ball's axle can swing
freely in that plane, only about 25 degrees across it.

## Workflow loop
1. `brickkit find` to pick parts that exist in your colours (prefer ≥3 sets since 2016).
2. Write/extend a sub-assembly in `design.py`.
3. `brickkit all SLUG` → fix every FAIL.
4. `brickkit render SLUG --size 700 --samples 48` → look at the PNGs, compare with references.
5. Record decisions and any deviations in `models/SLUG/NOTES.md`. Commit.

## Video
`brickkit video SLUG` makes `out/video.mp4`: a square 1080×1080, 30 fps showreel of the model
(H.264 + AAC, under 40 MB) and `out/video_poster.jpg`. Everything on screen comes from the
model: the parts list, `out/report.json`, the booklet, the poses, lights and colourways.
It needs Blender, ffmpeg and Playwright's Chromium (`.venv/bin/python -m playwright install
chromium`). A full render takes roughly an hour of GPU time per model; iterate with `--preview`.

| Flag | What it does |
|---|---|
| `--preview` | 540×540, low samples, 15 fps → `out/video_preview.mp4` (iterate with this) |
| `--segments build,scan` | only those segments → `out/video_build+scan.mp4` |
| `--no-render` | no Blender: compose from the plates already rendered (grey where missing) |
| `--stills 120,480` | write single composed frames to `out/video_frames/<q>/stills/`, no video |
| `--cold-open SCENE` | try a cold open (`sunset_road`, `night_desk`) for this run, tagged like `--theme` (`out/video_cold_open...`); `--segments cold_open,open` renders just it and the cut into the reel |
| `--scratch DIR` | write the run's work and outputs under `DIR` (the model's `out/` is only read): previews of a model someone else is working on |
| `--theme NAME` | try another theme for this run (model.toml's theme and its overrides left out): writes `out/video_NAME[...].mp4` and `out/video_frames/<q>@NAME/` (stills there too), never the model's own video, poster or plates; with `--no-render` it composes over the model's rendered plates read-only, keeping their tempo and backdrop so they line up |
| `--no-audio` | no music or sound effects |
| `--force` | re-render cached plates; `--engine cycles` / `--device cpu` as for stills |

**Segments** (beat-aligned; ones that don't apply are skipped):

| Segment | Beats | Shows | When |
|---|---:|---|---|
| cold_open | seconds + 1 | the model performs in a set of its own before anything else (a figure on a sunset road, a tap lamp on a desk at night), in two or three shots, then a hard cut to black for a beat and straight into the open (below) | `[video.cold_open]` |
| open | 6 | a brick drops and snaps, stud wipe, REAL LEGO PIECES. / CHECKED BY COMPUTER. | always |
| title | 8 | the name in kinetic type over a transparent Cycles hero, piece counter, one row of stats | always |
| build | 36 | the time-lapse build growing up from the table (parts by the height of their lowest point, outward from the centre, each waiting for something to stand on or connect to, dropping a short way into place); one orbiting shot per height band; HUD: pieces placed, height, progress | always |
| scan | 12 | a scan line sweeps the model: x-ray of its LDraw edges and connection points; the eight checks tick in with their numbers | always |
| mechanism | 12 | `model.pose`: build pose → 0 → 1 → back, with callouts tracked on real parts and a gauge | pose + groups |
| lights | 8 (+2) | the set goes dark, the lights switch on with a bloom flash; optionally a tap presses the mechanism as they do, and a second tap switches them off | lights / glow |
| lift | 6 | everything but `exclude_tag` rises and hovers | `[video] lift` |
| colourways | 4 per colourway | wipes between colourways that share the parts, with swatches | variants |
| booklet | 12 | the printed booklet: its real cover opens, a thumb-flip through the step pages (motion-blurred) lands on a step spread, then loose step sheets are dealt into a fan (from every colourway's booklet if there are any) | `out/booklet.pdf` |
| outro | 8 | logo, `bricks.superfun.games/m/SLUG`, the small print and the model's notice | always |

**Config** in model.toml (all optional; `model.meta["video"]` from design.py wins key by key):
```toml
[video]
theme = "tape"                  # brand (default) | scan | tape | playful | grindhouse
beats = { build = 28 }          # segment lengths in beats
skip = ["scan"]                 # leave segments out
facts = ["1:1 scale"]           # extra title chips (words from the model's own docs)
default_title = "Black"         # name of the default colourway (else [model] palette_title)
build_order = "ground_up"       # or "instructions": follow the booklet's order instead
sections = [[1, "Base"], ["Layer 1 (", "Dome"]]   # named parts of the build (step or caption
                                # start); ground-up bands are named after the one most of
                                # their parts belong to, when it's at least 60% of them
lift = { exclude_tag = "stand", height = 80 }
lift_label = "Lifts off its stand"
lights_label = "Nuclei light up"
lights_tap = true               # the mechanism presses as the lights switch on (a tap lamp)
lights_off = true               # a second tap switches them off again (lights_off_label)
drop = 24                       # LDU a part falls as it lands
[video.theme_overrides]         # any theme token, e.g. accent = "#FF3EA5"

[video.cold_open]               # opt-in: the reel opens on the model performing
scene = "sunset_road"           # a two-lane road running into a low sun
seconds = 7                     # the performance (rounded to beats; then a beat of black)
motion = "performance"          # meta["performance"] (else, or "pose": model.pose swinging 0..1)
spin_turns = 1.5                # the whole figure turns about its pivot, in three lurches
hide_tags = ["stand"]           # parts left out (added to performance_info's)
# optional: sun_elevation = 2.4, sun_size = 1.4 (deg), cycle = 2.5 (s), rev_tag = "saw",
# letterbox = 0.09; the set's look (defaults in render/blender_cold_open.py LOOK): exposure = -1.6
# (EV), sky_strength = 0.45, sky_tint = "#FFB070", sun_strength = 5, sun_color = "#FF9A4A",
# sun_disc = 90, fill_strength = 0.25, haze = 1900 (m), dust = 0.0015 (per m)
# a tap lamp instead: scene = "night_desk", motion = "tap" (no spin, nothing hidden), optional
# taps = [1.0, 3.0, 4.0] (s: on, off, on...; default beats 2, 6 and 8); the desk's look
# (DESK_LOOK): exposure = 0.9, moon_strength = 3.4, moon_color = "#9DB8FF", lamp_gain = 2.5
# (x the LEDs' own power), spill_strength = 2.2 (W), spill_color = "#FF7040"

[[video.callouts]]              # mechanism callouts; without any, one per moving group
label = "Dust door"
tag = "flap"                    # parts under a tag; globs make one anchor each: "fang_*"
part = "3937"                   # or a part number (one anchor per part), or color = "..."
sub = "Swings 90°"              # second line; default: how far its group turns, or its name
xray = true                     # also draw the parts' outlines (for parts hidden inside)
```
**Cold open.** `design.py` gives the motion: `model.meta["performance"] = f` with `f(u)` for u
in [0, 1) returning `{group: 4x4 world matrix}` like `model.pose` (one loop of the dance), and
`model.meta["performance_info"] = {"hide_tags": [...], "ground_y": y, "pivot": [x, z],
"cycle_s": 2.5}` (where it stands, what to hide, how long a loop takes). The loop plays at
that speed once the engine catches (after about half a second), the figure spins about the
pivot, and three shots cut hard: a 300 mm wide shot straight into the sun with the figure's
head just under it, a low 70 mm and an ankle-height 38 mm shot. `sunset_road`
(`render/blender_cold_open.py`, EEVEE) treats the figure as life-size (a man about 2 m tall
with his arms up) and builds everything procedurally: a physical sky with a dusty aureole and
thin cloud bands, a warm sun lamp along the sun's line and a camera-only sun disc; a worn
two-lane chip-seal road (patches, tar-filled cracks, polished wheel paths that take the sun's
glare, a faded dashed yellow centre line, worn edge lines, crumbling edges, caliche
shoulders); dry grass and seed stalks along the verges, lit through from behind; barbed-wire
fences; a power line and a telephone line of leaning poles with sagging wires (phased so none
stands out of the figure's head); mesquites, live oaks, a dead tree, a windpump, a farmhouse
and barn, a tree line and two ridges of low hills; aerial haze with distance and a thin dust
over the road. The lens focuses on the figure per shot (the wide shot deeper, the close shots
softer behind, oval bokeh), blurs the swing a little (a 180° shutter), and Blender's
compositor exposes each shot, blooms the highlights and throws sun beams from the visible part
of the disc. The web compositor adds letterbox bars, a veil of flare, a thin anamorphic streak
through the sun and aperture ghosts along the line through the middle (all dying when
something crosses the sun), and dust in the light; the sound is a chainsaw that is pulled,
catches, idles and roars with the saw's speed (the `rev_tag` parts'), over wind, cut dead at
the black. No music plays under it. Its plates render in about 0.6 s a frame at preview size
and 1.8 s at full size. A model without one is unchanged.

A **tap lamp** (`motion = "tap"`, for a model with a press pose and LEDs, e.g. in
`scene = "night_desk"`) is pressed and let go on three taps - on, off, on, then held into the
cut - `model.pose` 0 -> 1 -> 0 with a little rebound, clicking at the bottom of its travel,
where the push-on/push-off switch toggles its LEDs: they snap on with a flash that settles
(and its glowing parts glow with them), and go off in a few frames. The camera punches in on
each click and the picture jolts; the lamp doesn't spin. `night_desk` is a bedroom at night at
the model's real size: a varnished desk against the wall under a window of moonlit blue night
(a moon, stars and trees beyond), a curtain, books, a mug, a plant, a notebook and a print on
the wall, the moon the only light until the lamp comes on; then the LEDs light the parts they
glow in and a soft glow round them lights the room warm (light-linked, so the clear shell
isn't washed out). Two shots: the room at 40 mm from above the desk, cutting in the dark
before the third tap to a low 75 mm close with the moon through the window behind, both
slowly pushing in with shallow focus on the lamp. The compositor adds a warm haze round the
lamp while it's lit, a flash as it snaps on, and in the bottom bar what the last tap did
(TAP · ON, TAP · OFF). The sound: the switch's click on every tap, a pop as the light comes on
and a softer one as it goes off, the night under it all and a faint mains hum while it's lit
(synthesised: a plastic snap, the power-up and -down and a quiet wind unless recorded, below).
Its plates take about 0.7 s a frame at preview size and 1.7 s at full (the set renders at two
thirds of the job's samples).

**Recorded sounds** (optional). The music and effects are synthesised unless the model has
`[video.audio]`: sound files in the model's `audio/` (committed, so the video rebuilds offline)
by role. `tools/elevenlabs_sfx.py SLUG` generates them from `audio/sfx.toml` (`[[sfx]]` name,
prompt, seconds, variants, loop) with ElevenLabs' sound-generation API, skipping files that
exist and recording each file's prompt and settings in `audio/sfx_generated.json`; `--dry-run`
lists what it would make, `--analyse` measures every file (length, loudness, true peak,
silence, how it ends, band energy, engine periodicity, speech-like modulation) and ranks the
variants. The API key is read from `ELEVENLABS_API_KEY` or `~/.config/brickkit/elevenlabs.env`
and never printed or written. MP3s decode through ffmpeg.
```toml
[video.audio]
pull_start = "pull_start_1.mp3"   # the cold open: pulled at its start...
catch = 0.73                      # ...the engine catches this far in, the idle takes over
idle = "idle_1.mp3"               # looped (crossfaded) to the cut, ducked under the screams
screams = ["scream_3.mp3", ...]   # full throttle: on the swing's peaks (the saw's speed), and
                                  # quieter on the build's section changes
burst = "rev_burst_2.mp3"         # on the title's stamp (theme grindhouse), with the first...
stings = ["string_stab_1.mp3", "string_stab_3.mp3"]   # ...sting; the rest, the hits and the
hits = ["metal_hit_2.mp3"]        # booms take turns on the big cuts (a boom replaces the
booms = ["boom_2.mp3"]            # synthesised hit there)
levels = { scream = -8.5 }        # optional: peak dBFS per role (reel.SAMPLE_LEVEL)
# a tap cold open (a tap lamp):
clicks = ["click_2.mp3", ...]     # the switch, on each tap in turn
snaps_on = ["snap_on_1.mp3", ...] # a pop as the light comes on (in turn)...
snaps_off = ["snap_off_1.mp3"]    # ...and a soft one as it goes off
room = "crickets_2.mp3"           # the night outside, looped under it
```
Everything in the cold open stops dead at its cut; the synthesised music bed stays (ducked under
the stings) and the mix is mastered to the same -16 LUFS / -1.5 dBTP. Without the table a model
sounds exactly as before.

Callout anchors are the centres of the matched parts, moved by their group's pose every
frame and projected through the video camera, so the lines follow the real parts. Callouts
that match nothing are left out (with a note in the log).

**Themes** (`brickkit/video/themes.py`) set the tempo, colours, wipes, title animation and
overlay; they all share the site's type: Inter for display (700, set tight: -0.022 em for
headings, -0.028 em for the name; figures in fixed cells so counters don't jitter), Menlo
caps, tracked out, for small labels, Inter 500 for detail lines (tokens `display`, `mono`,
`brand_mono`; another face gets scaled to the same cap height). `brand` (cream and yellow,
stud wipes), `scan` (teal HUD, scan lines, blast-door wipes), `tape` (VCR on-screen display,
tracking glitches, chroma bleed; the on-screen display itself - PLAY, SP, the timecode, the
counters, CHAPTER, TRACKING - keeps a VCR's VT323 lettering), `playful` (bouncy type,
paw-print slides), `grindhouse` (a 70s drive-in horror print at 100 BPM: warm near-black,
bone type, blood red and apron yellow; gate weave, flicker, dust, hairs, scratches and light
leaks; film-burn cuts spliced in with a frame slip, frame slips between build sections, a
projector roll between colourways; the name rubber-stamped, typewritten labels, evidence-tag
callouts; a heartbeat, drone, string swells and scraped metal, with a two-stroke chainsaw on
the title). Fonts are bundled OFL fonts in `brickkit/video/web/fonts/` (Menlo is the
system's; elsewhere it falls back to the default monospace). Try one without
touching the model: `brickkit video SLUG --theme grindhouse --no-render --stills 90,150,600`.

**How it's made:** `video/timeline.py` plans the 3D shots (no Blender), `video/reel.py` the
graphics and the cue sheet from the model's data, `render/blender_animate.py` renders the
plates (EEVEE, always under the machine-wide `blender_slot()` lock, 40 frames per process),
`video/web/` is the compositor (a canvas `renderFrame(f)` run in headless Chromium by
`video/compose.py`) and `video/audio.py` synthesises the music and effects (numpy, mastered to
-16 LUFS). Plates are cached per segment, numbered from the segment's start, with a hash, so
editing graphics never re-renders 3D and moving a segment in the edit keeps its renders.

### Sizzle reel

`brickkit sizzle [SLUG ...] [--config FILE] [--out DIR] [--stills 60,240] [--preview]
[--no-audio]` cuts one quick brand reel from several models' showreels: by default
`showreel/sizzle.toml` -> `showreel/sizzle.mp4` (1080×1080, 30 fps, about 37 s, ~12 MB),
`sizzle_poster.jpg` (the finale's grid) and `sizzle_contact.jpg`. It renders nothing in 3D:
the footage is each model's last `brickkit video` run, read-only (its cached plates in
`out/video_frames/full/<segment>/`, `out/turntable.mp4`, the hero cut-out), and the frames it
uses are copied into `showreel/work/footage/` first (git-ignored), so a showreel re-rendering
at the same time doesn't matter. Run `brickkit video SLUG` for a model before adding it.

Everything sits on the music's beats. With `music` set, the track's beats are found in the
track itself (`video/beats.py`: the tempo from the onsets' autocorrelation, the beats by
dynamic programming, moved onto the kick if they locked to an off-beat hat, bars from the
claps on 2 and 4; cached in `work/beats.json`); without it a fixed grid at `bpm` drives the
house synth. Sections are counted in bars: the open (the logo, the tagline slammed on beats,
then one beat per model: its cut-out on a coloured card, in the bar before the drop), each
model (its name slammed on yellow bars over quick cuts of its own footage, a caption, stat
chips), the finale (the turntables in a 2×2 grid popping in on the beats, then "4 models ·
N pieces · every brick checked") and the outro (logo, URL, small print and the models'
notices). Wipes are the brand's: a brick wall at the drop, then studs in yellow and brick red.
```toml
title = "Bricks"
url = "bricks.superfun.games"
music = "audio/track_1.mp3"   # next to the config; omit for the synthesised music
bpm = 128                     # a hint for the beat tracker (or the synth's tempo)
whoosh = "audio/whoosh_1.mp3" # on every wipe (else the synthesised whoosh)
line = "{n} models · {pieces} pieces|every brick checked"   # the finale; | breaks the line
disclaimer = "Unofficial fan models · ..."
[theme]                       # overrides on the brand theme (the site's colours)
bg = "#FFFDF5"
bg2 = "#FEDB05"
[timeline]                    # bars
open = 4
finale = 3
outro = 2
open_words = [["Real", 4], ["LEGO.", 6], ["Checked by", 8], ["computer.", 10]]  # [word, beat]

[[model]]                     # in order; `brickkit sizzle ferret vhs_tape` keeps a subset
slug = "baby_metroid"
bars = 3
chips = ["pieces", "headline"]   # or steps, colours; in on the section's beats 4 and 6 (from 0)
[[model.shot]]                # shots follow each other, `beats` long (the last runs to the end)
source = "build"              # a plate segment of the model's video, or "turntable"
from = 0.2                    # a stretch of it (0..1), sped to fit...
to = 1.0
beats = 3
[[model.shot]]
source = "cold_open"
at = 30                       # ...or this frame of the segment lands `lead` (whole) beats in,
lead = 1                      # played at `speed` (default 1), so the moment hits the beat
beats = 3
caption = "Tap: lights on"
sfx = "../models/baby_metroid/audio/snap_on_1.mp3"   # a sound on that beat...
sfx_align = "peak"            # ...its loudest moment on it (else its start)
sfx_level = -1.0              # peak dBFS against the music (default -9); it stops at the cut
```
The sound is `video/audio.py`'s: the track as a bed (`cues["track"]`: balanced to the same
level as the synthesised music, faded out at the reel's end, which is the bar where the music
ends), the models' own sounds ducking it, clicks on the cuts, pops on the chips, snaps on the
slams, mastered to -16 LUFS / -2 dBTP (the AAC encode adds a few tenths; the file stays
under -1.5 dBTP). The track, whoosh and clunk are ElevenLabs'
(`showreel/audio/sfx.toml`: a `[[music]]` entry goes through the music API - prompt, seconds,
instrumental - and `[[sfx]]` through sound generation, as for a model: `python
tools/elevenlabs_sfx.py showreel/audio`). To choose a shot's `at`, look through the plates
(for example the frame a lamp snaps on or a door lands) and preview with `--stills`.

## Shape helpers
`brickkit.shapes.rings`: `ring_cells(r_out, r_in)`, `pack_cells(cells, lengths, offset, mode)`
(bonded 1xN runs), `exposed(lower, upper)` (step cells for slopes, with outward direction),
`shell_layers(profile, heights, thickness)` (shells of revolution).
