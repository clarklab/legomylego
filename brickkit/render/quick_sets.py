"""Runs inside Blender (imported by blender_quick.py): the Quick Bricks workshop, in three
mix-and-match layers, at the model's real size round it (metres; the table's top at the
model's lowest point). Any surface goes with any room and any light.

Surfaces - what the model stands on (and the desk under it):
    blue_mat     a blue self-healing cutting mat with a grid of white dots, on an oak desk
    green_mat    the classic green cutting mat, pale grid and diagonals, on a walnut desk
    kraft        a tan linen cloth with a big printed ring round the model, on a painted table
    oak          a bare light-oak desktop
    baseplate    a light grey LEGO baseplate (48 x 48 studs) on a white desk
    lego_yellow, lego_blue, lego_green, lego_red
                 a LEGO floor: one endless studded mat in that colour, out to the walls

Rooms - always far behind in the depth of field, so big shapes and colour, low on the walls
(the camera is low: it sees the desk and the walls' bottom 30 cm or so):
    workbench    warm plank walls, a pegboard of colourful tools, a desk lamp, a toolbox
    studio       a bright white studio: low white shelves, plants, pastel pots
    window       big windows of daylight (green bushes and sky outside), a sill of succulents
    night        a dark workshop at night: strings of warm lights, a glowing desk lamp
    bookshelf    a nook of shelves packed with colourful books

Lights - presets that work with any of them (a key, a fill, the room's ambient):
    morning      warm, low sun from the side, a cool fill
    day          bright, soft, neutral daylight from high up
    evening      cosy: a warm lamp-like key, little fill, a dark room (exposure up a little)
"""
import math

import bpy
import numpy as np
from mathutils import Vector

import blender_scene as bs
from blender_cold_open import NB, Mesh


# ---------------------------------------------------------------------------- helpers
def mat(name, build):
    m = bpy.data.materials.new(name)
    nb = NB(m.node_tree)
    out = nb.clear("OUTPUT_MATERIAL")
    m.node_tree.links.new(build(nb), out.inputs["Surface"])
    return m


def bsdf(nb, color, rough, **kw):
    b = nb.node("ShaderNodeBsdfPrincipled", Roughness=rough, **kw)
    nb.set(b.inputs["Base Color"], color)
    return b


def plain(name, color, rough=0.5, **kw):
    return mat(name, lambda nb: bsdf(nb, color, rough, **kw).outputs[0])


def glow(name, color, strength):
    def build(nb):
        em = nb.node("ShaderNodeEmission", Strength=strength)
        nb.set(em.inputs["Color"], color)
        return em.outputs[0]
    return mat(name, build)


def put(mesh, name, material, smooth=False):
    if not mesh.V:
        return None
    ob = mesh.build(name, material, 1.0, (0, 0, 0), smooth=smooth)
    ob.scale = (1, 1, 1)
    return ob


