# brickkit + Baby Metroid — Design Spec

Date: 2026-09-25
Status: approved in brainstorming (user: "just keep going")

## 1. Goal

Build a buildable, working, realistic LEGO model of a Baby Metroid from real LEGO elements, verified
on a computer, with a LEGO-style instruction booklet (PDF), a build/demo video, parts lists with
price estimates, and a local viewer site. Everything is produced by a model-agnostic engine
(`brickkit`) so future models (different shapes, parts, colours) reuse the same pipeline.

### Reference we are improving on

Victor M's "Microduck" (x.com/victormustar/status/2103110908444631120; booklet
`microduck_bookletV2.pdf`): 1113 basic bricks/plates in 6 opaque colours, voxel-sampled from CAD,
a pinned statue ("joints are fixed ... the model is a statue"), explicitly "not physically
build-tested"; computer checks for connections, collisions, step insertion, centre of mass;
Python-generated booklet; exploded build animation video; BrickLink wanted list.

Our improvements:
- **Realistic**: translucent dome, lit translucent nuclei, curved bone fangs, organic shaping with
  curved/round/dome parts and SNOT, not voxel stacking. Photoreal rendering (Blender Cycles).
- **Working**: knob-driven fang mechanism, switchable lights, removable hover stand.
- **Real**: every part+colour pair must be a real LEGO element (Rebrickable element catalogue),
  only standard connection types (LDCad snap metadata), stricter checks (mechanism sweep, cable
  reach, technique flags) on top of Victor's set.
- **Honest**: we also cannot physically build it; the booklet says so plainly.

## 2. Decisions (from the user)

| Topic | Decision |
|---|---|
| Working features | Fang mechanism + hover stand + light-up nuclei |
| Size | Large, ~25 cm body width, target 900–1400 parts |
| Dome colour | Let parts decide → **Trans-Light Blue** (145 shaping part types in sets since 2016 vs 48 Trans-Bright Green, 19 Trans-Green) |
| Skirt colour | **Coral** with **Dark Red** accents |
| Lights | **Power Functions** LEDs + battery box with on/off switch (discontinued 2018, sold on BrickLink) |
| Parts ordering | Lists + price estimate only (user places orders) |
| Video | Square 1080×1080, ~40 s |
| Renderer | Blender 5.2.2 (installed via Homebrew, runs headless, Metal GPU) |
| Extensibility | Whole system model-agnostic; viewer site ready for future models |

## 3. Architecture

```
metroid-lego/
  brickkit/                  # engine — never imports model-specific code
    catalog/                 # LDraw library + Rebrickable elements; colour/part mapping; availability
    ldraw/                   # LDraw parser, transforms, mesh flattening, MPD writer
    snaps/                   # LDCad shadow snap parser → per-part connection points
    model/                   # builder API: Model, Submodel, Step, place(), roles, joints, lights
    checks/                  # verifier plugins (registry), each returns pass/warn/fail + details
    bom/                     # parts CSV, BrickLink wanted XML, Pick a Brick CSV, price estimate
    render/                  # Blender scripts (instruction style, photoreal, animation)
    booklet/                 # HTML/CSS templates → PDF via headless Chromium (Playwright)
    video/                   # storyboard → Blender frames → ffmpeg
    viewer_export/           # packs model + geometry + steps + mechanism for the viewer
    cli.py                   # `brickkit <cmd> <model>`
  models/
    baby_metroid/
      model.toml             # name, scale, palette roles, booklet text, video storyboard, stand, lights
      design.py              # shape: builds sub-assemblies with the builder API
      out/                   # generated: .mpd, report, booklet, video, parts, viewer bundle (gitignored except final deliverables)
    _sample/                 # tiny test model used by engine tests
  viewer/                    # static three.js site; lists all models/*/out/viewer bundles
  tests/                     # pytest for the engine
  .cache/                    # downloaded libraries (gitignored)
  docs/superpowers/          # specs and plans
```

### 3.1 Data sources (cached in `.cache/`, fetched by `brickkit fetch`)
- LDraw complete library (`library.ldraw.org/library/updates/complete.zip`): part geometry, `LDConfig.ldr` colours.
- Rebrickable CSVs (`elements`, `parts`, `colors`, `inventory_parts`, `inventories`, `sets`, `part_relationships`, `part_categories`): real element IDs, production years, set counts.
- LDCad shadow library (GitHub `RolandMelkert/LDCadShadowLibrary`): `!LDCAD SNAP_CYL/CLP/FGR/GEN/INCL/CLEAR` connection metadata.

