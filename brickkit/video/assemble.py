"""How a model really goes together, piece by piece, for the Quick Bricks videos
(video/quick.py): nothing passes through anything, nothing hangs in the air.

    script = assemble(engine, model, placed, seq)     # what happens, in order (no timing)
    path = route(world, movers, start, turn, axis, travel, ...)   # one piece's way in

**The script.** The pieces go on in instruction order (a bought kit - a minifigure's legs, its
torso with its arms - is one piece). For each, the way in is found by sweeping its mesh out
from its place against what is already built (the collision engine of the checks): its
insertion hint, then the axes of its connections (studs straight on, a pin or bar slid in), a
clip or hinge pushed on across its bar (its jaws may touch the bar the last FLEX: they flex),
then its own top, up, the sides and from underneath. What is built stands on the table on its
lowest point: a piece that reaches lower lifts it first, and a piece that goes on from
underneath and becomes what it stands on slides in under it on the table while it is held up -
then it is set down on the piece ("under"). A sub-assembly is built in place when every piece
of it can go on there, supported and with a clear way in; if not it is built beside the model
(staged: upright in its own frame, clear of the model's footprint and of `keep_out`) and then
joined as one. A piece that cannot go on yet waits for the others of its step; one that still
cannot is put on the best way there is (`forced`, and a warning).

**A route.** From where a piece starts (off the frame, lying on the table, where its unit was
built) it rises, crosses at the lowest height that is clear, comes down at a gate in line with
its way in and runs straight in the last `travel`; corners rounded as far as stays clear.
Every sample of it is tested against everything on the table and the table itself."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..checks.base import press_links
from ..model.builder import Placement
from ..snaps.match import find_connections

SNAP = ("clip", "hinge", "pin", "ball", "gen")   # they flex as they go on
CROSS = ("clip", "hinge")     # pushed on across their axis (as well as slid along it)
FLEX = 8.0        # LDU: this far out a snap may still touch what it snaps onto
TRAVEL = 24.0     # LDU: the least clear run of a way in (as checks/buildability)
RUN = (12.0, 1.2, 6.0)    # the straight run in: at least, x the piece's size that way, plus
TOL = 0.6         # LDU: "on the table"
MARGIN = 28.0     # LDU: a staged unit this clear of the model's footprint
UP = np.array([0.0, -1.0, 0.0])
DOWN = -UP


class Stuck(Exception):
    """A piece that cannot go on (yet)."""


def trans(v) -> np.ndarray:
    M = np.eye(4)
    M[:3, 3] = v
    return M


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-12)


_HULL: dict = {}


def hull(engine, part: str) -> np.ndarray:
    """A part's outermost points (its own frame)."""
    if part not in _HULL:
        from scipy.spatial import ConvexHull, QhullError
        V = np.unique(np.round(engine.geom.mesh(part).tris.reshape(-1, 3), 3), axis=0)
        try:
            V = V[ConvexHull(V).vertices]
        except (QhullError, ValueError):
            pass
        _HULL[part] = V
    return _HULL[part]


def low(engine, part: str, M) -> float:
    """The lowest point (largest y: -Y is up) of a part at M."""
    return float((hull(engine, part) @ M[:3, :3].T)[:, 1].max() + M[1, 3])


@dataclass
class Item:
    kind: str                 # "piece" | "join" (a sub-assembly built beside the model)
    parts: list               # what moves, as one
    axis: np.ndarray          # the way it comes from as it goes on (world, unit)
    travel: float             # its straight run in (LDU)
    mode: str                 # "press": it runs in | "under": what it joins is set down on it
    seat: dict                # part -> 4 x 4: where it is as it lands
    rest: dict                # part -> 4 x 4: and once what it is on stands on the table again
    source: dict | None       # join: part -> 4 x 4, where the unit stood
    carry: dict               # part -> (before, during, after): what is built, lifted for it
    still: list               # [(part, 4 x 4)]: everything else on the table meanwhile
    snaps: list = field(default_factory=list)   # parts it snaps onto
    way: str = ""             # which candidate ("stud", "clip^", "hint", ...)
    forced: bool = False      # no clear way in was found


