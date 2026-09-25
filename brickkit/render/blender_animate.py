"""Runs inside Blender: renders the model-scene frames of a build video (see brickkit/video).

    Blender -b --factory-startup -P blender_animate.py -- job.json

job.json: {"timeline": "timeline.json", "frames": [[frame, "out.png"], ...],
           "size": [w, h], "samples": n, "engine": "eevee" | "cycles",
           "variant": null | colourway name (timeline["variants"]: same parts, other colours)}

The scene itself (LEGO plastic materials, studio lights, ground, LDraw -> Blender) comes from
blender_scene.SceneBuilder. This script adds what moves: parts dropping in (build), moving groups
(mechanism), studio lights dimming while LEDs and glowing parts fade in (lights), the hover
(lift) and the camera. Each frame is set up from the timeline alone, so any subset of frames can
be rendered in any order; frames whose file already exists are skipped (resume)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import blender_scene as bs  # noqa: E402

BACKDROP = "#D9DDE3"      # what the camera sees behind the model (a touch darker than the
                          # light the world gives, so white parts stand out)
TO_B = bs.TO_BLENDER
TO_B_INV = TO_B.inverted()
TINY = Matrix.Diagonal(Vector((1e-4, 1e-4, 1e-4, 1.0)))   # parts not yet built
LED_BOOST = 5.0          # model LED power is tuned for Cycles stills; EEVEE needs a bit more
GLOW_EEVEE = 0.7         # emission scale for glowing translucent parts in EEVEE


def _try(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def ld_matrix(flat):
    return Matrix(np.asarray(flat, float).reshape(4, 4).tolist())


def to_blender(M):
    """A world transform in LDraw coordinates, as a Blender world transform."""
    return TO_B @ M @ TO_B_INV


# ---------------------------------------------------------------------------- setup
def eevee_settings(sc, samples):
    sc.render.engine = "BLENDER_EEVEE"
    ee = sc.eevee
    _try(ee, "taa_render_samples", int(samples))
    _try(ee, "use_raytracing", True)
    _try(ee, "ray_tracing_method", "SCREEN")
    opts = getattr(ee, "ray_tracing_options", None)
    if opts is not None:
        _try(opts, "resolution_scale", "2")
        _try(opts, "use_denoise", True)
    _try(ee, "use_fast_gi", True)
    _try(ee, "fast_gi_method", "GLOBAL_ILLUMINATION")
    _try(ee, "use_shadows", True)
    _try(ee, "shadow_ray_count", 2)
    _try(ee, "shadow_step_count", 8)
    _try(ee, "clamp_surface_indirect", 10.0)
    # no shadow jitter: soft shadows come from shadow-map ray marching instead, and the shadow
    # maps then render once per frame rather than once per sample (each is a GPU round trip)
    for light in bpy.data.lights:
        _try(light, "use_shadow_jitter", False)


def cycles_settings(sc, job):
    """Cycles for video: SceneBuilder's still settings, but with a fixed noise seed (steadier
    denoising from frame to frame), fewer bounces and optionally the CPU (when the GPU is
    shared with other renders)."""
    cy = sc.cycles
    cy.samples = int(job["samples"])
    cy.use_denoising = True
    _try(cy, "denoiser", "OPENIMAGEDENOISE")
    _try(cy, "denoising_input_passes", "RGB_ALBEDO_NORMAL")
    _try(cy, "use_animated_seed", False)
    cy.seed = 7
    cy.max_bounces = 24
    cy.transmission_bounces = 24
    cy.transparent_max_bounces = 24
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 3
    _try(cy, "use_adaptive_sampling", True)
    _try(cy, "adaptive_threshold", 0.03)
    if job.get("device", "GPU").upper() == "CPU":
        cy.device = "CPU"
        sc.render.threads_mode = "AUTO"


def eevee_glass(mat):
    """SceneBuilder's translucent plastic relies on Cycles volume absorption; EEVEE turns that
    into fog. Rebuild it as blended glass: a tinted see-through layer, glossy reflections that
    get stronger at grazing angles, and (for coloured plastic) a touch of body colour. No
    diffuse white: that is what made stacked clear parts milky. Returns the emission input
    (for glowing parts)."""
    nt = mat.node_tree
    vol = next((n for n in nt.nodes if n.type == "VOLUME_ABSORPTION"), None)
    if vol is None:
        return None
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    rgb = list(vol.inputs["Color"].default_value)[:3]
    glow = float(bsdf.inputs["Emission Strength"].default_value)
    for sock in ("Volume", "Surface"):
        for link in list(out.inputs[sock].links):
            nt.links.remove(link)
    lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    sat = max(rgb) - min(rgb)                      # 0 for clear, up to 1 for vivid colours
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Transmission Weight"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.25
    bsdf.inputs["Coat Weight"].default_value = 0.0
    bsdf.inputs["Emission Strength"].default_value = 0.0
    _try(bsdf.inputs["Specular IOR Level"], "default_value", 0.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    # each layer absorbs like a thin wall: light colours stay light, dark ones smoke
    tr.inputs["Color"].default_value = (*[max(c, 0.0) ** 0.38 for c in rgb], 1)
    gl = None
    for idname in ("ShaderNodeBsdfGlossy", "ShaderNodeBsdfAnisotropic"):
        try:
            gl = nt.nodes.new(idname)
            break
        except RuntimeError:
            continue
    gl.inputs["Color"].default_value = (1, 1, 1, 1)
    gl.inputs["Roughness"].default_value = 0.04
    body = nt.nodes.new("ShaderNodeMixShader")        # see-through, with a little colour
    body.inputs["Fac"].default_value = min(0.1, 0.07 * (1 - lum) + 0.05 * sat)
    nt.links.new(tr.outputs[0], body.inputs[1])
    nt.links.new(bsdf.outputs[0], body.inputs[2])
    fr = nt.nodes.new("ShaderNodeLayerWeight")
    fr.inputs["Blend"].default_value = 0.22
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY_ADD"
    nt.links.new(fr.outputs["Fresnel"], fac.inputs[0])
    fac.inputs[1].default_value = 0.55
    fac.inputs[2].default_value = 0.035
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac.outputs[0], mix.inputs["Fac"])
    nt.links.new(body.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    final, emission = mix, None
    if glow > 0:
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*rgb, 1)
        em.inputs["Strength"].default_value = 0.0
        add = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(mix.outputs[0], add.inputs[0])
        nt.links.new(em.outputs[0], add.inputs[1])
        final, emission = add, (em.inputs["Strength"], glow * GLOW_EEVEE)
    nt.links.new(final.outputs[0], out.inputs["Surface"])
    _try(mat, "surface_render_method", "BLENDED")
    _try(mat, "use_backface_culling", True)
    # only the nearest layer of each part: the insides of a brick (tubes, stud holes) blended
    # in arbitrary order read as fog
    _try(mat, "use_transparency_overlap", False)
    _try(mat, "use_transparent_shadow", True)
    return emission


def glow_inputs(eevee):
    """(socket, full strength) for every glowing material; they start dark."""
    out = []
    for mat in list(bpy.data.materials):
        if mat.node_tree is None:
            continue
        if eevee:
            em = eevee_glass(mat)
            if em is not None:
                out.append(em)
                continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None and mat.name.endswith("_glow"):
            sock = bsdf.inputs["Emission Strength"]
            out.append((sock, float(sock.default_value)))
            sock.default_value = 0.0
    return out


def camera_backdrop(rgb):
    """Camera rays see `rgb`; everything else keeps SceneBuilder's world light. Returns the
    backdrop's strength input."""
    world = bpy.context.scene.world
    nt = world.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    light = bs.principled_world(world)
    cam = nt.nodes.new("ShaderNodeBackground")
    cam.inputs[0].default_value = (*rgb, 1)
    cam.inputs[1].default_value = light.inputs[1].default_value
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(light.outputs[0], mix.inputs[1])
    nt.links.new(cam.outputs[0], mix.inputs[2])
    for link in list(out.inputs["Surface"].links):
        nt.links.remove(link)
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return cam.inputs[1]


