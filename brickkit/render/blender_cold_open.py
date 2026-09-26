"""Runs inside Blender: renders a build video's cold open (brickkit/video/timeline.py's
cold_open_plan): the model performing in a set of its own before the reel proper.

    Blender -b --factory-startup -P blender_cold_open.py -- job.json

job.json as for blender_animate.py: {"timeline", "frames": [[frame, "out.png"], ...], "size",
"samples", "engine", "device"}. The parts, their materials and the engine settings are the
animator's (blender_scene.SceneBuilder, blender_animate's settings); the set is built here:

    sunset_road   a flat two-lane road running straight into a low sun: a physical sky (the sun
                  disc for the camera; the light itself from a warm sun lamp along the same line
                  and the sky without its disc), faded dashed centre line, gravel shoulders,
                  dry grass either side, the ground hazing into the horizon with distance

The figure stands at the pivot on the road's centre line with its display stand hidden; the
parts hang on a rig (spin empty > group empties > parts): the spin turns the whole figure, the
groups play the performance. Kept apart from blender_animate.py so the studio plates' cache
keys (which hash that script) don't change when the sets do."""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import blender_animate as ba  # noqa: E402
import blender_scene as bs  # noqa: E402

TO_B = bs.TO_BLENDER
LDU = bs.LDU


def _node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = float(v)
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _smooth(nt, v, lo, hi):
    """0 below lo, 1 above hi, smoothstep between (hi < lo inverts)."""
    n = nt.nodes.new("ShaderNodeMapRange")
    ba._try(n, "interpolation_type", "SMOOTHSTEP")
    n.inputs["From Min"].default_value = lo
    n.inputs["From Max"].default_value = hi
    nt.links.new(v, n.inputs["Value"])
    return n.outputs["Result"]