def links(engine, model, placed) -> dict:
    """part -> [(other, kind, axis, origin)]: its connections (its own connector's axis and
    origin in the world; None for a press fit)."""
    wc = [[c.transformed(p.M) for c in engine.shadow.connectors(p.part)] for p in placed]
    out: dict = {}
    for c in find_connections(wc) + press_links(model, engine.press_collide, placed):
        for a, b, ca in ((c.a, c.b, c.ca), (c.b, c.a, c.cb)):
            out.setdefault(a, []).append(
                (b, c.kind, None if ca is None else np.asarray(ca.axis, float),
                 None if ca is None else np.asarray(ca.origin, float)))
    return out


def structure(model, placed, seq) -> dict:
    """The model as pieces and units. {bodies: [[part, ...]] in order (a kit's parts
    together), hint: per body (world) or None, unit_of: per part, its unit's path (the indices
    of the sub-assemblies' uses down from the main model), uses: path -> {parent, W, insert,
    name}, children: path -> [("body", k) | ("unit", path)] in order, under: path -> every
    part in it}."""
    unit_of = [None] * len(placed)
    hint = [None] * len(placed)
    uses = {(): {"parent": None, "W": np.eye(4), "insert": None, "name": model.main.name}}
    n = [0]

    def walk(sub, W, path, kit):
        for k, it in enumerate(sub.items):
            if isinstance(it, Placement):
                unit_of[n[0]] = path
                if kit is not None:
                    hint[n[0]] = kit
                elif it.insert is not None:
                    hint[n[0]] = W[:3, :3] @ np.asarray(it.insert, float)
                n[0] += 1
                continue
            ins = None if it.insert is None else W[:3, :3] @ np.asarray(it.insert, float)
            if kit is not None or it.sub.kit is not None:      # bought assembled: one piece
                walk(it.sub, W @ it.M, path, kit if kit is not None else (ins if ins is not None else False))
            else:
                uses[path + (k,)] = {"parent": path, "W": W @ it.M, "insert": ins,
                                     "name": it.sub.name}
                walk(it.sub, W @ it.M, path + (k,), None)

    walk(model.main, np.eye(4), (), None)
    assert n[0] == len(placed)
    bodies, by_kit = [], {}
    for i in seq:
        k = placed[i].kit
        if k is not None and k in by_kit:
            bodies[by_kit[k]].append(i)
            continue
        if k is not None:
            by_kit[k] = len(bodies)
        bodies.append([i])
    children = {p: [] for p in uses}
    under = {p: [] for p in uses}
    seen = set()
    for b, parts in enumerate(bodies):
        path = unit_of[parts[0]]
        for depth in range(1, len(path) + 1):
            if path[:depth] not in seen:
                seen.add(path[:depth])
                children[path[:depth - 1]].append(("unit", path[:depth]))
        children[path].append(("body", b))
        for depth in range(len(path) + 1):
            under[path[:depth]] += parts
    hints = []
    for parts in bodies:
        h = hint[parts[0]]
        hints.append(None if h is None or h is False else unit(h))
    return {"bodies": bodies, "hint": hints, "unit_of": unit_of, "uses": uses,
            "children": children, "under": under}


