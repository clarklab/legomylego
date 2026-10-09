"""A model from a BrickLink Studio .io file or an LDraw .ldr / .mpd file: the exact parts,
colours and positions, written out as a design.py to carry on from.

    brickkit import SLUG FILE [--name "Name"] [--sub "SubModel Group 1"] [--as NAME]

A .io file is a zip (older ones locked with Studio's fixed password); inside, model.ldr is the
model in LDraw. Sub-models are flattened into it (`--sub`: take just that one). The model
is kept as its designer posed it, set down so its lowest point is on y = 0 and its middle on
x = z = 0.

Steps: the file's own, when it has enough of them; else a build order is worked out - the
order in which each piece can really go on, onto something already there, with a clear way
in (video/assemble.py) - one piece to a step, pairs of the same piece together.

It writes models/SLUG/ like `brickkit new --quick` (model.toml, NOTES.md, reference/), with
design.py from the file. Studio keeps its own copy of each part, and a few are not LDraw's
(another origin, a number LDraw does not use): those are matched to LDraw's by shape and
moved to suit. Part numbers that still have no LDraw file (Studio's own printed parts) are
listed: swap each for the LDraw print or the plain part (docs/brickkit-guide.md)."""
from __future__ import annotations

import itertools
import re
import zipfile
from pathlib import Path

import numpy as np

from .. import paths
from ..ldraw.library import normalize
from ..ldraw.matrix import parse_type1, rot

STUDIO_KEY = b"soho0909"          # Studio's own lock on older .io files (it is no secret)


def unpack(src: Path, into: Path) -> Path:
    """The LDraw file to read: `src` itself, or model.ldr out of a .io."""
    src = Path(src)
    if src.suffix.lower() != ".io":
        return src
    into.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for pwd in (None, STUDIO_KEY):
            try:
                z.extract("model.ldr", into, pwd=pwd)
                return into / "model.ldr"
            except RuntimeError:
                continue
    raise SystemExit(f"{src.name}: could not open model.ldr in it")


def read(path: Path, sub: str | None = None) -> list[dict]:
    """Every part of an LDraw file, sub-models flattened: [{part, color (LDraw code), M (4 x 4),
    step (of the top file), path (the sub-models it is in)}]."""
    files: dict[str, list] = {}
    order: list[str] = []
    cur = None
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        t = raw.split()
        if t[:2] == ["0", "FILE"]:
            cur = normalize(" ".join(t[2:]))
            files[cur] = []
            order.append(cur)
            continue
        if cur is None:                                # a plain .ldr: one file, no header
            cur = "main"
            files[cur] = []
            order.append(cur)
        if t[:2] == ["0", "NOFILE"]:
            continue
        files[cur].append(t)
    top = order[0]
    if sub is not None:
        stem = lambda k: re.sub(r"\.(ldr|dat|mpd)$", "", k)      # noqa: E731
        hits = [k for k in order if stem(k) == stem(normalize(sub))]
        if not hits:
            raise SystemExit(f"no sub-model {sub!r} in {path.name}: it has {order}")
        top = hits[0]
    out: list[dict] = []

    def walk(name, W, color, step, trail):
        k = 0
        for t in files[name]:
            if t[:2] == ["0", "STEP"]:
                k += 1
            if len(t) < 15 or t[0] != "1":
                continue
            c, M, ref = parse_type1(t)
            c = color if c == 16 else c
            key = normalize(ref)
            here = (k if name == top else step)
            if key in files:
                walk(key, W @ M, c, here, trail + (key,))
            else:
                out.append({"part": key, "color": c, "M": W @ M, "step": here, "path": trail})

    walk(top, np.eye(4), 16, 0, ())
    return out


def _files(path: Path) -> dict:
    files, cur = {}, None
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        t = raw.split()
        if t[:2] == ["0", "FILE"]:
            cur = normalize(" ".join(t[2:]))
            files[cur] = []
        elif cur is not None:
            files[cur].append(t)
    return files


