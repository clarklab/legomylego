"""Runs inside Blender. Builds a scene from brickkit's scene.json and renders its views.

    Blender -b --factory-startup -P blender_scene.py -- scene.json

Other brickkit Blender scripts import `build_scene` from this file (see animate.py)."""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

LDU = 0.0004  # metres per LDraw unit
# LDraw (x, y, z) with -Y up  ->  Blender (x, z, -y) with +Z up
TO_BLENDER = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1))) @ Matrix.Scale(LDU, 4)


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h):
    h = h.lstrip("#")
    return [srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]


def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def principled(mat):
    if mat.node_tree is None:
        try:
            mat.use_nodes = True
        except Exception:
            pass
    nt = mat.node_tree
    node = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if node is None:
        node = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or \
            nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(node.outputs[0], out.inputs[0])
    return node


class SceneBuilder:
    def __init__(self, scene):
        self.s = scene
        self.mats = {}
        self.meshes = {}
        self.objects = []

    # materials --------------------------------------------------------------
    def material(self, code, glow=0.0):
        key = (int(code), float(glow))
        if key in self.mats:
            return self.mats[key]
        info = self.s["colors"].get(str(code), {"rgb": "#888888", "alpha": 255, "material": ""})
        m = bpy.data.materials.new(f"ld{code}" + ("_glow" if glow else ""))
        b = principled(m)
        rgb = hex_to_linear(info["rgb"])
        _set(b, "Base Color", (*rgb, 1.0))
        _set(b, "Roughness", 0.3)
        _set(b, "Specular IOR Level", 0.5)
        _set(b, "Coat Weight", 0.15)
        _set(b, "Coat Roughness", 0.1)
        if info["alpha"] < 255:
            _set(b, "Transmission Weight", 1.0)
            _set(b, "Roughness", 0.03)
            _set(b, "IOR", 1.58)
            _set(b, "Coat Weight", 0.0)
        kind = info.get("material", "")
        if kind in ("chrome", "metal", "matte_metallic"):
            _set(b, "Metallic", 1.0)
            _set(b, "Roughness", 0.18)
        elif kind == "pearlescent":
            _set(b, "Metallic", 0.6)
            _set(b, "Roughness", 0.3)
        elif kind == "rubber":
            _set(b, "Roughness", 0.75)
            _set(b, "Coat Weight", 0.0)
        if self.s.get("bevel", 0.3) > 0:
            nt = m.node_tree
            bev = nt.nodes.new("ShaderNodeBevel")
            bev.inputs["Radius"].default_value = self.s.get("bevel", 0.3) * LDU
            bev.samples = 6
            nt.links.new(bev.outputs["Normal"], b.inputs["Normal"])
        if glow:
            _set(b, "Emission Color", (*rgb, 1.0))
            _set(b, "Emission Strength", float(glow))
        self.mats[key] = m
        return m

    # meshes -----------------------------------------------------------------
    def mesh(self, part):
        if part in self.meshes:
            return self.meshes[part]
        d = np.load(self.s["meshes"][part])
        T = d["tris"].astype(np.float64)
        cols = d["colors"].astype(np.int64)
        if len(T) == 0:
            self.meshes[part] = None
            return None
        V = T.reshape(-1, 3)
        key = np.round(V * 64).astype(np.int64)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        faces = inv.reshape(-1, 3)
        ok = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
        faces, cols = faces[ok], cols[ok]
        verts = uniq / 64.0
        gap = float(self.s.get("gap", 0.15))
        if gap > 0:
            lo, hi = verts.min(0), verts.max(0)
            ext = np.maximum(hi - lo, 1e-6)
            c = (lo + hi) / 2
            verts = c + (verts - c) * np.clip((ext - 2 * gap) / ext, 0.9, 1.0)
        me = bpy.data.meshes.new(part)
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.update()
        fixed = sorted({int(c) for c in cols.tolist()} - {16, 24})
        idx = np.zeros(len(me.polygons), np.int32)
        for k, c in enumerate(fixed):
            idx[cols[: len(idx)] == c] = k + 1
        me.materials.append(None)
        for c in fixed:
            me.materials.append(self.material(c))
        me.polygons.foreach_set("material_index", idx)
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
        try:
            me.set_sharp_from_angle(angle=math.radians(35))
        except Exception:
            me.polygons.foreach_set("use_smooth", np.zeros(len(me.polygons), bool))
        self.meshes[part] = me
        return me

    def instances(self, collection_name="model"):
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
        for k, inst in enumerate(self.s["instances"]):
            me = self.mesh(inst["part"])
            if me is None:
                self.objects.append(None)
                continue
            ob = bpy.data.objects.new(f"{k:05d}_{inst['part']}", me)
            coll.objects.link(ob)
            ob.matrix_world = TO_BLENDER @ Matrix(inst["matrix"])
            ob.material_slots[0].link = "OBJECT"
            ob.material_slots[0].material = self.material(inst["color"], inst.get("glow", 0.0))
            self.objects.append(ob)
        return coll

    # stage ------------------------------------------------------------------
    def bounds(self):
        lo, hi = self.s["bounds"]
        corners = [TO_BLENDER @ Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                   for z in (lo[2], hi[2])]
        mn = Vector([min(c[i] for c in corners) for i in range(3)])
        mx = Vector([max(c[i] for c in corners) for i in range(3)])
        return mn, mx

    def stage(self):
        s = self.s
        sc = bpy.context.scene
        mn, mx = self.bounds()
        center = (mn + mx) / 2
        radius = max((mx - mn).length / 2, 0.01)
        world = bpy.data.worlds.new("world")
        sc.world = world
        bg = principled_world(world)
        bg.inputs[0].default_value = (*hex_to_linear(s.get("background", "#E9ECEF")), 1.0)
        bg.inputs[1].default_value = s.get("world_strength", 0.35)
        if s.get("ground", True):
            bpy.ops.mesh.primitive_plane_add(size=radius * 40, location=(center.x, center.y, mn.z - 0.0002))
            ground = bpy.context.object
            gm = bpy.data.materials.new("ground")
            gb = principled(gm)
            _set(gb, "Base Color", (*hex_to_linear(s.get("ground_color", s.get("background", "#E9ECEF"))), 1))
            _set(gb, "Roughness", 0.6)
            ground.data.materials.append(gm)
            if s.get("transparent"):
                ground.is_shadow_catcher = True
        d = radius * 6.0
        key_power = s.get("light_power", 1.6) * d * d * 4
        for name, direction, power, size in (
                ("key", (-1.1, -1.5, 1.7), 1.0, 2.2),
                ("fill", (1.6, -0.9, 0.7), 0.35, 3.0),
                ("rim", (0.4, 1.8, 1.4), 0.6, 1.6)):
            ld = bpy.data.lights.new(name, "AREA")
            ld.energy = key_power * power
            ld.size = radius * size
            lo = bpy.data.objects.new(name, ld)
            sc.collection.objects.link(lo)
            lo.location = center + Vector(direction).normalized() * d
            lo.rotation_euler = (center - lo.location).to_track_quat("-Z", "Y").to_euler()
        for i, L in enumerate(s.get("lights", [])):
            ld = bpy.data.lights.new(f"led{i}", "POINT")
            ld.energy = float(L.get("power", 1.5))
            ld.color = hex_to_linear(L.get("color", "#FF3A1A"))
            ld.shadow_soft_size = 0.002
            lo = bpy.data.objects.new(f"led{i}", ld)
            sc.collection.objects.link(lo)
            lo.location = TO_BLENDER @ Vector(L["pos"])
        return center, radius

    def camera(self, view, center, radius):
        sc = bpy.context.scene
        cd = bpy.data.cameras.new("cam")
        cam = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(cam)
        lens = float(view.get("lens", 70))
        cd.lens = lens
        cd.sensor_width = 36
        w, h = self.s["size"]
        fov = 2 * math.atan(18 / lens) * (min(w, h) / max(w, h) if w != h else 1)
        margin = float(view.get("margin", 1.08))
        dist = radius / math.sin(fov / 2) * margin
        az, el = math.radians(view["azimuth"]), math.radians(view["elevation"])
        direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        target = center + Vector(view.get("offset", (0, 0, 0)))
        cam.location = target + direction * dist
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        if view.get("ortho"):
            cd.type = "ORTHO"
            cd.ortho_scale = radius * 2 * margin
        cd.clip_start = dist / 200
        cd.clip_end = dist * 20
        sc.camera = cam
        return cam

    def settings(self):
        s = self.s
        sc = bpy.context.scene
        engine = s.get("engine", "cycles")
        if engine == "cycles":
            sc.render.engine = "CYCLES"
            prefs = bpy.context.preferences.addons["cycles"].preferences
            try:
                prefs.compute_device_type = "METAL"
                prefs.get_devices()
                for dev in prefs.devices:
                    dev.use = True
                sc.cycles.device = "GPU"
            except Exception:
                pass
            sc.cycles.samples = int(s.get("samples", 64))
            sc.cycles.use_denoising = True
            sc.cycles.max_bounces = 16
            sc.cycles.transmission_bounces = 16
            sc.cycles.transparent_max_bounces = 16
            sc.cycles.caustics_reflective = False
            sc.cycles.caustics_refractive = False
            sc.cycles.blur_glossy = 1.0
        else:
            for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
                try:
                    sc.render.engine = name
                    break
                except TypeError:
                    continue
        w, h = s["size"]
        sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = bool(s.get("transparent", False))
        sc.render.use_persistent_data = True
        try:
            sc.view_settings.view_transform = "AgX"
            sc.view_settings.look = s.get("look", "AgX - Punchy")
        except TypeError:
            pass


def principled_world(world):
    if world.node_tree is None:
        try:
            world.use_nodes = True
        except Exception:
            pass
    nt = world.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None) or \
            nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs[0], out.inputs[0])
    return bg


def build_scene(scene):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    b = SceneBuilder(scene)
    b.settings()
    b.instances()
    center, radius = b.stage()
    return b, center, radius


def main():
    path = sys.argv[sys.argv.index("--") + 1]
    with open(path) as fh:
        scene = json.load(fh)
    b, center, radius = build_scene(scene)
    for view in scene["views"]:
        b.camera(view, center, radius)
        bpy.context.scene.render.filepath = f"{scene['out_dir']}/{view['name']}.png"
        bpy.ops.render.render(write_still=True)
        print("BRICKKIT_RENDERED", view["name"])
    print("BRICKKIT_DONE")


if __name__ == "__main__":
    main()
