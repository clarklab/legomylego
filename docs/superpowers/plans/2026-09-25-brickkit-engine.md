# brickkit Engine Implementation Plan (Plan 1 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A model-agnostic Python engine that loads real LEGO part data, lets a model be described in code, writes it as an LDraw MPD file, verifies it (real elements, connections, collisions, buildability, stability, mechanism, electrics, technique) and exports parts lists.

**Architecture:** `brickkit/` package. LDraw geometry is flattened (with BFC winding) and cached; LDCad shadow-library snap metadata gives connection points; FCL collides meshes shrunk 0.25 LDU inward so touching parts don't count; Rebrickable CSVs say which part/colour pairs LEGO really made. Models live in `models/<slug>/` (`model.toml` + `design.py`) and are loaded by `Project`. Checks are registered plugins. Spike results (2026-09-25): 3001 flattened to 700 triangles, volume 39,733 LDU³ (hand estimate ≈39,600); stacked/offset/touching bricks and seated pins don't collide, overlaps do, after insetting each triangle in its own plane.

**Tech Stack:** Python 3.12 venv (`.venv`), numpy, scipy, python-fcl, trimesh (later plans), pytest. Units are LDraw units (LDU): 1 stud = 20, 1 plate = 8, 1 brick = 24; −Y is up.

**Conventions for this plan:** every file block is preceded by `**File:** \`path\`` and contains the complete file. Run everything from the repo root with `.venv/bin/python`.

## Follow-up plans (written after this one lands, because they depend on its interfaces)
- **Plan 2 — Baby Metroid design:** `models/baby_metroid/` (design.py, model.toml, NOTES.md), PF electrics data, mechanism kinematics; iterate until all checks pass; hero render review gate.
- **Plan 3 — Render, booklet, video, prices:** Blender scene/materials/instruction-style renders, photoreal hero shots, HTML→PDF booklet, animation + ffmpeg video, BrickLink price estimate.
- **Plan 4 — Viewer site:** static three.js site reading `models/*/out/viewer/` bundles; `brickkit viewer` / `brickkit serve`; branded with `logo.png` ("L'Eggo my LEGO"); deployed on Netlify from GitHub `clarklab/legomylego` (`netlify.toml`, static publish dir, no build step). Final URL **https://lego.superfun.games**: full `<meta>` (description, theme-color, canonical), Open Graph + Twitter cards with a generated 1200x630 og:image per page, `site.webmanifest`, favicons (ico/svg/png 16-512, apple-touch-icon) generated from `logo.png`.

---

### Task 1: Project scaffold, paths, engine shell, fetch

**Files:**
- Create: `pyproject.toml`, `brickkit/__init__.py`, `brickkit/__main__.py`, `brickkit/paths.py`, `brickkit/engine.py`, `brickkit/fetch.py`, `tests/conftest.py`, `tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_paths.py`
```python
from brickkit import paths


def test_paths_are_under_repo_root():
    assert paths.CACHE.parent == paths.ROOT
    assert paths.MODELS_DIR == paths.ROOT / "models"
    assert paths.DATA_DIR.name == "data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit'`

- [ ] **Step 3: Write minimal implementation**

**File:** `pyproject.toml`
```toml
[project]
name = "brickkit"
version = "0.1.0"
description = "Design, verify and document buildable LEGO models"
requires-python = ">=3.12"
dependencies = ["numpy", "scipy", "trimesh", "python-fcl", "jinja2", "playwright"]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
brickkit = "brickkit.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["brickkit*"]

[tool.setuptools.package-data]
brickkit = ["data/*.json", "templates/model/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**File:** `brickkit/__init__.py`
```python
"""brickkit: design, verify and document buildable LEGO models."""

__version__ = "0.1.0"
```

**File:** `brickkit/__main__.py`
```python
from .cli import main

raise SystemExit(main())
```

**File:** `brickkit/paths.py`
```python
"""Well-known locations. Override the cache with BRICKKIT_CACHE."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("BRICKKIT_CACHE", ROOT / ".cache"))
MODELS_DIR = ROOT / "models"
DATA_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
```

**File:** `brickkit/engine.py`
```python
"""Lazily-built shared services (part library, caches, catalog) for one session."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path

from . import paths


class Engine:
    def __init__(self, cache: Path | None = None):
        self.cache = Path(cache) if cache else paths.CACHE

    @cached_property
    def lib(self):
        from .ldraw.library import LDrawLibrary
        return LDrawLibrary(self.cache / "ldraw")

    @cached_property
    def geom(self):
        from .ldraw.geometry import GeometryCache
        return GeometryCache(self.lib, self.cache / "geom")

    @cached_property
    def shadow(self):
        from .snaps.shadow import ShadowLibrary
        return ShadowLibrary(self.cache / "ldcad_shadow" / "LDCadShadowLibrary-main", self.lib)

    @cached_property
    def catalog(self):
        from .catalog.catalog import Catalog
        return Catalog.load(self.lib, self.cache / "rebrickable", self.cache / "rb_index.pkl")

    @cached_property
    def collide(self):
        from .geometry.collide import CollisionEngine
        return CollisionEngine(self.geom)

    def context(self, model, config: dict | None = None):
        from .checks.base import CheckContext
        return CheckContext(model, self, config or {})
```

**File:** `brickkit/fetch.py`
```python
"""Download and unpack the part libraries into the cache (idempotent)."""
from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

from . import paths

LDRAW_URL = "https://library.ldraw.org/library/updates/complete.zip"
SHADOW_URL = "https://github.com/RolandMelkert/LDCadShadowLibrary/archive/refs/heads/master.zip"
REBRICKABLE_URL = "https://cdn.rebrickable.com/media/downloads/{}.csv.gz"
REBRICKABLE_TABLES = ("elements", "parts", "colors", "inventory_parts", "inventories", "sets",
                      "part_relationships", "part_categories")