def _points(engine, files: dict, name: str, W=None, depth: int = 0, out=None) -> list:
    """The corners of every face of a part as a file defines it (its own sub-files first, the
    library's for the rest)."""
    W = np.eye(4) if W is None else W
    out = [] if out is None else out
    if name in files:
        lines = files[name]
    else:
        f = engine.lib.resolve(name)
        if f is None or depth > 14:
            return out
        lines = [ln.split() for ln in Path(f).read_text(encoding="utf-8", errors="replace").splitlines()]
    for t in lines:
        if len(t) >= 15 and t[0] == "1":
            _, M, ref = parse_type1(t)
            _points(engine, files, normalize(ref), W @ M, depth + 1, out)
        elif t and t[0] in ("3", "4") and len(t) >= (11 if t[0] == "3" else 14):
            n = 3 if t[0] == "3" else 4
            v = np.array([float(x) for x in t[2:2 + 3 * n]]).reshape(n, 3)
            out.append(v @ W[:3, :3].T + W[:3, 3])
    return out


def _quarter_turns() -> list:
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            P = np.zeros((3, 3))
            for i, (k, sg) in enumerate(zip(perm, signs)):
                P[i, k] = sg
            if np.linalg.det(P) > 0:
                out.append(P)
    return out


def _levels(polys, axis: int) -> np.ndarray:
    """The flat faces of a shape that are square to an axis: rows of (where along it, area)."""
    out = []
    for v in polys:
        n = np.cross(v[1] - v[0], v[2] - v[0])
        a = float(np.linalg.norm(n))
        if a > 1e-6 and abs(n[axis]) / a > 0.999:
            out.append((round(float(v[:, axis].mean()), 2), a if len(v) == 4 else a / 2))
    area: dict[float, float] = {}
    for at, a in out:                                  # (one row for each level)
        area[at] = area.get(at, 0.0) + a
    return np.array(sorted(area.items())).reshape(-1, 2)


def _slide(studio, ours, axis: int, span: float) -> float:
    """How far to slide our copy of a part along an axis so that its flat faces lie on
    Studio's. Their boxes can differ (Studio draws the logo on each stud, so its part is
    taller): lining up the boxes' corners would then leave the part a fraction off."""
    a, b = _levels(studio, axis), _levels(ours, axis)
    if not len(a) or not len(b):
        return 0.0
    best = (0.0, 0.0)
    for s in np.arange(-span, span + 1e-9, 0.01):
        on = np.abs(a[:, None, 0] - (b[None, :, 0] + s)) < 0.006
        score = float((np.minimum(a[:, None, 1], b[None, :, 1]) * on).sum())
        if score > best[0] * 1.001 or (score > best[0] * 0.999 and abs(s) < abs(best[1])):
            best = (max(score, best[0]), float(s))
    return round(best[1], 2)