class Assembler:
    def __init__(self, engine, model, placed, seq, keep_out=(), front: float = 0.0, log=None):
        self.e, self.col, self.placed = engine, engine.collide, placed
        self.M = [np.asarray(p.M, float) for p in placed]
        self.boxf = self.col.aabbs([(p.part, M) for p, M in zip(placed, self.M)])
        allp = self.boxf.reshape(-1, 3)
        self.lo, self.hi = allp.min(0), allp.max(0)
        self.ground = float(max(low(engine, p.part, M) for p, M in zip(placed, self.M)))
        self.link = links(engine, model, placed)
        self.s = structure(model, placed, seq)
        self.keep_out = [np.asarray(b, float) for b in keep_out]     # [[x0, z0], [x1, z1]]
        self.front = front
        self.log = log or (lambda m: None)
        self.base = {(): np.eye(4)}       # table unit -> where it is built (the main: in place)
        self.D = {(): np.eye(4)}          # ... and where it stands now (rested on the table)
        self.members = {(): []}
        self.lowb = {(): -1e9}            # ... its lowest point, in `base`
        self.spots: dict = {}             # staged unit -> its footprint [[x0, z0], [x1, z1]]
        self.items: list[Item] = []
        self.warnings: list[str] = []
        self.dry = False

    # ------------------------------------------------------------------ state
    def clone(self) -> "Assembler":
        c = object.__new__(Assembler)
        c.__dict__.update(self.__dict__)
        c.base, c.D = dict(self.base), dict(self.D)
        c.members = {k: list(v) for k, v in self.members.items()}
        c.lowb, c.spots = dict(self.lowb), dict(self.spots)
        c.items, c.warnings, c.dry = [], [], True
        return c

    def lowest(self, parts, D) -> float:
        return max(low(self.e, self.placed[i].part, D @ self.M[i]) for i in parts)

    def rested(self, u, parts) -> tuple[np.ndarray, float]:
        """Where table unit `u` stands with these parts added (its base moved straight up or
        down so its lowest point is on the table), and that lowest point in its base."""
        lowest = max(self.lowb[u], self.lowest(parts, self.base[u]))
        return trans([0.0, self.ground - lowest, 0.0]) @ self.base[u], lowest

    def name(self, parts) -> str:
        p = self.placed[parts[0]]
        tag = "/".join(p.tags)
        return f"{p.part[:-4]}{' (' + tag + ')' if tag else ''}" + (f" +{len(parts) - 1}" if len(parts) > 1 else "")

    # ------------------------------------------------------------------ ways in
    def sweep(self, parts, d, travel: float, S, boxes, snaps: set, reach: float = FLEX) -> tuple[int, int]:
        """(hard hits, flexing hits) of the piece moved out along d, a LDU at a time: against
        what is built (S), a snap's own partner within `reach` counted apart."""
        hard = flex = 0
        for k in np.arange(1.0, travel + 1e-6, 1.0):
            Tm = trans(d * k)
            h = f = False
            for i in parts:
                part, M = self.placed[i].part, Tm @ self.M[i]
                for j in self.col._candidates(self.col.world_aabb(part, M), boxes):
                    j = int(j)
                    if not self.col.collide_pair(part, M, self.placed[S[j]].part, self.M[S[j]]):
                        continue
                    if S[j] in snaps and k <= reach:
                        f = True
                    else:
                        h = True
                        break
                if h:
                    break
            hard += h
            flex += f
            if hard > 3:                               # (no need to know how bad)
                return 99, flex
        return hard, flex

    def ways(self, parts, S, hint, Ru) -> tuple[list, list]:
        """Ways in for a piece, best first: [(hard, rank, tie, label, d, travel, snaps)] in
        the model's own frame (d: where it comes from), and the built parts it connects to.
        `Ru`: how the unit it joins stands (to tell up from down)."""
        inS, mine = set(S), set(parts)
        boxes = self.boxf[S]
        pts = np.concatenate([self.boxf[i] for i in parts])
        cen = (pts.min(0) + pts.max(0)) / 2
        ext = pts.max(0) - pts.min(0)
        up = Ru.T @ UP
        partners, cands = set(), []
        if hint is not None:
            cands.append((0, "hint", unit(hint), set()))
        votes: dict = {}
        for i in parts:
            for j, kind, axis, org in self.link.get(i, ()):
                if j not in inS or j in mine:
                    continue
                partners.add(j)
                if axis is None:
                    continue
                a = unit(axis)
                other = (self.boxf[j][0] + self.boxf[j][1]) / 2      # it comes from its own side
                nat = a if float((cen - other) @ a) >= 0 else -a      # of what it goes onto
                snap = {j} if kind in SNAP else set()
                if kind in CROSS:
                    u = unit(np.cross(a, [0, 1, 0] if abs(a[1]) < 0.9 else [1, 0, 0]))
                    v = np.cross(a, u)
                    for t in range(8):
                        cands.append((2, kind + "^", u * math.cos(t * math.pi / 4) + v * math.sin(t * math.pi / 4), snap))
                    cands += [(3, kind, nat, snap), (4, kind + "'", -nat, snap)]
                else:
                    key = tuple(np.round(nat, 2))
                    votes[key] = votes.get(key, 0) + 1
                    cands += [(1, kind, nat, snap), (4, kind + "'", -nat, snap)]
        R = self.M[parts[0]][:3, :3]
        cands += [(5, "top", R @ UP, set()), (6, "up", up, set())]
        side = [unit(np.cross(up, v)) for v in ((1, 0, 0), (0, 0, 1)) if np.linalg.norm(np.cross(up, v)) > 0.5]
        h = unit((cen - (self.lo + self.hi) / 2) - up * float((cen - (self.lo + self.hi) / 2) @ up))
        cands += [(7, "side", v, set()) for v in ([h] if np.linalg.norm(h) > 0.5 else [])
                  + [s * q for q in side for s in (1, -1)]]
        cands += [(8, "under", -up, set())]
        if not partners:                               # it only stands by it: set down from above
            cands = [(0 if label == "hint" else 1 if label == "up" else rank + 2, label, d, snap)
                     for rank, label, d, snap in cands]
        snaps_all = {j for i in parts for j, kind, _, _ in self.link.get(i, ()) if kind in SNAP and j in inS}
        out, seen = [], set()
        for rank, label, d, snap in cands:
            key = (tuple(np.round(d, 3)), bool(snap))
            if key in seen:
                continue
            seen.add(key)
            run = min(TRAVEL * 2, max(RUN[0], RUN[1] * float(np.abs(ext) @ np.abs(d)) + RUN[2]))
            if rank == 2 or float(d @ up) < -0.7:      # pushed on across a bar, or up from
                run = RUN[0] + (2.0 if rank == 2 else 0.0)            # underneath: a short run
            if not snap and rank in (2, 3, 4):
                snap = snaps_all
            # pushed on across its bar a clip only flexes the last FLEX; slid along its own
            # axis (a pin in its hole, a clip along its bar) a snap never blocks itself
            hard, flex = self.sweep(parts, d, max(TRAVEL, run), S, boxes, snap, FLEX if rank == 2 else 1e9)
            if rank == 2 and flex > FLEX - 2:          # through the back of the clip, not its mouth
                hard = max(hard, 1)
            tie = (flex if rank == 2 else -votes.get(tuple(np.round(d, 2)), 0), -round(float(d @ up), 2))
            out.append((hard, rank, tie, label, d, run, snap))
        out.sort(key=lambda c: c[:3])
        return out, sorted(partners)

    # ------------------------------------------------------------------ putting a piece on
    def put(self, u, parts, hint, source=None, kind="piece", force=False) -> None:
        """One piece (or a staged unit) onto table unit `u`: its way in, what must be lifted
        for it; the item, and the table afterwards. Stuck if it cannot go on."""
        S, D0 = self.members[u], self.D[u]
        Ru = D0[:3, :3]
        forced = False
        if not S:
            label, d, run, snaps = "table", Ru.T @ UP, RUN[0], set()
            if hint is not None and float((Ru @ unit(hint)) @ UP) > 0.3:
                d = unit(hint)
        else:
            cands, partners = self.ways(parts, S, hint, Ru)
            standing = abs(self.lowest(parts, D0) - self.ground) < TOL     # on the table by it
            if not (partners or standing) and not force:
                raise Stuck(f"{self.name(parts)}: nothing to hold it yet")
            hard, _, _, label, d, run, snaps = cands[0]
            if hard:
                if not force:
                    raise Stuck(f"{self.name(parts)}: no clear way in")
                forced = True
        dw = unit(Ru @ d)
        D1, lowest = self.rested(u, parts)
        mode, Dd = "press", D1
        if S and float(dw @ DOWN) > 0.7:
            if self.lowest(parts, D1) > self.ground - TOL:     # it is what the unit will stand on
                mode, Dd = "under", trans(UP * run) @ D1
            else:                                              # room under it for the run in?
                need = max(self.lowest([i], trans(dw * run) @ D1) for i in parts) - self.ground + 1.0
                Dd = trans(UP * max(0.0, need)) @ D1
        seat = {i: (D1 if mode == "under" else Dd) @ self.M[i] for i in parts}
        rest = {i: D1 @ self.M[i] for i in parts}
        carry = {}
        if S and not (np.allclose(D0, Dd, atol=1e-6) and np.allclose(Dd, D1, atol=1e-6)):
            carry = {j: (D0 @ self.M[j], Dd @ self.M[j], D1 @ self.M[j]) for j in S}
        mine = set(parts)
        still = [(j, self.D[t] @ self.M[j]) for t, mem in self.members.items() if t != u
                 for j in mem if j not in mine]
        if not carry:                                  # (what it goes onto: carried, or still)
            still += [(j, D1 @ self.M[j]) for j in S]
        if forced:
            self.warnings.append(f"{self.name(parts)}: no clear way in was found (it goes on from "
                                 f"{np.round(dw, 2).tolist()})")
        self.items.append(Item(kind, list(parts), dw, float(run), mode, seat, rest, source, carry,
                               still, sorted(snaps), label, forced))
        self.members[u] = S + list(parts)
        self.D[u], self.lowb[u] = D1, lowest

    # ------------------------------------------------------------------ units
    def stage(self, path) -> None:
        """A place on the table to build a sub-assembly: upright in its own frame, clear of
        the model's footprint, of `keep_out` and of whatever else is being built beside it;
        on the side of the model it will go on, if there is room there."""
        use = self.s["uses"][path]
        parts = self.s["under"][path]
        pts = np.concatenate([self.boxf[i] for i in parts])
        c0 = (pts.min(0) + pts.max(0)) / 2
        R = use["W"][:3, :3].T
        if abs(np.linalg.det(R) - 1) > 1e-6 or np.allclose(R, np.eye(3), atol=1e-6):
            R = np.eye(3)
        turn = np.eye(4)
        turn[:3, :3] = R
        turn[:3, 3] = c0 - R @ c0                      # about its middle
        q = np.concatenate([np.array([[x, y, z] for x in (b[0, 0], b[1, 0]) for y in (b[0, 1], b[1, 1])
                                      for z in (b[0, 2], b[1, 2])]) for b in (self.boxf[i] for i in parts)])
        q = q @ R.T + turn[:3, 3]
        half = (q.max(0) - q.min(0))[[0, 2]] / 2
        mid = (self.lo + self.hi) / 2
        mh = (self.hi - self.lo)[[0, 2]] / 2
        v = (c0 - mid)[[0, 2]]
        a0 = math.atan2(v[1], v[0]) if np.linalg.norm(v) > 0.2 * max(mh) else 0.0
        busy = self.keep_out + list(self.spots.values())
        best = None
        for da in (0, 35, -35, 70, -70, 105, -105, 140, -140, 180):
            h = np.array([math.cos(a0 + math.radians(da)), math.sin(a0 + math.radians(da))])
            for more in (0.0, 30.0, 60.0, 120.0):
                dist = min((mh[k] + half[k] + MARGIN) / max(abs(h[k]), 1e-6) for k in (0, 1)) + more
                c = mid[[0, 2]] + h * dist
                box = np.array([c - half, c + half])
                if all(np.any(box[1] + MARGIN / 2 <= b[0]) or np.any(box[0] - MARGIN / 2 >= b[1]) for b in busy):
                    best = (c, box)
                    break
            if best:
                break
        if best is None:
            best = (mid[[0, 2]] + np.array([math.cos(a0), math.sin(a0)]) * (max(mh) + max(half) + MARGIN) * 2, None)
        c, box = best
        qc = (q.min(0) + q.max(0)) / 2
        base = trans([c[0] - qc[0], 0.0, c[1] - qc[2]]) @ turn
        self.base[path], self.D[path], self.members[path], self.lowb[path] = base, base.copy(), [], -1e9
        if box is not None:
            self.spots[path] = box

    def unit(self, path, u) -> None:
        """A sub-assembly: straight onto `u` if nothing is there yet or if every piece of it
        can go on in place; else built beside the model and joined."""
        if self.members[u]:
            trial = self.clone()
            try:
                trial.build(path, u)
                ok = True
            except Stuck:
                ok = False
        else:
            ok = True
        if ok:
            self.build(path, u)
            return
        self.stage(path)
        self.build(path, path)
        parts = self.members.pop(path)
        D = self.D.pop(path)
        self.base.pop(path)
        self.lowb.pop(path)
        self.spots.pop(path, None)
        self.put(u, parts, self.s["uses"][path]["insert"], source={i: D @ self.M[i] for i in parts},
                 kind="join", force=not self.dry)

    def build(self, path, u) -> None:
        """Everything of sub-assembly `path`, in order, onto table unit `u`."""
        bodies, hints = self.s["bodies"], self.s["hint"]
        kids = self.s["children"][path]
        step = lambda b: (self.placed[bodies[b][0]].owner, self.placed[bodies[b][0]].local_step)   # noqa: E731
        waiting: list[int] = []
        for n, (kind, x) in enumerate(kids):
            if kind == "unit":
                self.unit(x, u)
            else:
                waiting.append(x)
            again = True
            while again and waiting:
                again = False
                for b in list(waiting):
                    try:
                        self.put(u, bodies[b], hints[b])
                    except Stuck:
                        continue
                    waiting.remove(b)
                    again = True
            nxt = kids[n + 1] if n + 1 < len(kids) else None
            if waiting and (nxt is None or nxt[0] == "unit" or step(nxt[1]) != step(waiting[-1])):
                if self.dry:                           # the end of its step, and still not on
                    raise Stuck(self.name(bodies[waiting[0]]))
                for b in waiting:
                    self.put(u, bodies[b], hints[b], force=True)
                waiting = []


