"""Life-size ferret, mid-bounce: long tubular body with the arched running "hunch", head low and
forward, thick tapering tail. Brick-built sculpture: the body is sampled from a swept tube
(ferret_shape) in brick-high layers on the stud grid, smoothed with curved-slope caps, and cut
into sub-assemblies (chest, hips, back) that are planned so every part slides into place.

Units: LDU (stud 20, plate 8, brick 24), -Y up, the nose points to -Z."""
from __future__ import annotations

import sys
import tomllib
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ferret_head as fh  # noqa: E402
import ferret_sculpt as sc  # noqa: E402
import ferret_shape as fs  # noqa: E402
import ferret_tail as ft  # noqa: E402
from brickkit.ldraw.matrix import rot, transform, translate  # noqa: E402

# grid extent (cells) and the sculpt origin in LDU
XS = np.arange(-6, 6)
ZS = np.arange(-1, 66)
KS = np.arange(0, 18)
SEAM = 8                    # brick band where the back starts (chest and hips below it)
SOCKET = 2                  # band of the leg sockets (lower legs + paws are sub-assemblies)
TORSO = (11, 49)            # z cells of the brick-built body and tail (the head is built apart)
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
    # the throat runs forward under the back of the head: the head sits on it
    for j in range(fh.SHELF_ROW, TORSO[0]):
        S[fh.SHELF_TOP // 3 - 2] |= {(-1, j), (0, j)}
        S[fh.SHELF_TOP // 3 - 1] |= {(i, j) for i in range(-2, 2)}
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


ramps_of = sc.ramps_of


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
    if z < 96 and h < 80:
        return "face"                                   # white throat

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
    # the tail socket in the rump: its cells are taken by a 22885 and a plate
    socket, socket_cells, socket_bands = ft.socket_pieces()
    for k in socket_bands:
        S[k] |= socket_cells
    S[max(socket_bands) + 1] |= socket_cells        # a course over the socket ties it in
    sec = sections_of(S)
    legs = {(i + 1, j + 1) for i, j in FRONT_LEG + HIND_LEG}     # socket centres (cells)
    ks = sorted(k for k in S if S[k])
    sections: dict[str, list] = {"back": [], "chest": [], "hips": []}
    reserved = {(c, k) for k in socket_bands for c in socket_cells}
    fixed = {"back": {k: [(p, socket_cells)] for k, p in zip(socket_bands, socket)}}
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
        fx = fixed.get(name, {})
        for k in order:
            mine = {c for c in S[k] if sec[(c, k)] == name and (c, k) not in reserved}
            if mine or k in fx:
                layers.append((k, mine, {c: role_of[(c, k)] for c in mine},
                               "z" if k % 2 == 0 else "x"))
        pieces, n_clusters = sc.pack_section(layers, lambda r: av.sizes(sc.BRICK, r),
                                             fixed=fx)
        if n_clusters > 1:
            print(f"[ferret] {name}: packed into {n_clusters} separate clusters")
        sections[name] += pieces
    # the throat shelf's top: the turntable base the head turns on, and smooth tiles round it
    shelf_band = fh.SHELF_TOP // 3 - 1
    shelf_top = {c for c in S[shelf_band] if fh.SHELF_ROW <= c[1] < TORSO[0]}
    shelf_sec = sections[sec[(min(shelf_top), shelf_band)]]
    (ti, tj), tp = fh.TURNTABLE
    tt = frozenset(sc.rect(ti, tj, 2, 2))
    shelf_sec.append(sc.Piece("3680", "Black", tt, tp, tp + 1, frozenset(), {tp: tt},
                              (20.0 * (ti + 1), -8 * (tp + 1), 20.0 * (tj + 1)), None,
                              tp // 3, "turntable base"))
    rest = shelf_top - tt
    for run in sorted({frozenset(c for c in rest if c[0] == i) for i in {c[0] for c in rest}},
                      key=min):
        cells = sorted(run, key=lambda c: c[1])
        while cells:                                  # tiles along z, 1 x 2 then 1 x 1
            n = 2 if len(cells) >= 2 and cells[1][1] == cells[0][1] + 1 else 1
            t = sc.tile(cells[:n], tp + 1, "face", tp // 3)
            t.note = "throat tile"
            shelf_sec.append(t)
            cells = cells[n:]
    for k in ks:
        cells = S[k]
        above = S.get(k + 1, set())
        # caps on the exposed tops of this layer, in band k + 1 (not on the throat shelf)
        T = cells - above
        if 3 * (k + 1) == fh.SHELF_TOP:
            T -= shelf_top
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
        leg.step("Hind foot: a long 2 x 4 plate with rounded toes in front")
        leg.place("3020", "dark", (0, -8, -20), sc.rot(y=90))
        leg.place("15068", "dark", (0, -8, -40))
        level = 1
    else:
        # front paw: two 1x3 plates tied by the 2x2 plate above, a 1x2 cheese-slope toe row
        leg.step("Front paw: two 1 x 3 plates held together by a 2 x 2 plate")
        leg.place("3623", "dark", (-10, -8, -10), sc.rot(y=90))
        leg.place("3623", "dark", (10, -8, -10), sc.rot(y=90))
        leg.place("3022", "dark", (0, -16, 0))
        level = 2
    leg.step("Toes and the leg" if not hind else "The leg")
    if not hind:
        leg.place("85984", "dark", (0, -8, -30))
    while level < top:
        if top - level >= 3:
            leg.place("3003", "dark", (0, -8 * (level + 3), 0))
            level += 3
        else:
            leg.place("3022", "dark", (0, -8 * (level + 1), 0))
            level += 1
    return leg


SOCKET_NOTES = {
    "eye socket": "the round plates with a bar are the eye mounts: turn each bar 45 degrees "
                  "outwards from straight ahead",
    "ear socket": "the round plates with a bar on top are the ear mounts: turn each bar 55 "
                  "degrees outwards",
    "nose socket": "the brick with two side studs will hold the nose",
    "tongue socket": "the brick with a side stud will hold the tongue",
    "whisker clip": "clip tiles for the whiskers",
    "tail socket": "the grey brick with four side studs faces backwards: the tail plugs in here",
}


def emit_planned(sub, pieces, key, label: str, unit: str, intro: str, cap_text: str,
                 upside_down: bool = False):
    """Plan the pieces into steps and place them with booklet captions.

    Courses are numbered in the order the builder meets them physically: from the bottom up,
    or from the top down for a sub-assembly built upside down. A step whose parts go on against
    that direction (pushed up from underneath, or onto the far side of an upside-down build)
    says so."""
    steps, stuck = sc.plan_steps(pieces, key)
    if stuck:
        print(f"[ferret] {sub.name}: {len(stuck)} piece(s) could not be planned, e.g. "
              f"{[(p.part, sorted(p.cells)[:2], p.p0) for p in stuck[:5]]}")
        steps.append(stuck)
    bands = sorted({p.band for p in pieces}, reverse=upside_down)
    number = {b: n + 1 for n, b in enumerate(bands)}
    total = Counter((st[0].band, st[0].note == "cap") for st in steps)
    seen = Counter()
    for n, st in enumerate(steps):
        b, cap = st[0].band, st[0].note == "cap"
        seen[(b, cap)] += 1
        text = f"{label}, {unit} {number[b]} of {len(bands)}"
        if cap:
            text += f": {cap_text}"
        if total[(b, cap)] > 1:
            text += f" ({seen[(b, cap)]}/{total[(b, cap)]})"
        against = [p for p in st if p.hang != upside_down]
        if against:
            where = "these parts go" if len(against) == len(st) else "some of these parts go"
            text += (f"; {where} on the underside of the course above: push them up into it"
                     if not upside_down else
                     f"; {where} on the far side (the top of the {label.lower()})")
        notes = [SOCKET_NOTES[p.note] for p in st if p.note in SOCKET_NOTES]
        if notes:
            text += "; " + "; ".join(dict.fromkeys(notes))
        if n == 0:
            text = f"{intro}. {text}"
        sub.step(text)
        for p in st:
            sub.place(p.part, p.role, p.pos, p.rot, note=p.note)


# ------------------------------------------------------------------------------------------
# head

def attach(parent: sc.Piece, local_pos, local_rot=None):
    """World (pos, rot) of a part fixed to `parent` at a position in the parent's frame."""
    W = transform(parent.pos, parent.rot) @ transform(local_pos, local_rot)
    return tuple(W[:3, 3]), W[:3, :3]


def build_head(model, av: Avail):
    pieces, n_clusters, _ = fh.pieces(lambda r: av.sizes(sc.PLATE, r))
    if n_clusters > 1:
        print(f"[ferret] head: packed into {n_clusters} separate clusters")
    for p in pieces:                        # the head's own frame is centred on its pivot
        p.pos = (p.pos[0], p.pos[1], p.pos[2] - fh.PIVOT_Z)
    head = model.submodel("head", "Head")
    emit_planned(head, pieces, lambda p: (p.p0, min(c[1] for c in p.cells), min(p.cells)),
                 "Head", "layer", "Build the head on the grey turntable top, one plate layer "
                 "at a time: the jaw hangs below it at the front",
                 "slopes and tiles round it off")
    nose = next(p for p in pieces if p.note == "nose socket")
    for kind, caption, role in (("eye", "Big shiny eyes", "eye"), ("ear", "Round ears", "face")):
        head.step(caption)
        for p in (q for q in pieces if q.note == f"{kind} socket"):
            pos, R = attach(p, *fh.dish_local())
            side = "r" if min(p.cells)[0] < 0 else "l"
            head.place("4740", role, pos, R, tag=f"{kind}_{side}")
            if kind == "ear":
                # the pink inner ear: a round tile on the dish's centre stud
                dish = transform(pos, R)
                W = dish @ transform((0, -8, 0))
                head.place("98138", "ear_inner", tuple(W[:3, 3]), W[:3, :3],
                           tag=f"inner_ear_{side}")
    head.step("The nose and the tip of the tongue")
    pos, R = attach(nose, (0, 10, -18), rot(x=90))
    head.place("1748", "nose", pos, R, tag="nose")
    tongue = next(p for p in pieces if p.note == "tongue socket")
    pos, R = attach(tongue, (0, 10, -18), rot(x=90))
    head.place("24246", "tongue", pos, R, tag="tongue")
    head.step("Whiskers")
    for p in (q for q in pieces if q.note == "whisker clip"):
        # the clip holds a bar along X, 6 LDU above the tile; the bar runs outwards from it
        cx, cy, cz = p.pos[0], p.pos[1] - 6, p.pos[2]
        out = -1 if cx < 0 else 1
        x0 = cx - 56 if out < 0 else cx - 4
        side = "r" if out < 0 else "l"
        head.place("87994", "whisker", (x0, cy, cz), rot(z=-90), tag=f"whisker_{side}")
    return head


def build_tail(model, av: Avail):
    pieces, n_clusters = ft.pieces(lambda r: av.sizes(sc.BRICK, r) if r != "plate" else [])
    if n_clusters > 1:
        print(f"[ferret] tail: packed into {n_clusters} separate clusters")
    tail = model.submodel("tail", "Tail")
    emit_planned(tail, pieces, lambda p: (p.p0, min(p.cells)), "Tail", "slice",
                 "Build the tail standing up, from its root to the tip",
                 "curved slopes taper it")
    return tail


# ------------------------------------------------------------------------------------------

def build(model):
    av = Avail(model.catalog)
    S, secs = sculpt_pieces(av)

    subs = {}
    for name, title, key, label, intro in (
            ("chest", "Chest and front legs",
             lambda p: (-p.band, p.p0, min(c[1] for c in p.cells), min(p.cells)),
             "Chest", "Build the chest upside down: course 1 is the top of the chest, each "
                      "further course goes on underneath, down to the shoulders"),
            ("hips", "Hips and hind legs",
             lambda p: (-p.band, p.p0, -max(c[1] for c in p.cells), min(p.cells)),
             "Hips", "Build the hips upside down: course 1 is the top of the hips, each further "
                     "course goes on underneath, down to the thighs"),
            ("back", "Arched back, neck and rump",
             lambda p: (p.band, p.p0, min(c[1] for c in p.cells), min(p.cells)),
             "Back", "Build the arched back from the bottom up: the lowest courses are the "
                     "belly under the arch and the underside of the neck and rump")):
        sub = model.submodel(name, title)
        emit_planned(sub, secs[name], key, label, "course", intro,
                     "curved slopes round off the edges", upside_down=(name != "back"))
        subs[name] = sub

    fl = build_leg(model, "front_leg", "Front leg", leg_top(S, FRONT_LEG), hind=False)
    hl = build_leg(model, "hind_leg", "Hind leg", leg_top(S, HIND_LEG), hind=True)
    for sub, leg, sockets, tag in ((subs["chest"], fl, FRONT_LEG, "front"),
                                   (subs["hips"], hl, HIND_LEG, "hind")):
        for n, (i0, j0) in enumerate(sockets):
            sub.step(f"Turn the {'chest' if tag == 'front' else 'hips'} over and push "
                     f"{'a' if n == 0 else 'the second'} {tag} leg into the socket underneath")
            side = "l" if i0 > 0 else "r"
            sub.use(leg, (sc.STUD * (i0 + 1), 0, sc.STUD * (j0 + 1)), tag=f"{tag}_leg_{side}")

    head = build_head(model, av)
    tail = build_tail(model, av)

    main = model.main
    main.step("Stand the chest on its front legs")
    main.use(subs["chest"], tag="chest")
    main.step("Stand the hips on their hind legs behind it, then lower the arched back onto "
              "both")
    main.use(subs["back"], tag="back")
    main.use(subs["hips"], tag="hips")
    main.step(f"Set the head on the turntable in the white throat and turn it "
              f"{fh.TURN:.0f} degrees to look at you: it can be turned "
              f"{-fh.TURN_RANGE[0]:.0f} degrees the other way or {fh.TURN_RANGE[1]:.0f} this way")
    main.use(head, (0, 0, fh.PIVOT_Z), rot(y=fh.TURN), tag="head")

    # posable head: sweep it through its range on the turntable
    def pose(t: float) -> dict:
        a = fh.TURN_RANGE[0] + t * (fh.TURN_RANGE[1] - fh.TURN_RANGE[0])
        return {"head": translate(0, 0, fh.PIVOT_Z) @ transform((0, 0, 0), rot(y=a - fh.TURN))
                @ translate(0, 0, -fh.PIVOT_Z)}
    model.moving_group("head", "head")
    model.pose = pose
    main.step("Plug the tail onto the four side studs at the rump")
    F = ft.frame()
    main.use(tail, tuple(F[:3, 3]), F[:3, :3], tag="tail")
