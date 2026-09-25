"""Booklet flip for the build video: the instruction booklet lies on a table and its pages turn.

Two halves in one file:
  * engine side  `prepare(pdf, work, frames, fps, page_px)` picks the spreads to show, renders
                 those PDF pages to PNG (pypdfium2, else PyMuPDF) and returns the flip plan;
  * Blender side `main()` builds the book scene and renders the frames:
        Blender -b --factory-startup -P booklet_flip.py -- job.json
    job.json: {"plan": {...}, "frames": [[local_frame, "out.png"], ...], "size": [w, h],
               "samples": n}

The book opens from the cover. Leaf j carries pages (front F_j, back B_j); after it turns the
spread (B_j, F_j+1) shows. The spreads are spread evenly through the booklet so the flip shows
the cover, the first steps and the finished model. Pages bend as they turn (the free edge leads
while lifting and lands first)."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

HOLD_START = 14          # frames the closed booklet rests before the first turn
TURN = 30                # frames per page turn
STAGGER = 13             # frames between the starts of two turns
HOLD_END = 18
MAX_TURNS = 8


# ============================================================================ engine side
def _rasterizer(pdf: Path):
    """(page count, render(i, px) -> PIL image) or None when no PDF library is installed."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf))

        def render(i, px):
            page = doc[i]
            w, h = page.get_size()
            return page.render(scale=px / max(w, h)).to_pil().convert("RGB")
        return len(doc), render
    except ImportError:
        pass
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        doc = fitz.open(str(pdf))

        def render(i, px):
            page = doc[i]
            s = px / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
            return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return doc.page_count, render
    except ImportError:
        return None


def schedule(n_pages: int, frames: int) -> list[dict]:
    """Leaves to turn: [{front, back, start}] with 1-based page numbers (0 = blank)."""
    spreads = (n_pages - 1) // 2                    # spread m = pages (2m, 2m+1)
    fit = (frames - HOLD_START - TURN - HOLD_END) // STAGGER + 1
    n = max(0, min(MAX_TURNS, fit, spreads))
    if n == 0:
        return []
    ms = [1 + round(j * (spreads - 1) / (n - 1)) if n > 1 else 1 for j in range(n)]
    ms = sorted(set(ms))
    # a short booklet turns its few pages more slowly, over the same time
    span = frames - HOLD_START - TURN - HOLD_END
    stagger = STAGGER if len(ms) < 2 else min(max(STAGGER, span // (len(ms) - 1)), TURN)
    leaves, front = [], 1
    for j, m in enumerate(ms):
        leaves.append({"front": front, "back": 2 * m, "start": HOLD_START + j * stagger})
        front = 2 * m + 1 if 2 * m + 1 <= n_pages else 0
    leaves[-1]["next"] = front
    return leaves


def prepare(pdf: Path, work: Path, frames: int, fps: int = 30, page_px: int = 2048) -> dict | None:
    """Render the pages the flip needs; None if the PDF can't be read or is too short."""
    pdf = Path(pdf)
    r = _rasterizer(pdf)
    if r is None:
        print("booklet flip skipped: install pypdfium2 (or PyMuPDF) to read the booklet PDF")
        return None
    n_pages, render = r
    leaves = schedule(n_pages, frames)
    if not leaves:
        return None
    work.mkdir(parents=True, exist_ok=True)
    need = {1} | {x for lf in leaves for x in (lf["front"], lf["back"], lf.get("next", 0))}
    stamp = f"{pdf.stat().st_mtime_ns}-{pdf.stat().st_size}-{page_px}"
    pages, aspect = {}, None
    for n in sorted(x for x in need if 1 <= x <= n_pages):
        f = work / f"page{n:03d}_{page_px}.png"
        meta = f.with_suffix(".stamp")
        if not f.exists() or not meta.exists() or meta.read_text() != stamp:
            render(n - 1, page_px).save(f)
            meta.write_text(stamp)
        pages[str(n)] = str(f)
        if aspect is None:
            from PIL import Image
            with Image.open(f) as im:
                aspect = im.width / im.height
    return {"pdf": str(pdf), "stamp": stamp, "n_pages": n_pages, "pages": pages,
            "aspect": aspect or 297 / 210, "leaves": leaves, "turn": TURN, "frames": frames,
            "fps": fps}


# ============================================================================ Blender side
def _blender():
    import bpy
    import numpy as np
    from mathutils import Vector
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "render"))
    import blender_scene as bs
    return bpy, np, Vector, bs