def _mix_rgb(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    nt.links.new(fac, n.inputs["Factor"])
    for sock, v in ((n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (tuple, list)):
            sock.default_value = (*v, 1.0)
        else:
            nt.links.new(v, sock)
    return n.outputs[2]


def _sky(nt, sun, disc):
    s = nt.nodes.new("ShaderNodeTexSky")
    for kind in ("MULTIPLE_SCATTERING", "SINGLE_SCATTERING", "NISHITA"):
        if ba._try(s, "sky_type", kind):
            break
    s.sun_disc = disc
    s.sun_elevation = math.radians(sun["elevation"])
    s.sun_rotation = math.radians(sun["azimuth"])       # 0: along +Y (LDraw +Z), down the road
    s.sun_size = math.radians(sun["size"])
    ba._try(s, "sun_intensity", 1.0)
    ba._try(s, "altitude", 20.0)
    ba._try(s, "air_density", 1.2)
    ba._try(s, "aerosol_density", 3.0)                  # dusty: a big soft orange sun
    return s


def _tinted(nt, color, tint):
    """The sky warmed towards a dusty sunset (a filter over the physical sky)."""
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = "MULTIPLY"
    n.inputs["Factor"].default_value = 1.0
    nt.links.new(color, n.inputs[6])
    n.inputs[7].default_value = tint
    return n.outputs[2]


def sun_direction(sun) -> Vector:
    e, a = math.radians(sun["elevation"]), math.radians(sun["azimuth"])
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


# ---------------------------------------------------------------------------- sets
def sunset_road(sc, co, eevee):
    """The world, the sun, the road and the fields. Sizes follow the figure: it stands as tall as
    a man, so a lane is two of its heights wide."""
    sun = co["sun"]
    U = co["height"] * LDU                        # the figure's height, metres in Blender
    px, pz = co["pivot"]
    cx, cy = px * LDU, pz * LDU                   # LDraw (x, z) -> Blender (x, y)
    gz = -co["ground_y"] * LDU
    strength = float(co.get("sky_strength", 0.45))
    # sky: the camera sees the sun disc; everything else is lit by the sky without it
    world = bpy.data.worlds.new("sunset")
    sc.world = world
    nt = world.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    for n in list(nt.nodes):
        if n.name != out.name:
            nt.nodes.remove(n)
    cam_bg = _node(nt, "ShaderNodeBackground", Strength=strength)
    light_bg = _node(nt, "ShaderNodeBackground", Strength=strength)
    tint = (*bs.hex_to_linear(co.get("sky_tint", "#FFB070")), 1.0)
    nt.links.new(_tinted(nt, _sky(nt, sun, True).outputs[0], tint), cam_bg.inputs["Color"])
    light_sky = _sky(nt, sun, False)
    nt.links.new(_tinted(nt, light_sky.outputs[0], tint), light_bg.inputs["Color"])
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(light_bg.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    ba._try(world, "sun_threshold", 1e6)          # EEVEE: no second sun pulled from the sky
    # the sun itself: low, warm, long soft shadows towards the camera
    sd = bpy.data.lights.new("sun", "SUN")
    sd.color = tuple(bs.hex_to_linear(co.get("sun_color", "#FF9A4A")))
    sd.energy = float(co.get("sun_strength", 5.0))
    sd.angle = math.radians(sun["size"])
    ba._try(sd, "use_shadow_jitter", False)
    so = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(so)
    so.rotation_euler = (-sun_direction(sun)).to_track_quat("-Z", "Y").to_euler()
    # the rest of the sky bouncing back from the camera's side: a faint violet fill
    fd = bpy.data.lights.new("fill", "SUN")
    fd.color = tuple(bs.hex_to_linear("#8C7CC8"))
    fd.energy = float(co.get("fill_strength", 0.25))
    fd.angle = math.radians(40.0)
    ba._try(fd, "use_shadow", False)
    fo = bpy.data.objects.new("fill", fd)
    sc.collection.objects.link(fo)
    back = Vector((0.0, -1.0, 0.5)).normalized()
    fo.rotation_euler = (-back).to_track_quat("-Z", "Y").to_euler()
    # the ground: one big plane, road, shoulders and fields all in its material
    size = max(4000.0, 3000.0 * U)
    bpy.ops.mesh.primitive_plane_add(size=size, location=(cx, cy + size * 0.4, gz))
    ground = bpy.context.object
    ground.name = "ground"
    tint = (*bs.hex_to_linear(co.get("sky_tint", "#FFB070")), 1.0)
    ground.data.materials.append(road_material(co, U, cx, sun, strength, tint))
    sun_disc(sc, co)
    sc.view_settings.view_transform = "AgX"
    ba._try(sc.view_settings, "look", co.get("look", "AgX - Punchy"))
    sc.view_settings.exposure = float(co.get("exposure", -1.6))


DISC_AT = 1500.0          # m: where the sun disc hangs, along the sun's direction from the camera


def sun_disc(sc, co):
    """The sun as the camera sees it: an emissive disc facing the camera, as wide as the sun,
    yellow-white in the middle darkening to orange at the limb, soft-edged. (EEVEE draws the
    sky from a probe too coarse for the sky texture's own disc.) Camera rays only; it's kept
    at infinity (moved with the camera, see ColdOpen.apply)."""
    size = math.radians(co["sun"]["size"])
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=DISC_AT * math.tan(size / 2),
                                      fill_type="TRIFAN")
    ob = bpy.context.object
    ob.name = "sun_disc"
    for flag in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter"):
        ba._try(ob, flag, False)
    m = bpy.data.materials.new("sun_disc")
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    for n in list(nt.nodes):
        if n.name != out.name:
            nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    r = _math(nt, "DIVIDE", ln.outputs["Value"], DISC_AT * math.tan(size / 2))
    limb = _smooth(nt, r, 0.2, 1.0)
    col = _mix_rgb(nt, limb, (1.0, 0.56, 0.2), (0.95, 0.2, 0.025))
    em = _node(nt, "ShaderNodeEmission", Strength=float(co.get("sun_disc", 140.0)))
    nt.links.new(col, em.inputs["Color"])
    edge = _smooth(nt, r, 0.9, 1.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(edge, mix.inputs["Fac"])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    ba._try(m, "surface_render_method", "BLENDED")
    ob.data.materials.append(m)
    return ob


def road_material(co, U, cx, sun, strength, tint):
    m = bpy.data.materials.new("sunset_road")
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    for n in list(nt.nodes):
        if n.name != out.name:
            nt.nodes.remove(n)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    x = _math(nt, "SUBTRACT", sep.outputs["X"], cx)
    ax = _math(nt, "ABSOLUTE", x)
    y = sep.outputs["Y"]
    half = 1.95 * U                                # a lane each side of the centre line
    fine = _node(nt, "ShaderNodeTexNoise", Scale=1.0 / (0.012 * U), Detail=6.0)
    coarse = _node(nt, "ShaderNodeTexNoise", Scale=1.0 / (0.9 * U), Detail=4.0, Roughness=0.6)
    nt.links.new(geo.outputs["Position"], fine.inputs["Vector"])
    nt.links.new(geo.outputs["Position"], coarse.inputs["Vector"])
    # masks: road, shoulder (gravel), field (grass)
    road = _smooth(nt, ax, half + 0.02 * U, half - 0.02 * U)
    field = _smooth(nt, ax, half + 0.25 * U, half + 0.8 * U)
    # a faded dashed centre line (dashes 3 m of every 12 m, at the figure's scale)
    line_w = _smooth(nt, ax, 0.032 * U, 0.022 * U)
    period = 6.6 * U
    ph = _math(nt, "FRACT", _math(nt, "DIVIDE", y, period))
    dash = _smooth(nt, ph, 0.46, 0.43)
    wear = _smooth(nt, fine.outputs["Fac"], 0.35, 0.65)
    faded = _math(nt, "ADD", _math(nt, "MULTIPLY", wear, 0.5), 0.25)
    line = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", line_w, dash), faded)
    asphalt = _mix_rgb(nt, fine.outputs["Fac"], (0.028, 0.026, 0.024), (0.075, 0.07, 0.064))
    asphalt = _mix_rgb(nt, _smooth(nt, coarse.outputs["Fac"], 0.3, 0.7), asphalt, (0.05, 0.047, 0.043))
    col = _mix_rgb(nt, line, asphalt, (0.42, 0.3, 0.06))
    gravel = _mix_rgb(nt, fine.outputs["Fac"], (0.1, 0.075, 0.05), (0.2, 0.16, 0.11))
    col = _mix_rgb(nt, road, gravel, col)
    grass = _mix_rgb(nt, coarse.outputs["Fac"], (0.11, 0.065, 0.02), (0.36, 0.23, 0.07))
    grass = _mix_rgb(nt, _smooth(nt, fine.outputs["Fac"], 0.62, 0.72), grass, (0.05, 0.035, 0.015))
    col = _mix_rgb(nt, field, col, grass)
    rough = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, road), 0.5), 0.45)
    spec = _math(nt, "ADD", _math(nt, "MULTIPLY", road, 0.4), 0.12)
    bump = _node(nt, "ShaderNodeBump", Strength=0.25, Distance=0.004 * U)
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    bsdf = _node(nt, "ShaderNodeBsdfPrincipled")
    nt.links.new(spec, bsdf.inputs["Specular IOR Level"])     # the road's sheen, dull fields
    nt.links.new(col, bsdf.inputs["Base Color"])
    nt.links.new(rough, bsdf.inputs["Roughness"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    # haze: with distance the ground takes the colour of the sky at the horizon behind it
    cam = nt.nodes.new("ShaderNodeCameraData")
    dist = cam.outputs["View Distance"]
    haze = _math(nt, "SUBTRACT", 1.0, _math(nt, "EXPONENT", _math(nt, "DIVIDE", dist, -float(co.get("haze", 220.0)) * U)))
    view = nt.nodes.new("ShaderNodeVectorMath")
    view.operation = "SCALE"
    nt.links.new(geo.outputs["Incoming"], view.inputs[0])
    view.inputs["Scale"].default_value = -1.0
    flat = nt.nodes.new("ShaderNodeVectorMath")
    flat.operation = "MULTIPLY"
    nt.links.new(view.outputs[0], flat.inputs[0])
    flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    lift = nt.nodes.new("ShaderNodeVectorMath")
    lift.operation = "ADD"
    nt.links.new(flat.outputs[0], lift.inputs[0])
    lift.inputs[1].default_value = (0.0, 0.0, 0.02)
    norm = nt.nodes.new("ShaderNodeVectorMath")
    norm.operation = "NORMALIZE"
    nt.links.new(lift.outputs[0], norm.inputs[0])
    sky = _sky(nt, sun, False)
    nt.links.new(norm.outputs[0], sky.inputs["Vector"])
    em = _node(nt, "ShaderNodeEmission", Strength=strength)
    nt.links.new(_tinted(nt, sky.outputs[0], tint), em.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(haze, mix.inputs["Fac"])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


SETS = {"sunset_road": sunset_road}


# ---------------------------------------------------------------------------- the shoot
class ColdOpen:
    def __init__(self, tl, job):
        self.tl = tl
        co = self.co = tl["cold_open"]
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
        for sock, _ in ba.glow_inputs(self.eevee):     # EEVEE glass; glowing parts stay dark
            sock.default_value = 0.0
        SETS[co["scene"]](sc, co, self.eevee)
        self.exposure = sc.view_settings.exposure
        self.disc = bpy.data.objects.get("sun_disc")
        self.sun_dir = sun_direction(co["sun"])
        self._rig()
        cd = bpy.data.cameras.new("cold_cam")
        cd.sensor_width = 36
        U = co["height"] * LDU
        cd.clip_start = max(0.0005, 0.004 * U)
        cd.clip_end = max(4000.0, 3000.0 * U)
        self.cam = bpy.data.objects.new("cold_cam", cd)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam

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

    def apply(self, f):
        co = self.co
        k = min(max(f - co["start"], 0), len(co["spin"]) - 1)
        self.spin.matrix_basis = ba.to_blender(ba.ld_matrix(co["spin"][k]))
        for j, e in enumerate(self.groups):
            e.matrix_basis = ba.to_blender(ba.ld_matrix(co["frames"][k][j]))
        cam = co["camera"]
        loc = TO_B @ Vector(cam["pos"][k])
        tgt = TO_B @ Vector(cam["target"][k])
        self.cam.location = loc
        self.cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = cam["lens"][k]
        if self.disc is not None:                     # the sun stays at infinity
            self.disc.location = loc + self.sun_dir * DISC_AT
            self.disc.rotation_euler = self.sun_dir.to_track_quat("Z", "Y").to_euler()
        self.sc.view_settings.exposure = self.exposure + float(cam.get("exposure", [0.0] * (k + 1))[k])

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
