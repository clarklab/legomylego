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
    buy: object = None            # bought as this (a minifig Component), not as `part`


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
    buy: object = None       # what it is bought as (a minifig Component), if not itself
    buy_lead: bool = False   # the one part of a bought kit that counts it on the parts lists
    kit: int | None = None   # which bought kit (one per use of a kit sub-assembly) it is in

    @property
    def tag_path(self) -> str:
        return "/".join(self.tags)


def _ends(path: str, tail: str) -> bool:
    return path == tail or path.endswith("/" + tail)


class Submodel:
    def __init__(self, model: "Model", name: str, title: str = ""):
        self.model = model
        self.name = name
        self.title = title or name.replace("_", " ").capitalize()
        self.items: list[Placement | Use] = []
        self.captions: list[str] = [""]
        self.views: dict[int, str] = {}     # step -> "above" | "below" (booklet camera)
        self.kit = None     # a Component: bought assembled (a minifig torso), not built
        self.fits: list[tuple[str, str]] = []   # placement tags that fit snugly (hair, head)

    @property
    def current_step(self) -> int:
        return len(self.captions) - 1

    @property
    def n_steps(self) -> int:
        return len(self.captions)

    def step(self, caption: str = "", view: str | None = None) -> int:
        """Start a new step (reuses the current one if it is still empty). `view` tells the
        booklet to look from "above" or "below" (default: decided automatically)."""
        if any(it.step == self.current_step for it in self.items):
            self.captions.append(caption)
        elif caption:
            self.captions[-1] = caption
        if view:
            self.views[self.current_step] = view
        return self.current_step

    def place(self, part: str, color, pos=(0, 0, 0), rot=None, *, tag: str = "",
              note: str = "", insert=None, buy=None) -> Placement:
        """`buy`: what this part is bought as when that isn't the LDraw part itself (a minifig
        head's print as sold; see Model.minifig)."""
        p = Placement(self.model.canonical(part), self.model.resolve_color(color), transform(pos, rot),
                      self.current_step, tag, note, insert, buy)
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
        self.group_exclude: dict[str, set] = {}          # catch-all group -> excluded tags
        self.contacts: list[tuple[str, str, str]] = []   # allowed touching tag pairs
        self.fits: list[tuple[str, str]] = []            # tag paths that fit snugly (minifigs)
        self.captive_tags: dict[str, str] = {}           # tag -> why it's held without studs
        self.pose: Callable[[float], dict] | None = None  # t in [0,1] -> {group: 4x4 world}
        self.gear_pairs: list[tuple[str, str, str]] = []  # (tag path a, tag path b, kind)
        self.lights: list[dict] = []
        self.cables: list[dict] = []
        self.extras: list[tuple[str, Color, int, str]] = []   # bought, not placed in 3D
        self.hardware_items: list[dict] = []             # non-LEGO items, not placed in 3D
        self.press_fits: dict[str, dict] = {}            # tag -> {note, reach}
        self.lift_offs: set[str] = set()                 # groups that come away in the pose
        self.extra_checks: list[Callable] = []           # fn(ctx) -> list of issue dicts
        self.glow_tags: dict[str, float] = {}
        self.minifigs: list = []                         # Minifig records (model/minifig.py)
        self.variant: str | None = None
        self.meta: dict = {}

    def submodel(self, name: str, title: str = "") -> Submodel:
        if name in self.submodels:
            raise ValueError(f"submodel {name!r} already exists")
        s = Submodel(self, name, title)
        self.submodels[name] = s
        return s

    def minifig(self, name: str, at=(0, 0, 0), rot=None, *, head, torso, legs, hair=None,
                hat=None, accessory=None, pose=None, parent: "Submodel | None" = None,
                title: str = "", tag: str | None = None, insert=None):
        """Stand a minifigure at `at` (the plate top between the two studs its feet go on) in
        `parent` (default the main model), built in its own section (legs, torso, head,
        headwear, accessory). `head`, `torso`, `legs`: what is bought - a Rebrickable number
        ("973c01h01pr9741"), or an LDraw file or BrickLink number that LDraw's headers
        cross-reference, alone (its usual colour) or as (number, colour); the colour is the
        element's (the torso's, the hips'). Arm, hand and leg colours come from the number.
        `hair` / `hat`: (part, colour), on the head. `accessory`: (part, colour) or a dict /
        Held (hand, grip, spin, flip), or a list of them, held in a hand's clip by its bar.
        `pose`: a Pose or dict (head, arm_r, arm_l, hand_r, hand_l, leg_r, leg_l degrees).
        Prints LDraw has no model of are drawn plain in their colours (`stand_in`), and the
        parts lists name the real printed part. Returns the Minifig record."""
        from .minifig import build_minifig
        return build_minifig(self, name, at, rot, head=head, torso=torso, legs=legs, hair=hair,
                             hat=hat, accessory=accessory, pose=pose, parent=parent,
                             title=title, tag=tag, insert=insert)

    def canonical(self, part: str) -> str:
        return self.catalog.canonical(part) if self.catalog is not None else normalize(part)

    def resolve_color(self, key) -> Color:
        if isinstance(key, Color):
            return key
        return self.catalog.color(self.palette.get(key, key))

    # mechanisms and electrics -------------------------------------------------
    def moving_group(self, name: str, tag: str, exclude=(), lifts_off: bool = False) -> None:
        """Parts tagged `tag` move together under pose[name]. tag "*" makes a catch-all group:
        every part not in another group and not under any of the `exclude` tags (e.g. a whole
        body that slides on a fixed stand). `lifts_off`: the pose lifts the group away from the
        rest (a lid, a tower top): the mechanism check lets it come apart from the model, as
        long as it stays one piece itself and hits nothing on the way."""
        self.groups[name] = tag
        if tag == "*":
            self.group_exclude[name] = set(exclude)
        if lifts_off:
            self.lift_offs.add(name)

    def group_of(self, p: PlacedPart) -> str | None:
        for t in reversed(p.tags):
            for g, tag in self.groups.items():
                if t == tag:
                    return g
        for g, ex in self.group_exclude.items():
            if not (set(p.tags) & ex):
                return g
        return None

    def allow_contact(self, tag_a: str, tag_b: str, note: str = "") -> None:
        """Let parts under these two tags touch or overlap slightly without failing the
        collision checks, for contact the part geometry can't show: a presser pushing a
        spring-loaded button, a pin riding on a lever."""
        self.contacts.append((tag_a, tag_b, note))

    def captive(self, tag: str, note: str = "") -> None:
        """Parts under `tag` form a piece that is held in place by the parts around it without
        being clicked on (a slider in its guide). Within their own sub-assembly the buildability
        check doesn't count them as loose; the whole model must still join them up."""
        self.captive_tags[tag] = note

    def press_fit(self, tag: str, note: str = "", reach: float = 2.0) -> None:
        """Parts under `tag` are held by friction by the parts they touch (within `reach` LDU),
        not by studs: a bought clock insert pressed into its opening, a hand on its spindle.
        The connections, buildability and mechanism checks count those touches as
        connections ("press"). Tag the placements themselves (the tag on the part, or on the
        sub-assembly holding it) and give an `insert=` direction for the buildability check."""
        self.press_fits[tag] = {"note": note, "reach": float(reach)}

    def is_press_fit(self, p: PlacedPart) -> bool:
        return bool(self.press_fits) and any(t in self.press_fits for t in p.tags)

    def hardware(self, name: str, qty: int, description: str = "", price=(0.0, 0.0),
                 where: str = "") -> None:
        """A bought non-LEGO item that is not placed in 3D (glue, batteries, a stand): it goes
        on the hardware list with rough prices (USD each). Placed stand-in parts
        (data/hardware.json) are listed on their own."""
        self.hardware_items.append({"name": name, "qty": int(qty), "description": description,
                                    "price": tuple(map(float, price)), "where": where})

    def contact_ok(self, a: PlacedPart, b: PlacedPart) -> bool:
        if a.kit is not None and a.kit == b.kit:
            return True          # pieces of one bought kit (a minifig torso) come assembled
        if self.fits:            # a minifig's hair over its head
            pa, pb = a.tag_path, b.tag_path
            for x, y in self.fits:
                if (_ends(pa, x) and _ends(pb, y)) or (_ends(pa, y) and _ends(pb, x)):
                    return True
        ta, tb = set(a.tags), set(b.tags)
        return any((x in ta and y in tb) or (x in tb and y in ta) for x, y, _ in self.contacts)

    def gear_pair(self, a: str, b: str, kind: str = "spur") -> None:
        self.gear_pairs.append((a, b, kind))

    def light(self, name: str, tag_path: str, color: str = "#FF3A1A", power: float = 1.5,
              offset=(0.0, 0.0, 0.0)) -> None:
        """A light source at a part (for the electrics check and lit renders). `offset` (LDU, in
        the part's own frame) moves the renders' point light, e.g. out of an LED's housing to
        the middle of what it lights."""
        self.lights.append({"name": name, "part": tag_path, "color": color, "power": power,
                            "offset": tuple(map(float, offset))})

    def light_position(self, light: dict, placed: list) -> np.ndarray | None:
        """World position (LDU) of a light's point source, or None if its part is missing."""
        found = self.find(light["part"], placed)
        if not found:
            return None
        return (found[0].M @ np.append(np.asarray(light.get("offset", (0, 0, 0)), float), 1.0))[:3]

    def glow(self, tag: str, strength: float = 2.0) -> None:
        """Parts under this tag glow when the lights are on (renders only)."""
        self.glow_tags[tag] = strength

    def extra(self, part: str, color, qty: int = 1, note: str = "") -> None:
        """A part the builder needs that is not placed in 3D (it goes on the parts lists), e.g.
        the lead and plug of a light unit whose lamp heads are placed."""
        self.extras.append((self.canonical(part), self.resolve_color(color), int(qty), note))

    def cable(self, name: str, start: str, end: str, length: float, route=()) -> None:
        self.cables.append({"name": name, "from": start, "to": end, "length": float(length),
                            "route": [tuple(map(float, p)) for p in route]})

    # flattening ---------------------------------------------------------------
    def instruction_order(self) -> list[tuple[str, int]]:
        order, built = [], set()

        def build(sub: Submodel):
            for s in range(sub.n_steps):
                for it in sub.items:
                    if (it.step == s and isinstance(it, Use) and it.sub.name not in built
                            and it.sub.kit is None):        # kits come assembled
                        build(it.sub)
                order.append((sub.name, s))
            built.add(sub.name)

        build(self.main)
        return order

    def flatten(self, pose: dict | None = None) -> list[PlacedPart]:
        order = {k: i for i, k in enumerate(self.instruction_order())}
        out: list[PlacedPart] = []
        kits = [0]

        def walk(sub: Submodel, W, path, tags, top, kit):
            for it in sub.items:
                t = tags + ((it.tag,) if it.tag else ())
                bo = top if top is not None else order[(sub.name, it.step)]
                if isinstance(it, Placement):
                    p = PlacedPart(len(out), it.part, it.color, W @ it.M, path + (sub.name,), t,
                                   sub.name, it.step, bo)
                    if kit is not None:              # a piece of a bought kit
                        p.buy, p.kit = kit[0], kit[1]
                        p.buy_lead = not kit[2]
                        kit[2] = True
                    elif it.buy is not None:         # a part bought as something else
                        p.buy, p.buy_lead = it.buy, True
                    out.append(p)
                else:
                    inner = kit
                    if it.sub.kit is not None and kit is None:
                        kits[0] += 1
                        inner = [it.sub.kit, kits[0], False]
                    walk(it.sub, W @ it.M, path + (sub.name,), t, bo, inner)

        walk(self.main, np.eye(4), (), (), None, None)
        if pose:
            for p in out:
                g = self.group_of(p)
                if g in pose:
                    p.M = pose[g] @ p.M
        return out

    def find(self, tag_path: str, placed: list[PlacedPart]) -> list[PlacedPart]:
        return [p for p in placed if p.tag_path == tag_path or p.tag_path.endswith("/" + tag_path)]
