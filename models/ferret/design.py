"""Life-size ferret, mid-bounce: long tubular body with the arched running "hunch", head low and
forward, thick tapering tail. Brick-built sculpture: the body is sampled from a swept tube
(ferret_shape) in brick-high layers on the stud grid, smoothed with curved-slope caps, and cut
into sub-assemblies (chest, hips, back) that are planned so every part slides into place.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the nose points to -Z."""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ferret_sculpt as sc  # noqa: E402
import ferret_shape as fs  # noqa: E402

# grid extent (cells) and the sculpt origin in LDU
XS = np.arange(-6, 6)
ZS = np.arange(-1, 66)
KS = np.arange(0, 18)
SEAM = 8                    # brick band where the back starts (chest and hips below it)
SOCKET = 2                  # band of the leg sockets (lower legs + paws are sub-assemblies)
TORSO = (10, 64)            # z cells of the brick-built body and tail (the head is built apart)
FRONT_LEG = ((-3, 19), (1, 19))   # lower-left cell (i, j) of each 2x2 front-leg socket
HIND_LEG = ((-3, 43), (1, 43))


# ------------------------------------------------------------------------------------------
# colours: a part may only be used for a role if it exists in every colourway's colour

def role_colours() -> dict[str, set[str]]:
    cfg = tomllib.loads((HERE / "model.toml").read_text())
    out = {r: {c} for r, c in cfg.get("palette", {}).items()}
    for v in cfg.get("variants", {}).values():
        for r, c in v.items():
            if r != "title":
                out.setdefault(r, set()).add(c)
    return out


class Avail:
    def __init__(self, catalog):
        self.cat = catalog
        self.cols = role_colours()
        self.cache: dict = {}

    def ok(self, part: str, role: str) -> bool:
        key = (part, role)
        if key not in self.cache:
            good = True
            if self.cat is not None:
                for c in self.cols.get(role, {role}):
                    e = self.cat.element(part, c)
                    if e is None or e.set_count < 3 or e.last_year < 2016:
                        good = False
                        break
            self.cache[key] = good
        return self.cache[key]

    def sizes(self, table: dict, role: str) -> list:
        return [s for s, p in table.items() if self.ok(p, role)]


# ------------------------------------------------------------------------------------------
# the voxel body

def body_layers() -> dict[int, set]:
    V = fs.voxels(XS, ZS, KS)
    V[:, (ZS < TORSO[0]) | (ZS > TORSO[1]), :] = False
    S = {int(k): {(int(XS[i]), int(ZS[j])) for j, i in zip(*np.nonzero(V[n]))}
         for n, k in enumerate(KS)}
    # the lower legs and paws are separate sub-assemblies plugged in under the sockets
    for k in S:
        if k < SOCKET:
            S[k] = set()
    for i0, j0 in FRONT_LEG + HIND_LEG:
        S[SOCKET] |= sc.rect(i0, j0, 2, 2)
    return S


def grad_dir(x_mm, h_mm, z_mm):
    """Dominant horizontal outward direction of the surface near a point (lateral preferred:
    the body is a tube running along z, so most slopes should fall to the sides)."""
    e = 2.0
    f = fs.inside
    gx = f(x_mm + e, h_mm, z_mm) - f(x_mm - e, h_mm, z_mm)
    gz = f(x_mm, h_mm, z_mm + e) - f(x_mm, h_mm, z_mm - e)
    if abs(gx) >= 0.6 * abs(gz):
        return (1 if gx > 0 else -1, 0)
    return (0, 1 if gz > 0 else -1)


def centre_mm(c, k):
    return (c[0] + 0.5) * fs.STUD, (k + 0.5) * fs.BRICK, (c[1] + 0.5) * fs.STUD


def ramps_of(T: set, dirs: dict) -> list[tuple[list, tuple]]:
    """Group exposed cells into straight runs along their outward direction, outer end first."""
    out = []
    seen = set()
    for c in sorted(T):
        if c in seen:
            continue
        d = dirs[c]
        # walk inward to the start of the run, then outward
        step_in = (-d[0], -d[1])
        inner = c
        while True:
            n = (inner[0] + step_in[0], inner[1] + step_in[1])
            if n in T and dirs[n] == d and n not in seen:
                inner = n
            else:
                break
        run = [inner]
        while True:
            n = (run[-1][0] + d[0], run[-1][1] + d[1])
            if n in T and dirs[n] == d and n not in seen:
                run.append(n)
            else:
                break
        seen.update(run)
        out.append((run[::-1], d))
    return out


