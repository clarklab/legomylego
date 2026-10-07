"""Runs inside Blender: renders a build video's cold open (brickkit/video/timeline.py's
cold_open_plan): the model performing in a set of its own before the reel proper.

    Blender -b --factory-startup -P blender_cold_open.py -- job.json

job.json as for blender_animate.py: {"timeline", "frames": [[frame, "out.png"], ...], "size",
"samples", "engine", "device"}, and "plan": "coda" for the video's coda (timeline.py's
coda_plan: the same fields, in the deep_sea set, with its creature) instead. The parts, their materials and the engine settings are the
animator's (blender_scene.SceneBuilder, blender_animate's settings); the set is built here:

    sunset_road   a worn two-lane blacktop running dead straight into a huge low sun, the figure
                  treated as life-size (a man about 2 m tall with his arms up: the set is
                  scaled from its height). A physical sky with a dusty aureole round the sun and
                  thin streaks of cloud, lit by a warm sun lamp on the same line (the disc
                  itself a camera-only card at infinity). The road: chip seal, patched,
                  crack-sealed, polished wheel paths that take the sun's glare, a faded dashed
                  yellow centre line, worn edge lines, crumbling edges, caliche shoulders.
                  Round it, all procedural geometry: dry grass and seed stalks along the verges
                  (lit through from behind), barbed-wire fences on cedar posts, a power line
                  and a telephone line of leaning poles with sagging wires, mesquites, live
                  oaks and a dead tree in the pastures, a windpump, a farmhouse and barn, a tree
                  line and low hills on the horizon. Everything fades into the sky's colour
                  with distance (aerial haze); a thin dust hangs over the road.
                  The lens: focused on the figure, the background softer the closer the shot
                  (oval, anamorphic bokeh), a 180-degree shutter's motion blur on the swing;
                  the compositor exposes each shot, blooms the highlights and throws sun beams
                  from the visible part of the disc (so they die where the figure covers it).
                  The streak, ghosts and veil of the flare are the web compositor's.
    night_desk    a bedroom at night at the model's real size (a LEGO lamp is a real lamp): a
                  wooden desk against the wall under a window of moonlit blue night (a moon,
                  stars and trees beyond), a curtain, books, a mug, a plant, a notebook, a print
                  on the wall. The moon through the window is the only light until the model's
                  LEDs come on (the plan's `led`, a tap cold open's); then they light the parts
                  they glow in, and a soft glow round them lights the desk, the wall and the
                  props warm, light-linked so neither washes out the clear shell. Focused on
                  the model, shallow; bloom from the highlights, pumped as the light snaps on.

The model stands at the pivot (on the road's centre line, or on the desk) with any hide_tags
parts hidden; the parts hang on a rig (spin empty > group empties > parts): the spin turns the
whole figure, the groups play the performance (or the taps), keyed either side of each frame
so a 180-degree shutter blurs what moves. The model's LEDs (a tap lamp's) ride on their parts
at the plan's `led` level; its glowing parts glow with them. Kept apart from blender_animate.py
so the studio plates' cache keys (which hash that script) don't change when the sets do."""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import blender_animate as ba  # noqa: E402
import blender_scene as bs  # noqa: E402

TO_B = bs.TO_BLENDER
LDU = bs.LDU
MAN = 2.05          # m: how tall the figure stands in its world (arms up): sets the set's scale
DISC_AT = 1500.0    # Blender m: where the sun disc hangs, along the sun's line from the camera

# the set's look; [video.cold_open] can override any of these (the plan's "look")
LOOK = {"exposure": -1.6,          # EV (each shot adds its own)
        "sky_strength": 0.45, "sky_tint": "#FFB070",
        "sun_strength": 5.0, "sun_color": "#FF9A4A", "sun_disc": 90.0,
        "fill_strength": 0.25,     # violet fill from the sky behind the camera
        "haze": 1900.0,            # m: the air takes 63 % of a thing's colour this far off
        "dust": 0.0015,            # the dust over the road: extinction per metre at the ground
        "look": "AgX - Punchy"}


# ---------------------------------------------------------------------------- shader nodes
class NB:
    """Node building: inputs by name, a constant or a socket wherever a value goes."""

    def __init__(self, nt):
        self.nt = nt

    def clear(self, keep):
        for n in list(self.nt.nodes):
            if n.type != keep:
                self.nt.nodes.remove(n)
        return next(n for n in self.nt.nodes if n.type == keep)

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif isinstance(v, (tuple, list)) and len(v) == 3 and sock.type == "RGBA":
            sock.default_value = (*v, 1.0)
        else:
            sock.default_value = v

    def node(self, kind, **kw):
        n = self.nt.nodes.new(kind)
        for k, v in kw.items():
            if k in n.inputs:
                self.set(n.inputs[k], v)
            else:
                setattr(n, k, v)
        return n

    def math(self, op, a, b=None, c=None):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.set(n.inputs[i], float(v) if isinstance(v, (int, float)) else v)
        return n.outputs[0]

    def add(self, a, b):
        return self.math("ADD", a, b)

    def sub(self, a, b):
        return self.math("SUBTRACT", a, b)

    def mul(self, a, b):
        return self.math("MULTIPLY", a, b)

    def vec(self, op, a, b=None, out=0):
        n = self.nt.nodes.new("ShaderNodeVectorMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if op == "SCALE" and i == 1:
                self.set(n.inputs["Scale"], float(v) if isinstance(v, (int, float)) else v)
            else:
                self.set(n.inputs[i], v)
        return n.outputs[out]

    def xyz(self, v):
        n = self.node("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], v)
        return n.outputs

    def comb(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self.set(n.inputs[i], float(v) if isinstance(v, (int, float)) else v)
        return n.outputs[0]

    def smooth(self, v, lo, hi):
        """0 below lo, 1 above hi, smoothstep between (hi < lo inverts)."""
        n = self.nt.nodes.new("ShaderNodeMapRange")
        ba._try(n, "interpolation_type", "SMOOTHSTEP")
        self.set(n.inputs["From Min"], lo)
        self.set(n.inputs["From Max"], hi)
        self.set(n.inputs["Value"], v)
        return n.outputs["Result"]

    def mix(self, fac, a, b, blend="MIX"):
        """Colours: a to b by fac (or blended, "MULTIPLY"...)."""
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = blend
        self.set(n.inputs["Factor"], float(fac) if isinstance(fac, (int, float)) else fac)
        for sock, v in ((n.inputs[6], a), (n.inputs[7], b)):
            if isinstance(v, (tuple, list)):
                sock.default_value = (*v[:3], 1.0)
            else:
                self.nt.links.new(v, sock)
        return n.outputs[2]

    def tint(self, color, rgb):
        return self.mix(1.0, color, rgb, "MULTIPLY")

    def fmix(self, fac, a, b):
        """Values: a to b by fac."""
        return self.math("MULTIPLY_ADD", fac, self.sub(b, a), a)

    def noise(self, vec, scale, detail=2.0, rough=0.5, out="Fac"):
        n = self.node("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
        self.set(n.inputs["Vector"], vec)
        return n.outputs[out]

    def voronoi(self, vec, scale, feature="F1", out="Distance", rnd=1.0):
        n = self.node("ShaderNodeTexVoronoi", Scale=scale)
        n.feature = feature
        self.set(n.inputs["Randomness"], rnd)
        self.set(n.inputs["Vector"], vec)
        return n.outputs[out]

    def shader_mix(self, fac, a, b):
        n = self.node("ShaderNodeMixShader")
        self.set(n.inputs[0], float(fac) if isinstance(fac, (int, float)) else fac)
        self.nt.links.new(a, n.inputs[1])
        self.nt.links.new(b, n.inputs[2])
        return n.outputs[0]

    def group(self, tree, **kw):
        n = self.nt.nodes.new("ShaderNodeGroup")
        n.node_tree = tree
        for k, v in kw.items():
            self.set(n.inputs[k], v)
        return n

    def angle_to(self, d, target):
        """Radians between the unit vector d and a fixed direction."""
        c = self.vec("DOT_PRODUCT", d, tuple(target), out=1)
        return self.math("ARCCOSINE", self.math("MINIMUM", c, 1.0))


def sun_direction(sun) -> Vector:
    e, a = math.radians(sun["elevation"]), math.radians(sun["azimuth"])
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


# ---------------------------------------------------------------------------- meshes
class Mesh:
    """Triangles gathered with numpy, built into one object (metres; `_place` puts it in the
    set). `attrs`: per-vertex floats for the material ("rnd", "h")."""

    def __init__(self):
        self.V, self.F, self.A, self.n = [], [], {}, 0

    def tris(self, V, F, **attrs):
        V = np.asarray(V, np.float32).reshape(-1, 3)
        F = np.asarray(F, np.int64).reshape(-1, 3)
        for k in set(self.A) | set(attrs):
            self.A.setdefault(k, [np.zeros(self.n, np.float32)] if self.n else [])
            a = np.asarray(attrs.get(k, 0.0), np.float32)
            self.A[k].append(np.broadcast_to(a, (len(V),)).copy())
        self.V.append(V)
        self.F.append(F + self.n)
        self.n += len(V)

    def tube(self, pts, radii, sides=6, cap=True):
        """A tube along a polyline, a radius per point (a pole, a branch, a wire)."""
        P = np.asarray(pts, float)
        r = np.broadcast_to(np.asarray(radii, float), (len(P),))
        t = np.gradient(P, axis=0)
        t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
        up = np.where(np.abs(t[:, 2:3]) > 0.9, [[1.0, 0, 0]], [[0, 0, 1.0]])
        a = np.cross(t, up)
        a /= np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
        b = np.cross(t, a)
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        ring = np.cos(ang)[None, :, None] * a[:, None] + np.sin(ang)[None, :, None] * b[:, None]
        V = (P[:, None] + ring * r[:, None, None]).reshape(-1, 3)
        k = len(P)
        i = np.arange(k - 1)[:, None] * sides
        j = np.arange(sides)[None, :]
        a0, a1 = i + j, i + (j + 1) % sides
        F = np.concatenate([np.stack([a0, a1, a1 + sides], -1).reshape(-1, 3),
                            np.stack([a0, a1 + sides, a0 + sides], -1).reshape(-1, 3)])
        if cap:
            V = np.vstack([V, P[-1:]])
            top = (k - 1) * sides
            F = np.vstack([F, np.stack([top + np.arange(sides), np.full(sides, len(V) - 1),
                                        top + (np.arange(sides) + 1) % sides], -1)])
        self.tris(V, F)

    def box(self, center, size, R=None):
        c = np.array([[x, y, z] for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)], float)
        V = c * np.asarray(size, float) / 2
        if R is not None:
            V = V @ np.asarray(R, float).T
        V += np.asarray(center, float)
        q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        self.tris(V, [(a, b, c_) for a, b, c_, d in q] + [(a, c_, d) for a, b, c_, d in q])

    def quad(self, P):
        self.tris(P, [(0, 1, 2), (0, 2, 3)])

    def build(self, name, mat, M, origin, smooth=False):
        if not self.V:
            return None
        V = np.concatenate(self.V)
        F = np.concatenate(self.F).astype(np.int32)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(V))
        me.vertices.foreach_set("co", V.ravel())
        me.loops.add(F.size)
        me.loops.foreach_set("vertex_index", F.ravel())
        me.polygons.add(len(F))
        me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3, dtype=np.int32))
        if smooth:
            me.polygons.foreach_set("use_smooth", np.ones(len(F), bool))
        me.update(calc_edges=True)
        for k, parts in self.A.items():
            me.attributes.new(k, "FLOAT", "POINT").data.foreach_set("value", np.concatenate(parts))
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = origin
        ob.scale = (M, M, M)
        return ob


def _rot(yaw=0.0, tilt=0.0, tilt_dir=0.0):
    """A rotation: yaw about z, then leaning `tilt` towards `tilt_dir` (radians)."""
    cz, sz = math.cos(yaw), math.sin(yaw)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    ax = np.array([-math.sin(tilt_dir), math.cos(tilt_dir), 0.0])
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return (np.eye(3) + math.sin(tilt) * K + (1 - math.cos(tilt)) * K @ K) @ Rz