def assemble(engine, model, placed, seq, keep_out=(), front: float = 0.0, log=None) -> dict:
    """The build as it really goes: {items: [Item] in order, order: every part in the order
    it lands, landed: part -> 4 x 4 where it lands (not always where it ends up: its unit may
    be joined, or set down, later), axis: part -> the way it came in from, ground, warnings}."""
    a = Assembler(engine, model, placed, seq, keep_out, front, log)
    a.build((), ())
    order, landed, axis = [], {}, {}
    for it in a.items:
        if it.kind == "piece":
            order += it.parts
            for i in it.parts:
                landed[i], axis[i] = it.seat[i], it.axis
    assert sorted(order) == list(range(len(placed))), "a piece was lost or doubled"
    final = {}
    for it in a.items:
        final.update(it.rest)
        for j, (_, _, after) in it.carry.items():
            final[j] = after
    for i, M in enumerate(a.M):
        assert np.allclose(final[i], M, atol=1e-4), f"part {i} does not end in its place"
    for w in a.warnings:
        (log or print)(f"  quick: {w}")
    return {"items": a.items, "order": order, "landed": landed, "axis": axis,
            "ground": a.ground, "middle": (a.lo + a.hi) / 2, "warnings": a.warnings, "structure": a.s}


# ---------------------------------------------------------------------------- routes
class World:
    """What a moving piece may not touch: the parts on the table where they stand, and the
    table."""

    def __init__(self, engine, placed, still, ground: float):
        self.e, self.col, self.ground = engine, engine.collide, ground
        self.items = [(placed[i].part, np.asarray(M, float)) for i, M in still]
        self.boxes = self.col.aabbs(self.items)
        self.top = float(self.boxes[:, 0, 1].min()) if len(self.items) else ground

    def free(self, movers) -> bool:
        """movers: [(part, 4 x 4)]."""
        for part, M in movers:
            if low(self.e, part, M) > self.ground + 0.3:
                return False
            if self.items and self.col.hits(part, M, self.items, self.boxes):
                return False
        return True