def _download(url: str, dst: Path, log) -> Path:
    log(f"downloading {url}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh)
    tmp.replace(dst)
    return dst


def fetch(cache: Path | None = None, force: bool = False, log=print) -> None:
    cache = Path(cache) if cache else paths.CACHE
    cache.mkdir(parents=True, exist_ok=True)
    if force or not (cache / "ldraw" / "LDConfig.ldr").exists():
        z = _download(LDRAW_URL, cache / "ldraw_complete.zip", log)
        zipfile.ZipFile(z).extractall(cache)
    if force or not (cache / "ldcad_shadow" / "LDCadShadowLibrary-main").exists():
        z = _download(SHADOW_URL, cache / "ldcad_shadow.zip", log)
        zipfile.ZipFile(z).extractall(cache / "ldcad_shadow")
    for table in REBRICKABLE_TABLES:
        dst = cache / "rebrickable" / f"{table}.csv.gz"
        if force or not dst.exists():
            _download(REBRICKABLE_URL.format(table), dst, log)
    log(f"libraries ready in {cache}")
```

**File:** `tests/conftest.py`
```python
import pytest

from brickkit import paths
from brickkit.engine import Engine


@pytest.fixture(scope="session")
def engine():
    if not (paths.CACHE / "ldraw" / "LDConfig.ldr").exists():
        pytest.skip("part libraries missing: run `.venv/bin/python -m brickkit fetch`")
    return Engine()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pip install -q -e '.[dev]' && .venv/bin/python -m pytest tests/test_paths.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml brickkit tests
git commit -m "feat: brickkit package scaffold, paths, engine shell, library fetch"
```

---

### Task 2: Transform helpers

**Files:**
- Create: `brickkit/ldraw/__init__.py`, `brickkit/ldraw/matrix.py`
- Test: `tests/test_matrix.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_matrix.py`
```python
import numpy as np

from brickkit.ldraw.matrix import apply, format_type1, is_mirror, parse_type1, rot, transform


def test_rot_y_90_maps_x_to_minus_z():
    assert np.allclose(rot(y=90) @ [1, 0, 0], [0, 0, -1])


def test_parse_format_roundtrip():
    color, M, name = parse_type1("1 4 10 -24 0 0 0 1 0 1 0 -1 0 0 3001.dat".split())
    assert color == 4 and name == "3001.dat"
    assert np.allclose(M[:3, 3], [10, -24, 0])
    assert np.allclose(parse_type1(format_type1(color, M, name).split())[1], M)


def test_apply_and_mirror():
    M = transform((1, 2, 3), rot(z=90))
    assert np.allclose(apply(M, [[1, 0, 0]]), [[1, 3, 3]])
    assert not is_mirror(M)
    assert is_mirror(np.diag([-1.0, 1, 1, 1]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_matrix.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.ldraw'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/ldraw/__init__.py`
```python
"""LDraw file handling: library index, colours, geometry, transforms."""
```

**File:** `brickkit/ldraw/matrix.py`
```python
"""4x4 transforms in LDraw units (LDU). LDraw's -Y axis points up."""
from __future__ import annotations

import math

import numpy as np


def translate(x: float = 0, y: float = 0, z: float = 0) -> np.ndarray:
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def rot(x: float = 0, y: float = 0, z: float = 0) -> np.ndarray:
    """3x3 rotation from Euler angles in degrees, applied about X, then Y, then Z."""
    ax, ay, az = (math.radians(v) for v in (x, y, z))
    cx, sx, cy, sy, cz, sz = (math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay),
                              math.cos(az), math.sin(az))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    R[np.abs(R) < 1e-12] = 0.0
    return R


def transform(pos=(0, 0, 0), rot3=None) -> np.ndarray:
    M = np.eye(4)
    if rot3 is not None:
        M[:3, :3] = np.asarray(rot3, dtype=float)
    M[:3, 3] = pos
    return M


def parse_color(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        return int(token, 16) if token.lower().startswith("0x") else 16


def parse_type1(tokens: list[str]) -> tuple[int, np.ndarray, str]:
    """Parse a type-1 line given as tokens, including the leading '1'."""
    x, y, z, a, b, c, d, e, f, g, h, i = (float(t) for t in tokens[2:14])
    M = np.eye(4)
    M[:3, :3] = ((a, b, c), (d, e, f), (g, h, i))
    M[:3, 3] = (x, y, z)
    return parse_color(tokens[1]), M, " ".join(tokens[14:])


def _fmt(v: float) -> str:
    v = 0.0 if abs(v) < 1e-9 else float(v)
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def format_type1(color: int, M: np.ndarray, name: str) -> str:
    vals = list(M[:3, 3]) + list(M[:3, :3].reshape(-1))
    return f"1 {color} " + " ".join(_fmt(v) for v in vals) + f" {name}"


def apply(M: np.ndarray, pts) -> np.ndarray:
    pts = np.asarray(pts, dtype=float)
    return pts @ M[:3, :3].T + M[:3, 3]


def is_mirror(M: np.ndarray) -> bool:
    return float(np.linalg.det(M[:3, :3])) < 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_matrix.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/ldraw tests/test_matrix.py
git commit -m "feat: LDraw transform helpers"
```

---

### Task 3: LDraw library index and colours

**Files:**
- Create: `brickkit/ldraw/library.py`
- Test: `tests/test_library.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_library.py`
```python
from brickkit.ldraw.library import normalize


def test_normalize():
    assert normalize("S\\3001S01.DAT") == "s/3001s01.dat"
    assert normalize("3001") == "3001.dat"


def test_resolve_and_colours(engine):
    lib = engine.lib
    assert lib.resolve("3001") is not None
    assert lib.resolve("s\\3001s01.dat") is not None
    assert lib.resolve("48\\1-4cyli.dat") is not None
    assert lib.colors[43].name == "Trans_Light_Blue" and lib.colors[43].is_trans
    assert "Brick  2 x  4" in lib.description("3001.dat")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_library.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.ldraw.library'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/ldraw/library.py`
```python
"""Case-insensitive index of an LDraw-style library tree, plus LDConfig colours."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

SUBDIRS = (("parts", ""), ("parts/s", "s/"), ("p", ""), ("p/48", "48/"), ("p/8", "8/"),
           ("models", ""))


def normalize(name: str) -> str:
    n = name.strip().strip('"').replace("\\", "/").lower()
    if not n.endswith((".dat", ".ldr", ".mpd")):
        n += ".dat"
    return n


def part_id(name: str) -> str:
    n = normalize(name)
    return n[:-4] if n.endswith(".dat") else n


class FileIndex:
    def __init__(self, root):
        self.root = Path(root)
        self.files: dict[str, Path] = {}
        for sub, prefix in SUBDIRS:
            d = self.root / sub
            if not d.is_dir():
                continue
            for f in os.listdir(d):
                fl = f.lower()
                if fl.endswith((".dat", ".ldr")):
                    self.files.setdefault(prefix + fl, d / f)

    def resolve(self, name: str) -> Path | None:
        return self.files.get(normalize(name))

    def __contains__(self, name: str) -> bool:
        return normalize(name) in self.files


@dataclass(frozen=True)
class LDrawColor:
    code: int
    name: str
    rgb: str
    edge: str
    alpha: int
    material: str

    @property
    def is_trans(self) -> bool:
        return self.alpha < 255


COLOUR_RE = re.compile(
    r"^0\s+!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+(#[0-9A-Fa-f]{6})\s+EDGE\s+(\S+)(.*)$")
MATERIALS = ("CHROME", "PEARLESCENT", "RUBBER", "MATTE_METALLIC", "METAL", "GLITTER", "SPECKLE")


def parse_ldconfig(path) -> dict[int, LDrawColor]:
    out: dict[int, LDrawColor] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = COLOUR_RE.match(line.strip())
        if not m:
            continue
        name, code, value, edge, rest = m.groups()
        alpha = re.search(r"ALPHA\s+(\d+)", rest)
        material = next((w.lower() for w in MATERIALS if w in rest), "")
        out[int(code)] = LDrawColor(int(code), name, value.upper(), edge,
                                    int(alpha.group(1)) if alpha else 255, material)
    return out


class LDrawLibrary(FileIndex):
    def __init__(self, root):
        super().__init__(root)
        self.colors = parse_ldconfig(self.root / "LDConfig.ldr")

    def description(self, name: str) -> str:
        p = self.resolve(name)
        if not p:
            return ""
        with open(p, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
        return first[1:].strip() if first.startswith("0") else first
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_library.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/ldraw/library.py tests/test_library.py
git commit -m "feat: LDraw library index and LDConfig colours"
```

---

### Task 4: Geometry flattening with BFC and disk cache

**Files:**
- Create: `brickkit/ldraw/geometry.py`
- Test: `tests/test_geometry.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_geometry.py`
```python
import numpy as np


def test_brick_2x4_mesh(engine):
    m = engine.geom.mesh("3001.dat")
    lo, hi = m.bbox
    assert np.allclose(lo, [-40, -4, -20]) and np.allclose(hi, [40, 24, 20])
    assert m.certified
    V, cen = m.volume_centroid()
    assert 39000 < V < 40500
    assert abs(cen[0]) < 0.5 and abs(cen[2]) < 0.5


def test_main_colour_is_inherited(engine):
    assert set(np.unique(engine.geom.mesh("3001.dat").colors)) == {16}


def test_disk_cache_roundtrip(engine, tmp_path):
    from brickkit.ldraw.geometry import GeometryCache
    a = GeometryCache(engine.lib, tmp_path).mesh("3004.dat")
    b = GeometryCache(engine.lib, tmp_path).mesh("3004.dat")
    assert np.allclose(a.tris, b.tris) and a.certified == b.certified
    assert any(tmp_path.iterdir())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.ldraw.geometry'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/ldraw/geometry.py`
```python
"""Flatten LDraw parts into triangle meshes, honouring BFC winding (CCW = outward)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .library import LDrawLibrary, normalize
from .matrix import is_mirror, parse_color, parse_type1


@dataclass
class Mesh:
    tris: np.ndarray         # (N,3,3) float64
    colors: np.ndarray       # (N,) int32; 16 = the part's main colour
    edges: np.ndarray        # (E,2,3) type-2 lines
    edge_colors: np.ndarray  # (E,) int32; 24 = edge colour of the main colour
    cond: np.ndarray         # (C,4,3) type-5 conditional lines
    certified: bool          # winding is trustworthy for every triangle

    @property
    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        if len(self.tris) == 0:
            return np.zeros(3), np.zeros(3)
        pts = self.tris.reshape(-1, 3)
        return pts.min(0), pts.max(0)

    def volume_centroid(self) -> tuple[float, np.ndarray]:
        if len(self.tris) == 0:
            return 0.0, np.zeros(3)
        a, b, c = self.tris[:, 0], self.tris[:, 1], self.tris[:, 2]
        v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
        V = float(v.sum())
        if abs(V) < 1e-9:
            return 0.0, (a + b + c).mean(0) / 3.0
        return V, (v[:, None] * (a + b + c) / 4.0).sum(0) / V


def _empty(certified: bool = True) -> Mesh:
    return Mesh(np.zeros((0, 3, 3)), np.zeros(0, np.int32), np.zeros((0, 2, 3)),
                np.zeros(0, np.int32), np.zeros((0, 4, 3)), certified)


def _cat(arrs, shape, dtype=float):
    return np.concatenate(arrs).astype(dtype) if arrs else np.zeros(shape, dtype)


class GeometryCache:
    def __init__(self, lib: LDrawLibrary, cache_dir: Path | None = None):
        self.lib = lib
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._mem: dict[str, Mesh] = {}
        self._sub: dict[str, Mesh] = {}
        self.missing: set[str] = set()

    def mesh(self, name: str) -> Mesh:
        key = normalize(name)
        if key in self._mem:
            return self._mem[key]
        m = self._load(key)
        if m is None:
            m = self._flatten(key, ())
            self._save(key, m)
        self._mem[key] = m
        return m

    def _cache_file(self, key: str) -> Path | None:
        return self.cache_dir / (key.replace("/", "__") + ".npz") if self.cache_dir else None

    def _load(self, key: str) -> Mesh | None:
        f = self._cache_file(key)
        src = self.lib.resolve(key)
        if f is None or not f.exists() or src is None or f.stat().st_mtime < src.stat().st_mtime:
            return None
        d = np.load(f)
        return Mesh(d["tris"], d["colors"], d["edges"], d["edge_colors"], d["cond"],
                    bool(d["certified"]))

    def _save(self, key: str, m: Mesh) -> None:
        f = self._cache_file(key)
        if f is None or key in self.missing:
            return
        f.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(f, tris=m.tris, colors=m.colors, edges=m.edges,
                            edge_colors=m.edge_colors, cond=m.cond, certified=m.certified)

    def _flatten(self, key: str, stack: tuple) -> Mesh:
        if key in self._sub:
            return self._sub[key]
        path = self.lib.resolve(key)
        if path is None:
            self.missing.add(key)
            return _empty(False)
        tris, cols, edges, ecols, conds = [], [], [], [], []
        certified = nocert = False
        ccw = True
        invert_next = False
        subs_certified = True
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                t = raw.split()
                if not t:
                    continue
                kind = t[0]
                if kind == "0":
                    if len(t) >= 2 and t[1] == "BFC":
                        rest = [w.upper() for w in t[2:]]
                        if "NOCERTIFY" in rest:
                            nocert = True
                        elif "CERTIFY" in rest:
                            certified = True
                        if "CW" in rest:
                            ccw = False
                        if "CCW" in rest:
                            ccw = True
                        if "INVERTNEXT" in rest:
                            invert_next = True
                    continue
                if kind == "1" and len(t) >= 15:
                    color, M, sub = parse_type1(t)
                    subkey = normalize(sub)
                    inv = invert_next ^ is_mirror(M)
                    invert_next = False
                    if subkey in stack:
                        continue
                    sm = self._flatten(subkey, stack + (key,))
                    subs_certified = subs_certified and sm.certified
                    R, T = M[:3, :3].T, M[:3, 3]
                    if len(sm.tris):
                        pts = sm.tris @ R + T
                        tris.append(pts[:, ::-1] if inv else pts)
                        c = sm.colors.copy()
                        if color != 16:
                            c[c == 16] = color
                        cols.append(c)
                    if len(sm.edges):
                        edges.append(sm.edges @ R + T)
                        ec = sm.edge_colors.copy()
                        if color != 16:
                            ec[ec == 16] = color
                        ecols.append(ec)
                    if len(sm.cond):
                        conds.append(sm.cond @ R + T)
                elif kind == "3" and len(t) >= 11:
                    p = np.array(t[2:11], float).reshape(1, 3, 3)
                    tris.append(p if ccw else p[:, ::-1])
                    cols.append(np.array([parse_color(t[1])], np.int32))
                elif kind == "4" and len(t) >= 14:
                    q = np.array(t[2:14], float).reshape(4, 3)
                    pair = np.stack([q[[0, 1, 2]], q[[0, 2, 3]]])
                    tris.append(pair if ccw else pair[:, ::-1])
                    cols.append(np.full(2, parse_color(t[1]), np.int32))
                elif kind == "2" and len(t) >= 8:
                    edges.append(np.array(t[2:8], float).reshape(1, 2, 3))
                    ecols.append(np.array([parse_color(t[1])], np.int32))
                elif kind == "5" and len(t) >= 14:
                    conds.append(np.array(t[2:14], float).reshape(1, 4, 3))
        m = Mesh(_cat(tris, (0, 3, 3)), _cat(cols, (0,), np.int32), _cat(edges, (0, 2, 3)),
                 _cat(ecols, (0,), np.int32), _cat(conds, (0, 4, 3)),
                 certified and not nocert and subs_certified)
        self._sub[key] = m
        return m
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_geometry.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/ldraw/geometry.py tests/test_geometry.py
git commit -m "feat: LDraw geometry flattening with BFC winding and disk cache"
```

---

### Task 5: LDCad snap metadata → connectors

**Files:**
- Create: `brickkit/snaps/__init__.py`, `brickkit/snaps/connector.py`, `brickkit/snaps/shadow.py`
- Test: `tests/test_snaps.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_snaps.py`
```python
import numpy as np


def _studs(conns, gender):
    return [c for c in conns if c.kind == "cyl" and c.gender == gender and c.secs
            and abs(c.secs[0][1] - 6) < 0.1]


def test_brick_2x4_has_8_studs_and_8_antistuds(engine):
    cs = engine.shadow.connectors("3001.dat")
    assert len(_studs(cs, "M")) == 8
    assert len(_studs(cs, "F")) == 8


def test_duplicates_removed(engine):
    assert len(_studs(engine.shadow.connectors("3004.dat"), "M")) == 2


def test_stud_axis_points_up_from_top_face(engine):
    stud = _studs(engine.shadow.connectors("3001.dat"), "M")[0]
    assert np.allclose(stud.axis, [0, -1, 0])
    assert abs(stud.origin[1]) < 1e-6


def test_grid_expands(engine):
    from brickkit.snaps.shadow import grid_frames
    assert len(grid_frames("C 4 C 2 20 20")) == 8
    xs = sorted({round(f[0, 3]) for f in grid_frames("C 4 C 2 20 20")})
    assert xs == [-30, -10, 10, 30]


def test_technic_pin_has_two_pin_halves(engine):
    halves = [c for c in engine.shadow.connectors("2780.dat")
              if c.gender == "M" and c.secs and c.secs[0] == ("R", 8.0, 2.0)]
    assert len(halves) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_snaps.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.snaps'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/snaps/__init__.py`
```python
"""Connection points from the LDCad shadow library and matching between parts."""
```

**File:** `brickkit/snaps/connector.py`
```python
"""A connection point. Cylinder sections run from the origin along the frame's -Y axis."""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np


@dataclass
class Connector:
    kind: str                  # cyl | clp | fgr | gen
    gender: str                # M | F (fgr: gender of first finger)
    M: np.ndarray              # 4x4 orthonormal frame
    secs: tuple = ()           # ((shape, radius, length), ...); shape in R A S _L L_
    caps: str = "one"
    center: bool = False
    slide: bool = False
    group: str = ""
    cid: str = ""
    radius: float = 0.0        # clp / fgr
    length: float = 0.0        # clp
    seq: tuple = ()            # fgr finger widths
    bounding: tuple = ()       # gen
    scale_rule: str = "none"
    mirror_rule: str = "none"

    @property
    def origin(self) -> np.ndarray:
        return self.M[:3, 3]

    @property
    def axis(self) -> np.ndarray:
        return -self.M[:3, 1]

    def total_length(self) -> float:
        if self.kind == "cyl":
            return float(sum(s[2] for s in self.secs))
        if self.kind == "clp":
            return self.length
        if self.kind == "fgr":
            return float(sum(self.seq))
        return 0.0

    def intervals(self) -> list[tuple[float, float, str, float]]:
        """(t0, t1, shape, radius) along `axis`, measured from `origin`."""
        L = self.total_length()
        t = -L / 2 if self.center else 0.0
        if self.kind == "cyl":
            out = []
            for shape, r, ln in self.secs:
                out.append((t, t + ln, shape, r))
                t += ln
            return out
        if self.kind == "clp":
            return [(t, t + L, "R", self.radius)]
        if self.kind == "fgr":
            return [(t, t + L, "F", self.radius)]
        return []

    def transformed(self, W: np.ndarray) -> "Connector":
        return replace(self, M=W @ self.M)
```

**File:** `brickkit/snaps/shadow.py`
```python
"""Resolve LDCad `!LDCAD SNAP_*` metas for a part through its LDraw subfile tree."""
from __future__ import annotations

import itertools
import re
from dataclasses import replace

import numpy as np

from ..ldraw.library import FileIndex, LDrawLibrary, normalize
from ..ldraw.matrix import parse_type1
from .connector import Connector

META_RE = re.compile(r"^0\s+!LDCAD\s+(SNAP_\w+)\s*(.*)$")
PARAM_RE = re.compile(r"\[(\w+)=([^\]]*)\]")
KINDS = {"SNAP_CYL": "cyl", "SNAP_CLP": "clp", "SNAP_FGR": "fgr", "SNAP_GEN": "gen",
         "SNAP_SPH": "gen"}


def _floats(s: str) -> list[float]:
    return [float(x) for x in s.split()]


def _bool(s) -> bool:
    return str(s).strip().lower() == "true"


def _frame(P: dict) -> np.ndarray:
    M = np.eye(4)
    if "ori" in P:
        M[:3, :3] = np.array(_floats(P["ori"])).reshape(3, 3)
    if "pos" in P:
        M[:3, 3] = _floats(P["pos"])
    return M


def _secs(s: str) -> tuple:
    t = s.split()
    return tuple((t[i], float(t[i + 1]), float(t[i + 2])) for i in range(0, len(t) - 2, 3))


def grid_frames(spec: str | None) -> list[np.ndarray]:
    """Expand `[C] Xcnt [C] Zcnt Xstep Zstep` (or the 3-axis form) into offset frames."""
    if not spec:
        return [np.eye(4)]
    vals, centered, c = [], [], False
    for tok in spec.split():
        if tok.upper() == "C":
            c = True
            continue
        vals.append(float(tok))
        centered.append(c)
        c = False
    if len(vals) == 4:
        counts, flags, steps, axes = vals[:2], centered[:2], vals[2:], (0, 2)
    elif len(vals) == 6:
        counts, flags, steps, axes = vals[:3], centered[:3], vals[3:], (0, 1, 2)
    else:
        raise ValueError(f"unsupported grid spec {spec!r}")
    ranges = []
    for cnt, cf, st in zip(counts, flags, steps):
        n = int(cnt)
        off = -(n - 1) * st / 2 if cf else 0.0
        ranges.append([off + k * st for k in range(n)])
    frames = []
    for combo in itertools.product(*ranges):
        G = np.eye(4)
        for ax, v in zip(axes, combo):
            G[ax, 3] = v
        frames.append(G)
    return frames


def _make(kind: str, P: dict) -> Connector:
    k = KINDS[kind]
    gender = "F" if kind == "SNAP_CLP" else P.get("gender", "M").strip().upper()[:1]
    if kind == "SNAP_FGR":
        gender = P.get("genderofs", "M").strip().upper()[:1]
    bounding = tuple(P.get("bounding", "").split())
    if kind == "SNAP_SPH":
        bounding = ("sph", P.get("radius", "0"))
    return Connector(
        kind=k, gender=gender, M=np.eye(4), secs=_secs(P.get("secs", "")),
        caps=P.get("caps", "one").lower(), center=_bool(P.get("center")),
        slide=_bool(P.get("slide")), group=P.get("group", "").lower(),
        cid=P.get("id", "").lower(),
        radius=float(P.get("radius", 4.0 if kind == "SNAP_CLP" else 0.0)),
        length=float(P.get("length", 8.0 if kind == "SNAP_CLP" else 0.0)),
        seq=tuple(_floats(P.get("seq", ""))), bounding=bounding,
        scale_rule=P.get("scale", "none").lower(),
        mirror_rule=P.get("mirror", "cor" if kind == "SNAP_CYL" else "none").lower())


def place(c: Connector, W: np.ndarray) -> Connector | None:
    """Apply a (possibly scaled or mirrored) transform, following the snap's scale/mirror rules."""
    F = W @ c.M
    R = F[:3, :3].copy()
    sx, sy, sz = np.linalg.norm(R, axis=0)
    if min(sx, sy, sz) < 1e-9:
        return None
    if np.linalg.det(R) < 0:
        if c.mirror_rule == "none":
            return None
        R[:, 0] = -R[:, 0]
    y_scaled = abs(sy - 1) > 1e-4
    r_scaled = abs(sx - 1) > 1e-4 or abs(sz - 1) > 1e-4
    if y_scaled and c.scale_rule not in ("yonly", "yandr"):
        return None
    if r_scaled and c.scale_rule not in ("ronly", "yandr"):
        return None
    out = np.eye(4)
    out[:3, :3] = R / np.array([sx, sy, sz])
    out[:3, 3] = F[:3, 3]
    ky = sy if y_scaled else 1.0
    kr = sx if r_scaled else 1.0
    return replace(c, M=out,
                   secs=tuple((s, round(r * kr, 4), round(ln * ky, 4)) for s, r, ln in c.secs),
                   radius=c.radius * kr, length=c.length * ky,
                   seq=tuple(q * ky for q in c.seq))


def _dedupe(conns: list[Connector]) -> list[Connector]:
    seen, out = set(), []
    for c in conns:
        key = (c.kind, c.gender, tuple(np.round(c.M[:3, :], 2).ravel()), c.secs,
               round(c.radius, 2), round(c.length, 2), c.seq, c.group)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


class ShadowLibrary:
    def __init__(self, root, ldraw: LDrawLibrary):
        self.index = FileIndex(root)
        self.ldraw = ldraw
        self._metas: dict[str, list] = {}
        self._own: dict[str, list[Connector]] = {}
        self._all: dict[str, list[Connector]] = {}

    def metas(self, name: str) -> list[tuple[str, dict]]:
        key = normalize(name)
        if key not in self._metas:
            out = []
            p = self.index.resolve(key)
            if p:
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = META_RE.match(line.strip())
                    if m:
                        params = {k.lower(): v.strip() for k, v in PARAM_RE.findall(m.group(2))}
                        out.append((m.group(1).upper(), params))
            self._metas[key] = out
        return self._metas[key]

    def own_connectors(self, name: str) -> list[Connector]:
        """The shadow file's own metas plus SNAP_INCL'd files (no LDraw inheritance)."""
        key = normalize(name)
        if key in self._own:
            return self._own[key]
        self._own[key] = []
        out: list[Connector] = []
        for kind, P in self.metas(key):
            if kind == "SNAP_CLEAR":
                continue
            base = _frame(P)
            if kind == "SNAP_INCL":
                if "scale" in P:
                    base = base @ np.diag(_floats(P["scale"])[:3] + [1.0])
                for G in grid_frames(P.get("grid")):
                    for c in self.own_connectors(P.get("ref", "")):
                        cc = place(c, base @ G)
                        if cc is not None:
                            out.append(replace(cc, cid=P.get("id", cc.cid).lower()))
            elif kind in KINDS:
                proto = _make(kind, P)
                out.extend(replace(proto, M=base @ G) for G in grid_frames(P.get("grid")))
        self._own[key] = out
        return out

    def connectors(self, name: str) -> list[Connector]:
        """All connectors of a part in its own frame (own + included + inherited from subfiles)."""
        key = normalize(name)
        if key in self._all:
            return self._all[key]
        self._all[key] = []
        clear_all, clear_ids = False, set()
        for kind, P in self.metas(key):
            if kind == "SNAP_CLEAR":
                if P.get("id"):
                    clear_ids.add(P["id"].lower())
                else:
                    clear_all = True
        conns = list(self.own_connectors(key))
        path = self.ldraw.resolve(key)
        if path is not None and not clear_all:
            for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
                t = raw.split()
                if len(t) >= 15 and t[0] == "1":
                    _, M, sub = parse_type1(t)
                    for c in self.connectors(sub):
                        if c.cid and c.cid in clear_ids:
                            continue
                        cc = place(c, M)
                        if cc is not None:
                            conns.append(cc)
        self._all[key] = _dedupe(conns)
        return self._all[key]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_snaps.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/snaps tests/test_snaps.py
git commit -m "feat: resolve LDCad snap metadata into part connectors"
```

---

### Task 6: Matching connectors between placed parts

**Files:**
- Create: `brickkit/snaps/match.py`
- Test: `tests/test_match.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_match.py`
```python
from brickkit.ldraw.matrix import rot, transform
from brickkit.snaps.match import find_connections


def world(engine, placements):
    return [[c.transformed(M) for c in engine.shadow.connectors(p)] for p, M in placements]


def test_stacked_bricks_have_8_stud_connections(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((0, -24, 0)))]))
    assert len(conns) == 8 and all(c.kind == "stud" for c in conns)


def test_offset_by_one_stud_has_6(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((20, -24, 0)))]))
    assert len(conns) == 6


def test_half_stud_offset_does_not_connect(engine):
    conns = find_connections(world(engine, [("3001.dat", transform()),
                                            ("3001.dat", transform((10, -24, 0)))]))
    assert conns == []


def test_pin_seated_in_beam_hole(engine):
    conns = find_connections(world(engine, [("32523.dat", transform()),
                                            ("2780.dat", transform((0, -10, 0), rot(z=90)))]))
    assert any(c.kind == "pin" for c in conns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_match.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.snaps.match'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/snaps/match.py`
```python
"""Find which connectors of different parts engage each other."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .connector import Connector

# (male shape, female shape) pairs that engage
COMPAT = {("R", "R"), ("R", "S"), ("A", "A"), ("A", "R"), ("S", "S")}
RADIUS_TOL = 0.6


@dataclass
class Connection:
    a: int
    b: int
    ca: Connector
    cb: Connector
    kind: str       # stud | pin | axle | bar | clip | hinge | gen
    overlap: float  # engaged length in LDU


def _axis_key(axis: np.ndarray) -> tuple[tuple, np.ndarray]:
    a = axis / np.linalg.norm(axis)
    k = int(np.argmax(np.abs(a)))
    if a[k] < 0:
        a = -a
    return tuple(np.round(a, 3) + 0.0), a


def _mapped(m: Connector, f: Connector) -> list[tuple[float, float, str, float]]:
    """f's intervals expressed in m's axis parameter."""
    d = float(np.dot(f.origin - m.origin, m.axis))
    sgn = 1.0 if float(np.dot(m.axis, f.axis)) > 0 else -1.0
    out = []
    for t0, t1, s, r in f.intervals():
        a0, a1 = d + sgn * t0, d + sgn * t1
        out.append((min(a0, a1), max(a0, a1), s, r))
    return out


def cyl_overlap(m: Connector, f: Connector) -> float:
    total = 0.0
    fin = _mapped(m, f)
    for t0, t1, sm, rm in m.intervals():
        if sm in ("_L", "L_"):
            continue
        for u0, u1, sf, rf in fin:
            if sf in ("_L", "L_"):
                continue
            ov = min(t1, u1) - max(t0, u0)
            if ov > 0 and (sm, sf) in COMPAT and abs(rm - rf) <= RADIUS_TOL:
                total += ov
    return total


def extent_overlap(a: Connector, b: Connector) -> float:
    ia, ib = a.intervals(), _mapped(a, b)
    if not ia or not ib:
        return 0.0
    return min(ia[-1][1], ib[-1][1]) - max(ia[0][0], ib[0][0])


def _classify(m: Connector, f: Connector) -> str:
    if f.kind == "clp":
        return "clip"
    shapes = {s for _, _, s, _ in m.intervals()} | {s for _, _, s, _ in f.intervals()}
    if "A" in shapes:
        return "axle"
    r = max((r for _, _, s, r in m.intervals() if s in ("R", "S")), default=0.0)
    if abs(r - 6) < 0.7 and m.total_length() <= 6.5:
        return "stud"
    if r <= 4.6:
        return "bar"
    return "pin"


def match_pair(a: Connector, b: Connector, min_overlap: float = 0.9):
    """Return (kind, overlap) if the two (collinear) connectors engage, else None."""
    if a.kind == "fgr" and b.kind == "fgr":
        if a.group != b.group or abs(a.radius - b.radius) > RADIUS_TOL:
            return None
        ov = extent_overlap(a, b)
        return ("hinge", ov) if ov >= 1.0 else None
    if "gen" in (a.kind, b.kind) or "fgr" in (a.kind, b.kind):
        return None
    if a.kind == "clp" and b.kind == "clp":
        return None
    if a.kind == "clp":
        f, m = a, b
    elif b.kind == "clp":
        f, m = b, a
    else:
        if a.gender == b.gender:
            return None
        m, f = (a, b) if a.gender == "M" else (b, a)
    if m.gender != "M":
        return None
    if (m.group or f.group) and m.group != f.group:
        return None
    ov = cyl_overlap(m, f)
    if ov < min_overlap:
        return None
    return _classify(m, f), ov


def find_connections(conns_by_part: list[list[Connector]], min_overlap: float = 0.9
                     ) -> list[Connection]:
    buckets: dict[tuple, list] = defaultdict(list)
    gens: dict[str, list] = defaultdict(list)
    for i, conns in enumerate(conns_by_part):
        for c in conns:
            if c.kind == "gen":
                gens[c.group].append((i, c))
                continue
            key, a = _axis_key(c.axis)
            foot = c.origin - np.dot(c.origin, a) * a
            buckets[(key, tuple(np.round(foot / 0.5).astype(int)))].append((i, c))
    out: list[Connection] = []
    for items in buckets.values():
        for x in range(len(items)):
            i, ci = items[x]
            for y in range(x + 1, len(items)):
                j, cj = items[y]
                if i == j:
                    continue
                res = match_pair(ci, cj, min_overlap)
                if res:
                    out.append(Connection(i, j, ci, cj, res[0], res[1]))
    for items in gens.values():
        for x in range(len(items)):
            i, ci = items[x]
            for y in range(x + 1, len(items)):
                j, cj = items[y]
                if i == j or ci.gender == cj.gender:
                    continue
                if (np.linalg.norm(ci.origin - cj.origin) <= 1.0
                        and abs(np.dot(ci.M[:3, 1], cj.M[:3, 1])) > 0.999):
                    out.append(Connection(i, j, ci, cj, "gen", 0.0))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_match.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/snaps/match.py tests/test_match.py
git commit -m "feat: match engaged connectors between parts"
```

---

### Task 7: Collision engine and part mass

**Files:**
- Create: `brickkit/geometry/__init__.py`, `brickkit/geometry/collide.py`, `brickkit/geometry/mass.py`
- Test: `tests/test_collide.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_collide.py`
```python
import pytest

from brickkit.ldraw.matrix import rot, transform

I = transform()
CASES = [
    ("stacked", "3001.dat", I, "3001.dat", transform((0, -24, 0)), False),
    ("stacked offset one stud", "3001.dat", I, "3001.dat", transform((20, -24, 0)), False),
    ("overlap by a plate", "3001.dat", I, "3001.dat", transform((0, -16, 0)), True),
    ("side by side touching", "3001.dat", I, "3001.dat", transform((80, 0, 0)), False),
    ("side by side 1 LDU overlap", "3001.dat", I, "3001.dat", transform((79, 0, 0)), True),
    ("plate on brick", "3001.dat", I, "3024.dat", transform((10, -8, 10)), False),
    ("pin seated", "32523.dat", I, "2780.dat", transform((0, -10, 0), rot(z=90)), False),
    ("pin collar inside hole", "32523.dat", I, "2780.dat", transform((0, 0, 0), rot(z=90)), True),
]


@pytest.mark.parametrize("label,a,Ma,b,Mb,expected", CASES, ids=[c[0] for c in CASES])
def test_pair_collisions(engine, label, a, Ma, b, Mb, expected):
    assert engine.collide.collide_pair(a, Ma, b, Mb) is expected


def test_pairs_and_hits(engine):
    items = [("3001.dat", I), ("3001.dat", transform((0, -24, 0))),
             ("3001.dat", transform((0, -40, 0)))]
    assert engine.collide.pairs(items) == [(1, 2)]
    assert engine.collide.hits("3001.dat", transform((0, -12, 0)), items[:1])
    assert not engine.collide.hits("3001.dat", transform((0, -24, 0)), items[:1])


def test_mass_of_2x4_brick(engine):
    from brickkit.geometry.mass import part_mass
    g, cen, approx = part_mass(engine.geom.mesh("3001.dat"), is_trans=False)
    assert 2.0 < g < 3.2 and not approx
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_collide.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.geometry'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/geometry/__init__.py`
```python
"""Collision detection and mass properties on flattened part meshes."""
```

**File:** `brickkit/geometry/collide.py`
```python
"""Mesh collisions via FCL on shrunk meshes: faces move `shrink` LDU inward and are inset
in their own plane by the same amount, so parts that only touch never register."""
from __future__ import annotations

import fcl
import numpy as np

from ..ldraw.geometry import GeometryCache


def shrink_tris(T: np.ndarray, d: float) -> np.ndarray:
    if len(T) == 0:
        return T
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    L = np.linalg.norm(n, axis=1)
    keep = L > 1e-9
    T, n, L = T[keep], n[keep] / L[keep, None], L[keep]
    a = np.linalg.norm(T[:, 1] - T[:, 2], axis=1)
    b = np.linalg.norm(T[:, 2] - T[:, 0], axis=1)
    c = np.linalg.norm(T[:, 0] - T[:, 1], axis=1)
    per = a + b + c
    r = L / np.maximum(per, 1e-12)            # inradius = 2*area/perimeter, area = L/2
    inc = (a[:, None] * T[:, 0] + b[:, None] * T[:, 1] + c[:, None] * T[:, 2]) / per[:, None]
    k = 1 - d / np.maximum(r, 1e-12)
    ok = k > 0
    T = inc[:, None, :] + (T - inc[:, None, :]) * np.clip(k, 0, 1)[:, None, None]
    return (T - d * n[:, None, :])[ok]


class CollisionEngine:
    def __init__(self, geom: GeometryCache, shrink: float = 0.25):
        self.geom = geom
        self.shrink = shrink
        self._bvh: dict[str, object] = {}
        self._corners: dict[str, np.ndarray] = {}

    def _model(self, part: str):
        if part not in self._bvh:
            mesh = self.geom.mesh(part)
            S = shrink_tris(mesh.tris, self.shrink)
            if len(S) == 0:
                self._bvh[part] = None
            else:
                V = np.ascontiguousarray(S.reshape(-1, 3))
                F = np.arange(len(V), dtype=np.int32).reshape(-1, 3)
                m = fcl.BVHModel()
                m.beginModel(len(V), len(F))
                m.addSubModel(V, F)
                m.endModel()
                self._bvh[part] = m
            lo, hi = mesh.bbox
            self._corners[part] = np.array([[x, y, z] for x in (lo[0], hi[0])
                                            for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        return self._bvh[part]

    def world_aabb(self, part: str, M: np.ndarray) -> np.ndarray:
        self._model(part)
        pts = self._corners[part] @ M[:3, :3].T + M[:3, 3]
        return np.stack([pts.min(0), pts.max(0)])

    def aabbs(self, items) -> np.ndarray:
        if not items:
            return np.zeros((0, 2, 3))
        return np.stack([self.world_aabb(p, M) for p, M in items])

    def collide_pair(self, pa: str, Ma: np.ndarray, pb: str, Mb: np.ndarray) -> bool:
        a, b = self._model(pa), self._model(pb)
        if a is None or b is None:
            return False
        oa = fcl.CollisionObject(a, fcl.Transform(Ma[:3, :3], Ma[:3, 3]))
        ob = fcl.CollisionObject(b, fcl.Transform(Mb[:3, :3], Mb[:3, 3]))
        return fcl.collide(oa, ob, fcl.CollisionRequest(), fcl.CollisionResult()) > 0

    def _candidates(self, box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        m = 2 * self.shrink
        ok = np.all((boxes[:, 0] < box[1] - m) & (box[0] < boxes[:, 1] - m), axis=1)
        return np.nonzero(ok)[0]

    def pairs(self, items, only: set[int] | None = None) -> list[tuple[int, int]]:
        boxes = self.aabbs(items)
        out = []
        for i in range(len(items)):
            for j in self._candidates(boxes[i], boxes):
                j = int(j)
                if j <= i or (only is not None and i not in only and j not in only):
                    continue
                if self.collide_pair(items[i][0], items[i][1], items[j][0], items[j][1]):
                    out.append((i, j))
        return out

    def hits(self, part: str, M: np.ndarray, items, boxes: np.ndarray | None = None) -> bool:
        if not items:
            return False
        boxes = self.aabbs(items) if boxes is None else boxes
        for j in self._candidates(self.world_aabb(part, M), boxes):
            if self.collide_pair(part, M, items[j][0], items[j][1]):
                return True
        return False
```

**File:** `brickkit/geometry/mass.py`
```python
"""Estimated part mass from mesh volume. 1 LDU = 0.4 mm."""
from __future__ import annotations

import numpy as np

from ..ldraw.geometry import Mesh

LDU3_TO_CM3 = 0.04 ** 3
DENSITY_ABS = 1.05   # g/cm^3, opaque parts
DENSITY_PC = 1.20    # g/cm^3, transparent parts (polycarbonate)


def part_mass(mesh: Mesh, is_trans: bool, override_g: float | None = None
              ) -> tuple[float, np.ndarray, bool]:
    """(grams, local centroid, approximate?)"""
    V, cen = mesh.volume_centroid()
    approx = (not mesh.certified) or V <= 0
    if approx:
        lo, hi = mesh.bbox
        V, cen = float(np.prod(hi - lo)) * 0.35, (lo + hi) / 2
    grams = V * LDU3_TO_CM3 * (DENSITY_PC if is_trans else DENSITY_ABS)
    return (override_g if override_g is not None else grams), np.asarray(cen, float), approx
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_collide.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/geometry tests/test_collide.py
git commit -m "feat: FCL collision engine on shrunk meshes, part mass estimate"
```

---

### Task 8: Catalog — colours, Rebrickable index, real elements

**Files:**
- Create: `brickkit/catalog/__init__.py`, `brickkit/catalog/colors.py`, `brickkit/catalog/rebrickable.py`, `brickkit/catalog/catalog.py`, `brickkit/data/bricklink_colors.json`, `brickkit/data/color_aliases.json`, `brickkit/data/part_map.json`, `brickkit/data/masses.json`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_catalog.py`
```python
def test_palette_colours_map_across_systems(engine):
    cat = engine.catalog
    tlb = cat.color("Trans-Light Blue")
    assert tlb.ldraw == 43 and tlb.rb_id == 41 and tlb.bl_id == 15 and tlb.is_trans
    assert cat.color("Trans_Light_Blue") == tlb and cat.color(43) == tlb
    assert cat.color("Coral").bl_id == 220
    assert cat.color("Dark Bluish Gray").ldraw == 72
    for name in ["Trans-Red", "Dark Red", "White", "Light Nougat", "Trans-Clear", "Black",
                 "Light Bluish Gray", "Tan"]:
        c = cat.color(name)
        assert c.rb_id is not None and c.bl_id is not None, name


def test_real_element_lookup(engine):
    cat = engine.catalog
    e = cat.element("3001.dat", "White")
    assert e is not None and e.element_ids and e.set_count > 100 and not e.rare
    assert cat.element("1974.dat", "Trans-Light Blue") is not None
    assert "Brick 2 x 4" in cat.part_name("3001.dat")


def test_missing_element_offers_substitutes(engine):
    cat = engine.catalog
    col = next(c for c in cat.colors.by_code.values()
               if c.rb_id is not None and cat.element("3001.dat", c) is None)
    assert cat.substitutes("3001.dat", col)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.catalog'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/catalog/__init__.py`
```python
"""What LEGO actually made: colours and part/colour elements across LDraw, Rebrickable, BrickLink."""
```

**File:** `brickkit/catalog/colors.py`
```python
from __future__ import annotations

import re
from dataclasses import dataclass


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("grey", "gray"))


@dataclass(frozen=True)
class Color:
    name: str            # Rebrickable-style display name, e.g. "Trans-Light Blue"
    ldraw: int           # LDraw colour code
    rgb: str             # "#RRGGBB"
    alpha: int           # 255 = opaque
    rb_id: int | None    # Rebrickable colour id
    bl_id: int | None    # BrickLink colour id

    @property
    def is_trans(self) -> bool:
        return self.alpha < 255


class ColorTable:
    def __init__(self, ldraw_colors: dict, rb_colors: dict, bl_ids: dict, aliases: dict):
        rb_by_norm = {norm(r["name"]): r for r in rb_colors.values()}
        self.by_code: dict[int, Color] = {}
        self.by_norm: dict[str, Color] = {}
        for code, lc in ldraw_colors.items():
            n = aliases.get(norm(lc.name), norm(lc.name))
            rb = rb_by_norm.get(n)
            name = rb["name"] if rb else lc.name.replace("_", " ")
            col = Color(name, code, lc.rgb, lc.alpha, int(rb["id"]) if rb else None,
                        bl_ids.get(norm(name)))
            self.by_code[code] = col
            self.by_norm.setdefault(norm(name), col)
            self.by_norm.setdefault(norm(lc.name), col)

    def get(self, key) -> Color:
        if isinstance(key, Color):
            return key
        if isinstance(key, int) or (isinstance(key, str) and key.strip().isdigit()):
            return self.by_code[int(key)]
        c = self.by_norm.get(norm(key))
        if c is None:
            raise KeyError(f"unknown colour {key!r}")
        return c
```

**File:** `brickkit/catalog/rebrickable.py`
```python
"""Compact index over the Rebrickable CSV dumps (pickled next to the cache)."""
from __future__ import annotations

import csv
import gzip
import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

TABLES = ("parts", "colors", "elements", "inventory_parts", "inventories", "sets",
          "part_relationships", "part_categories")


@dataclass
class RBIndex:
    parts: dict          # part_num -> (name, category id)
    categories: dict     # id -> name
    colors: dict         # id -> row
    elements: dict       # (part_num, color_id) -> [element_id]
    last_year: dict      # (part_num, color_id) -> latest set year
    set_count: dict      # (part_num, color_id) -> number of set inventories
    related: dict        # part_num -> {alternate / mould variants}
    part_colors: dict    # part_num -> {color_id}


def _rows(d: Path, name: str):
    with gzip.open(d / f"{name}.csv.gz", "rt", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def build_index(d: Path) -> RBIndex:
    parts = {r["part_num"]: (r["name"], int(r["part_cat_id"])) for r in _rows(d, "parts")}
    cats = {int(r["id"]): r["name"] for r in _rows(d, "part_categories")}
    colors = {int(r["id"]): r for r in _rows(d, "colors")}
    elements: dict = defaultdict(list)
    for r in _rows(d, "elements"):
        elements[(r["part_num"], int(r["color_id"]))].append(r["element_id"])
    set_year = {r["set_num"]: int(r["year"]) for r in _rows(d, "sets")}
    inv_set = {r["id"]: r["set_num"] for r in _rows(d, "inventories")}
    last_year: dict = defaultdict(int)
    sets_with: dict = defaultdict(set)
    for r in _rows(d, "inventory_parts"):
        s = inv_set.get(r["inventory_id"])
        key = (r["part_num"], int(r["color_id"]))
        last_year[key] = max(last_year[key], set_year.get(s, 0))
        sets_with[key].add(s)
    related: dict = defaultdict(set)
    for r in _rows(d, "part_relationships"):
        if r["rel_type"] in ("A", "M"):
            related[r["child_part_num"]].add(r["parent_part_num"])
            related[r["parent_part_num"]].add(r["child_part_num"])
    part_colors: dict = defaultdict(set)
    for p, c in list(elements) + list(last_year):
        part_colors[p].add(c)
    return RBIndex(parts, cats, colors, dict(elements), dict(last_year),
                   {k: len(v) for k, v in sets_with.items()}, dict(related), dict(part_colors))


def load_index(d: Path, cache: Path) -> RBIndex:
    d, cache = Path(d), Path(cache)
    newest = max((d / f"{t}.csv.gz").stat().st_mtime for t in TABLES)
    if cache.exists() and cache.stat().st_mtime > newest:
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    idx = build_index(d)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "wb") as fh:
        pickle.dump(idx, fh)
    return idx
```

**File:** `brickkit/catalog/catalog.py`
```python
from __future__ import annotations

import json
from dataclasses import dataclass

from .. import paths
from ..ldraw.library import LDrawLibrary, part_id
from .colors import Color, ColorTable
from .rebrickable import RBIndex, load_index


def _data(name: str) -> dict:
    return json.loads((paths.DATA_DIR / name).read_text())


@dataclass
class ElementInfo:
    part: str
    color: Color
    element_ids: list[str]
    last_year: int
    set_count: int

    @property
    def rare(self) -> bool:
        return self.set_count < 3 or self.last_year < 2016


class Catalog:
    def __init__(self, ldraw: LDrawLibrary, rb: RBIndex, part_map: dict, bl_colors: dict,
                 aliases: dict, masses: dict):
        self.ldraw = ldraw
        self.rb = rb
        self.part_map = part_map
        self.masses = masses
        self.colors = ColorTable(ldraw.colors, rb.colors, bl_colors, aliases)

    @classmethod
    def load(cls, ldraw: LDrawLibrary, rb_dir, cache_path) -> "Catalog":
        return cls(ldraw, load_index(rb_dir, cache_path), _data("part_map.json"),
                   _data("bricklink_colors.json"), _data("color_aliases.json"),
                   _data("masses.json"))

    def color(self, key) -> Color:
        return self.colors.get(key)

    def _pm(self, part: str) -> dict:
        return self.part_map.get(part_id(part), {})

    def rb_part(self, part: str) -> str:
        return self._pm(part).get("rebrickable", part_id(part))

    def bl_part(self, part: str) -> str:
        return self._pm(part).get("bricklink", self.rb_part(part))

    def in_bom(self, part: str) -> bool:
        return self._pm(part).get("bom", True)

    def mass_override(self, part: str) -> float | None:
        return self.masses.get(part_id(part))

    def part_name(self, part: str) -> str:
        row = self.rb.parts.get(self.rb_part(part))
        return row[0] if row else self.ldraw.description(part)

    def element(self, part: str, color) -> ElementInfo | None:
        c = self.color(color)
        if c.rb_id is None:
            return None
        key = (self.rb_part(part), c.rb_id)
        ids = self.rb.elements.get(key, [])
        sets = self.rb.set_count.get(key, 0)
        if not ids and not sets:
            return None
        ids = sorted(ids, key=lambda e: int(e) if e.isdigit() else 0)
        return ElementInfo(part_id(part), c, ids, self.rb.last_year.get(key, 0), sets)

    def substitutes(self, part: str, color, limit: int = 6) -> list[str]:
        c = self.color(color)
        rbp = self.rb_part(part)
        out = []
        others = sorted(self.rb.part_colors.get(rbp, ()),
                        key=lambda cid: -self.rb.set_count.get((rbp, cid), 0))
        for cid in others:
            if cid != c.rb_id and len(out) < limit // 2 + 1:
                out.append(f"{rbp} in {self.rb.colors[cid]['name']} "
                           f"({self.rb.set_count.get((rbp, cid), 0)} sets)")
        for alt in sorted(self.rb.related.get(rbp, ())):
            if (alt, c.rb_id) in self.rb.elements or self.rb.set_count.get((alt, c.rb_id)):
                out.append(f"{alt} in {c.name}")
        return out[:limit]
```

**File:** `brickkit/data/bricklink_colors.json`
```json
{
  "white": 1, "tan": 2, "yellow": 3, "orange": 4, "red": 5, "green": 6, "blue": 7,
  "black": 11, "transclear": 12, "transblack": 13, "transdarkblue": 14,
  "translightblue": 15, "transneongreen": 16, "transred": 17, "transneonorange": 18,
  "transyellow": 19, "transgreen": 20, "chromegold": 21, "chromesilver": 22, "pink": 23,
  "purple": 24, "nougat": 28, "mediumorange": 31, "lime": 34, "brightgreen": 36,
  "darkturquoise": 39, "mediumblue": 42, "darkpink": 47, "sandgreen": 48,
  "transdarkpink": 50, "transpurple": 51, "sandblue": 55, "darkred": 59, "darkblue": 63,
  "darkorange": 68, "darktan": 69, "magenta": 71, "pearldarkgray": 77, "darkgreen": 80,
  "darkbluishgray": 85, "lightbluishgray": 86, "reddishbrown": 88, "darkpurple": 89,
  "lightnougat": 90, "flatsilver": 95, "transorange": 98, "brightlightyellow": 103,
  "brightpink": 104, "brightlightblue": 105, "transbrightgreen": 108,
  "brightlightorange": 110, "pearlgold": 115, "darkbrown": 120, "mediumnougat": 150,
  "lightaqua": 152, "darkazure": 153, "lavender": 154, "olivegreen": 155,
  "mediumazure": 156, "mediumlavender": 157, "yellowishgreen": 158, "coral": 220
}
```

**File:** `brickkit/data/color_aliases.json`
```json
{}
```

**File:** `brickkit/data/part_map.json`
```json
{}
```

**File:** `brickkit/data/masses.json`
```json
{}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_catalog.py -v`
Expected: PASS (3 passed). First run builds `.cache/rb_index.pkl` (~10–30 s).

- [ ] **Step 5: Commit**

```bash
git add brickkit/catalog brickkit/data tests/test_catalog.py
git commit -m "feat: catalog of real LEGO colours and elements"
```

---

### Task 9: Model builder

**Files:**
- Create: `brickkit/model/__init__.py`, `brickkit/model/builder.py`
- Test: `tests/test_builder.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_builder.py`
```python
import numpy as np

from brickkit.ldraw.matrix import translate
from brickkit.model.builder import Model


def make(engine):
    m = Model("T", "t", {"body": "White"}, engine.catalog)
    pillar = m.submodel("pillar")
    pillar.place("3003", "body")
    pillar.step()
    pillar.place("3003", "body", (0, -24, 0))
    m.main.place("3001", "Red")
    m.main.step("pillars")
    m.main.use(pillar, (-20, -24, 0), tag="left")
    m.main.use(pillar, (20, -24, 0), tag="right")
    return m


def test_flatten_world_positions(engine):
    placed = make(engine).flatten()
    assert [p.part for p in placed] == ["3001.dat"] + ["3003.dat"] * 4
    assert np.allclose(placed[2].M[:3, 3], [-20, -48, 0])
    assert placed[1].tags == ("left",)
    assert placed[0].color.name == "Red" and placed[1].color.name == "White"


def test_instruction_order_builds_subassembly_first(engine):
    assert make(engine).instruction_order() == [("t", 0), ("pillar", 0), ("pillar", 1), ("t", 1)]


def test_pose_moves_group(engine):
    m = make(engine)
    m.moving_group("lift", "left")
    placed = m.flatten(pose={"lift": translate(0, -100, 0)})
    assert np.allclose(placed[1].M[:3, 3], [-20, -124, 0])
    assert np.allclose(placed[3].M[:3, 3], [20, -24, 0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.model'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/model/__init__.py`
```python
"""Describe a model in code: submodels, steps, placements, mechanisms, electrics."""
from .builder import Model, PlacedPart, Placement, Submodel, Use

__all__ = ["Model", "PlacedPart", "Placement", "Submodel", "Use"]
```

**File:** `brickkit/model/builder.py`
```python
"""Builder API. Positions in LDU, -Y up. Colours are palette roles or real colour names."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..catalog.colors import Color
from ..ldraw.library import normalize
from ..ldraw.matrix import transform


@dataclass
class Placement:
    part: str
    color: Color
    M: np.ndarray
    step: int
    tag: str = ""
    note: str = ""
    insert: tuple | None = None   # optional insertion direction hint (submodel frame)


@dataclass
class Use:
    sub: "Submodel"
    M: np.ndarray
    step: int
    tag: str = ""
    note: str = ""
    insert: tuple | None = None


@dataclass
class PlacedPart:
    index: int
    part: str
    color: Color
    M: np.ndarray
    path: tuple        # submodel names from the root to the owner
    tags: tuple        # tags of every Use on the path, then the placement's own tag
    owner: str
    local_step: int
    build_order: int   # index into Model.instruction_order() when the part joins the model

    @property
    def tag_path(self) -> str:
        return "/".join(self.tags)


class Submodel:
    def __init__(self, model: "Model", name: str, title: str = ""):
        self.model = model
        self.name = name
        self.title = title or name.replace("_", " ").capitalize()
        self.items: list[Placement | Use] = []
        self.captions: list[str] = [""]

    @property
    def current_step(self) -> int:
        return len(self.captions) - 1

    @property
    def n_steps(self) -> int:
        return len(self.captions)

    def step(self, caption: str = "") -> int:
        """Start a new step (reuses the current one if it is still empty)."""
        if any(it.step == self.current_step for it in self.items):
            self.captions.append(caption)
        elif caption:
            self.captions[-1] = caption
        return self.current_step

    def place(self, part: str, color, pos=(0, 0, 0), rot=None, *, tag: str = "",
              note: str = "", insert=None) -> Placement:
        p = Placement(normalize(part), self.model.resolve_color(color), transform(pos, rot),
                      self.current_step, tag, note, insert)
        self.items.append(p)
        return p

    def use(self, sub: "Submodel", pos=(0, 0, 0), rot=None, *, tag: str = "", note: str = "",
            insert=None) -> Use:
        u = Use(sub, transform(pos, rot), self.current_step, tag, note, insert)
        self.items.append(u)
        return u

    def flatten_local(self) -> list[tuple[str, Color, np.ndarray]]:
        out = []
        for it in self.items:
            if isinstance(it, Placement):
                out.append((it.part, it.color, it.M))
            else:
                out += [(p, c, it.M @ M) for p, c, M in it.sub.flatten_local()]
        return out


class Model:
    def __init__(self, name: str, slug: str, palette: dict, catalog):
        self.name = name
        self.slug = slug
        self.palette = dict(palette)
        self.catalog = catalog
        self.submodels: dict[str, Submodel] = {}
        self.main = self.submodel(slug, name)
        self.groups: dict[str, str] = {}                 # group name -> tag
        self.pose: Callable[[float], dict] | None = None  # t in [0,1] -> {group: 4x4 world}
        self.gear_pairs: list[tuple[str, str, str]] = []  # (tag path a, tag path b, kind)
        self.lights: list[dict] = []
        self.cables: list[dict] = []
        self.extra_checks: list[Callable] = []           # fn(ctx) -> list of issue dicts
        self.meta: dict = {}

    def submodel(self, name: str, title: str = "") -> Submodel:
        if name in self.submodels:
            raise ValueError(f"submodel {name!r} already exists")
        s = Submodel(self, name, title)
        self.submodels[name] = s
        return s

    def resolve_color(self, key) -> Color:
        if isinstance(key, Color):
            return key
        return self.catalog.color(self.palette.get(key, key))

    # mechanisms and electrics -------------------------------------------------
    def moving_group(self, name: str, tag: str) -> None:
        self.groups[name] = tag

    def group_of(self, p: PlacedPart) -> str | None:
        for t in reversed(p.tags):
            for g, tag in self.groups.items():
                if t == tag:
                    return g
        return None

    def gear_pair(self, a: str, b: str, kind: str = "spur") -> None:
        self.gear_pairs.append((a, b, kind))

    def light(self, name: str, tag_path: str) -> None:
        self.lights.append({"name": name, "part": tag_path})

    def cable(self, name: str, start: str, end: str, length: float, route=()) -> None:
        self.cables.append({"name": name, "from": start, "to": end, "length": float(length),
                            "route": [tuple(map(float, p)) for p in route]})

    # flattening ---------------------------------------------------------------
    def instruction_order(self) -> list[tuple[str, int]]:
        order, built = [], set()

        def build(sub: Submodel):
            for s in range(sub.n_steps):
                for it in sub.items:
                    if it.step == s and isinstance(it, Use) and it.sub.name not in built:
                        build(it.sub)
                order.append((sub.name, s))
            built.add(sub.name)

        build(self.main)
        return order

    def flatten(self, pose: dict | None = None) -> list[PlacedPart]:
        order = {k: i for i, k in enumerate(self.instruction_order())}
        out: list[PlacedPart] = []

        def walk(sub: Submodel, W, path, tags, top):
            for it in sub.items:
                t = tags + ((it.tag,) if it.tag else ())
                bo = top if top is not None else order[(sub.name, it.step)]
                if isinstance(it, Placement):
                    out.append(PlacedPart(len(out), it.part, it.color, W @ it.M,
                                          path + (sub.name,), t, sub.name, it.step, bo))
                else:
                    walk(it.sub, W @ it.M, path + (sub.name,), t, bo)

        walk(self.main, np.eye(4), (), (), None)
        if pose:
            for p in out:
                g = self.group_of(p)
                if g in pose:
                    p.M = pose[g] @ p.M
        return out

    def find(self, tag_path: str, placed: list[PlacedPart]) -> list[PlacedPart]:
        return [p for p in placed if p.tag_path == tag_path or p.tag_path.endswith("/" + tag_path)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_builder.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/model tests/test_builder.py
git commit -m "feat: model builder with submodels, steps, tags and poses"
```

---

### Task 10: MPD writer and reader

**Files:**
- Create: `brickkit/io/__init__.py`, `brickkit/io/mpd.py`
- Test: `tests/test_mpd.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_mpd.py`
```python
import numpy as np

from brickkit.io.mpd import read_mpd, write_mpd
from tests.test_builder import make


def test_mpd_roundtrip(engine, tmp_path):
    m = make(engine)
    path = tmp_path / "t.mpd"
    write_mpd(m, path)
    parts = read_mpd(path)
    flat = m.flatten()
    assert len(parts) == len(flat)
    for (part, code, M), p in zip(parts, flat):
        assert part == p.part and code == p.color.ldraw and np.allclose(M, p.M)
    text = path.read_text()
    assert text.startswith("0 FILE t.ldr") and "0 FILE pillar.ldr" in text
    assert text.count("0 STEP") == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_mpd.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.io'`

- [ ] **Step 3: Write minimal implementation**

**File:** `tests/__init__.py`
```python
```

**File:** `brickkit/io/__init__.py`
```python
"""Model file formats."""
```

**File:** `brickkit/io/mpd.py`
```python
"""LDraw MPD (multi-part) files with STEP metas; opens in BrickLink Studio, LeoCAD, LDCad."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..ldraw.library import normalize
from ..ldraw.matrix import format_type1, parse_type1
from ..model.builder import Model, Placement


def write_mpd(model: Model, path) -> Path:
    path = Path(path)
    lines: list[str] = []
    subs = [model.main] + [s for s in model.submodels.values() if s is not model.main]
    for sub in subs:
        fname = f"{sub.name}.ldr"
        lines += [f"0 FILE {fname}", f"0 {sub.title}", f"0 Name: {fname}",
                  "0 Author: brickkit", ""]
        for s in range(sub.n_steps):
            if sub.captions[s]:
                lines.append(f"0 // {sub.captions[s]}")
            for it in sub.items:
                if it.step != s:
                    continue
                if isinstance(it, Placement):
                    lines.append(format_type1(it.color.ldraw, it.M, it.part))
                else:
                    lines.append(format_type1(16, it.M, f"{it.sub.name}.ldr"))
            lines.append("0 STEP")
        lines += ["0 NOFILE", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def read_mpd(path) -> list[tuple[str, int, np.ndarray]]:
    """Flatten an MPD into (part, colour, world matrix), expanding internal files."""
    files: dict[str, list[str]] = {}
    order: list[str] = []
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        t = raw.split()
        if len(t) >= 3 and t[0] == "0" and t[1] == "FILE":
            current = normalize(" ".join(t[2:]))
            files[current] = []
            order.append(current)
        elif len(t) >= 2 and t[0] == "0" and t[1] == "NOFILE":
            current = None
        elif current is not None:
            files[current].append(raw)
    out: list[tuple[str, int, np.ndarray]] = []

    def walk(name: str, W: np.ndarray, color: int):
        for raw in files[name]:
            t = raw.split()
            if len(t) >= 15 and t[0] == "1":
                c, M, sub = parse_type1(t)
                c = color if c == 16 else c
                key = normalize(sub)
                if key in files:
                    walk(key, W @ M, c)
                else:
                    out.append((key, c, W @ M))

    walk(order[0], np.eye(4), 16)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_mpd.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/io tests/__init__.py tests/test_mpd.py
git commit -m "feat: write and read LDraw MPD files"
```

---

### Task 11: Check framework + connections, collisions, real_elements, report

**Files:**
- Create: `brickkit/checks/__init__.py`, `brickkit/checks/base.py`, `brickkit/checks/connections.py`, `brickkit/checks/collisions.py`, `brickkit/checks/real_elements.py`, `brickkit/checks/report.py`
- Test: `tests/test_checks_basic.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_checks_basic.py`
```python
from brickkit.checks import run_checks
from brickkit.checks.report import write_report
from brickkit.model.builder import Model
from tests.test_builder import make


def run(engine, model, names):
    return {r.name: r for r in run_checks(engine.context(model), names)}


def test_good_model_passes(engine):
    res = run(engine, make(engine), ["connections", "collisions", "real_elements"])
    assert all(r.status == "pass" for r in res.values()), res


def test_floating_part_fails_connections(engine):
    m = Model("F", "f", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.place("3001", "White", (0, -100, 0))
    assert run(engine, m, ["connections"])["connections"].status == "fail"


def test_overlap_fails_collisions(engine):
    m = Model("C", "c", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.place("3001", "White", (0, -16, 0))
    r = run(engine, m, ["collisions"])["collisions"]
    assert r.status == "fail" and len(r.items) == 1


def test_unreal_colour_fails_real_elements(engine):
    cat = engine.catalog
    col = next(c for c in cat.colors.by_code.values()
               if c.rb_id is not None and cat.element("3001.dat", c) is None)
    m = Model("R", "r", {}, cat)
    m.main.place("3001", col)
    r = run(engine, m, ["real_elements"])["real_elements"]
    assert r.status == "fail" and r.items[0]["substitutes"]


def test_report_files(engine, tmp_path):
    results = run_checks(engine.context(make(engine)), ["connections"])
    write_report(results, tmp_path, "T")
    assert (tmp_path / "report.json").exists() and "connections" in (tmp_path / "report.html").read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_checks_basic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.checks'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/checks/__init__.py`
```python
"""Verification checks. Importing this package registers every built-in check."""
from . import buildability, collisions, connections, electrics, mechanism, real_elements  # noqa: F401
from . import stability, technique  # noqa: F401
from .base import REGISTRY, CheckContext, CheckResult, register, run_checks

__all__ = ["REGISTRY", "CheckContext", "CheckResult", "register", "run_checks"]
```

**File:** `brickkit/checks/base.py`
```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

from ..model.builder import Model, PlacedPart
from ..snaps.match import Connection, find_connections

ORDER = ["real_elements", "connections", "collisions", "buildability", "stability",
         "mechanism", "electrics", "technique"]


@dataclass
class CheckResult:
    name: str
    status: str                 # pass | warn | fail
    summary: str
    items: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


REGISTRY: dict[str, Callable] = {}


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


class CheckContext:
    def __init__(self, model: Model, engine, config: dict):
        self.model = model
        self.engine = engine
        self.config = config
        self.catalog = engine.catalog
        self.geom = engine.geom
        self.shadow = engine.shadow
        self.collide = engine.collide
        self.placed = model.flatten()

    def world_connectors(self, placed: list[PlacedPart] | None = None):
        placed = self.placed if placed is None else placed
        return [[c.transformed(p.M) for c in self.shadow.connectors(p.part)] for p in placed]

    @cached_property
    def connections(self) -> list[Connection]:
        return find_connections(self.world_connectors())


def components(n: int, edges) -> list[list[int]]:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=len, reverse=True)


def describe(p: PlacedPart) -> str:
    return f"{p.part[:-4]} {p.color.name} (#{p.index}, {p.owner} step {p.local_step + 1})"


def status_of(items: list, default_fail: bool = True) -> str:
    if not items:
        return "pass"
    if any(i.get("severity", "fail" if default_fail else "warn") == "fail" for i in items):
        return "fail"
    return "warn"


def run_checks(ctx: CheckContext, names: list[str] | None = None) -> list[CheckResult]:
    names = names or ctx.config.get("enabled") or [n for n in ORDER if n in REGISTRY]
    return [REGISTRY[n](ctx, ctx.config.get(n, {})) for n in names]
```

**File:** `brickkit/checks/connections.py`
```python
from collections import Counter

from .base import CheckResult, components, describe, register


@register("connections")
def check_connections(ctx, cfg) -> CheckResult:
    n = len(ctx.placed)
    comps = components(n, [(c.a, c.b) for c in ctx.connections])
    kinds = Counter(c.kind for c in ctx.connections)
    allowed = cfg.get("allow_separate_tags", [])
    items = []
    for comp in comps[1:]:
        tags = {t for i in comp for t in ctx.placed[i].tags}
        if any(t == a for t in tags for a in allowed):
            continue
        items.append({"count": len(comp),
                      "parts": [describe(ctx.placed[i]) for i in comp[:12]],
                      "problem": "not attached to the rest of the model"})
    kind_txt = ", ".join(f"{v} {k}" for k, v in kinds.most_common()) or "none"
    return CheckResult("connections", "fail" if items else "pass",
                       f"{len(ctx.connections)} connections ({kind_txt}); "
                       f"{len(comps)} separate piece(s)", items,
                       {"connections": len(ctx.connections), "by_kind": dict(kinds),
                        "pieces": len(comps)})
```

**File:** `brickkit/checks/collisions.py`
```python
from .base import CheckResult, describe, register


@register("collisions")
def check_collisions(ctx, cfg) -> CheckResult:
    pairs = ctx.collide.pairs([(p.part, p.M) for p in ctx.placed])
    items = [{"a": describe(ctx.placed[i]), "b": describe(ctx.placed[j]),
              "problem": "parts overlap"} for i, j in pairs]
    return CheckResult("collisions", "fail" if items else "pass",
                       f"{len(items)} overlapping pair(s) among {len(ctx.placed)} parts", items,
                       {"pairs": len(items)})
```

**File:** `brickkit/checks/real_elements.py`
```python
from ..ldraw.library import part_id
from .base import CheckResult, register


@register("real_elements")
def check_real_elements(ctx, cfg) -> CheckResult:
    min_year = cfg.get("min_year", 2016)
    min_sets = cfg.get("min_sets", 3)
    seen = {}
    for p in ctx.placed:
        seen.setdefault((p.part, p.color.ldraw), p)
    items = []
    n_warn = 0
    for (part, _), p in sorted(seen.items()):
        base = {"part": part_id(part), "name": ctx.catalog.part_name(part), "colour": p.color.name}
        if ctx.engine.lib.resolve(part) is None:
            items.append({**base, "severity": "fail", "problem": "not in the LDraw part library"})
            continue
        if not ctx.catalog.in_bom(part):
            continue
        e = ctx.catalog.element(part, p.color)
        if e is None:
            items.append({**base, "severity": "fail",
                          "problem": "LEGO never made this part in this colour",
                          "substitutes": ctx.catalog.substitutes(part, p.color)})
        elif e.last_year < min_year or e.set_count < min_sets:
            n_warn += 1
            items.append({**base, "severity": "warn",
                          "problem": f"rare: in {e.set_count} set(s), last seen "
                                     f"{e.last_year or 'never in a set'}",
                          "element_ids": e.element_ids})
    n_fail = sum(1 for i in items if i["severity"] == "fail")
    status = "fail" if n_fail else ("warn" if n_warn else "pass")
    return CheckResult("real_elements", status,
                       f"{len(seen)} part/colour combinations: {n_fail} not real, {n_warn} rare",
                       items, {"combinations": len(seen), "not_real": n_fail, "rare": n_warn})
```

**File:** `brickkit/checks/report.py`
```python
from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def overall(results) -> str:
    if any(r.status == "fail" for r in results):
        return "fail"
    return "warn" if any(r.status == "warn" for r in results) else "pass"


def write_report(results, out_dir, title: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = {"title": title, "status": overall(results), "checks": [asdict(r) for r in results]}
    (out / "report.json").write_text(json.dumps(data, indent=2, default=_jsonable))
    colours = {"pass": "#1d7a46", "warn": "#9a6700", "fail": "#b42318"}
    rows = []
    for r in results:
        issues = "".join(f"<li><code>{html.escape(json.dumps(i, default=_jsonable))}</code></li>"
                         for i in r.items[:50])
        more = f"<p>... and {len(r.items) - 50} more</p>" if len(r.items) > 50 else ""
        rows.append(f"<section><h2><span style='color:{colours[r.status]}'>{r.status.upper()}"
                    f"</span> {html.escape(r.name)}</h2><p>{html.escape(r.summary)}</p>"
                    f"<ul>{issues}</ul>{more}</section>")
    (out / "report.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>{html.escape(title)} checks</title>"
        f"<body style='font-family:system-ui;max-width:900px;margin:2rem auto'>"
        f"<h1>{html.escape(title)}: {data['status'].upper()}</h1>{''.join(rows)}</body>")
    return data
```

Create empty placeholder modules so the package import in `checks/__init__.py` succeeds until Tasks 12–13 fill them:

**File:** `brickkit/checks/buildability.py`
```python
"""Filled in by Task 12."""
```

**File:** `brickkit/checks/stability.py`
```python
"""Filled in by Task 13."""
```

**File:** `brickkit/checks/mechanism.py`
```python
"""Filled in by Task 13."""
```

**File:** `brickkit/checks/electrics.py`
```python
"""Filled in by Task 13."""
```

**File:** `brickkit/checks/technique.py`
```python
"""Filled in by Task 13."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_checks_basic.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/checks tests/test_checks_basic.py
git commit -m "feat: check framework with connections, collisions, real-element checks and report"
```

---

### Task 12: Buildability check

**Files:**
- Modify: `brickkit/checks/buildability.py` (replace placeholder)
- Test: `tests/test_buildability.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_buildability.py`
```python
from brickkit.checks import run_checks
from brickkit.model.builder import Model
from tests.test_builder import make


def check(engine, model):
    return run_checks(engine.context(model), ["buildability"])[0]


def test_simple_model_is_buildable(engine):
    assert check(engine, make(engine)).status == "pass"


def test_part_trapped_under_roof_fails(engine):
    m = Model("B", "b", {}, engine.catalog)
    s = m.main
    s.place("3001", "White")
    s.step()
    s.place("3005", "White", (-30, -24, -10))
    s.place("3005", "White", (30, -24, -10))
    s.step()
    s.place("3001", "White", (0, -48, 0))
    s.step()
    s.place("3004", "White", (0, -24, -10))
    r = check(engine, m)
    assert r.status == "fail"
    assert any(i["part"].startswith("3004") for i in r.items)


def test_same_step_order_is_free(engine):
    m = Model("B", "b", {}, engine.catalog)
    s = m.main
    s.place("3001", "White")
    s.step()
    s.place("3001", "White", (0, -48, 0))   # roof listed first, rests on the 1x1s
    s.place("3005", "White", (-30, -24, -10))
    s.place("3005", "White", (30, -24, -10))
    s.place("3004", "White", (0, -24, -10))
    assert check(engine, m).status == "pass"


def test_loose_piece_after_step_fails(engine):
    m = Model("L", "l", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.step()
    m.main.place("3001", "White", (0, -200, 0))
    r = check(engine, m)
    assert r.status == "fail" and any("loose" in i["problem"] for i in r.items)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_buildability.py -v`
Expected: FAIL with `KeyError: 'buildability'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/checks/buildability.py`
```python
"""Can every step be built? Each new part (or sub-assembly) must slide into place along one
of its connection axes (or its insertion hint) without hitting what is already built, and
each submodel must be one piece at the end of every step."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..ldraw.matrix import translate
from ..model.builder import Placement
from ..snaps.match import find_connections
from .base import CheckResult, components, register


@dataclass
class Unit:
    step: int
    label: str
    parts: list          # [(part, M in submodel frame)]
    insert: tuple | None


def _units(sub) -> list[Unit]:
    units = []
    for it in sub.items:
        if isinstance(it, Placement):
            units.append(Unit(it.step, f"{it.part[:-4]} {it.color.name}", [(it.part, it.M)],
                              it.insert))
        else:
            parts = [(p, it.M @ M) for p, _, M in it.sub.flatten_local()]
            units.append(Unit(it.step, f"sub-assembly {it.sub.name}", parts, it.insert))
    return units


def _unique(dirs):
    out, seen = [], set()
    for d in dirs:
        d = np.asarray(d, float)
        d = d / np.linalg.norm(d)
        k = tuple(np.round(d, 3))
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


def _clear(ctx, unit: Unit, d, items, boxes, stride: float, travel: float) -> bool:
    for k in np.arange(stride, travel + 1e-6, stride):
        T = translate(*(d * k))
        for part, M in unit.parts:
            if ctx.collide.hits(part, T @ M, items, boxes):
                return False
    return True


@register("buildability")
def check_buildability(ctx, cfg) -> CheckResult:
    stride = float(cfg.get("stride", 2.0))
    min_travel = float(cfg.get("travel", 24.0))
    items: list[dict] = []
    tried = 0
    for sub in ctx.model.submodels.values():
        if not sub.items:
            continue
        units = _units(sub)
        flat, owner = [], []
        for ui, u in enumerate(units):
            for part, M in u.parts:
                flat.append((part, M))
                owner.append(ui)
        boxes_all = ctx.collide.aabbs(flat)
        wc = [[c.transformed(M) for c in ctx.shadow.connectors(part)] for part, M in flat]
        links: dict[int, list] = defaultdict(list)
        for c in find_connections(wc):
            ua, ub = owner[c.a], owner[c.b]
            if ua != ub:
                links[ua].append((ub, c.ca.axis, c.overlap))
                links[ub].append((ua, c.ca.axis, c.overlap))
        parts_of = defaultdict(list)
        for i, ui in enumerate(owner):
            parts_of[ui].append(i)
        built: list[int] = []
        built_parts: list[int] = []

        def add(ui: int):
            built.append(ui)
            built_parts.extend(parts_of[ui])

        for s in range(sub.n_steps):
            pending = [ui for ui, u in enumerate(units) if u.step == s]
            while pending:
                bset = set(built)
                attached = [ui for ui in pending if any(o in bset for o, _, _ in links[ui])]
                progress = False
                for ui in attached:
                    tried += 1
                    if _insertable(ctx, units[ui], ui, links, set(built), flat, built_parts,
                                   boxes_all, stride, min_travel):
                        pending.remove(ui)
                        add(ui)
                        progress = True
                if progress:
                    continue
                free = [ui for ui in pending if ui not in attached]
                if not free:
                    break
                # nothing attached can go in yet: set down one unattached unit and retry
                pending.remove(free[0])
                add(free[0])
            for ui in pending:
                items.append({"submodel": sub.name, "step": s + 1, "part": units[ui].label,
                              "problem": "no clear path to push it into place"})
                add(ui)
            bset = set(built)
            index = {u: k for k, u in enumerate(built)}
            edges = [(index[a], index[b]) for a in built for b, _, _ in links[a] if b in bset]
            comps = components(len(built), edges)
            if len(comps) > 1:
                items.append({"submodel": sub.name, "step": s + 1,
                              "part": ", ".join(units[built[i]].label for i in comps[1][:5]),
                              "problem": f"step leaves {len(comps)} loose pieces"})
    return CheckResult("buildability", "fail" if items else "pass",
                       f"{tried} insertions tried across {len(ctx.model.submodels)} submodel(s); "
                       f"{len(items)} problem(s)", items, {"insertions": tried})


def _insertable(ctx, unit, ui, links, built, flat, built_parts, boxes_all, stride, min_travel):
    if not built_parts:
        return True
    dirs, depth = [], 0.0
    for other, axis, ov in links[ui]:
        if other in built:
            dirs += [axis, -axis]
            depth = max(depth, ov)
    if unit.insert is not None:
        dirs.insert(0, np.asarray(unit.insert, float))
    if not dirs:
        return True   # not attached yet; the loose-piece check decides
    items = [flat[i] for i in built_parts]
    boxes = boxes_all[built_parts]
    travel = max(min_travel, depth + 8.0)
    return any(_clear(ctx, unit, d, items, boxes, stride, travel) for d in _unique(dirs))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_buildability.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/checks/buildability.py tests/test_buildability.py
git commit -m "feat: buildability check (insertion paths, loose pieces per step)"
```

---

### Task 13: Stability, mechanism, electrics and technique checks

**Files:**
- Modify: `brickkit/checks/stability.py`, `brickkit/checks/mechanism.py`, `brickkit/checks/electrics.py`, `brickkit/checks/technique.py` (replace placeholders)
- Test: `tests/test_checks_physical.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_checks_physical.py`
```python
import numpy as np

from brickkit.checks import run_checks
from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.model.builder import Model
from tests.test_builder import make


def run(engine, model, name):
    return run_checks(engine.context(model), [name])[0]


def test_stable_tower(engine):
    r = run(engine, make(engine), "stability")
    assert r.status == "pass" and r.stats["mass_g"] > 5


def test_overhang_tips_over(engine):
    m = Model("O", "o", {}, engine.catalog)
    m.main.place("3024", "White")                      # 1x1 plate footprint
    for k in range(6):
        m.main.place("3008", "White", (70, -24 - 24 * k, 0))  # 1x8 bricks hanging off one side
    assert run(engine, m, "stability").status == "fail"


def test_mechanism_sweep(engine):
    m = make(engine)
    m.moving_group("left", "left")
    m.pose = lambda t: {"left": translate(40 * t, 0, 0)}   # slides into the right pillar
    r = run(engine, m, "mechanism")
    assert r.status == "fail" and any("collide" in i["problem"] for i in r.items)
    m.pose = lambda t: {"left": translate(0, -60 * t, 0)}  # lifts off the base
    assert any("falls apart" in i["problem"] for i in run(engine, m, "mechanism").items)
    m.pose = lambda t: {"left": np.eye(4)}
    assert run(engine, m, "mechanism").status == "pass"


def test_gear_spacing(engine):
    m = Model("G", "g", {}, engine.catalog)
    m.main.place("3648b", "Light Bluish Gray", (0, 0, 0), rot(x=90), tag="g24")
    m.main.place("3647", "Light Bluish Gray", (40, 0, 0), rot(x=90), tag="g8")
    m.gear_pair("g24", "g8")
    r = run(engine, m, "mechanism")
    assert not [i for i in r.items if "gear" in i["problem"]]
    m2 = Model("G", "g", {}, engine.catalog)
    m2.main.place("3648b", "Light Bluish Gray", (0, 0, 0), rot(x=90), tag="g24")
    m2.main.place("3647", "Light Bluish Gray", (50, 0, 0), rot(x=90), tag="g8")
    m2.gear_pair("g24", "g8")
    assert any("gear" in i["problem"] for i in run(engine, m2, "mechanism").items)


def test_electrics_cable_length(engine):
    m = Model("E", "e", {}, engine.catalog)
    m.main.place("3001", "White", tag="box")
    m.main.place("3001", "White", (0, -24, 0), tag="lamp")
    m.cable("led", "box", "lamp", length=30)
    assert run(engine, m, "electrics").status == "pass"
    m.cables.clear()
    m.cable("led", "box", "lamp", length=20)
    assert run(engine, m, "electrics").status == "fail"


def test_technique_passes_simple_model(engine):
    assert run(engine, make(engine), "technique").status in ("pass", "warn")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_checks_physical.py -v`
Expected: FAIL with `KeyError: 'stability'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/checks/stability.py`
```python
"""Centre of mass over the footprint of the lowest parts, and tipping angle."""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import ConvexHull, QhullError

from ..geometry.mass import part_mass
from ..ldraw.matrix import apply
from .base import CheckResult, register


@register("stability")
def check_stability(ctx, cfg) -> CheckResult:
    if not ctx.placed:
        return CheckResult("stability", "pass", "empty model")
    masses, cents, pts = [], [], []
    approx = 0
    for p in ctx.placed:
        mesh = ctx.geom.mesh(p.part)
        g, c, a = part_mass(mesh, p.color.is_trans, ctx.catalog.mass_override(p.part))
        approx += a
        masses.append(g)
        cents.append(apply(p.M, [c])[0])
        if len(mesh.tris):
            pts.append(apply(p.M, mesh.tris.reshape(-1, 3)))
    masses, cents = np.array(masses), np.array(cents)
    total = float(masses.sum())
    com = (masses[:, None] * cents).sum(0) / total
    allp = np.concatenate(pts)
    ymax = allp[:, 1].max()                       # +Y is down: the lowest point
    base = allp[allp[:, 1] > ymax - 0.5][:, [0, 2]]
    stats = {"mass_g": total, "com": com.tolist(), "approx_parts": int(approx)}
    try:
        hull = ConvexHull(base)
    except (QhullError, ValueError):
        return CheckResult("stability", "fail", "footprint is a point or a line", [
            {"problem": "the model stands on a point or a line"}], stats)
    eq = hull.equations                            # outward normals: n.x + c <= 0 inside
    d_com = float((-(eq[:, :2] @ com[[0, 2]] + eq[:, 2])).min())
    cen = base[hull.vertices].mean(0)
    d_cen = float((-(eq[:, :2] @ cen + eq[:, 2])).min())
    inside = d_com > 0
    margin = d_com / d_cen if d_cen > 0 else 0.0
    height = float(ymax - com[1])
    tilt = math.degrees(math.atan2(max(d_com, 0.0), max(height, 1e-6)))
    stats.update({"margin": margin, "tip_angle_deg": tilt, "com_height_ldu": height})
    items = []
    if not inside:
        items.append({"severity": "fail", "problem": "centre of mass is outside the base"})
    elif tilt < cfg.get("min_tilt_deg", 10):
        items.append({"severity": "fail", "problem": f"tips over at only {tilt:.1f} degrees"})
    elif margin < cfg.get("min_margin", 0.25):
        items.append({"severity": "warn", "problem": f"centre of mass only {margin:.0%} "
                                                     "from the edge of the base"})
    status = "fail" if any(i["severity"] == "fail" for i in items) else (
        "warn" if items else "pass")
    return CheckResult("stability", status,
                       f"about {total:.0f} g; centre of mass {'inside' if inside else 'OUTSIDE'} "
                       f"the base ({max(margin, 0):.0%} margin); tips at {tilt:.1f} deg",
                       items, stats)
```

**File:** `brickkit/checks/mechanism.py`
```python
"""Sweep the model's pose function: no collisions, linkage stays connected, gears mesh."""
from __future__ import annotations

import re

import numpy as np

from ..snaps.match import find_connections
from .base import CheckResult, components, describe, register

TEETH_RE = re.compile(r"(\d+)\s*Tooth", re.I)
PITCH = 1.25   # LEGO gears are module 1 mm: pitch radius = teeth * 0.5 mm = teeth * 1.25 LDU


def _teeth(ctx, part: str) -> int | None:
    name = ctx.catalog.part_name(part)
    if "worm" in name.lower():
        return 8
    m = TEETH_RE.search(name)
    return int(m.group(1)) if m else None


def _axis(ctx, p) -> np.ndarray:
    conns = [c.transformed(p.M) for c in ctx.shadow.connectors(p.part)]
    ax = [c for c in conns if c.kind == "cyl" and any(s[0] == "A" for s in c.secs)]
    c = ax[0] if ax else (conns[0] if conns else None)
    return c.axis if c is not None else p.M[:3, 1]


def _gear_items(ctx) -> list[dict]:
    items = []
    for ta, tb, kind in ctx.model.gear_pairs:
        a, b = ctx.model.find(ta, ctx.placed), ctx.model.find(tb, ctx.placed)
        if len(a) != 1 or len(b) != 1:
            items.append({"problem": f"gear pair {ta}/{tb}: tag must match exactly one part"})
            continue
        a, b = a[0], b[0]
        na, nb = _teeth(ctx, a.part), _teeth(ctx, b.part)
        if na is None or nb is None:
            items.append({"problem": f"gear pair {ta}/{tb}: unknown tooth count"})
            continue
        aa, ab = _axis(ctx, a), _axis(ctx, b)
        d = b.M[:3, 3] - a.M[:3, 3]
        want = PITCH * (na + nb)
        cross = np.cross(aa, ab)
        if kind == "spur":
            if np.linalg.norm(cross) > 1e-3:
                items.append({"problem": f"gear pair {ta}/{tb}: spur gear axes not parallel"})
                continue
            dist = float(np.linalg.norm(d - np.dot(d, aa) * aa))
        elif kind in ("worm", "bevel"):
            if abs(float(np.dot(aa, ab))) > 1e-3:
                items.append({"problem": f"gear pair {ta}/{tb}: {kind} axes not perpendicular"})
                continue
            dist = float(abs(np.dot(d, cross)) / np.linalg.norm(cross))
            if kind == "bevel":
                want = 0.0
        else:
            continue
        if abs(dist - want) > 0.6:
            items.append({"problem": f"gear pair {ta}/{tb}: centres {dist:.1f} LDU apart, "
                                     f"need {want:.1f} for {na}T + {nb}T"})
    return items


@register("mechanism")
def check_mechanism(ctx, cfg) -> CheckResult:
    m = ctx.model
    items = _gear_items(ctx)
    for fn in m.extra_checks:
        items += fn(ctx)
    if m.pose is None:
        return CheckResult("mechanism", "fail" if items else "pass",
                           "no moving parts defined" if not items else f"{len(items)} problem(s)",
                           items)
    n = int(cfg.get("poses", 24))
    base_pieces = len(components(len(ctx.placed), [(c.a, c.b) for c in ctx.connections]))
    for t in np.linspace(0.0, 1.0, n):
        placed = m.flatten(pose=m.pose(float(t)))
        moving = {i for i, p in enumerate(placed) if m.group_of(p) is not None}
        for i, j in ctx.collide.pairs([(p.part, p.M) for p in placed], only=moving):
            items.append({"pose": round(float(t), 3), "a": describe(placed[i]),
                          "b": describe(placed[j]), "problem": "parts collide while moving"})
        conns = find_connections(ctx.world_connectors(placed))
        pieces = len(components(len(placed), [(c.a, c.b) for c in conns]))
        if pieces > base_pieces:
            items.append({"pose": round(float(t), 3),
                          "problem": f"model falls apart into {pieces} pieces at this pose"})
    return CheckResult("mechanism", "fail" if items else "pass",
                       f"{n} poses swept for {len(m.groups)} moving group(s); "
                       f"{len(m.gear_pairs)} gear pair(s); {len(items)} problem(s)", items,
                       {"poses": n})
```

**File:** `brickkit/checks/electrics.py`
```python
"""Cables must reach: route length (end part -> waypoints -> end part) <= cable length."""
from __future__ import annotations

import numpy as np

from .base import CheckResult, register


@register("electrics")
def check_electrics(ctx, cfg) -> CheckResult:
    m = ctx.model
    if not m.cables and not m.lights:
        return CheckResult("electrics", "pass", "no electrics in this model")
    items = []
    for light in m.lights:
        if len(m.find(light["part"], ctx.placed)) != 1:
            items.append({"light": light["name"], "problem": "light part not found (tag path)"})
    for cab in m.cables:
        a, b = m.find(cab["from"], ctx.placed), m.find(cab["to"], ctx.placed)
        if len(a) != 1 or len(b) != 1:
            items.append({"cable": cab["name"], "problem": "cable end parts not found"})
            continue
        pts = [a[0].M[:3, 3]] + [np.asarray(q) for q in cab["route"]] + [b[0].M[:3, 3]]
        need = float(sum(np.linalg.norm(pts[k + 1] - pts[k]) for k in range(len(pts) - 1)))
        if need > cab["length"]:
            items.append({"cable": cab["name"], "problem": f"needs {need:.0f} LDU of cable, "
                                                           f"has {cab['length']:.0f}"})
    return CheckResult("electrics", "fail" if items else "pass",
                       f"{len(m.lights)} light(s), {len(m.cables)} cable run(s); "
                       f"{len(items)} problem(s)", items)
```

**File:** `brickkit/checks/technique.py`
```python
"""Building-technique warnings: brittle transparent clips, moving transparent parts, banned
parts, and parts whose geometry makes the collision check less precise."""
from __future__ import annotations

from ..ldraw.library import part_id
from .base import CheckResult, describe, register, status_of


@register("technique")
def check_technique(ctx, cfg) -> CheckResult:
    items = []
    for c in ctx.connections:
        if c.kind == "clip":
            p = ctx.placed[c.a if c.ca.kind == "clp" else c.b]
            if p.color.is_trans:
                items.append({"severity": "warn", "part": describe(p),
                              "problem": "clip on a transparent part (brittle plastic)"})
    for part in sorted({p.part for p in ctx.placed}):
        if not ctx.geom.mesh(part).certified:
            items.append({"severity": "warn", "part": part_id(part),
                          "problem": "geometry not BFC-certified; collision check less precise"})
    if ctx.model.groups:
        for p in ctx.placed:
            if ctx.model.group_of(p) and p.color.is_trans:
                items.append({"severity": "warn", "part": describe(p),
                              "problem": "transparent part in a moving group"})
    banned = set(cfg.get("banned_parts", []))
    for p in ctx.placed:
        if part_id(p.part) in banned:
            items.append({"severity": "fail", "part": describe(p), "problem": "banned part"})
    return CheckResult("technique", status_of(items, default_fail=False),
                       f"{len(items)} note(s)", items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_checks_physical.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/checks tests/test_checks_physical.py
git commit -m "feat: stability, mechanism, electrics and technique checks"
```

---

### Task 14: Parts lists (CSV, BrickLink wanted list, Pick a Brick)

**Files:**
- Create: `brickkit/bom/__init__.py`, `brickkit/bom/bom.py`
- Test: `tests/test_bom.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_bom.py`
```python
from brickkit.bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
from tests.test_builder import make


def test_bom_counts_and_exports(engine, tmp_path):
    lines = build_bom(make(engine).flatten(), engine.catalog)
    q = {(l.ldraw_part, l.color.name): l.qty for l in lines}
    assert q == {("3003", "White"): 4, ("3001", "Red"): 1}
    write_parts_csv(lines, tmp_path / "parts.csv")
    write_bricklink_xml(lines, tmp_path / "w.xml")
    write_pick_a_brick_csv(lines, tmp_path / "pab.csv")
    x = (tmp_path / "w.xml").read_text()
    assert "<ITEMID>3003</ITEMID>" in x and "<COLOR>1</COLOR>" in x and "<MINQTY>4</MINQTY>" in x
    assert (tmp_path / "parts.csv").read_text().startswith("qty,part,name")
    assert len((tmp_path / "pab.csv").read_text().strip().splitlines()) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_bom.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'brickkit.bom'`

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/bom/__init__.py`
```python
"""Bills of materials and shop exports."""
```

**File:** `brickkit/bom/bom.py`
```python
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from ..catalog.colors import Color
from ..ldraw.library import part_id


@dataclass
class BomLine:
    ldraw_part: str
    rb_part: str
    bl_part: str
    name: str
    color: Color
    qty: int
    element_id: str
    rare: bool


def build_bom(placed, catalog) -> list[BomLine]:
    counts = Counter((p.part, p.color.ldraw) for p in placed if catalog.in_bom(p.part))
    lines = []
    for (part, code), qty in counts.items():
        c = catalog.color(code)
        e = catalog.element(part, c)
        lines.append(BomLine(part_id(part), catalog.rb_part(part), catalog.bl_part(part),
                             catalog.part_name(part), c, qty,
                             e.element_ids[-1] if e and e.element_ids else "",
                             bool(e is None or e.rare)))
    lines.sort(key=lambda l: (l.color.name, l.ldraw_part))
    return lines


def write_parts_csv(lines: list[BomLine], path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qty", "part", "name", "colour", "ldraw_colour", "rebrickable_part",
                    "rebrickable_colour", "bricklink_part", "bricklink_colour", "element_id",
                    "rare"])
        for l in lines:
            w.writerow([l.qty, l.ldraw_part, l.name, l.color.name, l.color.ldraw, l.rb_part,
                        l.color.rb_id, l.bl_part, l.color.bl_id, l.element_id, int(l.rare)])


def write_bricklink_xml(lines: list[BomLine], path) -> None:
    out = ["<INVENTORY>"]
    for l in lines:
        colour = f"<COLOR>{l.color.bl_id}</COLOR>" if l.color.bl_id is not None else ""
        out.append(f"<ITEM><ITEMTYPE>P</ITEMTYPE><ITEMID>{escape(l.bl_part)}</ITEMID>{colour}"
                   f"<MINQTY>{l.qty}</MINQTY></ITEM>")
    out.append("</INVENTORY>")
    Path(path).write_text("\n".join(out) + "\n")


def write_pick_a_brick_csv(lines: list[BomLine], path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["elementId", "quantity"])
        for l in lines:
            if l.element_id:
                w.writerow([l.element_id, l.qty])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_bom.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add brickkit/bom tests/test_bom.py
git commit -m "feat: parts list, BrickLink wanted list and Pick a Brick exports"
```

---

### Task 15: Projects, CLI, model template and the `_sample` model

**Files:**
- Create: `brickkit/project.py`, `brickkit/cli.py`, `brickkit/templates/model/model.toml`, `brickkit/templates/model/design.py`, `models/_sample/model.toml`, `models/_sample/design.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

**File:** `tests/test_cli.py`
```python
import subprocess
import sys

from brickkit import paths


def test_cli_all_sample(engine):
    r = subprocess.run([sys.executable, "-m", "brickkit", "all", "_sample"],
                       capture_output=True, text=True, cwd=paths.ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    out = paths.MODELS_DIR / "_sample" / "out"
    for f in ["_sample.mpd", "report.json", "report.html", "parts.csv", "bricklink_wanted.xml",
              "pick_a_brick.csv"]:
        assert (out / f).exists(), f
    assert "[PASS] buildability" in r.stdout


def test_cli_new_scaffolds_model(tmp_path, monkeypatch):
    from brickkit import cli
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path)
    assert cli.main(["new", "robot_dog", "--name", "Robot Dog"]) == 0
    toml = (tmp_path / "robot_dog" / "model.toml").read_text()
    assert 'name = "Robot Dog"' in toml and (tmp_path / "robot_dog" / "design.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`
Expected: FAIL (`No module named brickkit.cli`)

- [ ] **Step 3: Write minimal implementation**

**File:** `brickkit/project.py`
```python
"""A model package: models/<slug>/model.toml + design.py (defining build(model))."""
from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

from . import paths
from .model.builder import Model


class Project:
    def __init__(self, slug: str, models_dir: Path | None = None):
        self.slug = slug
        self.dir = (models_dir or paths.MODELS_DIR) / slug
        if not (self.dir / "model.toml").exists():
            raise FileNotFoundError(f"no model.toml in {self.dir}")
        self.config = tomllib.loads((self.dir / "model.toml").read_text())

    @property
    def out(self) -> Path:
        d = self.dir / "out"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def checks_config(self) -> dict:
        return self.config.get("checks", {})

    def build(self, catalog) -> Model:
        cfg = self.config["model"]
        model = Model(cfg["name"], self.slug, self.config.get("palette", {}), catalog)
        model.meta = dict(cfg)
        design = self.dir / cfg.get("design", "design.py")
        spec = importlib.util.spec_from_file_location(f"brickkit_model_{self.slug}", design)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build(model)
        return model
```

**File:** `brickkit/cli.py`
```python
"""brickkit command line: fetch | new | build | verify | bom | all"""
from __future__ import annotations

import argparse

from . import paths


def _build(engine, slug):
    from .io.mpd import write_mpd
    from .project import Project
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    placed = model.flatten()
    out = write_mpd(model, proj.out / f"{slug}.mpd")
    print(f"{model.name}: {len(placed)} parts, {len(model.instruction_order())} steps -> {out}")
    return proj, model


def _verify(engine, proj, model) -> int:
    from .checks import run_checks
    from .checks.report import write_report
    results = run_checks(engine.context(model, proj.checks_config))
    data = write_report(results, proj.out, model.name)
    for r in results:
        print(f"[{r.status.upper()}] {r.name}: {r.summary}")
        for item in r.items[:5]:
            print(f"        {item}")
    print(f"overall: {data['status'].upper()} -> {proj.out / 'report.html'}")
    return 1 if data["status"] == "fail" else 0


def _bom(engine, proj, model) -> None:
    from .bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
    lines = build_bom(model.flatten(), engine.catalog)
    write_parts_csv(lines, proj.out / "parts.csv")
    write_bricklink_xml(lines, proj.out / "bricklink_wanted.xml")
    write_pick_a_brick_csv(lines, proj.out / "pick_a_brick.csv")
    print(f"parts list: {sum(l.qty for l in lines)} pieces in {len(lines)} lines "
          f"-> {proj.out / 'parts.csv'}")


def _new(slug: str, name: str | None) -> int:
    dst = paths.MODELS_DIR / slug
    if dst.exists():
        print(f"{dst} already exists")
        return 1
    dst.mkdir(parents=True)
    for f in (paths.TEMPLATES_DIR / "model").iterdir():
        text = f.read_text().replace("{{slug}}", slug).replace("{{name}}", name or slug)
        (dst / f.name).write_text(text)
    print(f"created {dst}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brickkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download part libraries")
    p = sub.add_parser("new", help="scaffold a new model")
    p.add_argument("slug")
    p.add_argument("--name")
    for c in ("build", "verify", "bom", "all"):
        sub.add_parser(c).add_argument("slug")
    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        from .fetch import fetch
        fetch()
        return 0
    if args.cmd == "new":
        return _new(args.slug, args.name)

    from .engine import Engine
    engine = Engine()
    proj, model = _build(engine, args.slug)
    code = 0
    if args.cmd in ("verify", "all"):
        code = _verify(engine, proj, model)
    if args.cmd in ("bom", "all"):
        _bom(engine, proj, model)
    return code
```

**File:** `brickkit/templates/model/model.toml`
```toml
[model]
name = "{{name}}"
design = "design.py"

[palette]
body = "Light Bluish Gray"

[checks]
enabled = ["real_elements", "connections", "collisions", "buildability", "stability",
           "mechanism", "electrics", "technique"]
```

**File:** `brickkit/templates/model/design.py`
```python
"""{{name}}: describe the model with the builder API. Units: LDU (stud 20, plate 8, brick 24),
-Y is up. Colours are palette roles from model.toml or real colour names."""


def build(model):
    main = model.main
    main.place("3001", "body")
```

**File:** `models/_sample/model.toml`
```toml
[model]
name = "Sample Tower"
design = "design.py"

[palette]
base = "Dark Bluish Gray"
body = "White"
roof = "Red"

[checks]
enabled = ["real_elements", "connections", "collisions", "buildability", "stability",
           "mechanism", "electrics", "technique"]
```

**File:** `models/_sample/design.py`
```python
"""A tiny tower used by the engine tests: a base, two pillar sub-assemblies, a roof."""


def build(model):
    pillar = model.submodel("pillar", "Pillar")
    pillar.place("3003", "body")
    pillar.step()
    pillar.place("3003", "body", (0, -24, 0))

    main = model.main
    main.place("3001", "base")
    main.step("Add the two pillars")
    main.use(pillar, (-20, -24, 0), tag="left")
    main.use(pillar, (20, -24, 0), tag="right")
    main.step("Roof")
    main.place("3001", "roof", (0, -72, 0))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v && .venv/bin/python -m pytest -q`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add brickkit/project.py brickkit/cli.py brickkit/templates models/_sample tests/test_cli.py
git commit -m "feat: projects, CLI (fetch/new/build/verify/bom/all) and sample model"
```