def _leaves(m, rng, centres, radii, n, size, flat=0.6, rnd=0.0):
    """Leaf cards (small triangles) in flattened ellipsoids round `centres`, crowded towards
    their skins so the crowns have ragged, see-through edges against the sky."""
    C = np.repeat(np.asarray(centres, float), n, axis=0)
    R = np.repeat(np.asarray(radii, float), n)
    d = rng.normal(size=(len(C), 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = C + d * (R * rng.uniform(0.35, 1.0, len(C)) ** 0.4)[:, None] * np.array([1.0, 1.0, flat])
    u = rng.normal(size=(len(C), 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(u, rng.normal(size=(len(C), 3)))
    v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    s = size * rng.uniform(0.6, 1.4, len(C))[:, None]
    V = np.stack([P, P + u * s, P + (0.5 * u + 0.8 * v) * s], 1).reshape(-1, 3)
    m.tris(V, np.arange(len(V)).reshape(-1, 3), rnd=rnd)


# ---------------------------------------------------------------------------- the set
class SunsetRoad:
    """The world, the sun, the road, the country round it, the air and the lens. Distances in
    the set are metres of the figure's world (self.M Blender units each), x across the road
    (the centre line at 0), y along it towards the sun, z up from the road."""

    BLUR = {"wide": 0.012, "low": 0.016, "close": 0.02}   # far background's blur / frame width
    TRIM = {"wide": -0.45}          # EV on the plan's: the long lens sees nothing but bright sky
    ROAD = 3.62                     # m from the centre line to the edge of the blacktop

    def __init__(self, sc, co, eevee):
        self.sc, self.co, self.eevee = sc, co, eevee
        self.look = dict(LOOK, **(co.get("look") or {}))
        self.sun = co["sun"]
        self.U = co["height"] * LDU                     # the figure's height, Blender m
        self.M = self.U / MAN                           # a metre of its world
        px, pz = co["pivot"]
        self.O = Vector((px * LDU, pz * LDU, -co["ground_y"] * LDU))
        self.sun_dir = sun_direction(self.sun)
        self.strength = float(self.look["sky_strength"])
        self.rng = np.random.default_rng(1974)
        self.looks = {}
        self.country = None
        self.sky_group = self._sky_group()
        self.haze_group = self._haze_group()
        self.world()
        self.lights()
        self.ground()
        self.verges()
        self.poles()
        self.fences()
        self.trees()
        self.far_country()
        self.dust()
        self.sun_disc()
        self.compositor()
        ee = sc.eevee
        # depth of field gathered, never scattered: bokeh sprites ring every dark silhouette
        # against the sky, and the sun
        ba._try(ee, "bokeh_threshold", 1e5)
        ba._try(ee, "bokeh_max_size", 64.0)
        sc.view_settings.view_transform = "AgX"
        ba._try(sc.view_settings, "look", self.look["look"])
        sc.view_settings.exposure = 0.0                 # exposed in the compositor (expose)

    # -- sky ----------------------------------------------------------------------------------
    def _sky_group(self):
        """The sky's colour in a direction: the physical sky (no disc) warmed by the tint, gold
        round the sun where the dust scatters its light forward (a tight aureole and a broad
        glow), darker and redder overhead."""
        g = bpy.data.node_groups.new("sunset_sky", "ShaderNodeTree")
        g.interface.new_socket("Dir", in_out="INPUT", socket_type="NodeSocketVector")
        g.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
        nb = NB(g)
        gi, go = nb.node("NodeGroupInput"), nb.node("NodeGroupOutput")
        d = nb.vec("NORMALIZE", gi.outputs[0])
        s = g.nodes.new("ShaderNodeTexSky")
        for kind in ("MULTIPLE_SCATTERING", "SINGLE_SCATTERING", "NISHITA"):
            if ba._try(s, "sky_type", kind):
                break
        s.sun_disc = False
        s.sun_elevation = math.radians(self.sun["elevation"])
        s.sun_rotation = math.radians(self.sun["azimuth"])    # 0: along +Y, down the road
        s.sun_size = math.radians(self.sun["size"])
        ba._try(s, "sun_intensity", 1.0)
        ba._try(s, "altitude", 20.0)
        ba._try(s, "air_density", 1.2)
        ba._try(s, "aerosol_density", 3.0)                  # dusty: a big soft orange sun
        nb.set(s.inputs["Vector"], d)
        col = nb.tint(s.outputs[0], bs.hex_to_linear(self.look["sky_tint"]))
        th = nb.angle_to(d, self.sun_dir)
        k = nb.add(nb.mul(nb.math("EXPONENT", nb.math("DIVIDE", th, -math.radians(1.6))), 0.9),
                   nb.mul(nb.math("EXPONENT", nb.math("DIVIDE", th, -math.radians(12.0))), 0.4))
        col = nb.vec("ADD", col, nb.vec("SCALE", nb.tint(col, (1.0, 1.05, 0.5)), k))
        high = nb.smooth(nb.xyz(d)[2], 0.05, 0.6)
        col = nb.mix(nb.mul(high, 0.55), col, nb.tint(col, (0.55, 0.3, 0.32)))
        g.links.new(col, go.inputs[0])
        return g

    def _haze_group(self):
        """Aerial perspective: a surface fades towards the sky's colour behind it with distance
        (never quite all the way: the far hills keep a trace of their own)."""
        g = bpy.data.node_groups.new("sunset_haze", "ShaderNodeTree")
        g.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
        g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
        nb = NB(g)
        gi, go = nb.node("NodeGroupInput"), nb.node("NodeGroupOutput")
        cam = nb.node("ShaderNodeCameraData")
        dist = nb.math("DIVIDE", cam.outputs["View Distance"], self.M * float(self.look["haze"]))
        h = nb.mul(nb.sub(1.0, nb.math("EXPONENT", nb.mul(dist, -1.0))), 0.88)
        v = nb.xyz(nb.vec("SCALE", nb.node("ShaderNodeNewGeometry").outputs["Incoming"], -1.0))
        d = nb.comb(v[0], v[1], nb.math("MAXIMUM", v[2], 0.012))    # the ground: its horizon
        em = nb.node("ShaderNodeEmission", Strength=self.strength)
        nb.set(em.inputs["Color"], nb.group(self.sky_group, Dir=d).outputs[0])
        g.links.new(nb.shader_mix(h, gi.outputs[0], em.outputs[0]), go.inputs[0])
        return g

    def hazed(self, name, build):
        """A material: build(nb) returns its surface shader; the haze goes over it. (Each one
        costs EEVEE a sky table every frame: keep them few.)"""
        m = bpy.data.materials.new(name)
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        hz = nb.group(self.haze_group)
        m.node_tree.links.new(build(nb), hz.inputs[0])
        m.node_tree.links.new(hz.outputs[0], out.inputs["Surface"])
        return m

    def world(self):
        """The camera sees the sky and a few streaks of cloud; everything is lit by the sky
        alone (the sun is the lamp)."""
        world = bpy.data.worlds.new("sunset")
        self.sc.world = world
        nb = NB(world.node_tree)
        out = nb.clear("OUTPUT_WORLD")
        d = nb.vec("NORMALIZE", nb.node("ShaderNodeTexCoord").outputs["Generated"])
        sky = nb.group(self.sky_group, Dir=d).outputs[0]
        light_bg = nb.node("ShaderNodeBackground", Strength=self.strength)
        nb.set(light_bg.inputs["Color"], sky)
        cam_bg = nb.node("ShaderNodeBackground", Strength=self.strength)
        nb.set(cam_bg.inputs["Color"], self._clouds(nb, d, sky))
        lp = nb.node("ShaderNodeLightPath")
        mix = nb.shader_mix(lp.outputs["Is Camera Ray"], light_bg.outputs[0], cam_bg.outputs[0])
        world.node_tree.links.new(mix, out.inputs["Surface"])
        ba._try(world, "sun_threshold", 1e6)          # EEVEE: no second sun pulled from the sky
        ba._try(world, "use_sun_shadow", False)

    def _clouds(self, nb, d, sky):
        """Long thin stratus bands on a flat layer (so they crowd towards the horizon): dark
        bellies with burning edges near the sun, dusky mauve away from it; none on the sun."""
        dx, dy, dz = nb.xyz(d)
        z = nb.math("MAXIMUM", dz, 0.004)
        uv = nb.comb(nb.math("DIVIDE", dx, z), nb.math("DIVIDE", dy, z), 0.0)
        warp = nb.noise(nb.vec("MULTIPLY", uv, (0.05, 0.05, 1.0)), 1.0, 2.0, 0.5, out="Color")
        st = nb.vec("ADD", nb.vec("MULTIPLY", uv, (0.3, 0.9, 1.0)), nb.vec("SCALE", warp, 1.6))
        n1 = nb.noise(st, 0.55, 6.0, 0.62)
        n2 = nb.noise(nb.vec("MULTIPLY", uv, (0.35, 0.07, 1.0)), 0.8, 3.0, 0.5)
        dens = nb.mul(nb.smooth(n1, 0.5, 0.64), nb.smooth(n2, 0.4, 0.56))
        el = nb.mul(nb.smooth(dz, 0.012, 0.05), nb.smooth(dz, 0.5, 0.2))  # lost low in the haze
        th = nb.angle_to(d, self.sun_dir)
        clear = nb.smooth(th, math.radians(1.1), math.radians(2.6))
        dens = nb.mul(nb.mul(dens, el), clear)
        near = nb.math("EXPONENT", nb.math("DIVIDE", th, -math.radians(16.0)))
        thin = nb.sub(1.0, nb.smooth(n1, 0.55, 0.7))
        lit = nb.mix(nb.mul(thin, near), nb.tint(sky, (0.36, 0.24, 0.26)), nb.tint(sky, (2.2, 1.7, 0.8)))
        cloud = nb.mix(nb.sub(1.0, near), lit, nb.tint(sky, (0.42, 0.3, 0.4)))
        return nb.mix(nb.mul(dens, 0.85), sky, cloud)

    def lights(self):
        sd = bpy.data.lights.new("sun", "SUN")
        sd.color = tuple(bs.hex_to_linear(self.look["sun_color"]))
        sd.energy = float(self.look["sun_strength"])
        sd.angle = math.radians(self.sun["size"])
        ba._try(sd, "use_shadow_jitter", False)
        so = bpy.data.objects.new("sun", sd)
        self.sc.collection.objects.link(so)
        so.rotation_euler = (-self.sun_dir).to_track_quat("-Z", "Y").to_euler()
        # the rest of the sky bouncing back from the camera's side: a faint violet fill
        fd = bpy.data.lights.new("fill", "SUN")
        fd.color = tuple(bs.hex_to_linear("#8C7CC8"))
        fd.energy = float(self.look["fill_strength"])
        fd.angle = math.radians(40.0)
        ba._try(fd, "use_shadow", False)
        ba._try(fd, "volume_factor", 0.0)
        fo = bpy.data.objects.new("fill", fd)
        self.sc.collection.objects.link(fo)
        fo.rotation_euler = Vector((0.0, 1.0, -0.5)).normalized().to_track_quat("-Z", "Y").to_euler()

    # -- the ground: road, shoulders, pasture --------------------------------------------------
    def ground(self):
        size = max(4000.0, 3000.0 * self.U)
        bpy.ops.mesh.primitive_plane_add(size=size, location=(self.O.x, self.O.y + size * 0.4, self.O.z))
        ob = bpy.context.object
        ob.name = "ground"
        ob.data.materials.append(self.hazed("sunset_road", self._road))

    def _road(self, nb):
        """Two 3.4 m lanes of old chip seal, its shoulders and the pasture beyond."""
        geo = nb.node("ShaderNodeNewGeometry")
        p = nb.vec("SCALE", nb.vec("SUBTRACT", geo.outputs["Position"], tuple(self.O)), 1.0 / self.M)
        x, y, _ = nb.xyz(p)
        ax = nb.math("ABSOLUTE", x)
        # the edge of the blacktop crumbles; the caliche shoulder frays into the grass
        e1 = nb.noise(p, 0.45, 3.0, 0.6)
        e2 = nb.noise(p, 4.0, 2.0, 0.6)
        edge = nb.add(self.ROAD, nb.add(nb.mul(nb.sub(e1, 0.5), 0.55), nb.mul(nb.sub(e2, 0.5), 0.22)))
        road = nb.smooth(ax, nb.add(edge, 0.02), nb.sub(edge, 0.02))
        sh_edge = nb.add(5.1, nb.mul(nb.sub(nb.noise(p, 0.3, 3.0, 0.6), 0.5), 1.6))
        field = nb.smooth(ax, nb.sub(sh_edge, 0.4), nb.add(sh_edge, 0.5))
        # chip seal: pale stones in a dark binder, sun-bleached in blotches
        stone = nb.smooth(nb.voronoi(p, 38.0), 0.42, 0.22)
        fine = nb.noise(p, 90.0, 2.0, 0.5)
        blotch = nb.noise(p, 0.18, 4.0, 0.62)
        asphalt = nb.mix(stone, (0.06, 0.057, 0.053), (0.2, 0.185, 0.165))
        asphalt = nb.mix(nb.mul(nb.smooth(blotch, 0.35, 0.7), 0.6), asphalt, (0.11, 0.1, 0.09))
        asphalt = nb.mix(nb.mul(fine, 0.25), asphalt, (0.03, 0.028, 0.026))
        # wheel paths: the binder flushed up by the tyres, darker and polished (the sun's glare)
        w = nb.math("ABSOLUTE", nb.sub(ax, 1.7))
        wp = nb.smooth(nb.math("ABSOLUTE", nb.sub(w, 0.9)), 0.42, 0.12)
        wp = nb.mul(wp, nb.smooth(nb.noise(nb.vec("MULTIPLY", p, (1.0, 0.06, 1.0)), 1.2, 2.0), 0.4, 0.62))
        asphalt = nb.mix(nb.mul(wp, 0.45), asphalt, (0.05, 0.047, 0.043))
        # patches of newer blacktop, part of a lane wide, a few metres long, ragged
        pw = nb.vec("ADD", nb.vec("MULTIPLY", p, (0.55, 0.2, 1.0)),
                    nb.vec("SCALE", nb.noise(p, 0.9, 2.0, 0.5, out="Color"), 0.12))
        pr = nb.xyz(nb.voronoi(pw, 1.0, "F1", "Color", rnd=0.3))[0]
        patch = nb.mul(nb.smooth(pr, 0.94, 0.945), nb.smooth(ax, 3.2, 3.0))
        asphalt = nb.mix(nb.mul(patch, 0.55), asphalt, nb.mix(stone, (0.045, 0.043, 0.04), (0.08, 0.075, 0.07)))
        # cracks with tar poured in them (thin black snakes, here and there), the centre joint
        warp = nb.vec("ADD", nb.vec("MULTIPLY", p, (0.9, 0.5, 1.0)),
                      nb.vec("SCALE", nb.noise(nb.vec("MULTIPLY", p, (1.3, 1.3, 1.0)), 1.0, 4.0, 0.6, out="Color"), 0.9))
        cr = nb.voronoi(warp, 1.0, "DISTANCE_TO_EDGE")
        crack = nb.mul(nb.smooth(cr, 0.009, 0.003), nb.smooth(nb.noise(p, 0.2, 2.0), 0.52, 0.62))
        joint = nb.mul(nb.smooth(nb.math("ABSOLUTE", nb.add(x, nb.mul(nb.sub(e2, 0.5), 0.12))), 0.022, 0.01),
                       nb.smooth(nb.noise(p, 0.4, 2.0), 0.5, 0.58))
        tar = nb.mul(nb.math("MAXIMUM", crack, joint), road)
        asphalt = nb.mix(tar, asphalt, (0.012, 0.011, 0.01))
        # paint: a faded dashed yellow centre line (3 m in 12) and worn white edge lines
        wear = nb.smooth(nb.noise(p, 3.0, 4.0, 0.6), 0.36, 0.6)
        wear = nb.mul(wear, nb.add(0.35, nb.mul(stone, 0.65)))
        dash = nb.smooth(nb.math("FRACT", nb.math("DIVIDE", nb.add(y, 1.5), 12.0)), 0.25, 0.245)
        cl = nb.mul(nb.mul(nb.smooth(ax, 0.07, 0.055), dash), wear)
        el = nb.smooth(nb.math("ABSOLUTE", nb.sub(ax, 3.3)), 0.055, 0.04)
        el = nb.mul(nb.mul(el, nb.add(0.4, nb.mul(wear, 0.6))),
                    nb.smooth(nb.noise(nb.vec("MULTIPLY", p, (1, 0.02, 1)), 2.0, 2.0), 0.3, 0.42))
        col = nb.mix(nb.mul(cl, 0.9), asphalt, (0.5, 0.33, 0.035))
        col = nb.mix(nb.mul(el, 0.6), col, (0.3, 0.285, 0.26))
        # caliche shoulder: pale limestone gravel, darker where the grass creeps in
        gravel = nb.mix(nb.smooth(nb.voronoi(p, 22.0), 0.5, 0.2), (0.16, 0.12, 0.085), (0.34, 0.28, 0.2))
        gravel = nb.mix(nb.mul(nb.smooth(nb.noise(p, 0.9, 3.0), 0.45, 0.7), 0.7), gravel, (0.12, 0.085, 0.05))
        col = nb.mix(road, gravel, col)
        # the pasture: dry grass, bare dirt, dark brush
        g1 = nb.noise(p, 0.06, 5.0, 0.62)
        grass = nb.mix(nb.noise(p, 1.6, 4.0, 0.6), (0.2, 0.13, 0.055), (0.42, 0.3, 0.14))
        grass = nb.mix(nb.smooth(g1, 0.56, 0.66), grass, (0.05, 0.04, 0.02))
        grass = nb.mix(nb.mul(nb.smooth(g1, 0.36, 0.3), 0.8), grass, (0.26, 0.18, 0.11))
        col = nb.mix(field, col, grass)
        rough = nb.fmix(road, 0.88, nb.fmix(wp, 0.46, 0.39))
        rough = nb.fmix(tar, rough, 0.36)
        rough = nb.fmix(patch, rough, nb.add(rough, 0.05))
        rough = nb.fmix(nb.math("MAXIMUM", cl, el), rough, 0.38)    # paint: glossy, beaded
        bump = nb.node("ShaderNodeBump", Strength=0.07, Distance=0.004 * self.M)
        nb.set(bump.inputs["Height"], nb.add(nb.mul(stone, road), nb.mul(fine, 0.3)))
        bsdf = nb.node("ShaderNodeBsdfPrincipled")
        nb.set(bsdf.inputs["Base Color"], col)
        nb.set(bsdf.inputs["Roughness"], rough)
        nb.set(bsdf.inputs["Specular IOR Level"], nb.fmix(road, 0.25, 0.5))
        nb.set(bsdf.inputs["Normal"], bump.outputs["Normal"])
        # dry grass seen against the light glows a little at grazing angles
        nb.set(bsdf.inputs["Sheen Weight"], nb.mul(field, 0.6))
        nb.set(bsdf.inputs["Sheen Tint"], (1.0, 0.75, 0.4))
        return bsdf.outputs[0]

    # -- the country's one material -----------------------------------------------------------
    def plain(self, name, color, rough=0.8, spec=0.3, translucent=0.0, var=0.0, tip=None):
        """A look for the country's shared material, set on each object as properties (every
        material with the haze's sky costs a sky table a frame, so the country shares one).
        `var`: how much darker by the vertices' "rnd"; `tip`: the colour blades take towards
        their tips ("h"); `translucent`: lit through from behind."""
        look = {"base": list(color), "rough": rough, "spec": spec, "trans": translucent,
                "var": var, "tipc": list(tip or color), "tip": 1.0 if tip else 0.0}
        self.looks[name] = look
        return look

    def _country(self):
        if self.country is not None:
            return self.country

        def build(nb):
            def prop(name, out="Fac"):
                n = nb.node("ShaderNodeAttribute", attribute_name=name)
                n.attribute_type = "OBJECT"
                return n.outputs[out]

            def vert(name):
                return nb.node("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]
            base = prop("base", "Color")
            col = nb.mix(nb.mul(vert("rnd"), prop("var")), base, nb.tint(base, (0.45, 0.45, 0.45)))
            col = nb.mix(nb.mul(nb.math("POWER", vert("h"), 1.5), prop("tip")), col, prop("tipc", "Color"))
            bsdf = nb.node("ShaderNodeBsdfPrincipled")
            nb.set(bsdf.inputs["Base Color"], col)
            nb.set(bsdf.inputs["Roughness"], prop("rough"))
            nb.set(bsdf.inputs["Specular IOR Level"], prop("spec"))
            tr = nb.node("ShaderNodeBsdfTranslucent")
            nb.set(tr.inputs["Color"], nb.tint(col, (1.6, 1.25, 0.8)))
            return nb.shader_mix(prop("trans"), bsdf.outputs[0], tr.outputs[0])
        self.country = self.hazed("country", build)
        return self.country

    def place(self, m, name, look, smooth=False, shadow=True):
        """A Mesh into the set with its look; far things cast no shadows (they'd fall out of
        sight, and cost)."""
        ob = m.build(name, self._country(), self.M, tuple(self.O), smooth)
        if ob is None:
            return None
        for k, v in look.items():
            ob[k] = v
        if not shadow:
            ba._try(ob, "visible_shadow", False)
        return ob

    # -- grass and weeds along the verges ------------------------------------------------------
    def verges(self):
        """Tussocks of dry grass along both verges, thick by the figure, thinning (and, for the
        long lens, growing) down the road; seed stalks nodding over them."""
        rng = self.rng
        m = Mesh()
        bands = [   # y from, y to, [(|x| from, to, clumps per m2)]
            (-9.0, 45.0, [(4.3, 5.2, 0.35), (5.2, 9.0, 2.2), (9.0, 16.0, 1.1)]),
            (45.0, 140.0, [(4.6, 9.0, 0.9), (9.0, 16.0, 0.35)]),
            (140.0, 420.0, [(4.8, 12.0, 0.18)]),
        ]
        cx, cy, far = [], [], []
        for y0, y1, xs in bands:
            for x0, x1, dens in xs:
                n = int(dens * (y1 - y0) * (x1 - x0) * 2)
                cx.append(rng.uniform(x0, x1, n) * rng.choice([-1, 1], n))
                cy.append(rng.uniform(y0, y1, n))
                far.append(np.full(n, min(2.0, max(0.0, y0 / 140.0))))
        cx, cy, far = np.concatenate(cx), np.concatenate(cy), np.concatenate(far)
        k = len(cx)
        idx = np.repeat(np.arange(k), rng.integers(10, 26, k))
        n = len(idx)
        big = 1.0 + 0.8 * far[idx]
        spread = 0.14 * big * np.sqrt(rng.uniform(0, 1, n))
        a = rng.uniform(0, 2 * np.pi, n)
        self._blades(m, rng, cx[idx] + spread * np.cos(a), cy[idx] + spread * np.sin(a),
                     tall=rng.uniform(0.35, 0.95, k)[idx] * rng.uniform(0.55, 1.1, n) * big,
                     lean=rng.uniform(0.15, 0.9, n) * (0.35 + spread / (0.14 * big)),
                     head=a + rng.normal(0, 0.5, n),              # leaning out of the tussock
                     wid=rng.uniform(0.006, 0.013, n) * big, rnd=rng.uniform(0, 1, k)[idx])
        # seed stalks: taller, thin, a nodding plume on each
        j = np.nonzero(rng.uniform(0, 1, k) < 0.45)[0]
        sj = np.repeat(j, rng.integers(1, 5, len(j)))
        ns = len(sj)
        self._blades(m, rng, cx[sj] + rng.normal(0, 0.08, ns), cy[sj] + rng.normal(0, 0.08, ns),
                     tall=rng.uniform(0.8, 1.45, ns) * (1.0 + 0.8 * far[sj]),
                     lean=rng.uniform(0.1, 0.35, ns), head=rng.uniform(0, 2 * np.pi, ns),
                     wid=np.full(ns, 0.004), rnd=rng.uniform(0, 1, ns), seeds=True)
        self.place(m, "verges", self.plain("dry_grass", (0.45, 0.32, 0.14), 0.55, 0.35,
                                           translucent=0.65, var=0.8, tip=(0.75, 0.58, 0.32)))

    @staticmethod
    def _blades(m, rng, x, y, tall, lean, head, wid, rnd, segs=4, seeds=False):
        """Grass blades: ribbons narrowing to a point, bending over as they rise."""
        n = len(x)
        t = np.linspace(0, 1, segs + 1)
        bend = lean[:, None] * t[None, :] ** 1.8 * tall[:, None]
        z = tall[:, None] * (t[None, :] - 0.25 * lean[:, None] ** 2 * t[None, :] ** 2)
        bx = x[:, None] + np.cos(head)[:, None] * bend
        by = y[:, None] + np.sin(head)[:, None] * bend
        side = head + np.pi / 2 + rng.normal(0, 0.6, n)
        w = wid[:, None] * (1 - t[None, :]) ** 0.7
        ox, oy = np.cos(side)[:, None] * w, np.sin(side)[:, None] * w
        V = np.stack([np.stack([bx - ox, by - oy, z], -1), np.stack([bx + ox, by + oy, z], -1)], 2)
        s = np.arange(segs)[None, :, None] * 2
        F = np.concatenate([np.concatenate([s, s + 1, s + 3], -1),
                            np.concatenate([s, s + 3, s + 2], -1)], 1) \
            + (np.arange(n) * 2 * (segs + 1))[:, None, None]
        h = np.broadcast_to(np.repeat(t, 2)[None, :], (n, 2 * (segs + 1)))
        m.tris(V.reshape(-1, 3), F.reshape(-1, 3), rnd=np.repeat(rnd, 2 * (segs + 1)),
               h=h.reshape(-1))
        if seeds:
            k = 7
            P = np.stack([bx[:, -1], by[:, -1], z[:, -1]], -1)[:, None] \
                + rng.normal(0, 1, (n, k, 3)) * np.array([0.03, 0.03, 0.05]) - np.array([0, 0, 0.04])
            Vs = np.stack([P, P + rng.normal(0, 0.02, (n, k, 3)), P + rng.normal(0, 0.02, (n, k, 3))],
                          2).reshape(-1, 3)
            m.tris(Vs, np.arange(len(Vs)).reshape(-1, 3), rnd=np.repeat(rnd, 3 * k), h=1.0)

    # -- poles, wires, fences ------------------------------------------------------------------
    def poles(self):
        """A power line down the left of the road (tall poles, one crossarm, three wires, now
        and then a transformer) and a telephone line down the right (shorter, two crossarms of
        insulators), their wires sagging between leaning poles."""
        wood, wires = Mesh(), Mesh()
        up = np.array([0.0, 0.0, 1.0])
        # (x, first pole's y, span, height, crossarms): phased so that no pole stands up out of
        # the figure's head in the low or the close shot
        for x0, y0, span, ht, arms in ((-8.5, -60.0, 60.0, 11.0, 1), (9.5, -38.0, 48.0, 8.2, 2)):
            rng = np.random.default_rng(int(span))
            ys = y0 + span * np.arange(int((2600.0 - y0) / span)) + rng.uniform(-1.5, 1.5, int((2600.0 - y0) / span))
            tops = []
            for y in ys:
                at = np.array([x0 + rng.normal(0, 0.25), y, 0.0])
                h = ht * rng.uniform(0.94, 1.06)
                R = _rot(rng.normal(0, 0.03), abs(rng.normal(0, 0.022)), rng.uniform(0, 2 * np.pi))
                wood.tube(np.array([[0, 0, -0.5], [0, 0, h * 0.5], [0, 0, h]]) @ R.T + at,
                          [0.16, 0.135, 0.11], 7)
                ends = []
                for a in range(arms):
                    z = h - 0.35 - a * 0.75
                    wood.box(np.array([0, 0, z]) @ R.T + at, (2.5 if arms == 1 else 1.9, 0.1, 0.11), R)
                    for s in (-1, 1):                          # braces
                        wood.tube(np.array([[s * 0.1, 0, z - 0.75], [s * 0.72, 0, z - 0.03]]) @ R.T + at,
                                  0.025, 4, cap=False)
                    for u in ([-1.1, 0.0, 1.1] if arms == 1 else [-0.85, -0.45, 0.45, 0.85]):
                        zz = h + 0.18 if arms == 1 and u == 0 else z + 0.16
                        ins = np.array([[u, 0, zz - 0.18], [u, 0, zz]]) @ R.T + at
                        wood.tube(ins, 0.05 if arms == 1 else 0.035, 6)
                        ends.append(ins[-1])
                if arms == 1 and rng.uniform() < 0.12:           # a transformer can
                    c = np.array([0.28, 0, h - 2.1]) @ R.T + at
                    wood.tube([c - 0.45 * up, c + 0.45 * up], 0.26, 10)
                tops.append(np.array(ends))
            t = np.linspace(0, 1, 16)[:, None]
            for a, b in zip(tops, tops[1:]):                      # catenaries
                for p, q in zip(a, b):
                    sag = (0.013 * np.linalg.norm(q - p) + rng.uniform(0, 0.25)) * 4 * t * (1 - t)
                    wires.tube(p + (q - p) * t - up * sag, 0.011, 3, cap=False)
        self.place(wood, "poles", self.plain("weathered_wood", (0.09, 0.075, 0.06), 0.85, 0.2))
        self.place(wires, "wires", self.plain("wire", (0.03, 0.03, 0.03), 0.4, 0.6))

    def fences(self):
        """Barbed-wire fences along the right of way: crooked cedar posts every few metres,
        now and then a steel T-post, four strands."""
        rng = self.rng
        posts, strands = Mesh(), Mesh()
        seg = np.linspace(0, 1, 4)[:, None]
        for x0 in (-15.5, 16.0):
            y, pts = -40.0, []
            while y < 1400.0:
                x = x0 + rng.normal(0, 0.06)
                h = rng.uniform(1.15, 1.4)
                if rng.uniform() < 0.18:
                    posts.tube([[x, y, -0.3], [x, y, h - 0.1]], 0.025, 4)
                else:
                    wx, wy = rng.normal(0, 0.05, 2)
                    posts.tube([[x, y, -0.3], [x + wx, y + wy, h * 0.5], [x + 1.6 * wx, y + 1.6 * wy, h]],
                               [0.075, 0.065, 0.05], 5)
                pts.append((x, y))
                y += rng.uniform(3.4, 4.3)
            P = np.array(pts)
            for z in (0.4, 0.68, 0.95, 1.18):
                zz = z + rng.normal(0, 0.03, len(P))
                for i in range(0, len(P) - 1, 6):                 # a strand, six posts at a time
                    line = []
                    for j in range(i, min(i + 6, len(P) - 1)):
                        a, b = np.array([*P[j], zz[j]]), np.array([*P[j + 1], zz[j + 1]])
                        line.append((a + (b - a) * seg - np.array([0, 0, 0.24]) * seg * (1 - seg))[:-1])
                    line.append(np.array([[*P[j + 1], zz[j + 1]]]))
                    strands.tube(np.concatenate(line), 0.0045, 3, cap=False)
        self.place(posts, "fence_posts", self.looks["weathered_wood"])
        self.place(strands, "fence_wire", self.looks["wire"])

    # -- trees ---------------------------------------------------------------------------------
    def _branch(self, wood, tips, rng, p, d, length, r, depth, kind):
        k = 3 if r > 0.06 else 2
        pts = [p]
        dd = np.array(d, float)
        for _ in range(k):
            dd = dd + rng.normal(0, 0.18, 3) * (0.5 if kind == "oak" else 1.0)
            if kind == "oak" and depth < 2:
                dd[2] *= 0.85
            dd /= np.linalg.norm(dd)
            pts.append(pts[-1] + dd * length / k)
        wood.tube(np.array(pts), np.linspace(r, r * 0.62, k + 1),
                  6 if r > 0.15 else 4 if r > 0.05 else 3, cap=False)
        if depth == 0 or r < 0.03:
            tips.append(pts[-1])
            return
        for _ in range(rng.integers(2, 4)):
            nd = dd + rng.normal(0, 0.55, 3)
            nd[2] = abs(nd[2]) * (0.5 if kind == "oak" else 1.0) + (0.1 if kind == "oak" else 0.25)
            self._branch(wood, tips, rng, pts[-1], nd / np.linalg.norm(nd),
                         length * rng.uniform(0.55, 0.78), r * 0.62, depth - 1, kind)

    def tree(self, wood, leaves, x, y, kind, scale=1.0, leaf=1.0):
        """A mesquite (a few leaning stems, a wide lacy crown), a live oak (a thick trunk,
        long low limbs, a broad dense dome) or a dead tree (bare limbs)."""
        rng = np.random.default_rng(int(abs(x) * 131 + abs(y) * 17) % 100000)
        tips = []
        base = np.array([x, y, -0.2])
        if kind == "mesquite":
            for _ in range(rng.integers(2, 4)):
                a = rng.uniform(0, 2 * np.pi)
                d = np.array([math.cos(a) * 0.45, math.sin(a) * 0.45, 1.0])
                self._branch(wood, tips, rng, base, d / np.linalg.norm(d), 2.4 * scale,
                             0.14 * scale, 3, kind)
            _leaves(leaves, rng, np.array(tips), np.full(len(tips), 1.3 * scale), int(70 * leaf),
                    0.22 * scale, 0.45, rnd=rng.uniform())
        elif kind == "oak":
            top = base + [0, 0, 2.4 * scale]
            wood.tube([base, top], [0.45 * scale, 0.38 * scale], 8, cap=False)
            for _ in range(rng.integers(4, 7)):
                a = rng.uniform(0, 2 * np.pi)
                d = np.array([math.cos(a), math.sin(a), rng.uniform(0.25, 0.7)])
                self._branch(wood, tips, rng, top, d / np.linalg.norm(d), 3.4 * scale,
                             0.24 * scale, 3, kind)
            _leaves(leaves, rng, np.array(tips) + [0, 0, 0.6 * scale], np.full(len(tips), 1.9 * scale),
                    int(110 * leaf), 0.3 * scale, 0.55, rnd=rng.uniform())
        else:
            d = np.array([rng.normal(0, 0.15), rng.normal(0, 0.15), 1.0])
            self._branch(wood, tips, rng, base, d / np.linalg.norm(d), 3.2 * scale,
                         0.28 * scale, 4, "dead")

    def trees(self):
        """Pasture trees placed for the three shots: within a few degrees of the sun for the
        wide shot (the long lens stacks them up), to the left for the low shot, to the right
        for the close one; then a scatter further out."""
        rng = self.rng
        near, far = (Mesh(), Mesh()), (Mesh(), Mesh())          # (wood, leaves)
        for x, y, kind, s in (
                (-24.0, 330.0, "mesquite", 1.3), (31.0, 610.0, "oak", 1.4), (-44.0, 820.0, "oak", 1.6),
                (12.0, 1150.0, "mesquite", 1.5), (58.0, 1350.0, "oak", 1.8), (-80.0, 1500.0, "oak", 2.0),
                (-36.0, 120.0, "mesquite", 1.1), (-60.0, 70.0, "dead", 1.3), (-95.0, 210.0, "oak", 1.5),
                (-150.0, 330.0, "mesquite", 1.3), (-210.0, 160.0, "oak", 1.7), (-120.0, 480.0, "oak", 1.6),
                (40.0, 55.0, "mesquite", 1.2), (75.0, 140.0, "oak", 1.6), (130.0, 95.0, "mesquite", 1.3),
                (150.0, 260.0, "oak", 1.9), (230.0, 180.0, "mesquite", 1.4), (95.0, 400.0, "dead", 1.6),
                (300.0, 420.0, "oak", 2.0), (-330.0, 640.0, "oak", 1.9), (-240.0, 900.0, "mesquite", 1.6)):
            self.tree(*(near if math.hypot(x, y) < 260 else far), x, y, kind, s)
        for _ in range(26):
            y = rng.uniform(250, 1800)
            self.tree(*far, rng.choice([-1, 1]) * rng.uniform(30, 0.6 * y), y,
                      "mesquite" if rng.uniform() < 0.55 else "oak", rng.uniform(1.2, 1.9), leaf=0.6)
        bark = self.plain("bark", (0.05, 0.04, 0.032), 0.9, 0.2)
        green = self.plain("leaves", (0.05, 0.055, 0.025), 0.7, 0.3, translucent=0.35, var=0.5)
        for (wood, leaves), tag, shadow in ((near, "tree", True), (far, "far_tree", False)):
            self.place(wood, tag + "_wood", bark, shadow=shadow)
            self.place(leaves, tag + "_leaves", green, shadow=shadow)

    # -- far off: a windpump, a farmhouse and barn, the tree line, the hills ------------------
    def far_country(self):
        rng = self.rng
        iron, farm, crowns, hills = Mesh(), Mesh(), Mesh(), Mesh()
        self._windpump(iron, -34.0, 720.0)
        self._farm(farm, 72.0, 330.0)
        # the tree line: crowns only, along field edges a kilometre or three out
        for row_y, n, spread in ((1300.0, 60, 1300.0), (2000.0, 90, 2600.0), (2900.0, 90, 4400.0)):
            for x in rng.uniform(-spread, spread, n):
                y = row_y + rng.normal(0, 120)
                h = rng.uniform(7, 13)
                k = rng.integers(3, 6)
                C = np.stack([x + rng.normal(0, h * 0.45, k), y + rng.normal(0, h * 0.3, k),
                              h * rng.uniform(0.45, 0.8, k)], -1)
                _leaves(crowns, rng, C, rng.uniform(0.3, 0.45, k) * h, 70, 0.9, 0.6, rnd=rng.uniform())
        # two ridges of low hills, the nearer lower
        xs = np.linspace(-14000, 14000, 420)
        n = len(xs)
        i = np.arange(n - 1)
        for y0, hmin, hmax, amp in ((2400.0, 10.0, 38.0, 500.0), (4600.0, 40.0, 120.0, 1200.0)):
            f, hh = np.zeros(n), np.zeros(n)
            for k in range(6):
                fr = rng.uniform(0.3, 1.0) * 2 ** k / 14000 * 2 * np.pi
                ph = rng.uniform(0, 2 * np.pi, 2)
                f += np.sin(xs * fr + ph[0]) / (k + 1)
                hh += np.sin(xs * fr * 1.3 + ph[1]) / (k + 1) ** 1.2
            hh = hmin + (hmax - hmin) * (hh - hh.min()) / (np.ptp(hh) + 1e-9)
            ys = y0 + f * amp / 2
            V = np.concatenate([np.stack([xs, ys - hh * 6, np.full(n, -2.0)], -1),
                                np.stack([xs, ys, hh], -1),
                                np.stack([xs, ys + hh * 8, np.full(n, -2.0)], -1)])
            hills.tris(V, np.concatenate([np.stack([i, i + 1, n + i + 1], -1),
                                          np.stack([i, n + i + 1, n + i], -1),
                                          np.stack([n + i, n + i + 1, 2 * n + i + 1], -1),
                                          np.stack([n + i, 2 * n + i + 1, 2 * n + i], -1)]))
        self.place(iron, "windpump", self.plain("iron", (0.03, 0.028, 0.026), 0.6, 0.5), shadow=False)
        self.place(farm, "farm", self.plain("boards", (0.1, 0.09, 0.08), 0.8, 0.3), shadow=False)
        self.place(crowns, "tree_line", self.plain("far_leaves", (0.035, 0.035, 0.02), 0.8, 0.2),
                   shadow=False)
        self.place(hills, "hills", self.plain("hills", (0.05, 0.04, 0.03), 0.9, 0.2), smooth=True,
                   shadow=False)

    @staticmethod
    def _windpump(m, x, y):
        """A lattice tower with its wheel of blades turned to the wind, a tail vane, a stock
        tank at its foot."""
        h, b, t = 10.0, 1.6, 0.35
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.tube([[x + sx * b, y + sy * b, -0.2], [x + sx * t, y + sy * t, h]], 0.05, 4)
        step = (h - 1.3) / 5
        corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
        for z in np.linspace(0.3, h - 1.0, 6):                 # girts and diagonal braces
            w = b + (t - b) * z / h
            w2 = b + (t - b) * min(h, z + step) / h
            for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
                m.tube([[x + ax * w, y + ay * w, z], [x + bx * w, y + by * w, z]], 0.025, 3, cap=False)
                m.tube([[x + ax * w, y + ay * w, z], [x + bx * w2, y + by * w2, z + step]], 0.018, 3,
                       cap=False)
        m.box((x, y, h + 0.05), (1.0, 1.0, 0.08))               # the platform
        hub = np.array([x, y - 0.7, h + 0.9])
        ang = math.radians(35)
        ax = np.array([math.sin(ang), -math.cos(ang), 0.0])
        u = np.array([math.cos(ang), math.sin(ang), 0.0])
        v = np.array([0.0, 0.0, 1.0])
        for k in range(18):
            a = 2 * np.pi * k / 18
            dr, dt = math.cos(a) * u + math.sin(a) * v, -math.sin(a) * u + math.cos(a) * v
            m.quad([hub + dr * 0.5, hub + dr * 1.8, hub + dr * 1.8 + dt * 0.3 + ax * 0.08,
                    hub + dr * 0.5 + dt * 0.12])
        for r in (0.5, 1.2, 1.8):                                # the wheel's rims
            m.tube([hub + r * (math.cos(a) * u + math.sin(a) * v) for a in np.linspace(0, 2 * np.pi, 25)],
                   0.03, 3, cap=False)
        tail = hub - ax * 3.2
        m.tube([hub, tail], 0.04, 4)
        m.quad([tail + v * 0.8, tail - v * 0.3, tail - ax * 1.5 - v * 0.1, tail - ax * 1.5 + v * 0.7])
        m.tube([[x - 1.5, y + 3.5, -0.2], [x - 1.5, y + 3.5, 1.0]], 2.4, 20)

    def _farm(self, m, x, y):
        """A farmhouse with a porch and a chimney, a gambrel-roofed barn, a pecan by the house."""
        at = np.array([x, y, 0.0])
        R = _rot(0.4)
        w, d, wall, rh = 9.0, 7.0, 3.0, 4.5 * math.tan(math.radians(38))
        m.box(np.array([0, 0, wall / 2 - 0.3]) @ R.T + at, (w, d, wall + 0.6), R)
        for s in (-1, 1):
            m.quad(np.array([[s * (w / 2 + 0.4), -d / 2 - 0.3, wall - 0.25], [0, -d / 2 - 0.3, wall + rh],
                             [0, d / 2 + 0.3, wall + rh], [s * (w / 2 + 0.4), d / 2 + 0.3, wall - 0.25]]) @ R.T + at)
            m.tris(np.array([[-w / 2, s * d / 2, wall], [0, s * d / 2, wall + rh],
                             [w / 2, s * d / 2, wall]]) @ R.T + at, [(0, 1, 2)])
        m.box(np.array([2.2, 0.8, wall + rh]) @ R.T + at, (0.6, 0.6, 2.4), R)   # chimney
        for px in (-4.0, -1.3, 1.3, 4.0):                        # the porch
            m.tube(np.array([[px, -5.2, 0], [px, -5.2, 2.5]]) @ R.T + at, 0.08, 4)
        m.quad(np.array([[-4.6, -3.5, 2.9], [4.6, -3.5, 2.9], [4.6, -5.6, 2.4], [-4.6, -5.6, 2.4]]) @ R.T + at)
        bat = at + [26.0, 30.0, 0.0]
        R2 = _rot(-0.25)
        m.box(np.array([0, 0, 2.2]) @ R2.T + bat, (12.0, 16.0, 5.0), R2)
        prof = [(-6.4, 4.6), (-4.6, 7.4), (0.0, 9.2), (4.6, 7.4), (6.4, 4.6)]
        for a, b in zip(prof, prof[1:]):
            m.quad(np.array([[a[0], -8.3, a[1]], [b[0], -8.3, b[1]], [b[0], 8.3, b[1]], [a[0], 8.3, a[1]]]) @ R2.T + bat)
        for s in (-1, 1):
            m.tris(np.array([[p[0], s * 8.0, p[1]] for p in prof] + [[0, s * 8.0, 4.6]]) @ R2.T + bat,
                   [(5, 0, 1), (5, 1, 2), (5, 2, 3), (5, 3, 4)])
        wood, leaves = Mesh(), Mesh()
        self.tree(wood, leaves, x - 9.0, y + 6.0, "oak", 1.9)
        self.place(wood, "farm_tree_wood", self.looks["bark"], shadow=False)
        self.place(leaves, "farm_tree_leaves", self.looks["leaves"], shadow=False)

    # -- the air -------------------------------------------------------------------------------
    def dust(self):
        """A thin dust over the road round the figure, thinning with height, that the low sun
        shines through."""
        if not self.eevee:
            return
        M, O = self.M, self.O
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(O.x, O.y + 10 * M, O.z + 7 * M))
        ob = bpy.context.object
        ob.name = "dust"
        ob.scale = (80 * M, 140 * M, 14 * M)
        ba._try(ob, "visible_shadow", False)
        m = bpy.data.materials.new("dust")
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        vol = nb.node("ShaderNodeVolumePrincipled", Anisotropy=0.72)
        nb.set(vol.inputs["Color"], (1.0, 0.86, 0.7))
        z = nb.xyz(nb.vec("SCALE", nb.vec("SUBTRACT", nb.node("ShaderNodeNewGeometry").outputs["Position"],
                                          tuple(O)), 1 / M))[2]
        nb.set(vol.inputs["Density"], nb.mul(nb.math("EXPONENT", nb.math("DIVIDE", z, -3.5)),
                                             float(self.look["dust"]) / M))
        m.node_tree.links.new(vol.outputs[0], out.inputs["Volume"])
        ob.data.materials.append(m)
        ee = self.sc.eevee
        ba._try(ee, "volumetric_tile_size", "8")
        ba._try(ee, "volumetric_samples", 48)
        ba._try(ee, "use_volumetric_shadows", True)
        ba._try(ee, "volumetric_shadow_samples", 12)
        ba._try(ee, "volumetric_start", 0.02 * M)
        ba._try(ee, "volumetric_end", 90 * M)

    # -- the sun as the camera sees it ---------------------------------------------------------
    def sun_disc(self):
        """An emissive card facing the camera, as wide as the sun, white-gold in the middle
        reddening to the limb, a touch flattened by the air at the horizon. Camera rays only;
        kept at infinity (moved with the camera, see ColdOpen.apply)."""
        r0 = DISC_AT * math.tan(math.radians(self.sun["size"]) / 2)
        bpy.ops.mesh.primitive_circle_add(vertices=96, radius=r0, fill_type="TRIFAN")
        ob = bpy.context.object
        ob.name = "sun_disc"
        ob.scale = (1.0, 0.93, 1.0)
        for flag in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
                     "visible_volume_scatter"):
            ba._try(ob, flag, False)
        m = bpy.data.materials.new("sun_disc")
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        r = nb.math("DIVIDE", nb.vec("LENGTH", nb.node("ShaderNodeTexCoord").outputs["Object"], out=1), r0)
        em = nb.node("ShaderNodeEmission", Strength=float(self.look["sun_disc"]))
        nb.set(em.inputs["Color"], nb.mix(nb.smooth(r, 0.15, 1.0), (1.0, 0.62, 0.24), (0.95, 0.2, 0.025)))
        tr = nb.node("ShaderNodeBsdfTransparent")
        m.node_tree.links.new(nb.shader_mix(nb.smooth(r, 0.93, 1.0), em.outputs[0], tr.outputs[0]),
                              out.inputs["Surface"])
        ba._try(m, "surface_render_method", "BLENDED")
        ob.data.materials.append(m)

    # -- the lens: exposure, bloom, sun beams --------------------------------------------------
    def compositor(self):
        """The exposure first (so the glare's thresholds hold in every shot), then bloom from
        every highlight and sun beams from the sun's disc alone: the picture through an ellipse
        round the disc (moved every frame), so where the figure hides the sun its beams are
        missing."""
        sc = self.sc
        ng = bpy.data.node_groups.new("cold_open_lens", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        sc.compositing_node_group = ng
        ba._try(sc.render, "use_compositing", True)
        ba._try(sc.render, "compositor_device", "GPU")
        nb = NB(ng)
        rl = nb.node("CompositorNodeRLayers")
        self.gain = nb.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", Factor=1.0)
        ng.links.new(rl.outputs["Image"], self.gain.inputs[6])
        img = self.gain.outputs[2]
        self.mask = nb.node("CompositorNodeEllipseMask")
        src = nb.mix(1.0, img, self.mask.outputs["Mask"], "MULTIPLY")

        def glare(source, kind, **kw):
            g = nb.node("CompositorNodeGlare", Type=kind, Quality="High")
            for k, v in kw.items():
                nb.set(g.inputs[k], v)
            ng.links.new(source, g.inputs["Image"])
            return g.outputs["Glare"]
        bloom = glare(img, "Bloom", Threshold=1.4, Smoothness=0.5, Strength=0.4, Size=0.75,
                      Tint=(1.0, 0.78, 0.55))
        self.beams = glare(src, "Sun Beams", Threshold=1.0, Smoothness=0.5, Strength=0.18,
                           Size=0.3, Tint=(1.0, 0.72, 0.45)).node
        out = nb.mix(1.0, nb.mix(1.0, img, bloom, "ADD"), self.beams.outputs["Glare"], "ADD")
        ng.links.new(out, nb.node("NodeGroupOutput").inputs[0])

    # -- per frame -----------------------------------------------------------------------------
    def frame(self, cam, shot, ev, focus):
        """The lens for this frame: exposed (`ev`, trimmed per shot) and focused on the figure
        (`focus`: a point on it); the sun beams and their mask follow the sun on screen."""
        g = 2.0 ** (ev + self.TRIM.get(shot, 0.0))
        sock = self.gain.inputs[7]
        if abs(sock.default_value[0] - g) > 1e-6:
            sock.default_value = (g, g, g, 1.0)
        cd = cam.data
        mw = cam.matrix_world
        s = max(0.05, (focus - mw.translation).dot(-(mw.to_3x3() @ Vector((0, 0, 1)))))
        f = cd.lens / 1000.0
        b = self.BLUR.get(shot, 0.012) * cd.sensor_width / 1000.0   # the blur of infinity
        cd.dof.use_dof = True
        cd.dof.focus_distance = s
        cd.dof.aperture_fstop = max(0.5, f * f / (b * max(1e-3, s - f)))
        cd.dof.aperture_blades = 0
        cd.dof.aperture_ratio = 1.6                                   # oval, anamorphic bokeh
        from bpy_extras.object_utils import world_to_camera_view
        p = world_to_camera_view(self.sc, cam, mw.translation + self.sun_dir * DISC_AT)
        w = 1.6 * self.sun["size"] / math.degrees(2 * math.atan(cd.sensor_width / 2 / cd.lens))
        self.beams.inputs["Sun Position"].default_value = (p.x, p.y)
        self.mask.inputs["Position"].default_value = (p.x, p.y)
        self.mask.inputs["Size"].default_value = (w, w * 0.93)


# ---------------------------------------------------------------------------- night_desk
DESK_LOOK = {"exposure": 0.9,       # EV
             "moon_strength": 3.4, "moon_color": "#9DB8FF",   # through the window, W/m2
             "lamp_gain": 2.5,      # the model's LEDs (their own power, as the animator's) x this
             "spill_strength": 2.2,  # W: the lamp's soft glow onto the room, at full brightness
             "spill_color": "#FF7040",
             "look": "AgX - Medium High Contrast"}


class NightDesk:
    """A bedroom at night, at the model's real size (a LEGO lamp is a real lamp): a wooden desk
    against the wall under a window of moonlit blue night (a moon, stars, trees against the
    sky), curtains, books, a mug, a plant and a notebook; the moon the only light until the
    lamp comes on, then the lamp's LEDs (and a soft glow of its own round the dome) light the
    desk, the wall and the props. Distances in metres: u across (right as the camera sees the
    model's front), v into the room's back wall, z up from the desk top; the model stands at
    the origin."""

    BLUR = {"room": 0.018, "close": 0.04}   # the blur of infinity per shot, / frame width
    TRIM = {}
    SAMPLES = 2 / 3                         # of the job's: 2,900 parts of glass and plastic are
    #                                         slow to sample, and 32 look the same as 48

    def __init__(self, sc, co, eevee):
        self.sc, self.co, self.eevee = sc, co, eevee
        self.look = dict(DESK_LOOK, **(co.get("look") or {}))
        px, pz = co["pivot"]
        self.O = Vector((px * LDU, pz * LDU, -co["ground_y"] * LDU))
        f = math.radians(float(co.get("front", 0.0)))
        # the model's front (LDraw, view_basis) is (sin f, 0, -cos f): Blender (sin f, -cos f, 0);
        # the room runs the other way, away from the camera
        self.F = Vector((-math.sin(f), math.cos(f), 0.0))
        self.R = self.F.cross(Vector((0.0, 0.0, 1.0)))
        self.Mw = Matrix((self.R.to_4d(), self.F.to_4d(), (0, 0, 1, 0), (0, 0, 0, 1))).transposed()
        self.Mw.translation = self.O
        self.rng = np.random.default_rng(1983)
        self.world()
        self.room()
        self.window_view()
        self.desk_props()
        self.lights()
        self.compositor()
        ee = sc.eevee
        ba._try(ee, "bokeh_threshold", 1e5)
        ba._try(ee, "bokeh_max_size", 80.0)
        sc.view_settings.view_transform = "AgX"
        ba._try(sc.view_settings, "look", self.look["look"])
        sc.view_settings.exposure = 0.0

    # -- helpers ------------------------------------------------------------------------------
    def mat(self, name, color, rough=0.6, spec=0.4, build=None):
        m = bpy.data.materials.new(name)
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        bsdf = nb.node("ShaderNodeBsdfPrincipled", Roughness=rough)
        nb.set(bsdf.inputs["Specular IOR Level"], spec)
        nb.set(bsdf.inputs["Base Color"], color if build is None else build(nb))
        m.node_tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
        return m, nb, bsdf

    def place(self, mesh, name, mat, smooth=False, shadow=True):
        ob = mesh.build(name, mat, 1.0, (0, 0, 0), smooth)
        if ob is None:
            return None
        ob.scale = (1, 1, 1)
        ob.matrix_world = self.Mw.copy()
        if not shadow:
            ba._try(ob, "visible_shadow", False)
        return ob

    def box(self, m, lo, hi, R=None):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        m.box((lo + hi) / 2, hi - lo, R)

    # -- the room -----------------------------------------------------------------------------
    def world(self):
        """A faint blue night for whatever the window and the lamp don't reach."""
        w = bpy.data.worlds.new("night")
        self.sc.world = w
        nb = NB(w.node_tree)
        out = nb.clear("OUTPUT_WORLD")
        bg = nb.node("ShaderNodeBackground", Strength=0.05)
        nb.set(bg.inputs["Color"], (0.35, 0.45, 0.85))
        w.node_tree.links.new(bg.outputs[0], out.inputs["Surface"])
        ba._try(w, "sun_threshold", 1e6)

    WIN = (-0.85, -0.05, 0.1, 1.2)         # window opening: u from, to; z from, to: its right
    #                                        edge behind the model, plain wall to the right
    WALL_V = 0.31                           # the wall's face behind the desk
    WALL_T = 0.13                           # its thickness (the window's reveal)

    def room(self):
        wall, desk, frame, floor = Mesh(), Mesh(), Mesh(), Mesh()
        u0, u1, z0, z1 = self.WIN
        v, t = self.WALL_V, self.WALL_T
        # the wall round the window: four slabs, and the reveal
        for lo, hi in (((-3.0, v, -0.76), (u0, v + t, 2.2)), ((u1, v, -0.76), (3.0, v + t, 2.2)),
                       ((u0, v, -0.76), (u1, v + t, z0)), ((u0, v, z1), (u1, v + t, 2.2))):
            self.box(wall, lo, hi)
        # a side wall far left, a ceiling (so the moon only comes in through the window)
        self.box(wall, (-3.1, -3.0, -0.76), (-3.0, v + t, 2.2))
        self.box(wall, (-3.0, -3.0, 2.2), (3.0, v + t, 2.3))
        # the window: frame, mullions, sash bars, a sill inside
        fw = 0.045
        for lo, hi in (((u0, v + 0.05, z0), (u0 + fw, v + 0.09, z1)),
                       ((u1 - fw, v + 0.05, z0), (u1, v + 0.09, z1)),
                       ((u0, v + 0.05, z0), (u1, v + 0.09, z0 + fw)),
                       ((u0, v + 0.05, z1 - fw), (u1, v + 0.09, z1)),
                       (((u0 + u1) / 2 - 0.02, v + 0.055, z0), ((u0 + u1) / 2 + 0.02, v + 0.085, z1)),
                       ((u0, v + 0.055, (z0 + z1) / 2 - 0.02), (u1, v + 0.085, (z0 + z1) / 2 + 0.02))):
            self.box(frame, lo, hi)
        self.box(frame, (u0 - 0.05, v - 0.035, z0 - 0.025), (u1 + 0.05, v + 0.07, z0))   # sill
        # the desk: a top, an apron, legs; the floor
        self.box(desk, (-0.78, -0.4, -0.035), (0.62, v - 0.005, 0.0))
        self.box(desk, (-0.74, -0.37, -0.13), (0.58, -0.35, -0.035))
        for uu in (-0.74, 0.54):
            for vv in (-0.37, v - 0.05):
                self.box(desk, (uu, vv, -0.76), (uu + 0.04, vv + 0.04, -0.035))
        self.box(floor, (-3.0, -3.0, -0.78), (3.0, v, -0.76))
        self.place(wall, "wall", self._wall_mat())
        self.place(desk, "desk", self._wood_mat())
        self.place(frame, "window_frame", self.mat("frame_paint", (0.62, 0.62, 0.6), 0.45, 0.4)[0])
        self.place(floor, "floor", self.mat("floor", (0.08, 0.05, 0.035), 0.5, 0.4)[0])
        self.curtains()
        self.picture()

    def _wall_mat(self):
        def build(nb):
            geo = nb.node("ShaderNodeNewGeometry")
            n = nb.noise(geo.outputs["Position"], 60.0, 4.0, 0.6)
            return nb.mix(nb.mul(n, 0.3), (0.42, 0.4, 0.37), (0.36, 0.34, 0.31))
        return self.mat("wall_paint", None, 0.85, 0.25, build)[0]

    def _wood_mat(self):
        """Varnished walnut: grain along the desk, a glossy top that mirrors the lamp."""
        def build(nb):
            loc = nb.node("ShaderNodeTexCoord").outputs["Object"]
            q = nb.vec("MULTIPLY", loc, (0.6, 18.0, 18.0))        # grain runs along the desk (u)
            warp = nb.noise(nb.vec("MULTIPLY", loc, (1.0, 4.0, 4.0)), 2.0, 3.0, 0.6)
            wave = nb.node("ShaderNodeTexWave", Scale=1.0, Distortion=4.0, Detail=4.0,
                           **{"Detail Scale": 1.5})
            wave.wave_type = "BANDS"
            wave.bands_direction = "Y"
            nb.set(wave.inputs["Vector"], nb.vec("ADD", q, nb.vec("SCALE", nb.comb(0, warp, warp), 0.8)))
            g = nb.smooth(wave.outputs["Fac"], 0.15, 0.95)
            fine = nb.noise(nb.vec("MULTIPLY", loc, (3.0, 400.0, 400.0)), 1.0, 2.0)
            col = nb.mix(g, (0.11, 0.055, 0.026), (0.2, 0.105, 0.05))
            return nb.mix(nb.mul(nb.smooth(fine, 0.4, 0.7), 0.4), col, (0.07, 0.035, 0.016))
        return self.mat("walnut", None, 0.28, 0.5, build)[0]

    def curtains(self):
        """Two curtains drawn back either side of the window, hanging in soft folds."""
        m = Mesh()
        u0, u1, z0, z1 = self.WIN
        for c, w in ((u0 - 0.22, 0.4),):
            nu, nz = 48, 24
            us = np.linspace(c - w / 2, c + w / 2, nu)
            zs = np.linspace(-0.05, z1 + 0.22, nz)
            U, Z = np.meshgrid(us, zs)
            V = self.WALL_V - 0.06 - 0.035 * (0.5 + 0.5 * np.sin((U - c) / w * 2 * np.pi * 3.5)) \
                - 0.01 * np.sin(Z * 7.0)
            P = np.stack([U, V, Z], -1).reshape(-1, 3)
            i = np.arange(nz - 1)[:, None] * nu + np.arange(nu - 1)[None, :]
            F = np.concatenate([np.stack([i, i + 1, i + nu + 1], -1).reshape(-1, 3),
                                np.stack([i, i + nu + 1, i + nu], -1).reshape(-1, 3)])
            m.tris(P, F)
        self.place(m, "curtains", self.mat("curtain", (0.16, 0.2, 0.26), 0.9, 0.2)[0], smooth=True)
        rod = Mesh()
        rod.tube([[u0 - 0.46, self.WALL_V - 0.06, z1 + 0.24], [u1 + 0.1, self.WALL_V - 0.06, z1 + 0.24]],
                 0.012, 8)
        self.place(rod, "curtain_rod", self.mat("brass", (0.35, 0.25, 0.12), 0.3, 0.8)[0])

    def picture(self):
        """A small framed print on the wall right of the window."""
        m = Mesh()
        self.box(m, (0.36, self.WALL_V - 0.02, 0.36), (0.66, self.WALL_V, 0.76))
        self.place(m, "picture_frame", self.mat("frame_black", (0.02, 0.02, 0.02), 0.4, 0.5)[0])
        p = Mesh()
        self.box(p, (0.385, self.WALL_V - 0.022, 0.385), (0.635, self.WALL_V - 0.02, 0.735))
        self.place(p, "picture", self.mat("print", None, 0.7, 0.3, lambda nb: nb.mix(
            nb.smooth(nb.xyz(nb.node("ShaderNodeTexCoord").outputs["Object"])[2], 0.35, 0.65),
            (0.55, 0.42, 0.3), (0.2, 0.3, 0.4)))[0])

    # -- outside ------------------------------------------------------------------------------
    def window_view(self):
        """The night beyond the glass: a sky of deepening blue with stars and a low moon on a
        far backdrop, and trees and a fence line between, dark against it."""
        u0, u1, z0, z1 = self.WIN
        D = 9.0                                            # the backdrop, metres out
        W, Hh = 16.0, 9.0
        bd = Mesh()
        bd.quad([(-W / 2, D, -3.0), (W / 2, D, -3.0), (W / 2, D, Hh), (-W / 2, D, Hh)])
        m = bpy.data.materials.new("night_sky")
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        x, _, z = nb.xyz(nb.node("ShaderNodeTexCoord").outputs["Object"])
        tc = nb.comb(x, 0.0, z)
        h = nb.smooth(z, -0.5, 7.0)
        sky = nb.mix(h, (0.045, 0.09, 0.22), (0.005, 0.01, 0.035))
        glow = nb.math("EXPONENT", nb.mul(nb.vec("LENGTH", nb.vec("SUBTRACT", tc, self.MOON), out=1), -0.55))
        sky = nb.vec("ADD", sky, nb.vec("SCALE", nb.comb(0.06, 0.09, 0.16), glow))
        st = nb.voronoi(nb.vec("MULTIPLY", tc, (1.0, 1.0, 1.0)), 9.0, "F1", "Distance")
        stars = nb.mul(nb.smooth(st, 0.035, 0.0), nb.smooth(nb.noise(tc, 3.0, 2.0), 0.55, 0.7))
        stars = nb.mul(stars, nb.smooth(z, 1.0, 3.0))
        sky = nb.vec("ADD", sky, nb.vec("SCALE", nb.comb(0.8, 0.85, 1.0), nb.mul(stars, 3.0)))
        r = nb.vec("LENGTH", nb.vec("SUBTRACT", tc, self.MOON), out=1)
        moon = nb.smooth(r, 0.27, 0.25)
        crater = nb.smooth(nb.noise(tc, 4.0, 4.0, 0.6), 0.45, 0.7)
        mc = nb.mix(nb.mul(crater, 0.35), (1.0, 0.97, 0.9), (0.72, 0.74, 0.78))
        col = nb.mix(moon, sky, nb.vec("SCALE", mc, 5.0))
        em = nb.node("ShaderNodeEmission", Strength=0.55)
        nb.set(em.inputs["Color"], col)
        m.node_tree.links.new(em.outputs[0], out.inputs["Surface"])
        self.place(bd, "night_sky", m, shadow=False)
        # trees and a fence line between the window and the sky
        trees = Mesh()
        rng = self.rng
        for tu, tv, th, tw in ((-2.2, 5.2, 5.5, 2.6), (1.4, 6.5, 6.8, 3.2), (3.6, 4.4, 4.2, 2.0),
                               (-4.6, 7.0, 6.0, 3.0), (5.8, 7.5, 7.0, 3.4)):
            trees.tube([[tu, tv, -2.5], [tu + rng.normal(0, 0.1), tv, th * 0.55]], [0.18, 0.12], 6)
            k = rng.integers(5, 9)
            C = np.stack([tu + rng.normal(0, tw * 0.3, k), tv + rng.normal(0, 0.4, k),
                          th * rng.uniform(0.5, 0.9, k)], -1)
            _leaves(trees, rng, C, rng.uniform(0.35, 0.55, k) * tw, 420, 0.16, 0.8)
        for fu in np.arange(-6.0, 6.0, 1.3):
            trees.tube([[fu, 3.2, -2.5], [fu, 3.2, -1.3]], 0.04, 4)
        trees.tube([[-6.0, 3.2, -1.5], [6.0, 3.2, -1.5]], 0.012, 4, cap=False)
        trees.tube([[-6.0, 3.2, -1.8], [6.0, 3.2, -1.8]], 0.012, 4, cap=False)
        self.place(trees, "night_trees", self.mat("silhouette", (0.01, 0.012, 0.018), 0.9, 0.2)[0],
                   shadow=False)
        # the ground outside, a dim grey-blue lawn
        g = Mesh()
        g.quad([(-10, 0.5, -2.5), (10, 0.5, -2.5), (10, 9.5, -2.5), (-10, 9.5, -2.5)])
        self.place(g, "lawn", self.mat("lawn", (0.02, 0.03, 0.03), 0.9, 0.2)[0], shadow=False)

    MOON = (-3.3, 0.0, 1.9)                 # on the backdrop (u, -, z): behind the close shot

    # -- the desk's things --------------------------------------------------------------------
    def desk_props(self):
        rng = self.rng
        # books: a stack of three, left and behind
        for i, (w, d, h, col, rot) in enumerate(((0.25, 0.18, 0.032, (0.3, 0.05, 0.04), 0.1),
                                                 (0.23, 0.165, 0.028, (0.42, 0.3, 0.06), -0.05),
                                                 (0.2, 0.15, 0.036, (0.05, 0.16, 0.18), 0.18))):
            z = sum(x[2] for x in ((0.25, 0.18, 0.032), (0.23, 0.165, 0.028), (0.2, 0.15, 0.036))[:i])
            R = _rot(rot)
            c = np.array([-0.44, 0.13, z + h / 2])
            cover, pages = Mesh(), Mesh()
            cover.box(c, (w, d, h), R)
            pages.box(c + R @ np.array([0.004, 0.0, 0.0]), (w - 0.006, d + 0.002, h * 0.8), R)
            self.place(cover, f"book_{i}", self.mat(f"book_{i}", col, 0.55, 0.35)[0])
            self.place(pages, f"pages_{i}", self.mat(f"pages_{i}", (0.55, 0.5, 0.4), 0.8, 0.2)[0])
        # a mug, right, in front
        mug = Mesh()
        mug.tube([[0.3, -0.07, 0.0], [0.3, -0.07, 0.098]], 0.042, 32)
        handle = [[0.3 + 0.042 + 0.028 * math.sin(t), -0.07, 0.05 + 0.03 * math.cos(t)]
                  for t in np.linspace(0.2, np.pi - 0.2, 12)]
        mug.tube(handle, 0.007, 8)
        self.place(mug, "mug", self.mat("ceramic", (0.55, 0.42, 0.18), 0.25, 0.6)[0], smooth=True)
        # a plant in a clay pot, far left
        pot, plant = Mesh(), Mesh()
        pot.tube([[-0.66, 0.2, 0.0], [-0.66, 0.2, 0.09]], [0.045, 0.058], 28)
        for k in range(26):
            ang = rng.uniform(0, 2 * np.pi)
            L = rng.uniform(0.09, 0.18)
            up = rng.uniform(0.5, 1.2)
            base = np.array([-0.66, 0.2, 0.085])
            d = np.array([math.cos(ang), math.sin(ang), up])
            d /= np.linalg.norm(d)
            side = np.cross(d, [0, 0, 1.0])
            side /= np.linalg.norm(side) + 1e-9
            tip = base + d * L - np.array([0, 0, 0.35 * L * L / 0.18])
            mid = base + d * L * 0.5
            w = rng.uniform(0.012, 0.02)
            plant.tris([base - side * w * 0.3, mid - side * w, tip, mid + side * w, base + side * w * 0.3],
                       [(0, 1, 2), (0, 2, 3), (0, 3, 4)])
        self.place(pot, "pot", self.mat("clay", (0.35, 0.14, 0.07), 0.8, 0.3)[0], smooth=True)
        self.place(plant, "plant", self.mat("leaf", (0.04, 0.09, 0.03), 0.6, 0.35)[0])
        # a notebook with a pencil, front right
        nbk, pencil = Mesh(), Mesh()
        R = _rot(-0.35)
        nbk.box(np.array([0.2, -0.24, 0.006]), (0.21, 0.15, 0.012), R)
        self.place(nbk, "notebook", self.mat("notebook", (0.3, 0.27, 0.22), 0.8, 0.2)[0])
        a, b = np.array([0.13, -0.3, 0.017]), np.array([0.29, -0.2, 0.017])
        pencil.tube([a, b], 0.0045, 6)
        self.place(pencil, "pencil", self.mat("pencil", (0.6, 0.38, 0.03), 0.4, 0.4)[0])

    # -- light --------------------------------------------------------------------------------
    def lights(self):
        """The moon through the window (a sun lamp from the moon's side, so the frame's bars
        cross the desk), and the lamp's own soft glow round its dome (off until it's on)."""
        lk = self.look
        md = bpy.data.lights.new("moon", "SUN")
        md.color = tuple(bs.hex_to_linear(lk["moon_color"]))
        md.energy = float(lk["moon_strength"])
        md.angle = math.radians(1.5)
        ba._try(md, "use_shadow_jitter", False)
        mo = bpy.data.objects.new("moon", md)
        self.sc.collection.objects.link(mo)
        into = (self.Mw.to_3x3() @ Vector((0.6, -0.55, -0.55))).normalized()     # moon -> room
        ba._try(md, "specular_factor", 0.6)
        mo.rotation_euler = into.to_track_quat("-Z", "Y").to_euler()
        leds = self.co.get("leds") or []
        if leds:
            c = sum((TO_B @ Vector(L["pos"]) for L in leds), Vector()) / len(leds)
        else:
            c = self.O + Vector((0, 0, 0.2))
        sd = bpy.data.lights.new("lamp_glow", "POINT")
        sd.color = tuple(bs.hex_to_linear(lk["spill_color"]))
        sd.energy = 0.0
        sd.shadow_soft_size = 0.09                     # the dome's size
        ba._try(sd, "use_shadow", False)               # the dome glows all round
        so = bpy.data.objects.new("lamp_glow", sd)
        self.sc.collection.objects.link(so)
        so.location = c
        self.spill, self.spill_ob = sd, so

    def link_lamp(self, parts, leds):
        """Light linking: the LEDs light only the glowing parts they sit in, the glow round
        them lights everything else (the clear shell round them glows faintly from inside) but
        not those (they'd wash out)."""
        glass = bpy.data.collections.new("lamp_glass")
        glowing = bpy.data.collections.new("lamp_glowing")
        for ob in parts:
            m = ob.active_material
            if m is not None and getattr(m, "surface_render_method", "") == "BLENDED":
                glass.objects.link(ob)
                if m.name.endswith("_glow"):
                    glowing.objects.link(ob)
        if not glass.objects:
            return
        only = bpy.data.collections.new("led_receivers")
        only.children.link(glowing if glowing.objects else glass)
        for lo in leds:
            lo.light_linking.receiver_collection = only
        but = bpy.data.collections.new("glow_receivers")
        but.children.link(glowing if glowing.objects else glass)
        but.collection_children[0].light_linking.link_state = "EXCLUDE"
        self.spill_ob.light_linking.receiver_collection = but

    def lamp(self, level):
        """The lamp's brightness this frame (0 off, 1 on, above 1 in the flash as it comes on)."""
        self.spill.energy = float(self.look["spill_strength"]) * max(0.0, level)
        g = min(2.0, max(0.0, level - 1.0))
        self.bloom.inputs["Strength"].default_value = 0.35 + 0.45 * g

    # -- the lens -----------------------------------------------------------------------------
    def compositor(self):
        sc = self.sc
        ng = bpy.data.node_groups.new("cold_open_lens", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        sc.compositing_node_group = ng
        ba._try(sc.render, "use_compositing", True)
        ba._try(sc.render, "compositor_device", "GPU")
        nb = NB(ng)
        rl = nb.node("CompositorNodeRLayers")
        self.gain = nb.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", Factor=1.0)
        ng.links.new(rl.outputs["Image"], self.gain.inputs[6])
        img = self.gain.outputs[2]
        g = nb.node("CompositorNodeGlare", Type="Bloom", Quality="High")
        for k, v in dict(Threshold=0.9, Smoothness=0.6, Strength=0.35, Size=0.8,
                         Tint=(1.0, 0.85, 0.8)).items():
            nb.set(g.inputs[k], v)
        ng.links.new(img, g.inputs["Image"])
        self.bloom = g
        ng.links.new(nb.mix(1.0, img, g.outputs["Glare"], "ADD"), nb.node("NodeGroupOutput").inputs[0])

    def frame(self, cam, shot, ev, focus):
        """Exposed (`ev`) and focused on the model (`focus`), the background as soft as BLUR."""
        g = 2.0 ** (ev + self.TRIM.get(shot, 0.0))
        sock = self.gain.inputs[7]
        if abs(sock.default_value[0] - g) > 1e-6:
            sock.default_value = (g, g, g, 1.0)
        cd = cam.data
        mw = cam.matrix_world
        s = max(0.05, (focus - mw.translation).dot(-(mw.to_3x3() @ Vector((0, 0, 1)))))
        f = cd.lens / 1000.0
        b = self.BLUR.get(shot, 0.02) * cd.sensor_width / 1000.0
        cd.dof.use_dof = True
        cd.dof.focus_distance = s
        cd.dof.aperture_fstop = max(0.5, f * f / (b * max(1e-3, s - f)))
        cd.dof.aperture_blades = 7
        cd.dof.aperture_ratio = 1.0


def night_desk(sc, co, eevee):
    return NightDesk(sc, co, eevee)


# ---------------------------------------------------------------------------- the squid
def _bend_curve(p0, T0, R0, length, n, k1, k2):
    """A curve of n points from p0, `length` long, setting off along T0: at each step its
    tangent turns by k1[i] radians towards R (its own frame's second axis, R0 to start) and by
    k2[i] about it (sideways). Returns (n, 3)."""
    ds = length / (n - 1)
    T, R = np.asarray(T0, float), np.asarray(R0, float)
    Q = np.cross(T, R)
    P = np.empty((n, 3))
    P[0] = p0
    for i in range(1, n):
        c, s = math.cos(k1[i]), math.sin(k1[i])
        T, R = T * c + R * s, R * c - T * s
        c, s = math.cos(k2[i]), math.sin(k2[i])
        T, Q = T * c + Q * s, Q * c - T * s
        P[i] = P[i - 1] + T * ds
    return P


def _tube_rings(P, r, a0, sides):
    """Rings of `sides` vertices round the polyline P (n, 3), radius r (n,) (or (n, 2): across
    and along a0, an ellipse), carried along it by parallel transport from a0 (so a moving
    curve's rings never twist). Returns (n * sides, 3)."""
    n = len(P)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    A = np.empty((n, 3))
    a = np.asarray(a0, float) - T[0] * float(np.dot(a0, T[0]))
    a /= np.linalg.norm(a) + 1e-12
    A[0] = a
    for i in range(1, n):
        v = np.cross(T[i - 1], T[i])
        s = np.linalg.norm(v)
        if s > 1e-9:
            k = v / s
            ang = math.atan2(s, float(np.dot(T[i - 1], T[i])))
            a = a * math.cos(ang) + np.cross(k, a) * math.sin(ang) + k * np.dot(k, a) * (1 - math.cos(ang))
        a = a - T[i] * float(np.dot(a, T[i]))
        a /= np.linalg.norm(a) + 1e-12
        A[i] = a
    B = np.cross(T, A)
    r = np.asarray(r, float)
    ra, rb = (r[:, 0], r[:, 1]) if r.ndim == 2 else (r, r)
    th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = (np.cos(th)[None, :, None] * A[:, None] * ra[:, None, None]
            + np.sin(th)[None, :, None] * B[:, None] * rb[:, None, None])
    return (P[:, None] + ring).reshape(-1, 3)


def _tube_faces(n, sides, base=0, tip=None):
    """Triangles joining n rings of `sides` vertices (from vertex `base`), closed at the end
    with the vertex `tip` if given."""
    i = np.arange(n - 1)[:, None] * sides
    j = np.arange(sides)[None, :]
    a0, a1 = i + j, i + (j + 1) % sides
    F = [np.stack([a0, a1, a1 + sides], -1).reshape(-1, 3),
         np.stack([a0, a1 + sides, a0 + sides], -1).reshape(-1, 3)]
    if tip is not None:
        top = (n - 1) * sides
        F.append(np.stack([top + np.arange(sides), np.full(sides, tip - base),
                           top + (np.arange(sides) + 1) % sides], -1))
    return np.concatenate(F) + base


class Squid:
    """A giant squid, built procedurally and posed every frame: a long mantle tapering to a
    point with a pair of fins at its tip, the head with two great eyes, eight thick arms and
    two long feeding tentacles ending in clubs. Its own frame, in mantle lengths: the arms point
    down -Y from the head (y -0.17..0), the mantle runs up to its tip at y = 1, its back
    (dorsal) is +Z. `pose(t, reach, writhe)`: the arms writhe and curl (more with `writhe`),
    the tentacles uncoil from curled (reach 0) to reaching straight out ahead (1), the fins
    ripple and the mantle breathes. Dark red-brown skin; its edges catch the light from above
    (`rim`, emission, 0..), its eyes a dull gold glint (`glint`)."""

    BODY = ((-0.19, 0.06), (-0.175, 0.08), (-0.15, 0.092), (-0.1, 0.106), (-0.05, 0.1),
            (-0.008, 0.11), (0.03, 0.15), (0.1, 0.158), (0.25, 0.158), (0.45, 0.142),
            (0.62, 0.112), (0.78, 0.078), (0.88, 0.048), (0.95, 0.022), (0.985, 0.007))
    ARM_N, TENT_N, SIDES = 30, 52, 10

    def __init__(self, name="squid", seed=7, eyes=True):
        self.rng = np.random.default_rng(seed)
        rng = self.rng
        ys = np.linspace(-0.19, 0.985, 46)
        tab = np.array(self.BODY)
        self.body_r = np.interp(ys, tab[:, 0], tab[:, 1])
        self.body_P = np.stack([np.zeros_like(ys), ys, np.zeros_like(ys)], 1)
        # arms round the head's front, the tentacles' bases between the ventral pairs (-Z)
        self.arms = []
        for i in range(8):
            phi = 2 * math.pi * i / 8 + math.pi / 8
            rho = np.array([math.cos(phi), 0.0, math.sin(phi)])
            ventral = -math.sin(phi)                         # 1 underneath, -1 on its back
            self.arms.append(dict(rho=rho, length=0.92 + 0.12 * ventral + rng.uniform(-0.05, 0.05),
                                  r0=0.044 + 0.006 * ventral, phase=rng.uniform(0, 2 * math.pi),
                                  rate=rng.uniform(0.75, 1.15), side=rng.choice([-1.0, 1.0]),
                                  n=self.ARM_N, tent=False))
        for sgn in (-1.0, 1.0):
            phi = -math.pi / 2 + sgn * 0.42
            rho = np.array([math.cos(phi), 0.0, math.sin(phi)])
            self.arms.append(dict(rho=rho, length=2.3 + rng.uniform(-0.08, 0.08), r0=0.02,
                                  phase=rng.uniform(0, 2 * math.pi), rate=rng.uniform(0.8, 1.1),
                                  side=sgn, n=self.TENT_N, tent=True))
        # the fins: a heart-shaped pair across the mantle's tip, a grid ny x nx
        self.fin_y = np.linspace(0.6, 1.06, 18)
        u = (self.fin_y - 0.6) / 0.46
        self.fin_w = 0.32 * np.sin(np.pi * np.clip(u, 0, 1) ** 0.85) ** 0.75 * (1.0 - 0.25 * u) + 0.004
        self.fin_x = np.linspace(-1.0, 1.0, 11)
        # topology: body, fins, arms, tentacles
        S = self.SIDES
        F, base = [], 0
        self.slices = {}
        nb = len(ys)
        F.append(_tube_faces(nb, 16, base, tip=base + nb * 16))
        self.slices["body"] = (base, base + nb * 16 + 1)
        base += nb * 16 + 1
        ny, nx = len(self.fin_y), len(self.fin_x)
        g = np.arange(ny - 1)[:, None] * nx + np.arange(nx - 1)[None, :]
        F.append((np.concatenate([np.stack([g, g + 1, g + nx + 1], -1).reshape(-1, 3),
                                  np.stack([g, g + nx + 1, g + nx], -1).reshape(-1, 3)]) + base))
        self.slices["fins"] = (base, base + ny * nx)
        base += ny * nx
        for k, a in enumerate(self.arms):
            F.append(_tube_faces(a["n"], S, base, tip=base + a["n"] * S))
            self.slices[k] = (base, base + a["n"] * S + 1)
            base += a["n"] * S + 1
        self.nv = base
        F = np.concatenate(F).astype(np.int32)
        me = bpy.data.meshes.new(name)
        me.vertices.add(self.nv)
        me.loops.add(F.size)
        me.loops.foreach_set("vertex_index", F.ravel())
        me.polygons.add(len(F))
        me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3, dtype=np.int32))
        me.polygons.foreach_set("use_smooth", np.ones(len(F), bool))
        self.mesh = me
        self.V = np.zeros((self.nv, 3))
        self.pose(0.0)
        me.update(calc_edges=True)
        self.rim = []
        me.materials.append(self._skin(name))
        me.materials.append(self._skin(name + "_fin", rim=0.15, spec=0.25))
        fa, fb = self.slices["fins"]
        tri = F.reshape(-1, 3)
        fin = (tri[:, 0] >= fa) & (tri[:, 0] < fb)
        me.polygons.foreach_set("material_index", fin.astype(np.int32))
        self.ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(self.ob)
        ba._try(self.ob, "visible_shadow", False)
        self.eyes = []
        if eyes:
            self._eyes(name)

    def _skin(self, name, rim=1.0, spec=0.7):
        """Dark red-brown, mottled, a little glossy (`spec`); its edges lit from above (`rim`,
        this much of it)."""
        m = bpy.data.materials.new(name + "_skin")
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        geo = nb.node("ShaderNodeNewGeometry")
        mott = nb.noise(nb.node("ShaderNodeTexCoord").outputs["Object"], 18.0, 3.0, 0.6)
        col = nb.mix(nb.smooth(mott, 0.35, 0.7), (0.05, 0.012, 0.01), (0.12, 0.03, 0.02))
        b = nb.node("ShaderNodeBsdfPrincipled", Roughness=0.32)
        nb.set(b.inputs["Base Color"], col)
        ba._try(b.inputs["Specular IOR Level"], "default_value", spec)
        lw = nb.node("ShaderNodeLayerWeight", Blend=0.3)
        up = nb.smooth(nb.xyz(geo.outputs["Normal"])[2], -0.35, 0.8)
        edge = nb.math("POWER", lw.outputs["Facing"], 3.2)
        v = nb.node("ShaderNodeValue")
        v.outputs[0].default_value = 0.0
        self.rim.append((v, rim))
        em = nb.node("ShaderNodeEmission")
        nb.set(em.inputs["Color"], (0.32, 0.62, 0.8))
        nb.set(em.inputs["Strength"], nb.mul(nb.mul(edge, nb.add(0.15, up)), v.outputs[0]))
        add = nb.node("ShaderNodeAddShader")
        nb.nt.links.new(b.outputs[0], add.inputs[0])
        nb.nt.links.new(em.outputs[0], add.inputs[1])
        nb.nt.links.new(add.outputs[0], out.inputs["Surface"])
        return m

    def _eyes(self, name):
        """Two great eyes on the sides of the head: a black glossy globe, a dull gold iris that
        glints (`glint`)."""
        import bmesh
        m = bpy.data.materials.new(name + "_eye")
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        b = nb.node("ShaderNodeBsdfPrincipled", Roughness=0.06)
        nb.set(b.inputs["Base Color"], (0.004, 0.003, 0.003))
        lw = nb.node("ShaderNodeLayerWeight", Blend=0.5)
        self.glint = nb.node("ShaderNodeValue")
        self.glint.outputs[0].default_value = 0.0
        f = lw.outputs["Facing"]                    # a dim gold iris round the black pupil
        iris = nb.mul(nb.add(0.25, nb.mul(0.75, nb.smooth(f, 0.04, 0.16))), nb.smooth(f, 0.55, 0.25))
        em = nb.node("ShaderNodeEmission")
        nb.set(em.inputs["Color"], (0.85, 0.5, 0.16))
        nb.set(em.inputs["Strength"], nb.mul(iris, self.glint.outputs[0]))
        add = nb.node("ShaderNodeAddShader")
        nb.nt.links.new(b.outputs[0], add.inputs[0])
        nb.nt.links.new(em.outputs[0], add.inputs[1])
        nb.nt.links.new(add.outputs[0], out.inputs["Surface"])
        for sx in (-1.0, 1.0):
            me = bpy.data.meshes.new(name + "_eye")
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=0.055)
            bm.to_mesh(me)
            bm.free()
            for p in me.polygons:
                p.use_smooth = True
            me.materials.append(m)
            eo = bpy.data.objects.new(name + "_eye", me)
            bpy.context.scene.collection.objects.link(eo)
            eo.parent = self.ob
            eo.location = (sx * 0.084, -0.1, 0.014)
            ba._try(eo, "visible_shadow", False)
            self.eyes.append(eo)

    def lit(self, rim, glint):
        """How much its edges (`rim`) and eyes (`glint`) catch the light."""
        for v, k in self.rim:
            v.outputs[0].default_value = float(rim) * k
        self.glint.outputs[0].default_value = float(glint)

    def pose(self, t, reach=0.5, writhe=1.0):
        """The squid at time t (s): arms writhing, tentacles reaching (0 coiled .. 1 straight
        out ahead), fins rippling, the mantle breathing."""
        S = self.SIDES
        V = self.V
        breath = 1.0 + 0.035 * math.sin(2 * math.pi * t / 2.9)
        r = self.body_r * np.where(self.body_P[:, 1] > 0.02, breath, 1.0)
        a, b = self.slices["body"]
        V[a:b - 1] = _tube_rings(self.body_P, r, (1.0, 0.0, 0.0), 16)
        V[b - 1] = (0.0, 1.0, 0.0)
        # fins: rippling, a wave running back along them
        a, b = self.slices["fins"]
        X = self.fin_x[None, :] * self.fin_w[:, None]
        Y = np.broadcast_to(self.fin_y[:, None], X.shape)
        wave = np.sin(2 * math.pi * t / 1.7 - 7.0 * self.fin_y)[:, None]
        Z = 0.045 * (np.abs(self.fin_x[None, :]) ** 1.6) * wave - 0.012 * self.fin_x[None, :] ** 2
        V[a:b] = np.stack([X, Y, Z], -1).reshape(-1, 3)
        # arms and tentacles
        for k, arm in enumerate(self.arms):
            n = arm["n"]
            s = np.linspace(0.0, 1.0, n)
            rho = arm["rho"]
            ph = arm["phase"] + arm["rate"] * t * 1.3
            if arm["tent"]:
                splay = 0.12 + 0.1 * (1 - reach)
                coil = (1.0 - reach) * (0.4 + 5.5 * s ** 2.0)              # rad per unit
                k1 = (coil + 0.35 * writhe * np.sin(ph - 4.0 * s)) * arm["length"] / (n - 1)
                k2 = (0.5 * writhe * np.sin(0.7 * ph + 2.5 * s) * (0.3 + s)
                      + (1 - reach) * 1.2 * arm["side"] * s) * arm["length"] / (n - 1)
                rad = arm["r0"] * (1.0 - 0.5 * s) + 0.003
                club = np.clip((s - 0.78) / 0.22, 0.0, 1.0)
                rad = rad + 0.03 * np.sin(np.pi * club) ** 0.6
                rr = np.stack([rad, rad * (1.0 - 0.45 * np.sin(np.pi * club))], 1)
            else:
                splay = 0.42
                curl = writhe * (0.9 + 0.8 * math.sin(ph)) * 4.6 * s ** 1.5
                k1 = (curl + writhe * 1.8 * np.sin(ph * 1.4 - 6.0 * s) * (0.25 + s)) \
                    * arm["length"] / (n - 1)
                k2 = (writhe * 1.1 * np.sin(ph * 0.8 + 1.3 + 4.5 * s) * (0.2 + s) * arm["side"]) \
                    * arm["length"] / (n - 1)
                rr = arm["r0"] * (1.0 - s) ** 0.85 + 0.0025
            T0 = np.array([0.0, -1.0, 0.0]) * math.cos(splay) + rho * math.sin(splay)
            R0 = rho - T0 * float(rho @ T0)
            R0 /= np.linalg.norm(R0)
            p0 = np.array([0.0, -0.17, 0.0]) + rho * (0.055 if not arm["tent"] else 0.035)
            P = _bend_curve(p0, T0, R0, arm["length"], n, k1, k2)
            a, b = self.slices[k]
            V[a:b - 1] = _tube_rings(P, rr, R0, S)
            V[b - 1] = P[-1]
        self.mesh.vertices.foreach_set("co", V.astype(np.float32).ravel())
        self.mesh.update()


# ---------------------------------------------------------------------------- deep_sea
SEA_LOOK = {"exposure": 0.5,         # EV
            "sun_strength": 8.0, "sun_color": "#C8EEFF",     # the light from the surface
            "water_color": "#0B4A8A",                         # what the water scatters
            "visibility": 1.5,       # model lengths: the water takes 63 % of the light this far
            "shafts": 16.0,          # how much denser the water is in the light's shafts
            "lamp_gain": 6.0,        # the model's LEDs (their own power) x this
            "room_light": 0.03,      # W: each of the warm lights in a flythrough's room
            "room_lamp_gain": 0.02,  # its LEDs' gain in there (lamp_gain is for seeing them out)
            "window_glow": 0.6,      # W: the room's light out through its windows into the water
            "squid_light": 3.0,      # a coda's squid: its own light from above and behind it...
            "squid_color": "#9CC8FF",
            "squid_rim": 1.0,        # ...its edges' glow (x the plan's rim)...
            "squid_glint": 0.3,      # ...and its eyes' (x the plan's glint)
            "look": "AgX - Medium High Contrast"}


class DeepSea:
    """Open water, well below a rippling surface, the model cruising through it (motion
    "glide"): a blue that thickens with distance and darkens with depth, shafts of light from
    the surface (its ripples cast them, and dapple the model), marine snow drifting, bubbles
    rising from vents in a rocky seabed far below with kelp swaying, and from the model's stern
    as it goes; its LEDs glow in the water. Scaled to the model: S Blender units is its length
    (the plan's glide length); the world's axes: x, y as Blender's, z up."""

    BLUR = {"approach": 0.02, "side": 0.022, "bow": 0.03, "under": 0.02, "silhouette": 0.012,
            "flythrough": 0.008, "coda": 0.014}
    TRIM = {}
    KEY_CAMERA = True                       # the camera tracks: blur with it, not against it

    def __init__(self, sc, co, eevee):
        self.sc, self.co, self.eevee = sc, co, eevee
        self.look = dict(SEA_LOOK, **(co.get("look") or {}))
        g = co.get("glide") or {}
        R3 = TO_B.to_3x3()
        self.S = float(g.get("length", co["height"])) * LDU
        self.path = [TO_B @ Vector(p) for p in g.get("path") or [(0, -co["height"] / 2, 0)]]
        self.F = (R3 @ Vector(g.get("forward", (-1, 0, 0)))).normalized()
        self.N = (R3 @ Vector(g.get("side", (0, 0, -1)))).normalized()
        ext = g.get("extent") or {}
        self.back = float(ext.get("behind", 0.5 * self.S / LDU)) * LDU
        mid = self.path[len(self.path) // 2]
        self.mid = mid
        self.top = mid.z + 1.35 * self.S                  # the surface
        self.floor = mid.z - 2.0 * self.S                 # the seabed
        self.rng = np.random.default_rng(20000)
        self.sun_down = (Vector((0, 0, -1)) - 0.3 * self.N - 0.15 * self.F).normalized()
        self.fly = co.get("flythrough")
        self.hull = None
        if self.fly:                          # the model's own frame, carried with it (tick)
            if "lamp_gain" not in (co.get("look") or {}):
                self.look["lamp_gain"] = self.look["room_lamp_gain"]
            self.hull = bpy.data.objects.new("hull_frame", None)
            sc.collection.objects.link(self.hull)
            self.SAMPLES = 0.5                # a long take of a big model: half the samples
        self.coda = co.get("coda")            # the coda: the dark sea and what's out there
        self.squid = None
        if self.coda:
            self.SAMPLES = 0.5
        self.world()
        self.surface()
        self.caustics = []
        if not self.coda:                     # the coda's abyss has no bottom in sight
            self.seabed()
        self.snow()
        self.bubbles_setup()
        self.lights()
        if self.fly:
            self.room_lights()
            if self.fly.get("lurk"):
                self.lurker()
        if self.coda and self.coda.get("squid"):
            self.monster(self.coda["squid"])
        self.compositor()
        ee = sc.eevee
        ba._try(ee, "bokeh_threshold", 1e5)
        ba._try(ee, "bokeh_max_size", 60.0)
        ba._try(ee, "volumetric_tile_size", "8")
        ba._try(ee, "volumetric_samples", 40)
        ba._try(ee, "use_volumetric_shadows", True)
        ba._try(ee, "volumetric_shadow_samples", 8)
        ba._try(ee, "volumetric_start", 0.02 * self.S)
        ba._try(ee, "volumetric_end", 12.0 * self.S)
        if self.fly:                          # cheaper water: coarser, fewer slices, no shadows
            ba._try(ee, "volumetric_tile_size", "16")
            ba._try(ee, "volumetric_samples", 16)
            ba._try(ee, "use_volumetric_shadows", False)
        sc.view_settings.view_transform = "AgX"
        ba._try(sc.view_settings, "look", self.look["look"])
        sc.view_settings.exposure = 0.0

    def _mat(self, name, build, method=None):
        m = bpy.data.materials.new(name)
        nb = NB(m.node_tree)
        out = nb.clear("OUTPUT_MATERIAL")
        m.node_tree.links.new(build(nb), out.inputs["Surface"])
        if method:
            ba._try(m, "surface_render_method", method)
        return m

    def _ob(self, mesh, name, mat, shadow=True):
        ob = mesh.build(name, mat, 1.0, (0, 0, 0))
        ob.scale = (1, 1, 1)
        if not shadow:
            ba._try(ob, "visible_shadow", False)
        return ob

    # -- the water ----------------------------------------------------------------------------
    def world(self):
        """The water itself: a world volume that scatters the surface's light blue and absorbs
        the red (so it thickens to deep blue with distance), and behind it a blue that pales
        towards the surface and darkens into the deep."""
        w = bpy.data.worlds.new("sea")
        self.sc.world = w
        nb = NB(w.node_tree)
        out = nb.clear("OUTPUT_WORLD")
        d = nb.vec("NORMALIZE", nb.node("ShaderNodeTexCoord").outputs["Generated"])
        z = nb.xyz(d)[2]
        up = nb.smooth(z, -0.4, 0.9)
        col = nb.mix(up, (0.002, 0.012, 0.035), (0.03, 0.16, 0.34))
        bg = nb.node("ShaderNodeBackground", Strength=3.5)
        nb.set(bg.inputs["Color"], col)
        w.node_tree.links.new(bg.outputs[0], out.inputs["Surface"])
        ba._try(w, "sun_threshold", 1e6)
        self.bg = bg
        # the water: a volume filling the sea from the seabed to the surface (a world volume
        # would put out the sun: EEVEE takes the sun's light through all of it)
        S, c = self.S, self.mid
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(c.x, c.y, (self.top + self.floor) / 2 - 0.1 * S))
        ob = bpy.context.object
        ob.name = "water"
        ob.scale = (30 * S, 30 * S, self.top - self.floor + 0.2 * S)
        ba._try(ob, "visible_shadow", False)
        m = bpy.data.materials.new("water")
        vb = NB(m.node_tree)
        vout = vb.clear("OUTPUT_MATERIAL")
        vis = float(self.look["visibility"]) * S
        vol = vb.node("ShaderNodeVolumePrincipled", Anisotropy=0.6)
        # shafts: streaks along the sun's light, brightest under the surface, fading with depth
        pos = vb.vec("SCALE", vb.vec("SUBTRACT", vb.node("ShaderNodeNewGeometry").outputs["Position"],
                                     tuple(c)), 1.0 / S)
        L = self.sun_down
        along = vb.vec("DOT_PRODUCT", pos, tuple(L), out=1)
        across = vb.vec("SUBTRACT", pos, vb.vec("SCALE", vb.comb(L.x, L.y, L.z), along))
        sw = vb.node("ShaderNodeValue")
        self.waves = getattr(self, "waves", []) + [sw]
        n1 = vb.node("ShaderNodeTexNoise", Scale=4.0, Detail=1.0, Roughness=0.5)
        n1.noise_dimensions = "4D"
        vb.set(n1.inputs["Vector"], across)
        vb.set(n1.inputs["W"], sw.outputs[0])
        shafts = vb.smooth(n1.outputs["Fac"], 0.57, 0.64)
        depth = vb.math("EXPONENT", vb.math("DIVIDE", vb.sub(vb.xyz(pos)[2], (self.top - c.z) / S), 1.8))
        dens = vb.mul(vb.add(1.0, vb.mul(vb.mul(shafts, depth), float(self.look["shafts"]))), 1.0 / vis)
        self.murk_dens = vb.node("ShaderNodeValue")          # thicker in the dark (murk)
        self.murk_dens.outputs[0].default_value = 1.0
        dens = vb.mul(dens, self.murk_dens.outputs[0])
        if self.fly:                          # no water inside the model's room, nor in its
            tc = vb.node("ShaderNodeTexCoord")  # walls where the camera goes through them
            tc.object = self.hull
            lo, hi = (np.asarray(v, float) for v in self.fly["bounds"])

            def outside(lo, hi):
                cen, half = (lo + hi) / 2, (hi - lo) / 2
                d = vb.vec("SUBTRACT", vb.vec("ABSOLUTE", vb.vec("SUBTRACT", tc.outputs["Object"],
                                                                 tuple(cen))), tuple(half))
                dx, dy, dz = vb.xyz(d)
                return vb.smooth(vb.math("MAXIMUM", vb.math("MAXIMUM", dx, dy), dz), -4.0, 4.0)
            dens = vb.mul(dens, outside(lo - 12.0, hi + 12.0))
            for P in self.fly.get("at", {}).values():         # the room out to each window
                P = np.asarray(P, float)
                dens = vb.mul(dens, outside(np.minimum(lo, P) - 4.0, np.maximum(hi, P) + 4.0))
        vb.set(vol.inputs["Density"], dens)
        # the water's own colour: paler and greener under the surface, deep blue below
        wc = bs.hex_to_linear(self.look["water_color"])
        self.murk_col = vb.node("ShaderNodeValue")           # darker in the dark
        self.murk_col.outputs[0].default_value = 1.0
        vb.set(vol.inputs["Color"], vb.vec("SCALE", vb.mix(depth, [x * 0.35 for x in wc],
                                                           [min(1.0, x * 2.2) for x in wc]),
                                           self.murk_col.outputs[0]))
        vb.set(vol.inputs["Absorption Color"], (0.08, 0.42, 0.8))
        m.node_tree.links.new(vol.outputs[0], vout.inputs["Volume"])
        ob.data.materials.append(m)

    def surface(self):
        """The underside of the sea's surface: bright straight up (the sky through it), dimmer
        at a slant, rippled with drifting bands of light (tick moves them). It casts no shadow:
        the shafts are in the water's own density (world), the caustics on the seabed."""
        S = self.S
        m = Mesh()
        c = self.mid
        h = 24.0 * S
        m.quad([(c.x - h, c.y - h, self.top), (c.x + h, c.y - h, self.top),
                (c.x + h, c.y + h, self.top), (c.x - h, c.y + h, self.top)])

        def build(nb):
            geo = nb.node("ShaderNodeNewGeometry")
            p = nb.vec("SCALE", geo.outputs["Position"], 1.0 / S)
            lines = self._caustic(nb, p, 1.3)
            v = nb.xyz(geo.outputs["Incoming"])[2]
            up = nb.smooth(v, 0.15, 0.95)
            soft = nb.noise(nb.vec("MULTIPLY", p, (1.2, 1.2, 0.0)), 1.0, 3.0, 0.5)
            col = nb.mix(nb.add(nb.mul(lines, 0.18), nb.mul(nb.smooth(soft, 0.35, 0.75), 0.5)),
                         (0.08, 0.36, 0.5), (0.65, 0.95, 1.05))
            em = nb.node("ShaderNodeEmission", Strength=1.0)
            nb.set(em.inputs["Color"], nb.vec("SCALE", col, nb.add(0.4, nb.mul(up, 2.6))))
            self.surface_em = em
            return em.outputs[0]
        ob = self._ob(m, "sea_surface", self._mat("sea_surface", build), shadow=False)
        ba._try(ob, "visible_volume_scatter", False)

    def _caustic(self, nb, p, scale):
        """0..1 bright caustic lines over (x, y) of `p`, two layers drifting through each other
        (their phase a Value node per material, all set by tick)."""
        w = nb.node("ShaderNodeValue")
        self.waves = getattr(self, "waves", []) + [w]
        warp = nb.noise(nb.vec("MULTIPLY", p, (0.8, 0.8, 0.0)), 1.0, 3.0, 0.55, out="Color")
        lines = None
        for sc_, dw in ((scale, 0.0), (scale * 1.6, 1.7)):
            q = nb.vec("ADD", nb.vec("MULTIPLY", p, (sc_, sc_, 0.0)), nb.vec("SCALE", warp, 0.9))
            vor = nb.node("ShaderNodeTexVoronoi", Scale=1.0)
            vor.voronoi_dimensions = "4D"
            vor.feature = "DISTANCE_TO_EDGE"
            nb.set(vor.inputs["Vector"], q)
            nb.set(vor.inputs["W"], nb.add(w.outputs[0], dw))
            l_ = nb.smooth(vor.outputs["Distance"], 0.035, 0.0)
            lines = l_ if lines is None else nb.math("MAXIMUM", lines, nb.mul(l_, 0.7))
        return lines

    # -- the bottom ---------------------------------------------------------------------------
    def seabed(self):
        """Rocky sand far below, a few boulders, kelp swaying up from it."""
        S, rng = self.S, self.rng
        c = self.mid
        n = 140
        xs = np.linspace(-9 * S, 9 * S, n)
        X, Y = np.meshgrid(xs + c.x, xs + c.y)
        Z = np.zeros_like(X)
        for k in range(6):
            f = rng.uniform(0.3, 1.0) * 2 ** k / (6 * S)
            a = rng.uniform(0, 2 * np.pi, 2)
            Z += 0.35 * S / (k + 1.5) * np.sin(X * f * 2 * np.pi + a[0]) * np.cos(Y * f * 1.7 * np.pi + a[1])
        Z += self.floor
        V = np.stack([X, Y, Z], -1).reshape(-1, 3)
        i = np.arange(n - 1)[:, None] * n + np.arange(n - 1)[None, :]
        F = np.concatenate([np.stack([i, i + 1, i + n + 1], -1).reshape(-1, 3),
                            np.stack([i, i + n + 1, i + n], -1).reshape(-1, 3)])
        bed = Mesh()
        bed.tris(V, F)

        def sand(nb):
            p = nb.vec("SCALE", nb.node("ShaderNodeNewGeometry").outputs["Position"], 1.0 / S)
            n1 = nb.noise(p, 3.0, 4.0, 0.6)
            col = nb.mix(n1, (0.025, 0.035, 0.03), (0.07, 0.08, 0.065))
            b = nb.node("ShaderNodeBsdfPrincipled", Roughness=0.95)
            nb.set(b.inputs["Base Color"], col)
            em = nb.node("ShaderNodeEmission", Strength=0.35)          # the surface's caustics
            self.caustics = getattr(self, "caustics", []) + [em]
            nb.set(em.inputs["Color"], nb.vec("SCALE", nb.comb(0.4, 0.8, 0.9), self._caustic(nb, p, 2.0)))
            add = nb.node("ShaderNodeAddShader")
            nb.nt.links.new(b.outputs[0], add.inputs[0])
            nb.nt.links.new(em.outputs[0], add.inputs[1])
            return add.outputs[0]
        self._ob(bed, "seabed", self._mat("sand", sand), shadow=False).data.polygons.foreach_set(
            "use_smooth", np.ones(len(F), bool))
        rocks, kelp = Mesh(), Mesh()
        for _ in range(26):
            a = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(0.5, 7.0) * S
            px, py = c.x + r * math.cos(a), c.y + r * math.sin(a)
            size = rng.uniform(0.15, 0.6) * S
            k = 6
            C = np.stack([px + rng.normal(0, size * 0.5, k), py + rng.normal(0, size * 0.5, k),
                          self.floor + rng.uniform(0, size * 0.6, k)], -1)
            _leaves(rocks, rng, C, rng.uniform(0.4, 0.8, k) * size, 60, size * 0.5, 0.7)
        self.kelp = []
        for _ in range(40):
            a = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(0.8, 6.0) * S
            px, py = c.x + r * math.cos(a), c.y + r * math.sin(a)
            hgt = rng.uniform(0.3, 0.8) * S
            pts = [[px, py, self.floor - 0.05 * S]]
            for j in range(1, 9):
                pts.append([px + 0.05 * S * math.sin(j * 0.9 + a), py + 0.04 * S * math.cos(j * 0.7),
                             self.floor + hgt * j / 8])
            kelp.tube(pts, np.linspace(0.025, 0.008, 9) * S, 4)
        self._ob(rocks, "rocks", self._mat("rock", lambda nb: self._bsdf(nb, (0.05, 0.06, 0.05), 0.9)),
                 shadow=False)
        self._ob(kelp, "kelp", self._mat("kelp", lambda nb: self._bsdf(nb, (0.06, 0.12, 0.04), 0.7)),
                 shadow=False)

    @staticmethod
    def _bsdf(nb, col, rough):
        b = nb.node("ShaderNodeBsdfPrincipled", Roughness=rough)
        nb.set(b.inputs["Base Color"], col)
        return b.outputs[0]

    # -- what floats ----------------------------------------------------------------------------
    def snow(self):
        """Marine snow: specks hanging in the water round the model's path, sinking slowly."""
        S, rng = self.S, self.rng
        n = 14000 if self.coda else 9000
        P = np.array(self.path)
        if self.coda:                         # all the way out to the camera
            P = np.vstack([P, [TO_B @ Vector(c) for c in self.co["camera"]["pos"][::10]]])
        lo, hi = P.min(0) - 1.6 * S, P.max(0) + 1.6 * S
        C = rng.uniform(lo, hi, (n, 3))
        if self.coda:                         # none right at the lens (a blot of bokeh)
            cams = np.array([TO_B @ Vector(c) for c in self.co["camera"]["pos"]])
            near = np.min(np.linalg.norm(C[:, None, :] - cams[None, ::4, :], axis=2), axis=1)
            C = C[near > 0.3 * S]
            n = len(C)
        size = S * 0.0022 * rng.uniform(0.5, 1.6, n)[:, None]
        d = rng.normal(size=(n, 3, 3))
        V = (C[:, None, :] + d * size[:, None, :]).reshape(-1, 3)
        m = Mesh()
        m.tris(V, np.arange(len(V)).reshape(-1, 3))

        def build(nb):
            em = nb.node("ShaderNodeEmission", Strength=0.45)
            nb.set(em.inputs["Color"], (0.6, 0.85, 1.0))
            b = self._bsdf(nb, (0.7, 0.8, 0.8), 0.6)
            return nb.shader_mix(0.5, b, em.outputs[0])
        self.snow_ob = self._ob(m, "marine_snow", self._mat("snow", build), shadow=False)

    def bubbles_setup(self):
        """Streams of bubbles: from vents in the seabed, and from the model's stern as it goes.
        One mesh of little spheres, moved every frame (tick)."""
        S, rng = self.S, self.rng
        c = self.mid
        self.vents = [(c.x + r * math.cos(a), c.y + r * math.sin(a))
                      for a, r in zip(rng.uniform(0, 2 * np.pi, 5), rng.uniform(0.6, 3.0, 5) * S)]
        self.nb_vent, self.nb_wake = 60, 90
        n = len(self.vents) * self.nb_vent + self.nb_wake
        self.b_phase = rng.uniform(0, 1, n)
        self.b_size = S * 0.008 * rng.uniform(0.4, 1.4, n)
        self.b_wob = rng.uniform(0, 2 * np.pi, n)
        ico = bpy.data.meshes.new("_ico")
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        bm.to_mesh(ico)
        bm.free()
        iv = np.array([v.co[:] for v in ico.vertices])
        it = np.array([[v for v in p.vertices] for p in ico.polygons])
        bpy.data.meshes.remove(ico)
        self.ico = iv
        V = np.zeros((n * len(iv), 3))
        F = (it[None] + (np.arange(n) * len(iv))[:, None, None]).reshape(-1, 3)
        m = Mesh()
        m.tris(V, F)

        def build(nb):
            lw = nb.node("ShaderNodeLayerWeight", Blend=0.35)
            em = nb.node("ShaderNodeEmission", Strength=0.9)
            nb.set(em.inputs["Color"], (0.75, 0.95, 1.0))
            tr = nb.node("ShaderNodeBsdfTransparent")
            return nb.shader_mix(nb.math("POWER", lw.outputs["Facing"], 2.0), tr.outputs[0], em.outputs[0])
        self.bubble_ob = self._ob(m, "bubbles", self._mat("bubble", build, "BLENDED"), shadow=False)
        self.bubble_ob.data.polygons.foreach_set("use_smooth", np.ones(len(F), bool))

    def tick(self, k, fps=30.0):
        """The water at plan frame k: ripples drift, snow sinks, bubbles rise; in a flythrough
        the room's frame follows the model, nothing floats in the room while the camera is in
        it, and something stirs in the dark; the sea darkens with the plan's murk (a
        flythrough's, a coda's); a coda's creature moves (monster_tick)."""
        S = self.S
        t = k / fps
        if self.fly:
            spin = self.co["spin"][min(k, len(self.co["spin"]) - 1)]
            self.hull.matrix_world = ba.to_blender(ba.ld_matrix(spin)) @ TO_B
            self.in_room = float(self.fly["room"][min(k, len(self.fly["room"]) - 1)])
            # in the room the water is only past its walls: finer slices, nearer, so none of
            # it bleeds in over the floor
            ee = bpy.context.scene.eevee
            fine = self.in_room > 0.02
            ba._try(ee, "volumetric_tile_size", "8" if fine else "16")
            ba._try(ee, "volumetric_samples", 64 if fine else 16)
            ba._try(ee, "volumetric_end", (5.0 if fine else 12.0) * self.S)
        murk = (self.fly or self.coda or {}).get("murk")
        if murk:
            mk = float(murk[min(k, len(murk) - 1)])
            room = getattr(self, "in_room", 0.0)
            for data, e in self.levels.items():
                data.energy = e * (1.0 - 0.94 * mk)
            self.bg.inputs["Strength"].default_value = 3.5 * (1.0 - 0.9 * mk) * (1.0 - 0.75 * room)
            for em in self.caustics:
                em.inputs["Strength"].default_value = 0.35 * (1.0 - mk)
            self.surface_em.inputs["Strength"].default_value = 1.0 - 0.95 * mk
            self.murk_dens.outputs[0].default_value = 1.0 + 1.2 * mk
            self.murk_col.outputs[0].default_value = 1.0 - 0.85 * mk
        if self.fly:
            a, b = self.fly["inside"]
            inside = a - self.co["start"] <= k < b - self.co["start"]
            self.snow_ob.hide_render = inside
            self.bubble_ob.hide_render = inside
            if getattr(self, "lurk", None) is not None:
                L = self.fly["lurk"]
                sq = self.lurk
                sq.ob.hide_render = k < L["from"]
                for eo in sq.eyes:
                    eo.hide_render = k < L["from"]
                e = max(0.0, (k - L["from"]) / fps)       # it rises, turning slowly
                rise = min(1.0, e / 1.5)
                rise = rise * rise * (3 - 2 * rise) * mk    # out of the murk
                sq.lit(0.9 * rise, 0.8 * rise)
                sq.ob.matrix_world = Matrix.Translation((0, 0, 0.05 * self.lurk_S * e)) @ \
                    self.lurk_base @ Matrix.Rotation(0.05 * e, 4, "X") @ Matrix.Scale(self.lurk_S, 4)
                sq.pose(t, reach=0.25 + 0.5 * min(1.0, e / 2.5), writhe=0.8)
        if self.squid is not None:
            self.monster_tick(k, fps)
        if self.coda:                         # the vents' columns would rise past the lens
            self.bubble_ob.hide_render = True
        for w in self.waves:
            w.outputs[0].default_value = 0.35 * t
        self.snow_ob.location = (0.01 * S * t, 0.004 * S * t, -0.02 * S * t)
        n_v = len(self.vents) * self.nb_vent
        rise = 0.35 * S                                   # per second
        P = np.zeros((len(self.b_phase), 3))
        # vents: bubbles cycling up a column
        life_v = (self.top - self.floor) / rise
        for j, (vx, vy) in enumerate(self.vents):
            s = slice(j * self.nb_vent, (j + 1) * self.nb_vent)
            age = ((t / life_v + self.b_phase[s]) % 1.0) * life_v
            P[s, 0] = vx + 0.03 * S * np.sin(2.5 * age + self.b_wob[s])
            P[s, 1] = vy + 0.03 * S * np.cos(2.1 * age + self.b_wob[s])
            P[s, 2] = self.floor + rise * age
        # the wake: born at the stern over the last two seconds, rising and spreading
        path = self.path
        life_w = 2.0
        w = slice(n_v, None)
        age = (self.b_phase[w] * life_w)
        born = np.clip(k - age * fps, 0, len(path) - 1).astype(int)
        src = np.array([path[i] - self.F * self.back for i in born])
        spread = 0.05 * S * age[:, None] * np.stack([np.sin(self.b_wob[w] * 3), np.cos(self.b_wob[w] * 5),
                                                    np.zeros(len(age))], -1)
        P[w] = src + spread + np.outer(rise * 0.6 * age, (0, 0, 1))
        V = (P[:, None, :] + self.ico[None] * self.b_size[:, None, None]).reshape(-1)
        me = self.bubble_ob.data
        me.vertices.foreach_set("co", V.astype(np.float32))
        me.update()

    # -- light ----------------------------------------------------------------------------------
    def lights(self):
        """The sun through the surface, nearly overhead, leaning a little towards the deep
        camera (its shafts slant across the frame); a faint blue from below for the bellies."""
        sd = bpy.data.lights.new("sea_sun", "SUN")
        sd.color = tuple(bs.hex_to_linear(self.look["sun_color"]))
        sd.energy = float(self.look["sun_strength"])
        sd.angle = math.radians(2.0)
        ba._try(sd, "use_shadow_jitter", False)
        ba._try(sd, "volume_factor", 1.0)
        so = bpy.data.objects.new("sea_sun", sd)
        self.sc.collection.objects.link(so)
        so.rotation_euler = self.sun_down.to_track_quat("-Z", "Y").to_euler()
        self.sun = so
        if self.fly:                          # it can't reach the room (link_room), so: no shadows
            ba._try(sd, "use_shadow", False)
        fd = bpy.data.lights.new("sea_fill", "SUN")
        fd.color = (0.1, 0.35, 0.6)
        fd.energy = 1.2
        fd.angle = math.radians(60)
        ba._try(fd, "use_shadow", False)
        ba._try(fd, "volume_factor", 0.0)
        fo = bpy.data.objects.new("sea_fill", fd)
        self.sc.collection.objects.link(fo)
        fo.rotation_euler = Vector((0.2, 0.1, 1.0)).normalized().to_track_quat("-Z", "Y").to_euler()
        self.fill = fo
        self.levels = {so.data: so.data.energy, fd: fd.energy}

    # -- a flythrough's room ------------------------------------------------------------------
    def room_lights(self):
        """Warm lamplight in the model's room (lights riding on its frame, lighting only the
        room: link_room), and the glow of it out through the windows the camera passes, into
        the water."""
        b = self.fly["bounds"]
        lo, hi = Vector(b[0]), Vector(b[1])
        c = (lo + hi) / 2
        self.room = []
        for fx in (0.22, 0.5, 0.78):
            p = Vector((lo.x + (hi.x - lo.x) * fx, lo.y + (hi.y - lo.y) * 0.22, c.z))
            ld = bpy.data.lights.new("room_light", "POINT")
            ld.color = tuple(bs.hex_to_linear("#FFB565"))
            ld.energy = float(self.look["room_light"])
            ld.shadow_soft_size = 0.01
            ba._try(ld, "use_shadow", False)
            lo_ = bpy.data.objects.new("room_light", ld)
            self.sc.collection.objects.link(lo_)
            lo_.parent = self.hull
            lo_.matrix_parent_inverse = Matrix.Identity(4)
            lo_.matrix_basis = Matrix.Translation(p) @ Matrix.Scale(1 / LDU, 4)
            self.room.append(lo_)
        self.glows = []
        cl = Vector(c)
        for key in ("enter", "exit"):
            w = Vector(self.fly["at"][key])
            out = (w - cl)
            out.y = 0.0
            out.normalize()
            ld = bpy.data.lights.new("window_glow", "SPOT")
            ld.color = tuple(bs.hex_to_linear("#FFB060"))
            ld.energy = float(self.look["window_glow"])
            ld.spot_size = math.radians(80)
            ld.spot_blend = 0.8
            ld.shadow_soft_size = 0.02
            ba._try(ld, "use_shadow", False)
            ob = bpy.data.objects.new("window_glow", ld)
            self.sc.collection.objects.link(ob)
            ob.parent = self.hull
            ob.matrix_parent_inverse = Matrix.Identity(4)
            q = (-out).to_track_quat("Z", "Y")                    # its -Z (the beam) outward
            ob.matrix_basis = Matrix.Translation(w - out * 30.0) @ q.to_matrix().to_4x4() @ \
                Matrix.Scale(1 / LDU, 4)
            self.glows.append(ob)

    def link_room(self, parts, keep):
        """Light linking for the room: the sun and the fill never reach it (no shadows needed to
        keep them out), its own lights reach nothing else, the windows' glow only the water.
        `parts` the model's objects (the rig at rest), `keep` the room's own instances."""
        if not self.fly:
            return
        bpy.context.view_layer.update()
        b = self.fly["bounds"]
        corners = [TO_B @ Vector((x, y, z)) for x in (b[0][0], b[1][0]) for y in (b[0][1], b[1][1])
                   for z in (b[0][2], b[1][2])]
        lo = Vector([min(c[i] for c in corners) for i in range(3)]) - Vector((1, 1, 1)) * 16 * LDU
        hi = Vector([max(c[i] for c in corners) for i in range(3)]) + Vector((1, 1, 1)) * 16 * LDU
        room = bpy.data.collections.new("room")
        n = 0
        for i, ob in enumerate(parts):
            if ob is None or ob.hide_render:
                continue
            bb = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
            blo = Vector([min(v[a] for v in bb) for a in range(3)])
            bhi = Vector([max(v[a] for v in bb) for a in range(3)])
            if all(blo[a] <= hi[a] and bhi[a] >= lo[a] for a in range(3)):
                room.objects.link(ob)
                n += 1
        if not n:
            return
        for light in (self.sun, self.fill):
            col = bpy.data.collections.new("not_room")
            col.children.link(room)
            col.collection_children[0].light_linking.link_state = "EXCLUDE"
            light.light_linking.receiver_collection = col
        only = bpy.data.collections.new("room_only")
        only.children.link(room)
        for lt in self.room:
            lt.light_linking.receiver_collection = only
        water = bpy.data.collections.new("water_only")
        water.objects.link(bpy.data.objects["water"])
        for lt in self.glows:
            lt.light_linking.receiver_collection = water

    def lurker(self):
        """Something huge in the dark beyond the model: a giant squid (Squid), barely there,
        rising out of the murk as the camera pulls away, its arms reaching up (tick)."""
        L = self.fly["lurk"]
        self.lurk_S = 0.4 * float(L["size"]) * LDU          # its mantle's length
        sq = self.lurk = Squid("lurker", seed=7)
        sq.ob.hide_render = True
        for eo in sq.eyes:
            eo.hide_render = True
        p = TO_B @ Vector(L["pos"])
        f = (TO_B.to_3x3() @ Vector(L["facing"])).normalized()      # where its arms reach
        self.lurk_base = Matrix.Translation(p) @ (-f).to_track_quat("Y", "Z").to_matrix().to_4x4()
        sq.ob.matrix_world = self.lurk_base @ Matrix.Scale(self.lurk_S, 4)

    # -- a coda's creature ---------------------------------------------------------------------
    def monster(self, sq):
        """The coda's giant squid (Squid), moved along the plan's path (monster_tick), with a
        light of its own from above and behind it (light-linked to it alone) so its back and
        edges catch the light while the rest of it stays dark against the water."""
        self.squid = Squid("squid", seed=int(sq.get("seed", 7)))
        self.squid_plan = sq
        ld = bpy.data.lights.new("squid_light", "SUN")
        ld.color = tuple(bs.hex_to_linear(self.look["squid_color"]))
        ld.energy = float(self.look["squid_light"])
        ba._try(ld, "angle", math.radians(6.0))
        ba._try(ld, "use_shadow", False)
        lo = bpy.data.objects.new("squid_light", ld)
        self.sc.collection.objects.link(lo)
        d = (TO_B.to_3x3() @ Vector(sq["light"])).normalized()     # the way its light travels
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        only = bpy.data.collections.new("squid_only")
        for ob in [self.squid.ob] + self.squid.eyes:
            only.objects.link(ob)
        lo.light_linking.receiver_collection = only
        self.squid_light = lo

    def _monster_matrix(self, i):
        sq = self.squid_plan
        i = min(max(i, 0), len(sq["pos"]) - 1)
        R3 = TO_B.to_3x3()
        ax = (R3 @ Vector(sq["axis"][i])).normalized()             # where its arms point
        back = R3 @ Vector(sq["back"][i])
        back = (back - ax * back.dot(ax)).normalized()
        y, z = -ax, back
        M = Matrix((y.cross(z), y, z)).transposed().to_4x4()
        M.translation = TO_B @ Vector(sq["pos"][i])
        return M @ Matrix.Scale(float(sq["size"]) * LDU, 4)

    def monster_tick(self, k, fps):
        """The squid at plan frame k: where the plan puts it (keyed either side of the frame,
        so it blurs with its own motion), arms writhing, tentacles reaching (`reach`), its
        edges (`rim`) and eyes (`glint`) lit as the plan says, its own light coming up with its
        edges (out of the murk)."""
        sq = self.squid_plan
        i = min(k, len(sq["pos"]) - 1)
        ob = self.squid.ob
        ob.animation_data_clear()
        ob.rotation_mode = "QUATERNION"
        T = ColdOpen.BLUR_AT
        at = {dk: self._monster_matrix(k + dk).decompose() for dk in (-1, 1, 0)}
        for dk in (-1, 1, 0):                     # this frame's last: it stays set
            loc, rot, scl = at[dk]
            if rot.dot(at[0][1]) < 0:
                rot.negate()
            ob.location, ob.rotation_quaternion, ob.scale = loc, rot, scl
            for path in ("location", "rotation_quaternion", "scale"):
                ob.keyframe_insert(path, frame=T + dk)
        self.squid.pose(k / fps, reach=float(sq["reach"][i]), writhe=float(sq.get("writhe", 1.0)))
        self.squid.lit(float(sq["rim"][i]) * float(self.look["squid_rim"]),
                       float(sq["glint"][i]) * float(self.look["squid_glint"]))
        self.squid_light.data.energy = float(self.look["squid_light"]) * (0.25 + 0.75 * float(sq["rim"][i]))

    def compositor(self):
        sc = self.sc
        ng = bpy.data.node_groups.new("cold_open_lens", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        sc.compositing_node_group = ng
        ba._try(sc.render, "use_compositing", True)
        ba._try(sc.render, "compositor_device", "GPU")
        nb = NB(ng)
        rl = nb.node("CompositorNodeRLayers")
        self.gain = nb.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY", Factor=1.0)
        ng.links.new(rl.outputs["Image"], self.gain.inputs[6])
        img = self.gain.outputs[2]
        g = nb.node("CompositorNodeGlare", Type="Bloom", Quality="High")
        for k, v in dict(Threshold=0.8, Smoothness=0.6, Strength=0.45, Size=0.8,
                         Tint=(0.8, 0.95, 1.0)).items():
            nb.set(g.inputs[k], v)
        ng.links.new(img, g.inputs["Image"])
        ng.links.new(nb.mix(1.0, img, g.outputs["Glare"], "ADD"), nb.node("NodeGroupOutput").inputs[0])

    def frame(self, cam, shot, ev, focus):
        g = 2.0 ** (ev + self.TRIM.get(shot, 0.0))
        w = getattr(self, "in_room", 0.0)           # lamplight: warm, the sea's blue held back
        col = (g * (1.0 + 0.35 * w), g * (1.0 + 0.02 * w), g * (1.0 - 0.4 * w), 1.0)
        sock = self.gain.inputs[7]
        if any(abs(a - b) > 1e-6 for a, b in zip(sock.default_value, col)):
            sock.default_value = col
        cd = cam.data
        mw = cam.matrix_world
        s = max(0.05, (focus - mw.translation).dot(-(mw.to_3x3() @ Vector((0, 0, 1)))))
        f = cd.lens / 1000.0
        b = self.BLUR.get(shot, 0.02) * cd.sensor_width / 1000.0
        cd.dof.use_dof = True
        cd.dof.focus_distance = s
        cd.dof.aperture_fstop = max(0.5, f * f / (b * max(1e-3, s - f)))
        cd.dof.aperture_blades = 0
        cd.dof.aperture_ratio = 1.0


def deep_sea(sc, co, eevee):
    return DeepSea(sc, co, eevee)


def sunset_road(sc, co, eevee):
    return SunsetRoad(sc, co, eevee)


SETS = {"sunset_road": sunset_road, "night_desk": night_desk, "deep_sea": deep_sea}


# ---------------------------------------------------------------------------- the shoot
class ColdOpen:
    BLUR_AT = 100             # the scene frame the rig is keyed round, for motion blur

    def __init__(self, tl, job):
        self.tl = tl
        co = self.co = tl[job.get("plan", "cold_open")]      # the cold open, or the coda
        scene = dict(tl["scene"])
        scene.update(engine=job.get("engine", "eevee"), size=job["size"],
                     samples=int(job["samples"]), lights=[], ground=False)
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        self.b = bs.SceneBuilder(scene)
        self.b.settings()
        self.b.instances()
        sc = self.sc = bpy.context.scene
        self.eevee = scene["engine"] != "cycles"
        if self.eevee:
            ba.eevee_settings(sc, job["samples"])
        else:
            ba.cycles_settings(sc, job)
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.image_settings.compression = 15
        self.glow = ba.glow_inputs(self.eevee)         # EEVEE glass; glowing parts start dark
        for sock, _ in self.glow:
            sock.default_value = 0.0
        self.set = SETS[co["scene"]](sc, co, self.eevee)
        self.exposure = float(self.set.look["exposure"])
        if self.eevee and getattr(self.set, "SAMPLES", 1.0) != 1.0:
            sc.eevee.taa_render_samples = max(8, round(int(job["samples"]) * self.set.SAMPLES))
        self._leds()
        self.disc = bpy.data.objects.get("sun_disc")
        self.sun_dir = sun_direction(co["sun"])
        self._rig()
        fly = co.get("flythrough") or {}
        if hasattr(self.set, "link_room"):
            self.set.link_room(self.b.objects, set(fly.get("keep", [])))
        self.fly_hide = fly.get("hide") or {}          # parts out of the camera's way, per frame
        self.hidden_now = set()
        cd = bpy.data.cameras.new("cold_cam")
        cd.sensor_width = 36
        U = co["height"] * LDU
        cd.clip_start = max(0.0005, 0.004 * U)
        cd.clip_end = max(4000.0, 3000.0 * U)
        self.cam = bpy.data.objects.new("cold_cam", cd)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        self.shots = sorted(co.get("shots") or [[0, "wide"]])
        # a little motion blur on the swing: a 180-degree shutter (EEVEE)
        self.blur = self.eevee
        if self.blur:
            sc.render.use_motion_blur = True
            sc.render.motion_blur_shutter = 0.5
            ba._try(sc.render, "motion_blur_position", "CENTER")
            ba._try(sc.eevee, "motion_blur_steps", 1)
            ba._try(sc.eevee, "motion_blur_max", 48)
            bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"

    def _rig(self):
        co, objs = self.co, self.b.objects
        coll = self.sc.collection
        self.spin = bpy.data.objects.new("spin", None)
        coll.objects.link(self.spin)
        self.groups = []
        for g in co["groups"]["names"]:
            e = bpy.data.objects.new(f"group_{g}", None)
            coll.objects.link(e)
            e.parent = self.spin
            self.groups.append(e)
        hidden = set(co["hidden"])
        for i, (ob, inst) in enumerate(zip(objs, self.tl["scene"]["instances"])):
            if ob is None:
                continue
            if i in hidden:
                ob.hide_render = True
                ob.hide_viewport = True
                continue
            g = co["groups"]["instance"][i]
            ob.parent = self.groups[g] if g >= 0 else self.spin
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob.matrix_basis = TO_B @ Matrix(inst["matrix"])

    def _leds(self):
        """The model's LEDs (a tap lamp's): point lights riding on their parts, dark until the
        plan's `led` turns them up (with the set's lamp_gain)."""
        self.leds, self.led_objects = [], []
        gain = float(self.set.look.get("lamp_gain", 1.0)) * ba.LED_BOOST
        for k, L in enumerate(self.co.get("leds") or []):
            ob = self.b.objects[L["instance"]]
            ld = bpy.data.lights.new(f"led{k}", "POINT")
            ld.color = bs.hex_to_linear(L["color"])
            ld.shadow_soft_size = 0.004
            ld.energy = 0.0
            ba._try(ld, "use_shadow", False)          # inside glass parts: shadows cost, add little
            lo = bpy.data.objects.new(f"led{k}", ld)
            self.sc.collection.objects.link(lo)
            local = Matrix.Translation(Vector(L.get("offset", (0, 0, 0)))) @ Matrix.Scale(1 / LDU, 4)
            if ob is not None:
                lo.parent = ob
                lo.matrix_parent_inverse = Matrix.Identity(4)
                lo.matrix_basis = local
            self.leds.append((ld, float(L["power"]) * gain))
            self.led_objects.append(lo)
        if hasattr(self.set, "link_lamp"):
            self.set.link_lamp([ob for ob in self.b.objects if ob is not None], self.led_objects)

    def _light(self, k):
        """The lamp's brightness at plan frame k: LEDs, glowing parts, the set's own glow."""
        led = self.co.get("led")
        if not led:
            return
        v = max(0.0, float(led[min(k, len(led) - 1)]))
        for data, power in self.leds:
            data.energy = power * v
        for sock, strength in self.glow:
            sock.default_value = strength * min(v, 1.6)
        if hasattr(self.set, "lamp"):
            self.set.lamp(v)

    def _pose(self, k):
        """The rig's transforms at plan frame k (spin, then the groups)."""
        k = min(max(k, 0), len(self.co["spin"]) - 1)
        return [ba.to_blender(ba.ld_matrix(self.co["spin"][k]))] + \
            [ba.to_blender(ba.ld_matrix(self.co["frames"][k][j])) for j in range(len(self.groups))]

    def _key_rig(self, k):
        """Key the rig linearly at the frames either side of k, so the motion blur sees the
        figure move through this frame (the camera isn't keyed: no blur across the cuts)."""
        T = self.BLUR_AT
        poses = {dk: self._pose(k + dk) for dk in (-1, 0, 1)}
        for i, ob in enumerate([self.spin] + self.groups):
            ob.animation_data_clear()
            ob.rotation_mode = "QUATERNION"
            prev = None
            for dk in (-1, 0, 1):
                loc, rot, scl = poses[dk][i].decompose()
                if prev is not None and rot.dot(prev) < 0:
                    rot.negate()
                prev = rot
                ob.location, ob.rotation_quaternion, ob.scale = loc, rot, scl
                for path in ("location", "rotation_quaternion", "scale"):
                    ob.keyframe_insert(path, frame=T + dk)
        self.sc.frame_set(T)

    def shot(self, k):
        return [n for f, n in self.shots if f <= k][-1] if k >= self.shots[0][0] else self.shots[0][1]

    def _cam_at(self, k):
        cam = self.co["camera"]
        k = min(max(k, 0), len(cam["pos"]) - 1)
        loc = TO_B @ Vector(cam["pos"][k])
        tgt = TO_B @ Vector(cam["target"][k])
        return loc, (tgt - loc).to_track_quat("-Z", "Y")

    def _key_camera(self, k):
        """Key the camera either side of k within its shot (a tracking camera blurs with what
        it follows; nothing blurs across a cut)."""
        T = self.BLUR_AT
        lo = max([f for f, _ in self.shots if f <= k] or [0])
        hi = min([f for f, _ in self.shots if f > k] or [len(self.co["camera"]["pos"])]) - 1
        ob = self.cam
        ob.animation_data_clear()
        ob.rotation_mode = "QUATERNION"
        prev = None
        for dk in (-1, 0, 1):
            loc, q = self._cam_at(min(max(k + dk, lo), hi))
            if prev is not None and q.dot(prev) < 0:
                q.negate()
            prev = q
            ob.location, ob.rotation_quaternion = loc, q
            ob.keyframe_insert("location", frame=T + dk)
            ob.keyframe_insert("rotation_quaternion", frame=T + dk)
        self.sc.frame_set(T)

    def apply(self, f):
        co = self.co
        k = min(max(f - co["start"], 0), len(co["spin"]) - 1)
        if self.fly_hide or self.hidden_now:
            want = set(self.fly_hide.get(str(k), []))
            for i in self.hidden_now ^ want:
                if self.b.objects[i] is not None:
                    self.b.objects[i].hide_render = i in want
            self.hidden_now = want
        if hasattr(self.set, "tick"):
            self.set.tick(k, float(self.tl.get("fps", 30)))
        if self.blur:
            self._key_rig(k)
        else:
            pose = self._pose(k)
            self.spin.matrix_basis = pose[0]
            for e, M in zip(self.groups, pose[1:]):
                e.matrix_basis = M
        self._light(k)
        cam = co["camera"]
        loc = TO_B @ Vector(cam["pos"][k])
        tgt = TO_B @ Vector(cam["target"][k])
        if self.blur and getattr(self.set, "KEY_CAMERA", False):
            self._key_camera(k)
        else:
            self.cam.location = loc
            self.cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = cam["lens"][k]
        if self.disc is not None:                     # the sun stays at infinity
            self.disc.location = loc + self.sun_dir * DISC_AT
            self.disc.rotation_euler = self.sun_dir.to_track_quat("Z", "Y").to_euler()
        ev = self.exposure + float(cam.get("exposure", [0.0] * (k + 1))[k])
        if hasattr(self.set, "frame"):
            px, pz = co["pivot"]
            chest = TO_B @ Vector(cam["focus"][k] if cam.get("focus") else
                                  (px, co["ground_y"] - 0.6 * co["height"], pz))
            bpy.context.view_layer.update()
            self.set.frame(self.cam, self.shot(k), ev, chest)
        else:
            self.sc.view_settings.exposure = ev

    def render(self, frames):
        for f, path in frames:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                continue
            t = time.time()
            self.apply(int(f))
            tmp = path + ".tmp.png"
            self.sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            os.replace(tmp, path)
            print(f"BRICKKIT_FRAME {f} {time.time() - t:.2f}", flush=True)


def main():
    job_path = sys.argv[sys.argv.index("--") + 1]
    with open(job_path) as fh:
        job = json.load(fh)
    with open(job["timeline"]) as fh:
        tl = json.load(fh)
    t = time.time()
    shoot = ColdOpen(tl, job)
    print(f"BRICKKIT_SETUP {time.time() - t:.1f}", flush=True)
    shoot.render(job["frames"])
    print("BRICKKIT_DONE", flush=True)


if __name__ == "__main__":
    main()
