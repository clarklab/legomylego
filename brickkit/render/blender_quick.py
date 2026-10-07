"""Runs inside Blender: renders the frames of a Quick Bricks video (brickkit/video/quick.py).

    Blender -b --factory-startup -P blender_quick.py -- job.json

job.json: {"plan": "plan.json", "frames": [[frame, "out.png"], ...], "size": [w, h],
           "samples": n, "engine": "cycles", "device": "gpu" | "cpu"}

Photoreal (Cycles, the parts' plastic from blender_scene.SceneBuilder) in a little workshop at
the model's real size, the model in the middle of it: the plan's surface, room and light, any
with any (quick_sets.py: five surfaces, five rooms, three lights). The parts
fly in on the plan's per-frame transforms (hidden before they launch, and all of them from the
cut on: the empty set again - or, laid out, lying where the plan's `start` puts them before
they launch and again from the cut on, the surface big enough for them all: `floor`), keyed
either side of each frame so a 180-degree shutter blurs them, and the camera with them; its
depth of field from the plan (focus point, f-number), the 36 mm sensor on the frame's height."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import blender_animate as ba  # noqa: E402
import blender_scene as bs  # noqa: E402
import quick_sets  # noqa: E402

TO_B = bs.TO_BLENDER
BLUR_AT = 100


class Quick:
    def __init__(self, pl, job):
        self.pl = pl
        scene = dict(pl["scene"])
        scene.update(engine="cycles", size=job["size"], samples=int(job["samples"]), lights=[],
                     ground=False)
        self.b, self.center, self.radius = bs.build_scene(scene)
        sc = self.sc = bpy.context.scene
        for ob in list(sc.objects):                       # SceneBuilder's studio lights: ours instead
            if ob.type == "LIGHT":
                bpy.data.objects.remove(ob, do_unlink=True)
        ba.cycles_settings(sc, job)
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.image_settings.compression = 15
        if pl.get("view", "agx") == "filmic":          # the parts' colours true: under AgX a
            sc.view_settings.view_transform = "Filmic"  # bright yellow goes a pale orange
            ba._try(sc.view_settings, "look", "Medium High Contrast")
        else:
            ba._try(sc.view_settings, "look", "AgX - Medium High Contrast")
        exposure = float(pl.get("exposure", 0.0))
        sc.render.use_motion_blur = True
        sc.render.motion_blur_shutter = 0.5
        ba._try(sc.render, "motion_blur_position", "CENTER")
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        lo, hi = pl.get("floor") or pl["bounds"]       # (laid out: the parts on the table too)
        corners = [TO_B @ Vector((x, y, zz)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                   for zz in (lo[2], hi[2])]
        mn = Vector([min(v[i] for v in corners) for i in range(3)])
        mx = Vector([max(v[i] for v in corners) for i in range(3)])
        ev = quick_sets.build_set(pl["surface"], pl["room"], pl["light"], mn, mx, int(pl.get("seed", 7)),
                                  float(pl.get("reach", 0.0)))
        sc.view_settings.exposure = exposure + ev
        self.rest = [TO_B @ Matrix(inst["matrix"]) for inst in scene["instances"]]
        self.start = [TO_B @ ba.ld_matrix(p["start"]) if p and p.get("start") else None
                      for p in pl["parts"]]            # laid out: where each lies till it lifts
        for ob, M in zip(self.b.objects, self.rest):
            if ob is not None:
                ob.matrix_basis = M
        cd = bpy.data.cameras.new("quick_cam")
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 36.0
        cd.clip_start = 0.002
        cd.clip_end = 50.0
        cd.dof.use_dof = True
        cd.dof.aperture_blades = 7
        self.cam = bpy.data.objects.new("quick_cam", cd)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        self.moving = set()

    def part_matrix(self, i, f):
        """Part i at frame f (Blender world), or None while it isn't there."""
        p = self.pl["parts"][i]
        if p is None:
            return None
        if f >= self.pl["cut"] or f < p["launch"]:
            return self.start[i]
        k = f - p["launch"]
        if k >= len(p["frames"]):
            return self.rest[i]
        return TO_B @ ba.ld_matrix(p["frames"][k])

    def _key(self, ob, mats):
        ob.animation_data_clear()
        ob.rotation_mode = "QUATERNION"
        prev = None
        for dk, M in mats:
            loc, rot, scl = M.decompose()
            if prev is not None and rot.dot(prev) < 0:
                rot.negate()
            prev = rot
            ob.location, ob.rotation_quaternion, ob.scale = loc, rot, scl
            for path in ("location", "rotation_quaternion", "scale"):
                ob.keyframe_insert(path, frame=BLUR_AT + dk)

    def cam_matrix(self, f):
        c = self.pl["camera"]
        f = min(max(f, 0), len(c["pos"]) - 1)
        loc = TO_B @ Vector(c["pos"][f])
        tgt = TO_B @ Vector(c["target"][f])
        q = (tgt - loc).to_track_quat("-Z", "Y")
        return Matrix.Translation(loc) @ q.to_matrix().to_4x4()

    def apply(self, f):
        pl = self.pl
        now = set()
        for i, ob in enumerate(self.b.objects):
            if ob is None:
                continue
            M = self.part_matrix(i, f)
            ob.hide_render = M is None
            if M is None:
                continue
            p = pl["parts"][i]
            flying = p["launch"] <= f < p["launch"] + len(p["frames"]) + 1
            if flying:
                prev = self.part_matrix(i, f - 1)
                nxt = self.part_matrix(i, f + 1)
                self._key(ob, [(-1, prev or M), (0, M), (1, nxt or M)])
                now.add(i)
            else:
                if ob.animation_data is not None:
                    ob.animation_data_clear()
                ob.matrix_basis = M
        for i in self.moving - now:
            ob = self.b.objects[i]
            if ob is not None and ob.animation_data is not None:
                ob.animation_data_clear()
                M = self.part_matrix(i, f)
                if M is not None:
                    ob.matrix_basis = M
        self.moving = now
        cut = pl["cut"]
        same_shot = lambda a, b: (a < cut) == (b < cut)     # noqa: E731 (no blur across the cut)
        self._key(self.cam, [(dk, self.cam_matrix(f + dk if same_shot(f, f + dk) else f))
                             for dk in (-1, 0, 1)])
        self.sc.frame_set(BLUR_AT)
        c = pl["camera"]
        k = min(max(f, 0), len(c["pos"]) - 1)
        cd = self.cam.data
        cd.lens = float(c["lens"][k])
        loc = TO_B @ Vector(c["pos"][k])
        foc = TO_B @ Vector(c["focus"][k])
        axis = self.cam_matrix(k).to_3x3() @ Vector((0, 0, -1))
        cd.dof.focus_distance = max(0.01, (foc - loc).dot(axis))
        cd.dof.aperture_fstop = float(c["fstop"][k])

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
    with open(job["plan"]) as fh:
        pl = json.load(fh)
    t = time.time()
    q = Quick(pl, job)
    print(f"BRICKKIT_SETUP {time.time() - t:.1f}", flush=True)
    q.render(job["frames"])
    print("BRICKKIT_DONE", flush=True)


if __name__ == "__main__":
    main()