def smooth_layers(S: dict) -> dict:
    """Grow each layer so no ramp on the layer below is longer than 3 studs."""
    for k in sorted(S):
        if k + 1 not in S:
            continue
        T = S[k] - S[k + 1]
        dirs = {c: grad_dir(*centre_mm(c, k + 1)) for c in T}
        for run, d in ramps_of(T, dirs):
            wall = (run[-1][0] - d[0], run[-1][1] - d[1]) in S[k + 1]
            if wall and len(run) > 3:
                S[k + 1] |= set(run[3:])
    return S


def cell_role(c, k, S, legs: set) -> str:
    """Coat colour by position (the caller decides whether the cell is visible)."""
    x, h, z = centre_mm(c, k)
    if z > 396:
        return "dark"                                   # tail
    if fs.limb_dist(x, h, z) <= 1.0:
        return "dark"                                   # legs, dark up to shoulders and thighs
    if z < 44:
        return "face" if h < 84 else ("mask" if z > 20 and h < 96 else "coat")
    below = (c not in S.get(k - 1, set()))
    if below:
        return "belly"
    return "coat"


def sections_of(S: dict) -> dict:
    """(cell, band) -> section. Below the seam, the islands that carry the front legs form the
    chest and those with the hind legs the hips; anything else below the seam hangs from the
    back, which is everything from the seam up."""
    sec = {}
    lower = {(c, k) for k in S if k < SEAM for c in S[k]}
    seen = set()
    front = {(c, k) for i0, j0 in FRONT_LEG for c in sc.rect(i0, j0, 2, 2) for k in S}
    hind = {(c, k) for i0, j0 in HIND_LEG for c in sc.rect(i0, j0, 2, 2) for k in S}
    for start in sorted(lower, key=lambda ck: (ck[1], ck[0])):
        if start in seen:
            continue
        comp, todo = set(), [start]
        seen.add(start)
        while todo:
            (i, j), k = todo.pop()
            comp.add(((i, j), k))
            for n in (((i + 1, j), k), ((i - 1, j), k), ((i, j + 1), k), ((i, j - 1), k),
                      ((i, j), k + 1), ((i, j), k - 1)):
                if n in lower and n not in seen:
                    seen.add(n)
                    todo.append(n)
        name = "chest" if comp & front else ("hips" if comp & hind else "back")
        for ck in comp:
            sec[ck] = name
    for k in S:
        for c in S[k]:
            sec.setdefault((c, k), "back")
    # a fringe only one layer thick under the back cannot hold together on its own: hang it
    # from the back above it (rim cells with nothing above stay and bond sideways)
    changed = True
    while changed:
        changed = False
        for (c, k), name in list(sec.items()):
            if name == "back":
                continue
            if sec.get((c, k + 1)) != name and sec.get((c, k - 1)) != name \
                    and sec.get((c, k + 1)) == "back":
                sec[(c, k)] = "back"
                changed = True
    return sec


