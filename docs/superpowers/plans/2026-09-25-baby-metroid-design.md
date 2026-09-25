# Baby Metroid Design Implementation Plan (Plan 2 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Engine tooling every model needs (part-id canonicalisation, part search, Blender renders, revolved shells), then the Baby Metroid model itself, iterated until every check passes and the hero renders look right.

**Architecture:** Tooling lands in `brickkit/` (model-agnostic). The model lives in `models/baby_metroid/` as sub-assembly functions in `design.py`. Design tasks are exploratory CAD: their "tests" are the engine checks plus explicit numeric acceptance criteria; exact coordinates are found by iterating (build → verify → render → adjust). Decisions and deviations go in `models/baby_metroid/NOTES.md`.

**Tech Stack:** as Plan 1, plus Blender 5.2 (`/Applications/Blender.app/Contents/MacOS/Blender`, headless, Cycles on Metal).

**Parts research (2026-09-25, Rebrickable set counts in the named colour):**
- Trans-Light Blue dome vocabulary: 3005 brick 1x1 (107), 3065 brick 1x2 w/o tube (141), 3024 plate 1x1 (138), 3023b plate 1x2 (314), 3069b/2431/3070b tiles, 54200 cheese (219), 11477 curved 2x1 (45), 3062b round 1x1 (363), 6141 round plate (631), 25269 quarter tile (44), 4740/43898/3960/4285b dishes 2/3/4/6 (157/51/19/18), 30562 quarter cylinder panel (27), 2571 curved-top panel (35), 42022 curved 6x1 (13). Bigger TLB bricks/plates (1x4, 2x2, 2x4…) have element ids but no sets → avoid.
- Trans-Red nuclei: 6141 (1685), 98138 (663), 3024 (648), 3062b (276), 59900 cone (157), 4740 (123), 3941 (10).
- Fangs: Tan has far more shaping parts than Light Nougat → `fang_base = "Tan"`; White tips 40379 (55), 87747 (143), 11089 (18), 13564 (52).
- Skirt: Coral (bricks/plates/tiles/11477/54200/27925/25269) with Dark Red for everything Coral lacks.
- Mechanism: 4716 worm, 3648b 24T, 3647 8T, 3743 rack 1x4, beams/pins/axles in LBG/Black.
- Electrics: LDraw splits PF 8870 into 62501c01 (junction box) + 2x 62498c01 (LED heads); Rebrickable has one part 61930. AAA box 64228 (LBG). 50 cm LED lead per the LEGO product listing (assumption, stated in NOTES/booklet).
- LDraw "~Moved to" aliases exist (3023→3023b, 4073→6141, 2654→2654a…); Rebrickable sometimes uses the base number (3023b→3023).

---

### Task 1: Canonical part ids, moved aliases, `brickkit find`

**Files:**
- Modify: `brickkit/catalog/catalog.py` (add `rb_part` fallback, `canonical`, `search`)
- Modify: `brickkit/model/builder.py` (`Submodel.place` canonicalises part names)
- Modify: `brickkit/cli.py` (add `find`)
- Test: `tests/test_catalog_ids.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_catalog_ids.py`
```python
from brickkit.model.builder import Model


def test_moved_alias_is_followed(engine):
    assert engine.catalog.canonical("4073.dat") == "6141.dat"
    m = Model("T", "t", {}, engine.catalog)
    assert m.main.place("4073", "Trans-Red").part == "6141.dat"


def test_rebrickable_fallback_strips_variant_letter(engine):
    cat = engine.catalog
    assert cat.element("3023b.dat", "Trans-Light Blue") is not None


def test_search_by_words_and_colour(engine):
    rows = engine.catalog.search("dish inverted", color="Trans-Light Blue")
    parts = [r[1] for r in rows]
    assert "4740" in parts and all(r[0] >= 0 for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_catalog_ids.py -v`
Expected: FAIL with `AttributeError: 'Catalog' object has no attribute 'canonical'`

- [ ] **Step 3: Implement**

Add to `Catalog` (keep existing methods):

```python
    def canonical(self, part: str) -> str:
        """Follow LDraw '~Moved to X' aliases to the current file name."""
        name = normalize(part)
        for _ in range(5):
            desc = self.ldraw.description(name)
            m = re.match(r"~Moved to\s+(\S+)", desc)
            if not m:
                break
            name = normalize(m.group(1))
        return name

    def rb_part(self, part: str) -> str:
        pm = self._pm(part)
        if "rebrickable" in pm:
            return pm["rebrickable"]
        pid = part_id(part)
        if pid in self.rb.parts:
            return pid
        m = re.match(r"^(\d+)[a-z]$", pid)
        if m and m.group(1) in self.rb.parts:
            return m.group(1)
        return pid

    def search(self, text: str, color=None, limit: int = 40) -> list[tuple]:
        """(sets, part, name, has_ldraw) for Rebrickable parts whose name has every word."""
        words = text.lower().split()
        c = self.color(color) if color else None
        rows = []
        for pnum, (name, _) in self.rb.parts.items():
            low = name.lower()
            if not all(w in low for w in words):
                continue
            if c is not None:
                key = (pnum, c.rb_id)
                sets = self.rb.set_count.get(key, 0)
                if not sets and key not in self.rb.elements:
                    continue
            else:
                sets = max((self.rb.set_count.get((pnum, cid), 0)
                            for cid in self.rb.part_colors.get(pnum, ())), default=0)
            rows.append((sets, pnum, name, self.ldraw.resolve(pnum) is not None))
        rows.sort(key=lambda r: -r[0])
        return rows[:limit]
```
(imports: `import re`, `from ..ldraw.library import normalize`). In `Submodel.place`, use `self.model.canonical(part)` where `Model.canonical` calls `self.catalog.canonical` when a catalog is present. In `cli.py` add `find TEXT [--color C] [--limit N]` printing `sets  part  ldraw?  name`.