PAGE_H = 0.21            # metres (A4 short side); the width follows the PDF's aspect
STACK = 0.0022           # thickness of each half of the booklet
NX = 48                  # page mesh segments across the page
CURL = 1.5               # radians of bend at mid-turn
TABLE = "#FFDB06"        # brand yellow
KEY = 13.0               # key light (W); fill and rim follow
WORLD = 0.2


def page_curve(u: float, width: float, nx: int = NX):
    """(x, z) along a turning page from the spine (x=0) to the free edge. u: 0 flat on the
    right .. 1 flat on the left; the free edge leads while lifting and lands first."""
    import numpy as np
    s = (np.arange(nx) + 0.5) / nx
    c = CURL * math.sin(math.pi * u)
    phi = np.clip(math.pi * u - c / 2 + c * s, 0.0, math.pi)
    ds = width / nx
    x = np.concatenate([[0.0], np.cumsum(np.cos(phi) * ds)])
    z = np.concatenate([[0.0], np.cumsum(np.sin(phi) * ds)])
    return x, z


class Book:
    def __init__(self, plan, job):
        bpy, np, Vector, bs = _blender()
        self.bpy, self.np, self.Vector, self.bs = bpy, np, Vector, bs
        self.plan = plan
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        sc = self.sc = bpy.context.scene
        if job.get("engine", "eevee") == "cycles":
            sc.render.engine = "CYCLES"
            cy = sc.cycles
            cy.samples = int(job["samples"])
            cy.use_denoising = True
            cy.seed = 7
            cy.max_bounces = 6
            if job.get("device", "GPU").upper() == "CPU":
                cy.device = "CPU"
            else:
                try:
                    prefs = bpy.context.preferences.addons["cycles"].preferences
                    prefs.compute_device_type = "METAL"
                    prefs.get_devices()
                    for dev in prefs.devices:
                        dev.use = True
                    cy.device = "GPU"
                except Exception:
                    pass
        else:
            sc.render.engine = "BLENDER_EEVEE"
            ee = sc.eevee
            for k, v in (("taa_render_samples", int(job["samples"])), ("use_raytracing", True),
                         ("use_fast_gi", True), ("use_shadows", True), ("shadow_ray_count", 2),
                         ("shadow_step_count", 8)):
                try:
                    setattr(ee, k, v)
                except (AttributeError, TypeError):
                    pass
        w, h = job["size"]
        sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.image_settings.compression = 15
        # Standard keeps the table the brand yellow of the title and end cards
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = float(job.get("exposure", 0.0))
        self.H = PAGE_H
        self.W = PAGE_H * float(plan["aspect"])
        self.images = {}
        self._world()
        self._table()
        self._stacks()
        self._pages()
        self._lights()
        self._camera()

    # materials -------------------------------------------------------------------------------
    def image(self, n):
        path = self.plan["pages"].get(str(n)) if n else None
        if path is None:
            return None
        if path not in self.images:
            img = self.bpy.data.images.load(path)
            img.colorspace_settings.name = "sRGB"
            self.images[path] = img
        return self.images[path]

    def page_material(self, name, two_sided):
        bpy = self.bpy
        m = bpy.data.materials.new(name)
        b = self.bs.principled(m)
        nt = m.node_tree
        b.inputs["Roughness"].default_value = 0.55
        uv = nt.nodes.new("ShaderNodeTexCoord")
        front = nt.nodes.new("ShaderNodeTexImage")
        front.extension = "EXTEND"
        nt.links.new(uv.outputs["UV"], front.inputs["Vector"])
        tint = nt.nodes.new("ShaderNodeMix")
        tint.data_type = "RGBA"
        tint.blend_type = "MULTIPLY"
        tint.inputs["Factor"].default_value = 1.0
        tint.inputs["B"].default_value = (0.92, 0.92, 0.9, 1)
        col = front.outputs["Color"]
        back = None
        if two_sided:
            # the back face shows the other page, mirrored across the page (u -> 1 - u)
            back = nt.nodes.new("ShaderNodeTexImage")
            back.extension = "EXTEND"
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "SUBTRACT"
            inv.inputs[0].default_value = 1.0
            comb = nt.nodes.new("ShaderNodeCombineXYZ")
            nt.links.new(uv.outputs["UV"], sep.inputs[0])
            nt.links.new(sep.outputs["X"], inv.inputs[1])
            nt.links.new(inv.outputs[0], comb.inputs["X"])
            nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
            nt.links.new(comb.outputs[0], back.inputs["Vector"])
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            pick = nt.nodes.new("ShaderNodeMix")
            pick.data_type = "RGBA"
            nt.links.new(geo.outputs["Backfacing"], pick.inputs["Factor"])
            nt.links.new(front.outputs["Color"], pick.inputs["A"])
            nt.links.new(back.outputs["Color"], pick.inputs["B"])
            col = pick.outputs["Result"]
        nt.links.new(col, tint.inputs["A"])
        nt.links.new(tint.outputs["Result"], b.inputs["Base Color"])
        return m, front, back

    def set_image(self, node, n):
        img = self.image(n)
        if img is None:                      # a blank page when the booklet has no such page
            if "blank_page" not in self.bpy.data.images:
                blank = self.bpy.data.images.new("blank_page", 4, 4)
                blank.pixels.foreach_set([1.0] * 64)
            img = self.bpy.data.images["blank_page"]
        if node.image != img:
            node.image = img

    # scene -----------------------------------------------------------------------------------
    def _world(self):
        bpy = self.bpy
        w = bpy.data.worlds.new("book_world")
        self.sc.world = w
        bg = self.bs.principled_world(w)
        bg.inputs[0].default_value = (1.0, 0.97, 0.9, 1)
        bg.inputs[1].default_value = WORLD

    def _table(self):
        bpy, bs = self.bpy, self.bs
        bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, 0))
        t = bpy.context.object
        m = bpy.data.materials.new("table")
        b = bs.principled(m)
        b.inputs["Base Color"].default_value = (*bs.hex_to_linear(TABLE), 1)
        b.inputs["Roughness"].default_value = 0.7
        t.data.materials.append(m)

    def _box(self, name, x0, x1, z1, mat):
        bpy = self.bpy
        me = bpy.data.meshes.new(name)
        H = self.H / 2
        v = [(x0, -H, 0), (x1, -H, 0), (x1, H, 0), (x0, H, 0),
             (x0, -H, z1), (x1, -H, z1), (x1, H, z1), (x0, H, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(v, [], f)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        self.sc.collection.objects.link(ob)
        return ob

    def _plane(self, name, x0, x1, z, mat):
        bpy = self.bpy
        me = bpy.data.meshes.new(name)
        H = self.H / 2
        me.from_pydata([(x0, -H, z), (x1, -H, z), (x1, H, z), (x0, H, z)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new()
        for li, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
            uv.data[li].uv = (u, v)
        me.materials.append(mat)
        ob = self.bpy.data.objects.new(name, me)
        self.sc.collection.objects.link(ob)
        return ob

    def _stacks(self):
        bpy, bs = self.bpy, self.bs
        paper = bpy.data.materials.new("paper_edge")
        b = bs.principled(paper)
        b.inputs["Base Color"].default_value = (*bs.hex_to_linear("#EDEBE4"), 1)
        b.inputs["Roughness"].default_value = 0.8
        W = self.W
        self.right_stack = self._box("right_stack", 0, W, STACK, paper)
        self.left_stack = self._box("left_stack", -W, 0, STACK, paper)
        mr, self.right_tex, _ = self.page_material("right_top", False)
        ml, self.left_tex, _ = self.page_material("left_top", False)
        self.right_top = self._plane("right_top", 0, W, STACK + 0.00005, mr)
        self.left_top = self._plane("left_top", -W, 0, STACK + 0.00005, ml)

    def _pages(self):
        """Three reusable page meshes (at most three pages are in the air at once)."""
        bpy, np = self.bpy, self.np
        self.turners = []
        ny = 2
        for k in range(3):
            me = bpy.data.meshes.new(f"page{k}")
            verts = [(0.0, 0.0, 0.0)] * ((NX + 1) * (ny + 1))
            faces = [(j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1,
                      (j + 1) * (NX + 1) + i) for j in range(ny) for i in range(NX)]
            me.from_pydata(verts, [], faces)
            uv = me.uv_layers.new()
            for poly in me.polygons:
                for li in poly.loop_indices:
                    vi = me.loops[li].vertex_index
                    i, j = vi % (NX + 1), vi // (NX + 1)
                    uv.data[li].uv = (i / NX, j / ny)
            me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
            mat, front, back = self.page_material(f"turn{k}", True)
            me.materials.append(mat)
            ob = bpy.data.objects.new(f"page{k}", me)
            self.sc.collection.objects.link(ob)
            ob.hide_render = True
            self.turners.append((ob, front, back))
        self.ys = np.linspace(-self.H / 2, self.H / 2, ny + 1)

    def _lights(self):
        bpy, Vector = self.bpy, self.Vector
        for name, loc, energy, size in (("key", (-0.55, -0.7, 1.1), KEY, 0.9),
                                        ("fill", (0.9, -0.3, 0.6), KEY * 0.25, 1.2),
                                        ("rim", (0.2, 0.9, 0.8), KEY * 0.2, 0.8)):
            ld = bpy.data.lights.new(name, "AREA")
            ld.energy = energy
            ld.size = size
            lo = bpy.data.objects.new(name, ld)
            self.sc.collection.objects.link(lo)
            lo.location = loc
            lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    def _camera(self):
        bpy = self.bpy
        cd = bpy.data.cameras.new("book_cam")
        cd.lens = 50
        cd.sensor_width = 36
        cd.clip_start = 0.01
        cd.clip_end = 50
        self.cam = bpy.data.objects.new("book_cam", cd)
        self.sc.collection.objects.link(self.cam)
        self.sc.camera = self.cam

    # per frame -------------------------------------------------------------------------------
    def apply(self, f):
        np, Vector = self.np, self.Vector
        plan = self.plan
        leaves, turn = plan["leaves"], plan["turn"]
        started = [lf for lf in leaves if lf["start"] <= f]
        finished = [lf for lf in leaves if lf["start"] + turn <= f]
        flying = [lf for lf in started if lf not in finished]
        nxt = leaves[len(started)]["front"] if len(started) < len(leaves) else leaves[-1]["next"]
        self.set_image(self.right_tex, nxt)
        opened = bool(finished)
        self.left_stack.hide_render = not opened
        self.left_top.hide_render = not opened
        if opened:
            self.set_image(self.left_tex, finished[-1]["back"])
        for k, (ob, front, back) in enumerate(self.turners):
            if k >= len(flying):
                ob.hide_render = True
                continue
            lf = flying[k]
            j = leaves.index(lf)
            u = (f - lf["start"]) / turn
            u = u * u * (3 - 2 * u)
            x, z = page_curve(u, self.W)
            lift = STACK + 0.0002 * (1 + (len(leaves) - j) * (1 - u) + j * u)
            co = np.zeros((len(self.ys), NX + 1, 3))
            co[:, :, 0] = x[None, :]
            co[:, :, 1] = self.ys[:, None]
            co[:, :, 2] = z[None, :] + lift
            ob.data.vertices.foreach_set("co", co.reshape(-1))
            ob.data.update()
            self.set_image(front, lf["front"])
            self.set_image(back, lf["back"])
            ob.hide_render = False
        # camera: a slow push-in over the open booklet, turned a little for a diagonal layout
        n = plan["frames"]
        k = f / max(1, n - 1)
        ease = k * k * (3 - 2 * k)
        dist = (1.02 - 0.08 * ease) * (self.W / 0.297)
        az = math.radians(-12 + 6 * ease)
        el = math.radians(50 + 5 * ease)
        tgt = Vector((self.W * (0.18 * (1 - ease)), 0.0, 0.03))
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        self.cam.location = tgt + d * dist
        self.cam.rotation_euler = (tgt - self.cam.location).to_track_quat("-Z", "Y").to_euler()

    def render(self, frames):
        bpy = self.bpy
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
    book = Book(job["plan"], job)
    book.render(job["frames"])
    print("BRICKKIT_DONE", flush=True)


if __name__ == "__main__":
    main()