def sculpt_pieces(av: Avail):
    S = smooth_layers(body_layers())
    sec = sections_of(S)
    legs = {(i + 1, j + 1) for i, j in FRONT_LEG + HIND_LEG}     # socket centres (cells)
    ks = sorted(k for k in S if S[k])
    sections: dict[str, list] = {"back": [], "chest": [], "hips": []}
    role_of = {}
    for k in ks:
        cells = S[k]
        below = S.get(k - 1, set())
        for c in cells:
            nb = [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            visible = any(n not in cells for n in nb) or c not in below
            role_of[(c, k)] = cell_role(c, k, S, legs) if visible else "core"
    for name in sections:
        order = ks if name == "back" else ks[::-1]
        layers = []
        for k in order:
            mine = {c for c in S[k] if sec[(c, k)] == name}
            if mine:
                layers.append((k, mine, {c: role_of[(c, k)] for c in mine},
                               "z" if k % 2 == 0 else "x"))
        pieces, n_clusters = sc.pack_section(layers, lambda r: av.sizes(sc.BRICK, r))
        if n_clusters > 1:
            print(f"[ferret] {name}: packed into {n_clusters} separate clusters")
        sections[name] += pieces
    for k in ks:
        cells = S[k]
        above = S.get(k + 1, set())
        # caps on the exposed tops of this layer, in band k + 1
        T = cells - above
        dirs = {c: grad_dir(*centre_mm(c, k + 1)) for c in T}
        for run, d in ramps_of(T, dirs):
            role = cell_role(run[-1], k, S, legs)
            target = sections[sec[(run[-1], k)]]
            wall = (run[-1][0] - d[0], run[-1][1] - d[1]) in above
            if not wall:
                target += sc.roof_pieces(run, d, 3 * (k + 1), role, k + 1)
                continue
            for m in range(0, len(run), 3):
                target += sc.ramp_pieces(run[m:m + 3], d, 3 * (k + 1), role, k + 1)
    return S, sections


# ------------------------------------------------------------------------------------------
# legs

def leg_top(S, sockets) -> int:
    i0, j0 = sockets[0]
    cells = sc.rect(i0, j0, 2, 2)
    return min(k for k in S if cells & S[k])


def build_leg(model, name: str, title: str, band: int, hind: bool):
    """A 2x2 leg column on a paw; origin = ground under the column centre."""
    leg = model.submodel(name, title)
    top = 3 * band                           # plates
    if hind:
        # long hind foot: 2x4 plate, toes (2x2 curved slope) in front of the column
        leg.place("3020", "dark", (0, -8, -20), sc.rot(y=90))
        leg.step()
        leg.place("15068", "dark", (0, -8, -40))
    else:
        # front paw: two 1x3 plates tied by the 2x2 plate above, a 1x2 cheese-slope toe row
        leg.place("3623", "dark", (-10, -8, -10), sc.rot(y=90))
        leg.place("3623", "dark", (10, -8, -10), sc.rot(y=90))
        leg.place("3022", "dark", (0, -16, 0))
        leg.step()
        leg.place("85984", "dark", (0, -8, -30))
    level = 2 if not hind else 1
    leg.step()
    while level < top:
        if top - level >= 3:
            leg.place("3003", "dark", (0, -8 * (level + 3), 0))
            level += 3
        else:
            leg.place("3022", "dark", (0, -8 * (level + 1), 0))
            level += 1
        leg.step()
    return leg


# ------------------------------------------------------------------------------------------

def build(model):
    av = Avail(model.catalog)
    S, secs = sculpt_pieces(av)

    subs = {}
    for name, title, key in (
            ("chest", "Chest and front legs", lambda p: (-p.band, p.p0, p.cells and min(p.cells)[1], min(p.cells))),
            ("hips", "Hips and hind legs", lambda p: (-p.band, p.p0, -max(c[1] for c in p.cells), min(p.cells))),
            ("back", "Arched back, neck and tail", lambda p: (p.band, p.p0, min(c[1] for c in p.cells), min(p.cells)))):
        pieces = secs[name]
        pl = sc.plan(pieces, key)
        if pl.stuck:
            print(f"[ferret] {name}: {len(pl.stuck)} piece(s) could not be planned, e.g. "
                  f"{[(p.part, sorted(p.cells)[:2], p.p0) for p in pl.stuck[:5]]}")
        sub = model.submodel(name, title)
        sc.emit(sub, sc.steps(pl.order + pl.stuck))
        subs[name] = sub

    fl = build_leg(model, "front_leg", "Front leg", leg_top(S, FRONT_LEG), hind=False)
    hl = build_leg(model, "hind_leg", "Hind leg", leg_top(S, HIND_LEG), hind=True)
    for sub, leg, sockets, tag in ((subs["chest"], fl, FRONT_LEG, "front"),
                                   (subs["hips"], hl, HIND_LEG, "hind")):
        for n, (i0, j0) in enumerate(sockets):
            sub.step(f"{tag.capitalize()} leg")
            side = "l" if i0 > 0 else "r"
            sub.use(leg, (sc.STUD * (i0 + 1), 0, sc.STUD * (j0 + 1)), tag=f"{tag}_leg_{side}")

    main = model.main
    main.step("Stand the chest on its front legs")
    main.use(subs["chest"], tag="chest")
    main.step("Set the hips beside it and lower the back onto both")
    main.use(subs["back"], tag="back")
    main.use(subs["hips"], tag="hips")