### 3.2 Engine interfaces (contracts, not final code)
- `Catalog`: `part(part_id) -> PartInfo(name, ldraw_file, category)`, `color(name|ldraw_code) -> Color(ldraw_code, rebrickable_id, bricklink_id?, rgb, is_trans)`, `element(part, color) -> ElementInfo(element_ids, last_year, set_count) | None`, `substitutes(part, color) -> list`.
- `Geometry`: `mesh(part) -> triangles (LDU)`, `bbox(part)`, `volume(part)`.
- `Snaps`: `connectors(part) -> list[Connector(kind, gender, pos, axis, profile)]` resolved through `SNAP_INCL`/`SNAP_CLEAR` and the part's primitive references.
- `Model` builder: `Model(name, palette)`; `sub = model.submodel("fang_left")`; `sub.step()`; `sub.place(part, role|color, pos, rot, note=None)`; `sub.use(other_submodel, pos, rot)`; joints: `model.joint(name, kind="revolute"|"prismatic", axis, parts|submodel, range, driven_by=...)`; lights: `model.light(name, part, cable_to=...)`. Units are LDU (1 stud = 20, plate = 8, brick = 24). Colours are **roles** resolved through the palette.
- `Check` plugin: `name`, `run(model, catalog, geometry, snaps) -> CheckResult(status, items)`; registered in a registry; `model.toml` can enable/disable/configure checks.
- Outputs are driven by `model.toml`; the engine has no Metroid knowledge.

### 3.3 Extensibility requirements
- `brickkit new <name>` scaffolds `models/<name>/` from a template.
- Changing a palette role in `model.toml` (e.g. `dome = "Trans-Bright Green"`) and re-running `brickkit verify` reports every part that does not exist in the new colour, with substitutes.
- New parts need no engine change (geometry and snaps come from the libraries).
- Checks, booklet sections and video shots are data/plugins; a model can add its own check module.
- The viewer discovers models from `viewer/models.json`, regenerated by `brickkit viewer`.

## 4. The Baby Metroid model

### 4.1 Size and proportions (targets, LDU; 1 stud = 8 mm)
- Body max diameter 30–32 studs (24–25.6 cm), body height dome top → skirt bottom ~18–20 cm.
- Fangs extend 6–8 cm below the skirt. Stand lifts fang tips ~4–6 cm above the base.
- Part count 900–1400.

### 4.2 Palette roles (`model.toml`)
| Role | Colour |
|---|---|
| dome | Trans-Light Blue |
| nucleus | Trans-Red |
| nucleus_core, veins, inner_dark | Dark Red |
| skirt | Coral |
| skirt_accent | Dark Red |
| fang | White |
| fang_base | Light Nougat |
| mouth / ribbing | Dark Red / Tan |
| frame (hidden) | Light Bluish Gray / Black / Dark Bluish Gray |
| stand_column | Trans-Clear |
| stand_base | Black / Dark Bluish Gray |

### 4.3 Sub-assemblies
1. **Core frame** (Technic): carries everything; mounts nuclei, dome base ring, mechanism, battery box, stand socket.
2. **Mechanism**: knob (Dark Red) at the back of the skirt → worm gear (self-locking) → pinion → vertical rack/slider → 4 link rods → 4 fang levers pivoting on tangential axles at the skirt rim. Fangs swing ~35–45° outward (open) / inward (closed). Worm holds any position.
3. **Nuclei ×3**: bumpy spheres ~7–9 studs across (two lower front-left/front-right, one upper back-centre, like the reference), Trans-Red round plates / cones / 2×2 domes on SNOT cores, each containing a PF LED head.
4. **Lights**: 2× PF LED light (4 heads: 3 nuclei + 1 mouth glow), PF battery box with switch inside the body, switch reachable from below. Cable reach verified.
5. **Mouth / inner body**: ribbed Dark Red/Tan structure under the nuclei (visible through the dome).
6. **Dome shell**: Trans-Light Blue, self-supporting ring-stacked shell with curved/dome parts smoothing the profile and a large dome/dish cap; minimal internal structure visible.
7. **Skirt ring**: Coral with Dark Red accents, organic lip under the dome, fang openings.
8. **Fangs ×4** at 45°/135°/225°/315°: Light Nougat bases, White curved tips (e.g. 40379, 13564, 11089, 87747), Technic beam core.
9. **Hover stand**: Trans-Clear 2×2 round bricks (3941) on an axle, weighted Black/Dark Bluish Gray base; Metroid lifts off.