def ground_fade(center, radius, bg, strength):
    """The ground melts into the background colour away from the model: no horizon line, a
    seamless studio sweep from any camera height. Returns the emission input (it dims with
    the world)."""
    gm = bpy.data.materials.get("ground")
    if gm is None or gm.node_tree is None:
        return None
    nt = gm.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    gb = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dist = nt.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = (center.x, center.y, 0.0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], dist.inputs[0])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    _try(ramp, "interpolation_type", "SMOOTHSTEP")
    ramp.inputs["From Min"].default_value = radius * 1.3
    ramp.inputs["From Max"].default_value = radius * 6.0
    nt.links.new(dist.outputs["Value"], ramp.inputs["Value"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*bg, 1)
    em.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(gb.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    for link in list(out.inputs["Surface"].links):
        nt.links.remove(link)
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return em.inputs["Strength"]


class Animator:
    def __init__(self, tl, job):
        self.tl = tl
        self.job = job
        scene = dict(tl["scene"])
        variant = job.get("variant")
        if variant:                  # a colourway: same parts, other colours
            v = tl["variants"][variant]
            scene["instances"] = [dict(inst, color=int(c)) for inst, c in
                                  zip(scene["instances"], v["instance_colors"])]
            scene["colors"] = {**scene["colors"], **v["colors"]}
        scene["engine"] = job.get("engine", "eevee")
        scene["size"] = job["size"]
        scene["samples"] = int(job["samples"])
        scene["lights"] = []
        self.eevee = scene["engine"] != "cycles"
        self.b, self.center, self.radius = bs.build_scene(scene)
        sc = self.sc = bpy.context.scene
        if self.eevee:
            eevee_settings(sc, job["samples"])
        else:
            cycles_settings(sc, job)
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.image_settings.compression = 15
        self.glow = glow_inputs(self.eevee)
        backdrop = bs.hex_to_linear(scene.get("backdrop", BACKDROP))
        self.world_strength = float(scene.get("world_strength", 1.2))
        self.world_bg = [bs.principled_world(sc.world).inputs[1], camera_backdrop(backdrop)]
        self.ground_em = ground_fade(self.center, self.radius, backdrop, self.world_strength)
        self.studio = [(ob.data, ob.data.energy) for ob in sc.objects
                       if ob.type == "LIGHT" and ob.name in ("key", "fill", "rim")]
        self._rig()
        self._camera()
        self._leds()
        self.state = np.full(len(self.b.objects), -2, np.int8)

    # rig: lift empty > group empties > parts ------------------------------------------------
    def _rig(self):
        tl, objs = self.tl, self.b.objects
        groups, lift = tl["groups"], tl["lift"]
        coll = bpy.context.scene.collection
        self.lift_empty = None
        if any(lift["instance"]):
            self.lift_empty = bpy.data.objects.new("lift", None)
            coll.objects.link(self.lift_empty)
        self.group_empties = {}          # (group index, lifted) -> empty

        def group_empty(g, lifted):
            key = (g, lifted)
            if key not in self.group_empties:
                e = bpy.data.objects.new(f"group_{groups['names'][g]}_{int(lifted)}", None)
                coll.objects.link(e)
                if lifted:
                    e.parent = self.lift_empty
                self.group_empties[key] = e
            return self.group_empties[key]

        self.rest = []
        off = []
        R = TO_B.to_3x3()
        for i, (ob, inst) in enumerate(zip(objs, tl["scene"]["instances"])):
            M = TO_B @ Matrix(inst["matrix"])
            self.rest.append(M)
            off.append(R @ Vector(tl["build"]["offset"][i]))
            if ob is None:
                continue
            g = groups["instance"][i]
            lifted = bool(lift["instance"][i]) and self.lift_empty is not None
            parent = group_empty(g, lifted) if g >= 0 else (self.lift_empty if lifted else None)
            if parent is not None:
                ob.parent = parent
                ob.matrix_parent_inverse = Matrix.Identity(4)
            ob.matrix_basis = M
        self.offset = off
        self.appear = np.asarray(tl["build"]["appear"], float)
        self.drop = float(tl["build"]["drop"])

    def _camera(self):
        cd = bpy.data.cameras.new("video_cam")
        cd.sensor_width = 36
        cd.clip_start = self.radius / 100
        cd.clip_end = self.radius * 200
        self.cam = bpy.data.objects.new("video_cam", cd)
        self.sc.collection.objects.link(self.cam)
        self.sc.camera = self.cam

    def _leds(self):
        self.leds = []
        for k, L in enumerate(self.tl["lights"]["leds"]):
            ob = self.b.objects[L["instance"]]
            ld = bpy.data.lights.new(f"led{k}", "POINT")
            ld.color = bs.hex_to_linear(L["color"])
            ld.shadow_soft_size = 0.002
            ld.energy = 0.0
            lo = bpy.data.objects.new(f"led{k}", ld)
            self.sc.collection.objects.link(lo)
            # at the light's offset in the part's own frame, cancelling the part's LDU scale
            local = Matrix.Translation(Vector(L.get("offset", (0, 0, 0)))) @ \
                Matrix.Scale(1 / bs.LDU, 4)
            if ob is not None:
                lo.parent = ob
                lo.matrix_parent_inverse = Matrix.Identity(4)
                lo.matrix_basis = local
            else:
                lo.matrix_world = self.rest[L["instance"]] @ local
            self.leds.append((ld, float(L["power"]) * LED_BOOST))

    # per frame -------------------------------------------------------------------------------
    def _keyed(self, block, f, index=None):
        """Matrix for frame f from a {start, frames[, after]} block: identity before, the last
        (or `after`) matrix once the block has played."""
        frames = block["frames"]
        if not frames:
            return Matrix.Identity(4)
        k = f - block["start"]
        if k < 0:
            return Matrix.Identity(4)
        if k >= len(frames):
            row = block["after"] if block.get("after") else frames[-1]
        else:
            row = frames[k]
        flat = row[index] if index is not None else row
        return to_blender(ld_matrix(flat))

    def apply(self, f):
        tl = self.tl
        # parts dropping in
        p = (f - self.appear) / self.drop
        new = np.where(p < 0, -1, np.where(p < 1, 1, 2)).astype(np.int8)
        todo = np.nonzero((new != self.state) | (new == 1))[0]
        for i in todo:
            ob = self.b.objects[i]
            if ob is None:
                continue
            if new[i] == -1:
                ob.matrix_basis = self.rest[i] @ TINY
            elif new[i] == 2:
                ob.matrix_basis = self.rest[i]
            else:
                e = 1 - (1 - p[i]) ** 3
                m = self.rest[i].copy()
                m.translation = self.rest[i].translation + self.offset[i] * (1 - e)
                ob.matrix_basis = m
        self.state = new
        # mechanism and hover
        for (g, _lifted), e in self.group_empties.items():
            e.matrix_basis = self._keyed(tl["groups"], f, g)
        if self.lift_empty is not None:
            self.lift_empty.matrix_basis = self._keyed(tl["lift"], f)
        # lights
        lt = tl["lights"]
        k = min(max(f - lt["start"], 0), len(lt["dim"]) - 1)
        dim, led, glow = lt["dim"][k], lt["led"][k], lt["glow"][k]
        for data, energy in self.studio:
            data.energy = energy * dim
        for sock in self.world_bg:
            sock.default_value = self.world_strength * dim
        if self.ground_em is not None:
            self.ground_em.default_value = self.world_strength * dim
        for data, power in self.leds:
            data.energy = power * led
        for sock, strength in self.glow:
            sock.default_value = strength * glow
        # camera
        cam = tl["camera"]
        k = min(max(f - cam["start"], 0), len(cam["pos"]) - 1)
        loc = TO_B @ Vector(cam["pos"][k])
        tgt = TO_B @ Vector(cam["target"][k])
        self.cam.location = loc
        self.cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = cam["lens"][k]

    def render(self, frames):
        done = 0
        for f, path in frames:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                continue
            t = time.time()
            self.apply(int(f))
            tmp = path + ".tmp.png"
            self.sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            os.replace(tmp, path)
            done += 1
            print(f"BRICKKIT_FRAME {f} {time.time() - t:.2f}", flush=True)
        return done


def main():
    job_path = sys.argv[sys.argv.index("--") + 1]
    with open(job_path) as fh:
        job = json.load(fh)
    with open(job["timeline"]) as fh:
        tl = json.load(fh)
    t = time.time()
    anim = Animator(tl, job)
    print(f"BRICKKIT_SETUP {time.time() - t:.1f}", flush=True)
    anim.render(job["frames"])
    print("BRICKKIT_DONE", flush=True)


if __name__ == "__main__":
    main()