- [ ] **Step 4: Run test to verify it passes** — `.venv/bin/python -m pytest -q` (all green)
- [ ] **Step 5: Commit** — `feat: canonical LDraw ids, Rebrickable id fallback, part search`

---

### Task 2: Blender renderer (`brickkit render`)

**Files:**
- Create: `brickkit/render/__init__.py`, `brickkit/render/scene.py` (engine side), `brickkit/render/blender_scene.py` (runs inside Blender)
- Modify: `brickkit/model/builder.py` (`light(..., color, power)`, `glow_tags`), `brickkit/cli.py` (add `render`)
- Test: `tests/test_render.py`

Scene contract (`scene.json`, all positions in LDU, LDraw axes):
```json
{"meshes": {"3001.dat": "/abs/.cache/blender/3001.dat.npz"},
 "instances": [{"part": "3001.dat", "color": 4, "matrix": [[...4x4...]], "glow": 0.0}],
 "colors": {"4": {"rgb": "#C91A09", "alpha": 255, "material": ""}},
 "bounds": [[minx, miny, minz], [maxx, maxy, maxz]],
 "lights": [{"pos": [x, y, z], "color": "#FF2A10", "power": 1.5}],
 "views": [{"name": "front", "azimuth": 0, "elevation": 8, "lens": 70, "ortho": false}],
 "size": [900, 900], "samples": 64, "engine": "cycles", "background": "#E9ECEF",
 "ground": true, "transparent": false, "out_dir": "/abs/out/renders"}
```
Blender converts LDraw → Blender with `(x, y, z) → (x, z, -y) * 0.0004 m`, welds vertices, smooth-by-angle 35°, one mesh per part, object-linked material slot 0 for the main colour, Principled BSDF (trans → transmission 1, roughness 0.04, IOR 1.58), 3-point area lights scaled to the model, optional ground plane, camera framed on the bounding sphere. Prints `BRICKKIT_DONE` on success.

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_render.py`
```python
import shutil

import numpy as np
import pytest
from PIL import Image

from brickkit.project import Project
from brickkit.render.scene import BLENDER, render_model


@pytest.mark.skipif(not shutil.which(BLENDER) and not __import__("os").path.exists(BLENDER),
                    reason="Blender not installed")
def test_render_sample(engine, tmp_path):
    model = Project("_sample").build(engine.catalog)
    files = render_model(engine, model, tmp_path, views=["three_quarter"], size=160, samples=8)
    im = np.asarray(Image.open(files[0]).convert("RGB"), float)
    assert im.shape[:2] == (160, 160)
    assert im.std() > 8          # not a blank frame
```

- [ ] **Step 2: Run** — FAIL (`No module named brickkit.render`)
- [ ] **Step 3: Implement** `scene.py` (`export_meshes`, `model_scene`, `run_blender`, `render_model`, `VIEWS`) and `blender_scene.py` per the contract above; CLI `render SLUG [--views a,b] [--size N] [--samples N] [--pose T] [--lights]` writing `out/renders/<view>.png`.
- [ ] **Step 4: Run** — `.venv/bin/python -m pytest tests/test_render.py -v` PASS; `python -m brickkit render _sample` produces images; eyeball them.
- [ ] **Step 5: Commit** — `feat: Blender renderer for any model`

---

### Task 3: Revolved shells (`brickkit.shapes`)

**Files:**
- Create: `brickkit/shapes/__init__.py`, `brickkit/shapes/rings.py`
- Test: `tests/test_shapes.py`

Behaviour:
- `ring_cells(r_out, r_in, center=(0,0))` → set of integer stud cells `(i, k)` (cell centre at `(i+0.5, k+0.5)` studs from the centre when the ring is on an even grid) whose centre distance d satisfies `r_in <= d < r_out`.
- `pack_cells(cells, lengths=(2, 1), offset=0)` → list of runs `(i, k, length, axis)` covering every cell exactly once with straight 1×N runs along X on even `offset` layers and Z on odd, preferring the longest allowed length, so consecutive layers bond (seams alternate).
- `exposed(cells_below, cells_above)` → cells of the lower layer not covered by the upper one, each with its outward radial direction (one of ±X/±Z) for placing slopes.
- `shell_layers(profile, heights)` → per layer `(y, r_out, r_in)` where `r_in = min(r_out - thickness, r_out_next - 1)` so the next layer always sits on this one.

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_shapes.py`
```python
from brickkit.shapes.rings import exposed, pack_cells, ring_cells, shell_layers


def test_ring_is_symmetric_and_thin():
    cells = ring_cells(6, 5)
    assert cells and all((-i - 1, k) in cells and (i, -k - 1) in cells for i, k in cells)
    assert all(5 <= ((i + .5) ** 2 + (k + .5) ** 2) ** .5 < 6 for i, k in cells)


def test_pack_covers_every_cell_once():
    cells = ring_cells(8, 6)
    runs = pack_cells(cells, lengths=(2, 1), offset=0)
    covered = []
    for i, k, n, axis in runs:
        covered += [(i + d, k) if axis == "x" else (i, k + d) for d in range(n)]
    assert sorted(covered) == sorted(cells)


def test_exposed_cells_face_outward():
    lower, upper = ring_cells(8, 6), ring_cells(7, 5)
    ex = exposed(lower, upper)
    assert ex and all(c in lower and c not in upper for c, _ in ex)


def test_shell_layers_overlap():
    layers = shell_layers(lambda h: 8 - h / 3, [0, 1, 2, 3, 4, 5, 6])
    for (y0, ro0, ri0), (y1, ro1, ri1) in zip(layers, layers[1:]):
        assert ri0 <= ro1 - 1
```