Exact parts and positions are decided in implementation, bounded by the checks. Deviations from this
section are allowed when a check requires it and must be recorded in `models/baby_metroid/NOTES.md`.

## 5. Checks (all must pass before booklet/video)
1. **real_elements** — every (part, colour) has a Rebrickable element ID; warn if not seen in a set since 2016 or if set count < 3 (rare); report BrickLink availability in price step.
2. **connections** — build connection graph from snaps (stud/anti-stud, pin/hole, axle/axle-hole, clip/bar, finger hinges, ball/socket); every part connected to the model; no part held only by a non-standard contact.
3. **collisions** — no two parts' meshes interpenetrate beyond 0.2 LDU tolerance (after shrinking by tolerance; touching faces allowed).
4. **buildability** — per step, each new part can translate along its insertion axis (from its connectors) from ≥1 stud away without colliding; each sub-assembly is one connected piece after every step.
5. **stability** — mass from mesh volume × ABS density (1.05 g/cm³) + known electric part masses; model centre of mass projects inside the stand base footprint with ≥ 25% margin; body on stand survives ±10° tilt.
6. **mechanism** — gear pairs at valid centre distances; sweep the knob across its full range in ≥ 24 poses; no collisions in any pose; fang opening angle in 30–50°; linkage consistent (link lengths constant).
7. **electrics** — each LED head connected to battery box via cables whose required route length ≤ available cable length (+ extension wires if listed); switch accessible.
8. **technique** — flag trans parts carrying mechanism loads, clips on trans parts, single-stud cantilevers > 4 studs, known illegal techniques list.

Report: `out/report.json` + `out/report.html`.

## 6. Outputs
- `out/baby_metroid.mpd` — LDraw multi-part file with STEP metas and submodels (opens in BrickLink Studio / LeoCAD / LDCad).
- `out/booklet.pdf` — A4 landscape, LEGO style: cover (photoreal), before-you-start (honest "checked on a computer, not built yet"), how to read, build overview (sub-assemblies), steps with parts callouts and new-part outlines, rotate icons, "turn the knob now"/"switch on" test steps, gallery, parts inventory (element IDs + BrickLink numbers), about/verification page.
- `out/video.mp4` — 1080×1080, H.264, 35–45 s: title → build animation (parts fly in per step, orbit) → lights on → fangs open/close → lift off stand → booklet flip → end card.
- `out/parts.csv`, `out/bricklink_wanted.xml`, `out/pick_a_brick.csv`, `out/price_estimate.md`.
- `out/renders/` — hero renders (front, 3/4, top, fangs open, lights on).
- `out/viewer/` — bundle for the viewer site.
- `viewer/` — static site: model index, three.js 3D view, step slider, mechanism slider, lights toggle, parts list, check report. `brickkit serve` runs it locally.

## 7. Review gate
After the first full model passes checks, render hero images and show them to the user before
producing the booklet and video.

## 8. Testing
- pytest for the engine: LDraw parse/transform, colour/part mapping, snap resolution (3001 has 8 studs + tubes), connection matching (stacked bricks connect, offset bricks don't), collision (overlapping bricks fail, stacked pass), insertion, BOM export round-trip.
- `_sample` model exercised end-to-end in tests (build → verify → bom → viewer export).
- Booklet: every model step appears; parts inventory totals equal model part count.
- Video: ffprobe confirms 1080×1080 and 35–45 s.

## 9. Limits (stated in booklet and README)
- Not physically build-tested. Clutch, friction, tolerances, plastic flex and real cable stiffness are not simulated.
- Prices are a snapshot on the generation date.
- Power Functions is discontinued; availability via BrickLink.

## 10. Out of scope
Ordering/checkout, motorisation, sound, public hosting of the viewer (can be added later).