def _slerp(R0, q: float) -> np.ndarray:
    """R0 turned back towards no turn at all: q = 1 is R0, q = 0 the identity."""
    if q <= 1e-9:
        return np.eye(3)
    if q >= 1 - 1e-9:
        return R0
    from scipy.spatial.transform import Rotation
    return Rotation.from_rotvec(Rotation.from_matrix(R0).as_rotvec() * q).as_matrix()


def poses(movers, c, p, R) -> list:
    """The movers [(part, seat 4 x 4)] as one, turned by R about their middle c and moved p."""
    X = np.eye(4)
    X[:3, :3] = R
    X[:3, 3] = c + p - R @ c
    return [(part, X @ M) for part, M in movers]


def _round(pts, radius, keep_last: float):
    """A polyline with its corners rounded (each by a quadratic curve reaching up to `radius`
    along its two sides, never more than 0.45 of a side, and into the last side no further
    than `keep_last` from its end): the points, 8 to a corner."""
    out = [pts[0]]
    for k in range(1, len(pts) - 1):
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        la, lc = np.linalg.norm(b - a), np.linalg.norm(c - b)
        ra = min(radius, 0.45 * la)
        rc = min(radius, 0.45 * lc)
        if k == len(pts) - 2:
            rc = min(rc, max(0.0, lc - keep_last))
        if min(ra, rc) < 0.5:
            out.append(b)
            continue
        p0, p2 = b + (a - b) / la * ra, b + (c - b) / lc * rc
        for t in np.linspace(0.0, 1.0, 9):
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t * t * p2)
    out.append(pts[-1])
    return out