def reconcile(engine, rows: list[dict], studio: Path) -> tuple[list[str], list[str]]:
    """Studio keeps its own copy of every part (model2.ldr in the .io), and a few of them are
    not LDraw's: another origin, another way up, or a number LDraw does not have. Each such
    part is matched to LDraw's by its shape and its rows moved to suit (in place). Returns
    (what was adjusted or renamed, the parts that could not be matched)."""
    from scipy.spatial import cKDTree
    files = _files(studio)
    fixed, lost = [], []
    for part in sorted({r["part"] for r in rows}):
        pts = _points(engine, files, part) if part in files else []
        if not pts:
            if engine.lib.resolve(part) is None:
                lost.append(part)
            continue
        V = np.unique(np.round(np.concatenate(pts), 2), axis=0)
        slo, shi = V.min(0), V.max(0)
        stem = re.match(r"\d+", part)
        names = [part] if engine.lib.resolve(part) is not None else []
        if not names and stem:                         # (not LDraw's number: the same mould under
            n = len(stem.group(0))                     # another letter?)
            names = sorted(k for k in engine.lib.files if k.startswith(stem.group(0)) and "/" not in k
                           and k.endswith(".dat") and "p" not in k[n:-4] and len(k) <= n + 6)
        best = None
        for name in names:
            try:
                mesh = engine.geom.mesh(name)
            except Exception:
                continue
            O = np.unique(np.round(mesh.tris.reshape(-1, 3), 2), axis=0)
            for P in _quarter_turns():
                Q = O @ P.T
                if np.abs((Q.max(0) - Q.min(0)) - (shi - slo)).max() > 1.0:
                    continue
                t = slo - Q.min(0)
                err = float(cKDTree(Q + t).query(V[:: max(1, len(V) // 400)])[0].mean())
                turned = not np.allclose(P, np.eye(3)) or np.abs(t).max() > 0.6
                key = (round(err, 2), name != part, turned)
                if best is None or key < best[0]:
                    best = (key, name, P, t, Q.max(0) - Q.min(0), mesh.tris)
        if best is None or best[0][0] > 2.0:
            lost.append(part)
            continue
        _, name, P, t, size, tris = best
        for axis in range(3):                          # (a box that is not quite Studio's size)
            gap = float(abs((shi - slo)[axis] - size[axis]))
            if gap > 0.05:
                ours = [v @ P.T + t for v in tris]
                t = t.copy()
                t[axis] += _slide(pts, ours, axis, gap + 0.05)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = P, t
        if name != part or not np.allclose(T, np.eye(4), atol=0.6):
            for r in rows:
                if r["part"] == part:
                    r["part"], r["M"] = name, r["M"] @ T
            fixed.append(f"{part} -> {name}" + ("" if np.allclose(T, np.eye(4), atol=0.6) else " (moved to LDraw's origin)"))
    return fixed, lost


def settle(rows: list[dict], engine) -> None:
    """Move the model (in place) so its lowest point is on y = 0 and its middle on x = z = 0,
    to the nearest unit that keeps its parts on their grid."""
    pts = []
    for r in rows:
        try:
            lo, hi = engine.geom.mesh(r["part"]).bbox
        except Exception:                              # (a part LDraw has no file for)
            lo, hi = np.array([-10.0, 0, -10]), np.array([10.0, 8, 10])
        box = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        pts.append(box @ r["M"][:3, :3].T + r["M"][:3, 3])
    pts = np.concatenate(pts)
    mid = (pts.min(0) + pts.max(0)) / 2
    first = rows[0]["M"][:3, 3]
    shift = np.array([-round((mid[0] - first[0]) / 10) * 10 - first[0], -pts[:, 1].max(),
                      -round((mid[2] - first[2]) / 10) * 10 - first[2]])
    for r in rows:
        r["M"] = r["M"].copy()
        r["M"][:3, 3] += shift
        r["M"][np.abs(r["M"]) < 1e-9] = 0.0


_TURNS: dict | None = None


def turn(R) -> str | None:
    """`rot(...)` for a rotation that is quarter turns only (None for identity), else a literal
    `R(...)` of its nine numbers."""
    global _TURNS
    if _TURNS is None:
        _TURNS = {}
        for x, y, z in sorted(itertools.product((0, 90, 180, -90), repeat=3),
                              key=lambda a: (sum(1 for v in a if v), sum(abs(v) for v in a))):
            _TURNS.setdefault(tuple(np.round(rot(x, y, z).reshape(-1)).astype(int)), (x, y, z))
    key = tuple(np.round(np.asarray(R).reshape(-1), 4))
    if all(abs(v - round(v)) < 1e-4 for v in key):
        hit = _TURNS.get(tuple(int(round(v)) for v in key))
        if hit is not None:
            args = ", ".join(f"{n}={v}" for n, v in zip("xyz", hit) if v)
            return f"rot({args})" if args else None
    return "R(" + ", ".join(f"{v:.5f}".rstrip("0").rstrip(".") for v in np.asarray(R).reshape(-1)) + ")"


def role(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _num(v: float) -> str:
    v = round(float(v), 3)
    return str(int(v)) if v == int(v) else f"{v:g}"


def sequence(engine, rows: list[dict], name: str) -> list[list[int]]:
    """Steps for a model that came without them: the order each piece can really go on, pairs
    of the same piece in one step."""
    from ..model.builder import Model
    from ..video import assemble as A
    model = Model(name, "import", {}, engine.catalog)
    order = sorted(range(len(rows)), key=lambda i: (-rows[i]["M"][1, 3], rows[i]["M"][0, 3]))   # low first
    for i in order:
        model.main.place(rows[i]["part"], engine.catalog.color(rows[i]["color"]), rows[i]["M"][:3, 3],
                         rows[i]["M"][:3, :3])
    placed = model.flatten()
    script = A.assemble(engine, model, placed, list(range(len(placed))), log=lambda m: None)
    steps: list[list[int]] = []
    for it in script["items"]:
        idx = [order[i] for i in it.parts]
        same = steps and len(steps[-1]) < 2 and all(
            (rows[a]["part"], rows[a]["color"]) == (rows[idx[0]]["part"], rows[idx[0]]["color"])
            for a in steps[-1])
        if same:
            steps[-1] += idx
        else:
            steps.append(idx)
    return steps


def design(engine, rows: list[dict], steps: list[list[int]], name: str, source: str) -> tuple[str, dict]:
    """design.py for the rows, and the palette its colour roles need."""
    palette, lines = {}, []
    loose = False
    for k, step in enumerate(steps):
        names = {}
        for i in step:
            try:
                label = engine.catalog.part_name(rows[i]["part"])
            except Exception:
                label = rows[i]["part"]
            names[label] = names.get(label, 0) + 1
        caption = "; ".join(f"{n}x {label}" if n > 1 else label for label, n in names.items())
        lines.append(f"\n    m.step({caption!r})")
        for i in step:
            r = rows[i]
            col = engine.catalog.color(r["color"]).name
            palette[role(col)] = col
            t = turn(r["M"][:3, :3])
            loose = loose or (t or "").startswith("R(")
            pos = ", ".join(_num(v) for v in r["M"][:3, 3])
            lines.append(f"    m.place({r['part'].removesuffix('.dat')!r}, {role(col)!r}, ({pos})"
                         + (f", {t}" if t else "") + ")")
    head = f'''"""{name}: a Quick Bricks model, imported from {source} (brickkit import).

Every part is where its designer put it. Frame: LDU (stud 20, plate 8, brick 24), -Y up; the
model's lowest point is on y = 0. Colours are palette roles from model.toml."""
'''
    if loose:
        head += '''import numpy as np

from brickkit.ldraw.matrix import rot  # noqa: F401


def R(*m):
    """A part that is not on a quarter turn (a wing on its clip): its rotation, row by row."""
    return np.array(m, float).reshape(3, 3)
'''
    else:
        head += "from brickkit.ldraw.matrix import rot  # noqa: F401\n"
    return head + "\n\ndef build(model):\n    m = model.main\n" + "\n".join(lines) + "\n", palette


def import_model(engine, slug: str, src: Path, name: str | None = None, sub: str | None = None,
                 who: str | None = None, models_dir: Path | None = None) -> dict:
    """Scaffold models/SLUG from a .io / .ldr / .mpd file. Returns {parts, steps, own_steps,
    unknown (part numbers LDraw has no file for), dir}."""
    from ..cli import _new
    base = models_dir or paths.MODELS_DIR
    src = Path(src)
    name = name or slug.replace("_", " ").title()
    work = src.parent / "unpacked"
    rows = read(unpack(src, work), sub)
    if not rows:
        raise SystemExit(f"{src.name}: no parts in it")
    fixed: list[str] = []
    if src.suffix.lower() == ".io":                    # Studio's own parts, matched to LDraw's
        with zipfile.ZipFile(src) as z:
            if "model2.ldr" in z.namelist():
                for pwd in (None, STUDIO_KEY):
                    try:
                        z.extract("model2.ldr", work, pwd=pwd)
                        break
                    except RuntimeError:
                        continue
                fixed, _ = reconcile(engine, rows, work / "model2.ldr")
    unknown = sorted({r["part"] for r in rows if engine.lib.resolve(r["part"]) is None})
    settle(rows, engine)
    n_file = len({r["step"] for r in rows})
    own = n_file >= max(3, len(rows) / 6)
    if own:
        by = {}
        for i, r in enumerate(rows):
            by.setdefault(r["step"], []).append(i)
        steps = [by[k] for k in sorted(by)]
    elif unknown:                                      # (no geometry to work an order out from)
        steps = [[i] for i in sorted(range(len(rows)), key=lambda i: -rows[i]["M"][1, 3])]
    else:
        steps = sequence(engine, rows, name)
    text, palette = design(engine, rows, steps, name, src.name)
    if _new(slug, name, quick=True, who=who) != 0:
        raise SystemExit(1)
    d = base / slug
    (d / "design.py").write_text(text)
    toml = (d / "model.toml").read_text()
    toml = toml.replace('[palette]                     # role -> a real colour name; design.py places parts by role\n'
                        'body = "Light Bluish Gray"\n',
                        "[palette]                     # role -> a real colour name; design.py places parts by role\n"
                        + "".join(f'{k} = "{v}"\n' for k, v in sorted(palette.items())))
    (d / "model.toml").write_text(toml)
    return {"parts": len(rows), "steps": len(steps), "own_steps": own, "unknown": unknown, "fixed": fixed,
            "dir": d}