- [ ] **Step 2–5:** run → fail, implement, run → pass, commit `feat: ring and shell helpers for revolved shapes`

---

### Task 3b: Palette variants (colourways)

**Files:** Modify `brickkit/project.py`, `brickkit/model/builder.py`, `brickkit/cli.py`; Test `tests/test_variants.py`.

`model.toml` may define `[variants.<name>]` tables that override palette roles (plus optional `title`). `Project.variants()` returns `{name: merged palette}`; `Project.build(catalog, variant=None)` builds with that palette and sets `model.variant`. CLI: `--variant NAME` on build/verify/bom/render; `all` runs the full pipeline on the default palette, then for every variant runs `real_elements` + `technique`, the BOM and renders into `out/variants/<name>/`.

```python
def test_variants_change_colours_only(engine, tmp_path):
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "model.toml").write_text(
        '[model]\nname = "V"\n[palette]\nbody = "White"\n[variants.red]\nbody = "Red"\n')
    (tmp_path / "v" / "design.py").write_text(
        'def build(model):\n    model.main.place("3001", "body")\n')
    p = Project("v", tmp_path)
    assert list(p.variants()) == ["red"]
    a, b = p.build(engine.catalog), p.build(engine.catalog, variant="red")
    assert a.flatten()[0].color.name == "White" and b.flatten()[0].color.name == "Red"
    assert b.variant == "red"
```
Commit: `feat: palette variants (colourways) per model`

### Task 4: Baby Metroid scaffold + stand + core frame
`brickkit new baby_metroid --name "Baby Metroid"`; palette from spec §4.2 with `fang_base = "Tan"`; `design.py` with `build(model)` calling `stand()`, `core()` sub-assembly functions. Acceptance: `brickkit all baby_metroid` → all checks pass; stand base ≥ 16×16 studs; stand column of Trans-Clear 3941 on an axle; core has a Technic socket that the column's axle enters.

### Task 5: Mechanism + fangs
Knob (Black 32072) at the back → worm 4716 → 24T 3648b → pinion → rack 3743 (vertical slider) → 4 links → 4 fang levers on tangential pins. Model registers `moving_group`s for slider/links/fangs, `gear_pair`s, and `model.pose(t)` computed from the linkage geometry (t=0 closed, t=1 open). Acceptance: mechanism check passes over 24 poses; fang tip opening angle 30–50° (extra check in design.py); every fang tip is a White claw part.

### Task 6: Skirt ring
Coral/Dark Red ring around the core at the fang level with openings for the fangs' swing. Acceptance: checks pass at every pose (fangs clear the skirt).

### Task 7: Nuclei ×3 + electrics
Nucleus sub-assembly (≈8 studs across, bumpy Trans-Red surface, PF LED head inside); two lower-front and one upper-back; 2× PF 8870 (junction boxes) + AAA box 64228 in the body with switch reachable from below; `model.cable` runs with route waypoints; `model.light` entries for renders. Acceptance: electrics check passes; nuclei read as red bumpy spheres in the render.

### Task 8: Dome shell
Trans-Light Blue shell from `shapes.shell_layers` with a Metroid profile (widest ~25% up, tucked rim), 1x2/1x1 bricks and plates with alternating bond, 11477/54200/25269 smoothing on exposed steps, dish cap. Acceptance: all checks pass; ≥ 90% of dome parts have ≥ 3 sets in TLB; render reads as a smooth translucent dome.

### Task 9: Final assembly, verification, hero renders (review gate)
Assemble; `brickkit all baby_metroid` all PASS (warnings reviewed and recorded in NOTES.md); hero renders (front, three-quarter, fangs open, lights on) shown to the user before Plan 3 output production.
