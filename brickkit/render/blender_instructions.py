"""Runs inside Blender: instruction-style step pictures and part pictures (Workbench engine).

    Blender -b --factory-startup -P blender_instructions.py -- scene.json
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from blender_scene import TO_BLENDER, hex_to_linear  # noqa: E402


def lifted(rgb):
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    if lum < 0.03:                        # black and near-black: show as charcoal so edges read
        return [c * 0.3 + 0.045 for c in rgb]
    return rgb


def _srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


class Instr:
    def __init__(self, s):
        self.s = s
        self.mats = {}
        self.meshes = {}

    def material(self, code, pale=False):
        key = (int(code), pale)
        if key in self.mats:
            return self.mats[key]
        info = self.s["colors"].get(str(code), {"rgb": "#888888", "alpha": 255})
        rgb = lifted(hex_to_linear(info["rgb"]))
        alpha = 0.5 if info["alpha"] < 255 else 1.0
        if pale:                          # mix toward white in sRGB so the hue survives
            rgb = [_lin(_srgb(c) * 0.62 + 0.38) for c in rgb]
            alpha = min(alpha, 0.85) if info["alpha"] < 255 else 1.0
        m = bpy.data.materials.new(f"i{code}{'p' if pale else ''}")
        m.diffuse_color = (*rgb, alpha)
        self.mats[key] = m
        return m

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
        lo, hi = verts.min(0), verts.max(0)
        ext = np.maximum(hi - lo, 1e-6)
        c = (lo + hi) / 2
        verts = c + (verts - c) * np.clip((ext - 0.3) / ext, 0.9, 1.0)
        me = bpy.data.meshes.new(part)
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.update()
        fixed = sorted({int(x) for x in cols.tolist()} - {16, 24})
        idx = np.zeros(len(me.polygons), np.int32)
        for k, code in enumerate(fixed):
            idx[cols[: len(idx)] == code] = k + 1
        me.materials.append(None)
        for code in fixed:
            me.materials.append(self.material(code))
        me.polygons.foreach_set("material_index", idx)
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
        try:
            me.set_sharp_from_angle(angle=math.radians(35))
        except Exception:
            pass
        self.meshes[part] = (me, fixed)
        return self.meshes[part]

    def objects(self, set_name, items):
        coll = bpy.data.collections.new(set_name)
        bpy.context.scene.collection.children.link(coll)
        objs = []
        for k, inst in enumerate(items):
            got = self.mesh(inst["part"])
            if got is None:
                objs.append(None)
                continue
            me, _ = got
            ob = bpy.data.objects.new(f"{set_name}_{k}", me)
            coll.objects.link(ob)
            ob.matrix_world = TO_BLENDER @ Matrix(inst["matrix"])
            ob.material_slots[0].link = "OBJECT"
            ob.hide_render = True
            objs.append(ob)
        return objs


def setup(s):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.curvature_ridge_factor = 1.2
    sh.curvature_valley_factor = 1.0
    sh.show_object_outline = True
    sh.object_outline_color = (0.08, 0.08, 0.08)
    sh.show_specular_highlight = True
    sc.display.render_aa = "16"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = 0.55
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.color = (1, 1, 1)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def view_rotation(az, el):
    a, e = math.radians(az), math.radians(el)
    direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    rot = (-direction).to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return direction, rot


def frame(cam, objs, az, el, aspect, margin=1.08):
    direction, rot = view_rotation(az, el)
    inv = rot.inverted()
    pts = []
    for ob in objs:
        for c in ob.bound_box:
            pts.append(inv @ (ob.matrix_world @ Vector(c)))
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cam.data.ortho_scale = max(w, h * aspect) * margin if aspect >= 1 else max(w / aspect, h) * margin
    centre = rot @ Vector((cx, cy, max(zs) + 1.0))
    cam.matrix_world = Matrix.Translation(centre) @ rot
    cam.data.clip_start = 0.001
    cam.data.clip_end = 100
    return w, h


def main():
    s = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = setup(s)
    sc = bpy.context.scene
    ins = Instr(s)
    sets = {name: ins.objects(name, items) for name, items in s["sets"].items()}
    colors_of = {name: [i["color"] for i in items] for name, items in s["sets"].items()}
    all_objs = [o for objs in sets.values() for o in objs if o is not None]
    W, H = s["size"]
    visible = set()                             # objects currently shown, over all sets
    for job in s["jobs"]:
        objs = sets[job["set"]]
        cols = colors_of[job["set"]]
        new = set(job["new"])
        shown, want = [], {}
        for n in job["visible"]:
            ob = objs[n]
            if ob is None:
                continue
            want[ob] = ins.material(cols[n], pale=not (n in new or job.get("all_full")))
            shown.append(ob)
        # touch only what changes: every property write re-tags the object for evaluation
        for ob in list(visible):
            if ob not in want:
                ob.hide_render = True
                visible.discard(ob)
        for ob, mat in want.items():
            if ob not in visible:
                ob.hide_render = False
                visible.add(ob)
            if ob.material_slots[0].material != mat:
                ob.material_slots[0].material = mat
        sc.render.resolution_x, sc.render.resolution_y = W, H
        sc.render.film_transparent = bool(job.get("transparent", job["name"].startswith("sub_")))
        if sc.render.film_transparent:
            sc.render.image_settings.file_format = "PNG"
            sc.render.image_settings.color_mode = "RGBA"
        else:
            sc.render.image_settings.file_format = "JPEG"
            sc.render.image_settings.color_mode = "RGB"
            sc.render.image_settings.quality = 88
        frame(cam, shown, job["azimuth"], job["elevation"], W / H)
        ext = ".png" if sc.render.film_transparent else ".jpg"
        sc.render.filepath = f"{s['out_dir']}/{job['name']}{ext}"
        bpy.ops.render.render(write_still=True)
        print("BRICKKIT_RENDERED", job["name"])
    for ob in all_objs:
        ob.hide_render = True
    # parts at one fixed scale
    coll = bpy.data.collections.new("parts")
    bpy.context.scene.collection.children.link(coll)
    px = float(s.get("part_px_per_ldu", 1.6))
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    for job in s["part_jobs"]:
        got = ins.mesh(job["part"])
        if got is None:
            continue
        me, _ = got
        ob = bpy.data.objects.new(job["name"], me)
        coll.objects.link(ob)
        ob.matrix_world = TO_BLENDER
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = ins.material(job["color"])
        bpy.context.view_layer.update()
        direction, rot = view_rotation(-35, 30)
        inv = rot.inverted()
        pts = [inv @ (ob.matrix_world @ Vector(c)) for c in ob.bound_box]
        w = max(p.x for p in pts) - min(p.x for p in pts)
        h = max(p.y for p in pts) - min(p.y for p in pts)
        ldu = 0.0004
        rw = max(24, int(w / ldu * px) + 16)
        rh = max(24, int(h / ldu * px) + 16)
        sc.render.resolution_x, sc.render.resolution_y = rw, rh
        frame(cam, [ob], -35, 30, rw / rh, margin=1.0 + 16 / max(rw, rh))
        sc.render.filepath = f"{s['out_dir']}/{job['name']}.png"
        bpy.ops.render.render(write_still=True)
        ob.hide_render = True
    print("BRICKKIT_DONE")


if __name__ == "__main__":
    main()