def box(m, lo, hi, **attrs):
    """An axis-aligned box from lo to hi (per-vertex attrs, e.g. rnd for a colour)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1)], float)
    V = lo + c * (hi - lo)
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    m.tris(V, [(a, b, c_) for a, b, c_, d in q] + [(a, c_, d) for a, b, c_, d in q], **attrs)


def blob(m, centre, r, flat=1.0, sides=12):
    """A rounded lump (a bush, a plant's head, a bulb) of radius r."""
    x, y, z = centre
    zs = np.linspace(-1, 1, 7)
    m.tube([(x, y, z + r * flat * k) for k in zs], [r * math.sqrt(max(0.0, 1 - k * k)) + 1e-4 for k in zs],
           sides)


def lines(nb, coord, spacing, half_width, aa):
    """1 on lines `spacing` m apart along coord (a value socket), `half_width` m wide."""
    d = nb.mul(nb.math("PINGPONG", nb.mul(coord, 1.0 / spacing), 0.5), spacing)
    return nb.smooth(d, half_width + aa, half_width - aa)


def dots(nb, gx, gy, spacing, radius, aa):
    """1 on dots of `radius` m at every crossing of a `spacing` m grid over (gx, gy)."""
    d = [nb.mul(nb.math("PINGPONG", nb.mul(v, 1.0 / spacing), 0.5), spacing) for v in (gx, gy)]
    r = nb.vec("LENGTH", nb.comb(d[0], d[1], 0.0), out=1)
    return nb.smooth(r, radius + aa, radius - aa)


def hsv(nb, h, s, v):
    n = nb.node("ShaderNodeCombineColor")
    n.mode = "HSV"
    for i, x in enumerate((h, s, v)):
        nb.set(n.inputs[i], float(x) if isinstance(x, (int, float)) else x)
    return n.outputs[0]


def attr(nb, name="rnd"):
    n = nb.node("ShaderNodeAttribute")
    n.attribute_name = name
    return n.outputs["Fac"]


class Ctx:
    """Where things go: the model's middle `c`, the table's top `z`, its footprint `foot`, the
    walls `R` out (close enough to see past the model, clear of the camera's path), a seeded
    rng; `reach` how far out the camera goes (m, from the middle)."""

    def __init__(self, mn, mx, seed, reach=0.0):
        self.c = (mn + mx) / 2
        self.z = mn.z
        self.foot = max(mx.x - mn.x, mx.y - mn.y)
        self.reach = float(reach)
        self.R = max(0.45, 4.0 * self.foot, self.reach + 0.32)     # room for props past it
        self.rng = np.random.default_rng(seed)

    def prop(self, ang, frac, size=0.0):
        """A spot on the desk for a prop `size` m across at `ang` degrees: `frac` of the way
        to the walls, but never on the camera's path (outside its reach) nor in a wall."""
        r = min(max(frac * self.R, self.reach + 0.07 + size / 2), self.R - 0.02 - size / 2)
        a = math.radians(ang)
        return self.c.x + r * math.cos(a), self.c.y + r * math.sin(a)

    def walls(self):
        """The four walls: (base point at table height, outward normal n, along t)."""
        out = []
        for a in range(4):
            ang = a * math.pi / 2
            n = Vector((math.cos(ang), math.sin(ang), 0.0))
            t = Vector((-n.y, n.x, 0.0))
            out.append((Vector((self.c.x, self.c.y, self.z)) + n * self.R, n, t))
        return out


# ---------------------------------------------------------------------------- desks
def wood(nb, light, dark, scale=1.0, coat=0.2):
    """Planked wood, its grain along x."""
    p = nb.node("ShaderNodeTexCoord").outputs["Object"]
    warp = nb.noise(p, 3.0 * scale, 4.0, 0.6)
    q = nb.vec("ADD", nb.vec("MULTIPLY", p, (1.0 * scale, 18.0 * scale, 1.0)),
               nb.vec("SCALE", nb.comb(warp, warp, 0.0), 0.6))
    wave = nb.node("ShaderNodeTexWave", Scale=2.2, Distortion=3.0, Detail=3.0)
    nb.set(wave.inputs["Vector"], q)
    planks = nb.noise(nb.vec("MULTIPLY", p, (0.4, 7.0, 0.4)), 1.0, 0.0, 0.5)
    col = nb.mix(nb.smooth(wave.outputs["Fac"], 0.2, 0.9), dark, light)
    col = nb.mix(nb.smooth(planks, 0.3, 0.7), col, nb.tint(col, (0.86, 0.82, 0.78)))
    b = bsdf(nb, col, 0.42)
    nb.set(b.inputs["Coat Weight"], coat)
    return b.outputs[0]


DESKS = {"oak": ((0.42, 0.24, 0.11), (0.24, 0.12, 0.05)),
         "light_oak": ((0.62, 0.43, 0.24), (0.42, 0.26, 0.12)),
         "walnut": ((0.16, 0.08, 0.04), (0.07, 0.035, 0.018))}


def desk(x, kind, top):
    """The desk under everything: its top at `top`, out to the walls."""
    c, R = x.c, x.R
    m = Mesh()
    s = 1.2 * R
    m.quad([(c.x - s, c.y - s, top), (c.x + s, c.y - s, top), (c.x + s, c.y + s, top),
            (c.x - s, c.y + s, top)])
    if kind in DESKS:
        light, dark = DESKS[kind]
        material = mat("desk", lambda nb: wood(nb, light, dark))
    else:                                            # painted: white, or warm cream
        col = (0.6, 0.6, 0.58) if kind == "white" else (0.22, 0.14, 0.08)

        def painted(nb):
            n = nb.noise(nb.node("ShaderNodeTexCoord").outputs["Object"], 9.0, 4.0, 0.6)
            return bsdf(nb, nb.mix(n, [v * 0.9 for v in col], col), 0.5).outputs[0]
        material = mat("desk", painted)
    put(m, "desk", material)


# ---------------------------------------------------------------------------- surfaces
def cutting_mat(x, base, line, diagonals=False, dotted=False):
    """A self-healing cutting mat, 2.5 mm thick, the model a little off its middle: a
    centimetre grid (every fifth line stronger), a border, optionally 45-degree guides - or
    `dotted`, a dot at every centimetre and a bigger one every fifth."""
    c, z = x.c, x.z
    w = max(0.45, x.foot * 3.2)
    h = w * 2 / 3
    x0, y0 = c.x - w * 0.42, c.y - h * 0.55
    m = Mesh()
    box(m, (x0, y0, z - 0.0025), (x0 + w, y0 + h, z))

    def build(nb):
        p = nb.node("ShaderNodeTexCoord").outputs["Object"]
        px, py, _ = nb.xyz(p)
        gx, gy = nb.sub(px, x0), nb.sub(py, y0)
        minor = nb.math("MAXIMUM", lines(nb, gx, 0.01, 0.00016, 0.00008), lines(nb, gy, 0.01, 0.00016, 0.00008))
        major = nb.math("MAXIMUM", lines(nb, gx, 0.05, 0.00035, 0.0001), lines(nb, gy, 0.05, 0.00035, 0.0001))
        inside = nb.mul(nb.mul(nb.smooth(gx, 0.012, 0.0125), nb.smooth(gx, w - 0.012, w - 0.0125)),
                        nb.mul(nb.smooth(gy, 0.012, 0.0125), nb.smooth(gy, h - 0.012, h - 0.0125)))
        grid = nb.math("MAXIMUM", nb.mul(minor, 0.4), nb.mul(major, 0.85))
        if dotted:
            grid = nb.math("MAXIMUM", nb.mul(dots(nb, gx, gy, 0.01, 0.00055, 0.0001), 0.85),
                           dots(nb, gx, gy, 0.05, 0.0011, 0.0001))
        if diagonals:
            diag = lines(nb, nb.add(gx, gy), 0.1 * math.sqrt(2), 0.0003, 0.0001)
            grid = nb.math("MAXIMUM", grid, nb.mul(diag, 0.6))
        grid = nb.mul(grid, inside)
        for v, e in ((gx, 0.012), (gx, w - 0.012), (gy, 0.012), (gy, h - 0.012)):
            grid = nb.math("MAXIMUM", grid, nb.mul(lines(nb, nb.sub(v, e), 1e3, 0.0005, 0.0001), 0.9))
        n = nb.noise(p, 60.0, 3.0, 0.6)
        col = nb.mix(grid, nb.mix(n, [v * 0.8 for v in base], base), line)
        return bsdf(nb, col, nb.add(0.62, nb.mul(n, 0.12))).outputs[0]
    put(m, "surface", mat("surface", build))


def surface_blue_mat(x):
    desk(x, "oak", x.z - 0.0025)
    cutting_mat(x, (0.018, 0.08, 0.25), (0.8, 0.83, 0.86), dotted=True)


def surface_green_mat(x):
    desk(x, "walnut", x.z - 0.0025)
    cutting_mat(x, (0.02, 0.15, 0.06), (0.55, 0.8, 0.55), diagonals=True)


def surface_kraft(x):
    """A tan linen cloth with a big printed ring (and a thin one inside it) round the model."""
    c, z = x.c, x.z
    desk(x, "cream", z - 0.0004)
    m = Mesh()
    s = max(0.5, x.foot * 5)
    m.quad([(c.x - s, c.y - s, z - 0.0002), (c.x + s, c.y - s, z - 0.0002),
            (c.x + s, c.y + s, z - 0.0002), (c.x - s, c.y + s, z - 0.0002)])
    ring = max(0.06, x.foot * 0.95)

    def cloth(nb):
        p = nb.node("ShaderNodeTexCoord").outputs["Object"]
        px, py, _ = nb.xyz(p)
        weave = None
        for d in ("X", "Y"):
            w = nb.node("ShaderNodeTexWave", Scale=1.0, Distortion=0.6, Detail=1.0)
            w.wave_type = "BANDS"
            w.bands_direction = d
            nb.set(w.inputs["Vector"], nb.vec("SCALE", p, 1.0 / 0.0007))
            weave = w.outputs["Fac"] if weave is None else nb.mul(weave, w.outputs["Fac"])
        slub = nb.noise(nb.vec("MULTIPLY", p, (900.0, 40.0, 1.0)), 1.0, 2.0, 0.6)
        base = nb.mix(nb.add(nb.mul(weave, 0.5), nb.mul(slub, 0.5)), (0.2, 0.115, 0.055), (0.29, 0.18, 0.095))
        r = nb.vec("LENGTH", nb.vec("SUBTRACT", nb.comb(px, py, 0.0), (c.x, c.y, 0.0)), out=1)
        band = nb.smooth(nb.math("ABSOLUTE", nb.sub(r, ring)), 0.0022, 0.0018)
        band2 = nb.smooth(nb.math("ABSOLUTE", nb.sub(r, ring * 0.9)), 0.0007, 0.0005)
        ink = nb.mul(nb.math("MAXIMUM", band, nb.mul(band2, 0.8)), nb.add(0.75, nb.mul(slub, 0.25)))
        b = bsdf(nb, nb.mix(ink, base, (0.09, 0.055, 0.035)), 0.82)
        bump = nb.node("ShaderNodeBump", Strength=0.25, Distance=0.0003)
        nb.set(bump.inputs["Height"], weave)
        nb.nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        return b.outputs[0]
    put(m, "surface", mat("surface", cloth))


def surface_oak(x):
    desk(x, "light_oak", x.z)


def surface_baseplate(x):
    """A light grey 48 x 48 baseplate, 3.2 mm thick, studs and all, the model on its studs."""
    c, z = x.c, x.z
    desk(x, "white", z - 0.0017 - 0.0032)
    pitch = 0.008
    n = 48
    half = n * pitch / 2
    m = Mesh()
    top = z - 0.0017
    box(m, (c.x - half, c.y - half, top - 0.0032), (c.x + half, c.y + half, top))
    studs = Mesh()
    for i in range(n):
        for j in range(n):
            px, py = c.x - half + (i + 0.5) * pitch, c.y - half + (j + 0.5) * pitch
            studs.tube([(px, py, top), (px, py, z)], 0.0024, 10)
    grey = plain("baseplate", (0.36, 0.37, 0.38), 0.32, **{"Coat Weight": 0.15})
    put(m, "surface", grey)
    put(studs, "studs", grey, smooth=True)


LEGO_FLOORS = {"lego_yellow": "#F2CD37", "lego_blue": "#0055BF", "lego_green": "#237841",
               "lego_red": "#C91A09"}
STUD_NEAR = 0.3           # m from the model: studs out to here are round, 12-sided; past it,
#                           where the depth of field has melted them, 6-sided


def lego_floor(x, colour):
    """An endless LEGO mat in one colour: a plate's worth of plastic out past the walls, and
    its studs, real ones (the model stands on them, loose parts lie on them). The studs are on
    the world's own 8 mm grid, the one the model's studs are on."""
    c, z = x.c, x.z
    pitch, top = 0.008, z - 0.0017
    s = 1.25 * x.R
    m = Mesh()
    box(m, (c.x - s, c.y - s, top - 0.0032), (c.x + s, c.y + s, top))
    n = int(math.ceil(1.08 * x.R / pitch))
    ks = np.arange(-n, n) + 0.5
    px, py = np.meshgrid((math.floor(c.x / pitch) + ks) * pitch, (math.floor(c.y / pitch) + ks) * pitch)
    at = np.stack([px.ravel(), py.ravel(), np.zeros(px.size)], -1)
    near = np.hypot(at[:, 0] - c.x, at[:, 1] - c.y) < STUD_NEAR
    studs = Mesh()
    for where, sides in ((at[near], 12), (at[~near], 6)):
        if not len(where):
            continue
        one = Mesh()
        one.tube([(0, 0, top), (0, 0, z)], 0.0024, sides)
        V1, F1 = np.concatenate(one.V), np.concatenate(one.F)
        studs.tris((V1[None] + where[:, None]).reshape(-1, 3),
                   (F1[None] + (np.arange(len(where)) * len(V1))[:, None, None]).reshape(-1, 3))
    plastic = plain("lego_floor", bs.hex_to_linear(colour), 0.3, **{"Coat Weight": 0.15})
    put(m, "surface", plastic)
    put(studs, "studs", plastic, smooth=True)


# ---------------------------------------------------------------------------- rooms
def wall_mesh(x, height):
    m = Mesh()
    for p0, n, t in x.walls():
        a, b = p0 - t * x.R * 1.2, p0 + t * x.R * 1.2
        m.quad([tuple(a - Vector((0, 0, 0.01))), tuple(b - Vector((0, 0, 0.01))),
                tuple(b + Vector((0, 0, height))), tuple(a + Vector((0, 0, height)))])
    return m


def desk_lamp(x, ang, frac, bulb=8.0):
    """An anglepoise lamp on the desk (out past the camera's path), its arm and warm glowing
    head reaching round the desk's edge, not in towards the model."""
    z = x.z
    bx, by = x.prop(ang, frac, 0.12)
    a = math.radians(ang)
    tx, ty = -math.sin(a), math.cos(a)                  # along the walls, round the model
    body = Mesh()
    body.tube([(bx, by, z), (bx, by, z + 0.012)], 0.055, 20)
    body.tube([(bx, by, z + 0.012), (bx + 0.03 * tx, by + 0.03 * ty, z + 0.22),
               (bx - 0.09 * tx, by - 0.09 * ty, z + 0.36)], 0.008, 8)
    hx, hy, hz = bx - 0.12 * tx, by - 0.12 * ty, z + 0.33
    body.tube([(hx + 0.04 * tx, hy + 0.04 * ty, hz + 0.03), (hx - 0.03 * tx, hy - 0.03 * ty, hz - 0.04)],
              [0.03, 0.075], 20, cap=False)
    put(body, "lamp", plain("lamp", (0.02, 0.02, 0.022), 0.3), smooth=True)
    b = Mesh()
    b.tube([(hx - 0.01 * tx, hy - 0.01 * ty, hz - 0.01), (hx - 0.03 * tx, hy - 0.03 * ty, hz - 0.04)], 0.03, 16)
    put(b, "lamp_bulb", glow("lamp_bulb", (1.0, 0.72, 0.42), bulb))
    ld = bpy.data.lights.new("lamp_light", "POINT")
    ld.energy = 2.5 * bulb
    ld.color = (1.0, 0.7, 0.4)
    ld.shadow_soft_size = 0.03
    ob = bpy.data.objects.new("lamp_light", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (hx - 0.04 * tx, hy - 0.04 * ty, hz - 0.06)


def room_workbench(x):
    """Warm plank walls, pegboards of colourful tools, a desk lamp, a red toolbox."""
    rng = x.rng

    def planks(nb):
        p = nb.node("ShaderNodeTexCoord").outputs["Object"]
        px, py, pz = nb.xyz(p)
        br = nb.node("ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.004})
        nb.set(br.inputs["Vector"], nb.vec("MULTIPLY", nb.comb(nb.add(px, py), pz, 0.0), (1 / 0.14, 1 / 2.5, 1.0)))
        nb.set(br.inputs["Color1"], (0.3, 0.17, 0.08))
        nb.set(br.inputs["Color2"], (0.42, 0.25, 0.12))
        nb.set(br.inputs["Mortar"], (0.08, 0.04, 0.02))
        return bsdf(nb, br.outputs["Color"], 0.6).outputs[0]
    put(wall_mesh(x, 1.2 * x.R), "walls", mat("walls", planks))
    board, handles, heads = Mesh(), Mesh(), Mesh()
    for p0, n, t in x.walls():
        a, b = p0 - t * x.R * 0.8 - n * 0.02, p0 + t * x.R * 0.8 - n * 0.015
        lo = Vector((min(a.x, b.x), min(a.y, b.y), x.z + 0.02))
        hi = Vector((max(a.x, b.x), max(a.y, b.y), x.z + 0.6))
        box(board, lo, hi)
        for k in range(12):                                  # tools hung on it
            s = rng.uniform(-0.75, 0.75) * x.R
            hz = x.z + rng.uniform(0.12, 0.34)
            q = p0 + t * s - n * 0.03
            hl = rng.uniform(0.07, 0.12)
            box(handles, (q.x - 0.012, q.y - 0.012, hz - hl), (q.x + 0.012, q.y + 0.012, hz), rnd=rng.random())
            box(heads, (q.x - 0.03, q.y - 0.008, hz), (q.x + 0.03, q.y + 0.008, hz + 0.05))

    def pegboard(nb):
        p = nb.node("ShaderNodeTexCoord").outputs["Object"]
        px, py, pz = nb.xyz(p)
        u = nb.add(px, py)
        hole = nb.mul(lines(nb, u, 0.025, 0.003, 0.001), lines(nb, pz, 0.025, 0.003, 0.001))
        return bsdf(nb, nb.mix(hole, (0.5, 0.36, 0.2), (0.05, 0.03, 0.02)), 0.75).outputs[0]
    put(board, "pegboard", mat("pegboard", pegboard))
    put(handles, "tool_handles", mat("tool_handles", lambda nb: bsdf(nb, hsv(nb, nb.mul(attr(nb), 0.9), 0.85, 0.55), 0.4).outputs[0]))
    put(heads, "tool_heads", plain("tool_heads", (0.5, 0.5, 0.52), 0.3, Metallic=1.0))
    desk_lamp(x, 150, 0.8)
    tb = Mesh()
    bx, by = x.prop(40, 0.85, 0.17)
    box(tb, (bx - 0.08, by - 0.045, x.z), (bx + 0.08, by + 0.045, x.z + 0.075))
    put(tb, "toolbox", plain("toolbox", (0.5, 0.03, 0.02), 0.35))


def room_studio(x):
    """A bright white studio: white walls, low white shelves, plants, pastel pots and books."""
    rng = x.rng
    put(wall_mesh(x, 1.2 * x.R), "walls", plain("walls", (0.75, 0.74, 0.71), 0.9))
    shelves, pots, leaves, books = Mesh(), Mesh(), Mesh(), Mesh()
    for p0, n, t in x.walls():
        for hz in (0.05, 0.24):
            a, b = p0 - t * x.R * 0.75 - n * 0.16, p0 + t * x.R * 0.75 - n * 0.005
            box(shelves, (min(a.x, b.x), min(a.y, b.y), x.z + hz - 0.018),
                (max(a.x, b.x), max(a.y, b.y), x.z + hz))
            s = -0.65 * x.R
            while s < 0.65 * x.R:
                q = p0 + t * s - n * 0.08
                kind = rng.random()
                if kind < 0.45:                              # a potted plant
                    r = rng.uniform(0.035, 0.055)
                    pots.tube([(q.x, q.y, x.z + hz), (q.x, q.y, x.z + hz + r * 1.6)], [r * 0.8, r], 16)
                    blob(leaves, (q.x, q.y, x.z + hz + r * 1.6 + r * 1.3), r * 1.6, flat=0.8)
                    s += 3 * r + 0.05
                else:                                        # a few books
                    for k in range(rng.integers(3, 7)):
                        w = rng.uniform(0.015, 0.03)
                        hb = rng.uniform(0.12, 0.2)
                        qq = p0 + t * s - n * 0.08
                        box(books, (qq.x - w / 2, qq.y - w / 2, x.z + hz), (qq.x + w / 2, qq.y + w / 2, x.z + hz + hb),
                            rnd=rng.random())
                        s += w + 0.002
                    s += 0.05
    put(shelves, "shelves", plain("shelves", (0.8, 0.79, 0.76), 0.5))
    put(pots, "pots", plain("pots", (0.7, 0.42, 0.3), 0.6), smooth=True)
    put(leaves, "leaves", plain("leaves", (0.04, 0.2, 0.05), 0.55), smooth=True)
    put(books, "books", mat("books", lambda nb: bsdf(nb, hsv(nb, attr(nb), 0.35, 0.65), 0.6).outputs[0]))
    plant = Mesh()
    px, py = x.prop(-120, 0.85, 0.24)
    for k in range(5):
        blob(plant, (px + rng.normal(0, 0.05), py + rng.normal(0, 0.05), x.z + 0.18 + 0.1 * k), 0.09, flat=0.7)
    put(plant, "big_plant", plain("big_plant", (0.03, 0.22, 0.06), 0.5), smooth=True)


def room_window(x):
    """Big windows of daylight in three walls (white frames, green bushes and sky outside),
    cream walls, a sill of succulents."""
    rng = x.rng
    put(wall_mesh(x, 1.2 * x.R), "walls", plain("walls", (0.6, 0.53, 0.44), 0.9))
    panes, frames, sill, pots, leaves = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    for k, (p0, n, t) in enumerate(x.walls()):
        if k == 3:                                           # windows on three sides
            continue
        w0, w1, h0, h1 = -0.75 * x.R, 0.75 * x.R, x.z + 0.04, x.z + 0.9 * x.R
        q0, q1 = p0 + t * w0 - n * 0.004, p0 + t * w1 - n * 0.004
        panes.quad([(q0.x, q0.y, h0), (q1.x, q1.y, h0), (q1.x, q1.y, h1), (q0.x, q0.y, h1)])
        for s in np.linspace(w0, w1, 5):                     # mullions
            q = p0 + t * s - n * 0.01
            box(frames, (q.x - 0.015, q.y - 0.015, h0), (q.x + 0.015, q.y + 0.015, h1))
        for hz in (h0, x.z + 0.3 * x.R, h1):
            a, b = q0 - n * 0.01, q1 - n * 0.01
            box(frames, (min(a.x, b.x) - 0.015, min(a.y, b.y) - 0.015, hz - 0.015),
                (max(a.x, b.x) + 0.015, max(a.y, b.y) + 0.015, hz + 0.015))
        a, b = p0 + t * w0 - n * 0.09, p0 + t * w1
        box(sill, (min(a.x, b.x), min(a.y, b.y), x.z + 0.02), (max(a.x, b.x), max(a.y, b.y), x.z + 0.04))
        for s in rng.uniform(w0 * 0.9, w1 * 0.9, 4):
            q = p0 + t * s - n * 0.05
            pots.tube([(q.x, q.y, x.z + 0.04), (q.x, q.y, x.z + 0.09)], [0.025, 0.032], 14)
            blob(leaves, (q.x, q.y, x.z + 0.12), 0.04, flat=0.6)

    def outside(nb):                                         # daylight, trees beyond the glass
        p = nb.node("ShaderNodeTexCoord").outputs["Object"]
        n1 = nb.noise(nb.vec("MULTIPLY", p, (9.0, 9.0, 9.0)), 1.0, 3.0, 0.6)
        h = nb.sub(nb.xyz(p)[2], x.z)                      # bushes low outside, sky above
        green = nb.smooth(nb.sub(nb.add(nb.mul(n1, 0.16), 0.2), h), -0.01, 0.02)
        col = nb.mix(green, (1.0, 0.96, 0.88), (0.25, 0.55, 0.18))
        em = nb.node("ShaderNodeEmission", Strength=5.0)
        nb.set(em.inputs["Color"], col)
        return em.outputs[0]
    put(panes, "window", mat("window", outside))
    put(frames, "window_frames", plain("window_frames", (0.8, 0.8, 0.78), 0.4))
    put(sill, "sill", plain("sill", (0.75, 0.74, 0.7), 0.4))
    put(pots, "pots", plain("pots", (0.75, 0.75, 0.72), 0.3), smooth=True)
    put(leaves, "succulents", plain("succulents", (0.12, 0.3, 0.15), 0.5), smooth=True)


def room_night(x):
    """A dark workshop at night: navy walls, strings of warm lights sagging along them, a
    glowing desk lamp, a mug."""
    put(wall_mesh(x, 1.2 * x.R), "walls", plain("walls", (0.02, 0.025, 0.045), 0.9))
    bulbs, wire = Mesh(), Mesh()
    for p0, n, t in x.walls():
        for row, hz in enumerate((0.12, 0.26)):
            pts = []
            for s in np.linspace(-0.85, 0.85, 22):
                sag = 0.05 * (1 - (s / 0.85) ** 2)
                q = p0 + t * (s * x.R) - n * 0.03
                pts.append((q.x, q.y, x.z + hz - sag + 0.02 * row))
            wire.tube(pts, 0.0015, 4, cap=False)
            for q in pts[1:-1]:
                blob(bulbs, q, 0.008, sides=8)
    put(wire, "wire", plain("wire", (0.01, 0.01, 0.01), 0.5))
    put(bulbs, "string_lights", glow("string_lights", (1.0, 0.68, 0.32), 30.0))
    desk_lamp(x, 135, 0.8, bulb=14.0)
    mug = Mesh()
    mx, my = x.prop(-60, 0.85, 0.08)
    mug.tube([(mx, my, x.z), (mx, my, x.z + 0.095)], 0.04, 24)
    put(mug, "mug", plain("mug", (0.5, 0.15, 0.08), 0.2), smooth=True)


def room_bookshelf(x):
    """A nook of wooden shelves on every wall, packed with colourful books."""
    rng = x.rng
    put(wall_mesh(x, 1.2 * x.R), "walls", plain("walls", (0.18, 0.1, 0.05), 0.7))
    shelves, books = Mesh(), Mesh()
    for p0, n, t in x.walls():
        for hz in np.arange(0.0, 0.9, 0.2):
            a, b = p0 - t * x.R * 1.1 - n * 0.22, p0 + t * x.R * 1.1
            box(shelves, (min(a.x, b.x), min(a.y, b.y), x.z + hz - 0.02), (max(a.x, b.x), max(a.y, b.y), x.z + hz))
            s = -1.05 * x.R
            while s < 1.05 * x.R:
                w = rng.uniform(0.018, 0.04)
                hb = rng.uniform(0.15, 0.21)
                lean = rng.random() < 0.05
                q = p0 + t * s - n * 0.11
                d = 0.08 if not lean else 0.06
                box(books, (q.x - w / 2 - (d if abs(n.x) > 0.5 else 0), q.y - w / 2 - (d if abs(n.y) > 0.5 else 0), x.z + hz),
                    (q.x + w / 2 + (d if abs(n.x) > 0.5 else 0), q.y + w / 2 + (d if abs(n.y) > 0.5 else 0), x.z + hz + hb),
                    rnd=rng.random())
                s += w + 0.001 + (0.06 if rng.random() < 0.04 else 0.0)
    put(shelves, "shelves", mat("shelves", lambda nb: wood(nb, (0.3, 0.16, 0.07), (0.16, 0.08, 0.03), 2.0)))
    put(books, "books", mat("books", lambda nb: bsdf(nb, hsv(nb, attr(nb), 0.6, nb.add(0.3, nb.mul(attr(nb), 0.2))), 0.55).outputs[0]))


# ---------------------------------------------------------------------------- lights
LIGHTS = {   # key (direction from the model, colour, power, size), fill, world, exposure (EV)
    # ("filmic": EV on top under the Filmic view, which shows the two daylights much brighter
    # than AgX does: without it coral goes pale pink, lime yellow, and the mats wash out)
    "morning": {"key": ((-0.8, -0.45, 0.42), "#FFD7A6", 230.0, 0.9), "fill": ((0.8, 0.4, 0.4), "#CFE0FF", 40.0, 1.2),
                "world": ("#C4A88A", 0.25), "ev": 0.0, "filmic": -1.0},
    "day": {"key": ((-0.5, -0.6, 0.85), "#FFF4E6", 260.0, 1.3), "fill": ((0.7, 0.5, 0.5), "#E6EEFF", 80.0, 1.4),
            "world": ("#D8DCE0", 0.45), "ev": -0.15, "filmic": -1.2},
    # (evening: a big soft warm lamp on the model's front, a cool fill round its back: a hard
    # key from behind burnt out the back and left the face in shadow)
    "evening": {"key": ((-0.7, -0.5, 0.5), "#FFC48A", 95.0, 1.3), "fill": ((0.75, 0.45, 0.4), "#A9B8E6", 45.0, 1.5),
                "world": ("#3A2A20", 0.2), "ev": 0.2},
}


def light(x, kind):
    """The light preset: a key and a fill (area lights), the room's ambient. Returns its EV."""
    L = LIGHTS[kind]
    sc = bpy.context.scene
    R = x.R
    for name in ("key", "fill"):
        d, col, power, size = L[name]
        ld = bpy.data.lights.new(f"{name}_light", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size * R, size * R * 0.75
        ld.energy = power * R * R
        ld.color = bs.hex_to_linear(col)
        ob = bpy.data.objects.new(f"{name}_light", ld)
        sc.collection.objects.link(ob)
        ob.location = x.c + Vector(d).normalized() * R * 0.85
        ob.rotation_euler = (x.c - ob.location).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("room")
    sc.world = w
    bg = bs.principled_world(w)
    col, strength = L["world"]
    bg.inputs[0].default_value = (*bs.hex_to_linear(col), 1.0)
    bg.inputs[1].default_value = strength
    return float(L["ev"])


SURFACES = {"blue_mat": surface_blue_mat, "green_mat": surface_green_mat, "kraft": surface_kraft,
            "oak": surface_oak, "baseplate": surface_baseplate,
            **{name: (lambda x, colour=colour: lego_floor(x, colour)) for name, colour in LEGO_FLOORS.items()}}
ROOMS = {"workbench": room_workbench, "studio": room_studio, "window": room_window,
         "night": room_night, "bookshelf": room_bookshelf}


def build_set(surface, room, light_name, mn, mx, seed=7, reach=0.0) -> float:
    """The workshop round the model's box (mn, mx: Blender, metres): a surface, a room and a
    light, everything on the desk out past `reach` (m: how far the camera goes from the
    middle). Returns the light's exposure (EV)."""
    x = Ctx(mn, mx, seed, reach)
    SURFACES[surface](x)
    ROOMS[room](x)
    return light(x, light_name)