def _dense(pts, step: float):
    """Points every `step` along a polyline, and how far along each is."""
    P, s = [np.asarray(pts[0], float)], [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L = float(np.linalg.norm(b - a))
        if L < 1e-9:
            continue
        for k in range(1, max(1, int(math.ceil(L / step))) + 1):
            P.append(a + (b - a) * min(1.0, k * step / L))
            s.append(s[-1] + float(np.linalg.norm(P[-1] - P[-2])))
    return np.array(P), np.array(s)


def route(world: World, movers, start, turn, ways, *, direct: bool = False, hop: float = 10.0,
          rounding: float = 45.0, step: float = 2.0, tilt=None) -> dict:
    """One piece's way in. movers: [(part, seat 4 x 4)] (they move as one); `start`: where
    their middle is at first, from where it is seated; `turn`: how they are turned then (3 x 3,
    about their middle; None: not at all); `ways`: [(axis, travel)] to try in turn - the way
    it comes from for its straight last run, and that run's length; `tilt` (axis, degrees): a
    tumble that straightens as it comes over; `direct`: it may come straight down to its gate
    (it starts up in the air, off the frame). It rises (turning upright once it is off the
    table), crosses at the lowest height that is clear, comes down at a gate - out along its
    axis, or off to a side of that - and runs straight in; from the table to a gate on the
    table (a piece that goes underneath) it just slides across, if the way is clear.
    Returns {p (n, 3): its middle from
    where it is seated, every `step` LDU; s (n,): how far along; q (n,): how much of its turn
    (or tumble) is left, 1..0; R(q): the turn for a q; c: its middle, seated; run: s where the
    straight run in starts; axis, travel; clear: False if no clear way was found}."""
    pts = np.concatenate([world.col.world_aabb(part, M) for part, M in movers])
    c = (pts.min(0) + pts.max(0)) / 2
    r = float(np.linalg.norm(pts.max(0) - pts.min(0))) / 2
    start = np.asarray(start, float)
    R0 = np.eye(3) if turn is None else np.asarray(turn, float)
    if tilt is not None:
        from scipy.spatial.transform import Rotation
        R0 = Rotation.from_rotvec(unit(tilt[0]) * math.radians(tilt[1])).as_matrix()
    turning = not np.allclose(R0, np.eye(3), atol=1e-6)
    top = world.top - c[1] - r - 8.0                   # (as p.y) over everything on the table
    spin = lambda x: _slerp(R0, float(x)) if turning else np.eye(3)     # noqa: E731

    def build(axis, travel, gate, cruise, radius, lift_off):
        pre = axis * travel
        if cruise is None:                             # straight to the gate
            line, marks = [start, gate, pre, np.zeros(3)], (start, gate)
        else:
            line = [start, np.array([start[0], cruise, start[2]]), np.array([gate[0], cruise, gate[2]]),
                    gate, pre, np.zeros(3)]
            marks = (line[1], line[2])                 # off the table; over the gate
        keep = [line[0]]
        for v in line[1:]:
            if np.linalg.norm(v - keep[-1]) > 1e-6:
                keep.append(v)
        straight = min(travel, max(0.6 * travel, FLEX + 1.0))       # of the run in, never rounded
        P, s = _dense(_round(keep, radius, straight) if radius > 0 else keep, step)
        run = float(s[-1] - travel)
        near = lambda v: float(s[int(np.argmin(np.linalg.norm(P - v, axis=1)))])   # noqa: E731
        s0 = 0.0 if tilt is not None else min(near(marks[0]), lift_off)
        s1 = max(s0 + 1.0, min(near(marks[1]), run))
        q = 1.0 - np.clip((s - s0) / (s1 - s0), 0, 1)
        q = q * q if tilt is not None else q * q * (3 - 2 * q)
        return {"p": P, "s": s, "q": q, "run": run, "sure": float(s[-1] - straight), "axis": axis,
                "travel": float(travel)}

    def checked(path):                                 # (the last of the run in is the sweep's)
        n = int(np.searchsorted(path["s"], path["sure"])) + 1
        return all(world.free(poses(movers, c, p, spin(x))) for p, x in zip(path["p"][:n], path["q"][:n]))

    first = None
    middle = world.boxes.reshape(-1, 3).mean(0) if len(world.items) else c
    for lift_off in ((14.0, 40.0, 90.0) if turning and tilt is None else (0.0,)):
        for axis, travel in ways:
            axis = unit(axis)
            pre = axis * travel
            flat = [unit(v) for v in (axis * [1, 0, 1], (c - middle) * [1, 0, 1], [1, 0, 0], [-1, 0, 0],
                                      [0, 0, 1], [0, 0, -1]) if np.linalg.norm(np.asarray(v, float)) > 1e-6]
            gates = [pre + axis * m for m in (0.0, 16.0, 32.0, 64.0, 120.0)]
            gates += [pre + h * m for m in (24.0, 48.0, 96.0, 160.0) for h in flat]
            for gate in gates:
                highest = min(start[1], gate[1])
                over = min(top, highest - hop)
                heights = ([None] if direct and start[1] < gate[1] - hop else []) + [
                    v for v in dict.fromkeys(round(v, 3) for v in (highest - hop, (highest - hop + over) / 2, over, over - 40.0))
                    if v <= highest + 1e-6]
                if abs(start[1] - gate[1]) < 0.5 and float((R0 @ UP) @ UP) > 0.999:
                    heights = [None] + heights         # (level with it, and upright: slid across)
                for cruise in heights:
                    path = build(axis, travel, gate, cruise, 0.0, lift_off)
                    if first is None:
                        first = path
                    if not checked(path):
                        continue
                    for radius in (rounding, rounding / 2, rounding / 4):
                        smooth = build(axis, travel, gate, cruise, radius, lift_off)
                        if checked(smooth):
                            path = smooth
                            break
                    path.update(clear=True, R=spin, c=c)
                    return path
    if tilt is not None:                               # (once more, without the tumble)
        return route(world, movers, start, turn, ways, direct=direct, hop=hop, rounding=rounding, step=step)
    first.update(clear=False, R=spin, c=c)
    return first
