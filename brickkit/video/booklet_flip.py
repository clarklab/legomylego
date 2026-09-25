"""Booklet beat of the build video: the printed instruction booklet, as a hero moment.

A saddle-stitched landscape booklet lies across the table (its stacks as thick as its page
count makes them, sheet edges, satin paper, staples in the gutter). It starts closed on its
real cover; the cover opens and a thumb-flip riffles through the real step pages, fast then
slowing, the last turns landing on a clear step spread. Then loose step sheets are dealt
into a fan like a hand of cards (for a model with colourways, from every colourway's
booklet). Motion blur comes from averaging sub-frames where pages move fast.

Two halves in one file:
  * engine side  `prepare(pdf, work, frames, fps, page_px, beat, variant_pdfs)` finds the
                 cover and the step pages, plans the turns and the fan, renders the pages it
                 needs to PNG (pypdfium2, else PyMuPDF) and returns the plan;
  * Blender side `main()` builds the scene and renders frames (local frame numbers may be
                 fractional: sub-frames for motion blur):
        Blender -b --factory-startup -P booklet_flip.py -- job.json
    job.json: {"plan": {...}, "frames": [[local_frame, "out.png"], ...], "size": [w, h],
               "samples": n}
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

HOLD = 6                 # frames on the closed cover
COVER_TURN = 16          # the cover's turn (slower than the riffle)
TURNS = 14               # leaves turned in the thumb-flip (after the cover)
FAN_SHEETS = 6
FLIP_SHARE = 0.58        # of the segment: the flip, then the fan
LEAF = 0.00012           # m per leaf (two pages) of 80 gsm paper
BLUR = (-0.4, -0.2, 0.0, 0.2, 0.4)   # sub-frames averaged where pages move fast
FAST = 0.1               # radians per frame a page must turn to be motion-blurred


# ============================================================================ engine side
def _rasterizer(pdf: Path):
    """(page count, render(i, px) -> PIL image, text(i) -> str) or None."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf))

        def render(i, px):
            page = doc[i]
            w, h = page.get_size()
            return page.render(scale=px / max(w, h)).to_pil().convert("RGB")

        def text(i):
            try:
                return doc[i].get_textpage().get_text_range()
            except Exception:              # noqa: BLE001 - text only helps find the steps
                return ""
        return len(doc), render, text
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

        def text(i):
            return doc[i].get_text()
        return doc.page_count, render, text
    except ImportError:
        return None


def step_pages(texts: list[str]) -> tuple[int, int]:
    """(first, last) 1-based step pages: after the build overview, before 'It works!' / the
    parts inventory / 'About this model'. Falls back to everything but the first and last."""
    n = len(texts)
    heads = [t.strip().split("\n", 1)[0].strip().lower() for t in texts]
    first = next((i + 2 for i, h in enumerate(heads) if h.startswith("build overview")), None)
    ends = [i + 1 for i, h in enumerate(heads)
            if h.startswith(("it works", "parts inventory", "about this model"))]
    last = (min(e for e in ends if first is None or e > first) - 1) if ends else None
    first = first or min(2, n)
    last = last if last and last >= first else max(first, n - 1)
    return first, last


def _ease_gaps(n: int, lo: float, hi: float, power: float) -> list[float]:
    return [lo + (hi - lo) * (k / max(1, n - 1)) ** power for k in range(n)]


def outline_spread(render, first: int, last: int, samples: int = 16) -> int | None:
    """The mid-book step spread whose pages show the most yellow new-part outline (the section
    tag in the top corner is left out): where the thumb-flip lands, so the outlines read."""
    import numpy as np
    lo, hi = max(1, (first + 1) // 2), max(1, (last - 1) // 2)
    if hi <= lo:
        return None
    a, b = lo + round(0.3 * (hi - lo)), lo + round(0.8 * (hi - lo))
    cands = sorted({round(a + (b - a) * k / max(1, samples - 1)) for k in range(samples)})
    best, score = None, -1
    for m in cands:
        total = 0
        for page in (2 * m, 2 * m + 1):
            if not first <= page <= last:
                continue
            im = np.asarray(render(page - 1, 240), np.int16)
            im = im[int(0.2 * im.shape[0]):]             # below the section tag
            r, g, bl = im[..., 0], im[..., 1], im[..., 2]
            total += int(((r > 200) & (g > 150) & (bl < 90) & (r - bl > 130)).sum())
        if total > score:
            best, score = m, total
    return best


def flip_schedule(n_pages: int, first: int, last: int, end: int, turns: int = TURNS,
                  final: int | None = None) -> dict:
    """Leaves to turn ([{front, back, start, dur}], 1-based pages, 0 = blank): the cover, then
    `turns` leaves riffling through the step pages - quick at first, slowing - so the last
    one lands on a step spread by frame `end`. A spread m shows pages (2m, 2m+1)."""
    lo, hi = max(1, (first + 1) // 2), max(1, (last - 1) // 2)       # step spreads
    if final is None:
        final = lo + round(0.55 * (hi - lo))
    final = min(hi, max(lo, final))
    turns = max(1, min(turns, final - lo + 1 if final > lo else 1))
    ms = sorted({lo + round(j * (final - lo) / max(1, turns - 1)) for j in range(turns)})
    if ms[-1] != final:
        ms.append(final)
    leaves = [{"front": 1, "back": 2, "start": HOLD, "dur": COVER_TURN}]
    front = 3
    gaps = _ease_gaps(len(ms), 2.4, 11.0, 2.2)
    durs = _ease_gaps(len(ms), 10.0, 21.0, 1.4)
    t = HOLD + 9.0
    starts = []
    for g in gaps:
        starts.append(t)
        t += g
    # fit: the last turn ends a few frames before `end`
    last_end = starts[-1] + durs[-1]
    room = end - 5 - (HOLD + 9.0)
    if last_end - (HOLD + 9.0) > room > 0:
        k = room / (last_end - (HOLD + 9.0))
        starts = [HOLD + 9.0 + (s - HOLD - 9.0) * k for s in starts]
        durs = [d * max(k, 0.7) for d in durs]
    for m, s, d in zip(ms, starts, durs):
        leaves.append({"front": front if front <= n_pages else 0, "back": 2 * m,
                       "start": round(s, 2), "dur": round(d, 2)})
        front = 2 * m + 1
    leaves[-1]["next"] = front if front <= n_pages else 0
    return {"leaves": leaves, "final": [leaves[-1]["back"], leaves[-1]["next"]],
            "spreads": [0] + ms}


def fan_plan(first: int, last: int, avoid: set, start: int, frames: int, beat: int,
             books: list[str], n: int = FAN_SHEETS) -> dict:
    """Loose step sheets dealt into a fan: [{page key, t0, dur, angle}]. Keys are "12" for
    the booklet's page 12 or "albino:12" for a colourway booklet's."""
    pool = [p for p in range(first, last + 1) if p not in avoid] or list(range(first, last + 1))
    picks = [pool[round((k + 0.5) * (len(pool) - 1) / n)] for k in range(n)]
    step = max(3, min(beat // 3, (frames - start - 26) // max(1, n)))
    sheets = []
    for k, p in enumerate(picks):
        book = books[k % len(books)]
        key = f"{book}:{p}" if book else str(p)
        ang = -24.0 + 48.0 * k / max(1, n - 1)
        # the first sheet is already in the air at the cut
        sheets.append({"page": key, "t0": start - 3 + k * step, "dur": 13, "angle": ang})
    return {"start": start, "sheets": sheets,
            "settle": sheets[-1]["t0"] + sheets[-1]["dur"] if sheets else start}


def page_curve(u: float, width: float, nx: int = 40, curl: float = 1.5):
    """(x, z) along a turning page from the spine (x=0) to the free edge. u: 0 flat on the
    right .. 1 flat on the left; the free edge leads while lifting and lands first."""
    import numpy as np
    s = (np.arange(nx) + 0.5) / nx
    c = curl * math.sin(math.pi * u)
    phi = np.clip(math.pi * u - c / 2 + c * s, 0.0, math.pi)
    ds = width / nx
    x = np.concatenate([[0.0], np.cumsum(np.cos(phi) * ds)])
    z = np.concatenate([[0.0], np.cumsum(np.sin(phi) * ds)])
    return x, z


def turn_u(leaf: dict, f: float) -> float:
    """How far a leaf has turned at (local) frame f, eased: 0 .. 1."""
    u = min(1.0, max(0.0, (f - leaf["start"]) / leaf["dur"]))
    return u * u * (3 - 2 * u)


def blur_frames(plan: dict) -> dict[int, list[float]]:
    """Local frames whose pages move fast enough to be rendered as averaged sub-frames."""
    out = {}
    for f in range(plan["frames"]):
        fast = False
        for lf in plan["flip"]["leaves"]:
            a, b = turn_u(lf, f - 0.5), turn_u(lf, f + 0.5)
            if abs(b - a) * math.pi > FAST:
                fast = True
                break
        if not fast:
            for sh in plan["fan"]["sheets"]:
                if sh["t0"] <= f < sh["t0"] + sh["dur"] * 0.7:
                    fast = True
                    break
        if fast:
            out[f] = list(BLUR)
    return out


def prepare(pdf: Path, work: Path, frames: int, fps: int = 30, page_px: int = 2048,
            beat: int = 15, variant_pdfs: dict | None = None) -> dict | None:
    """Render the pages the beat needs and plan it; None if the PDF can't be read."""
    pdf = Path(pdf)
    r = _rasterizer(pdf)
    if r is None:
        print("booklet beat skipped: install pypdfium2 (or PyMuPDF) to read the booklet PDF")
        return None
    n_pages, render, text = r
    if n_pages < 4:
        return None
    first, last = step_pages([text(i) for i in range(n_pages)])
    flip_end = max(beat * 2, round(frames * FLIP_SHARE / beat) * beat)
    flip = flip_schedule(n_pages, first, last, flip_end,
                         final=outline_spread(render, first, last))
    books = {"": (pdf, render, first, last)}
    for name, vp in (variant_pdfs or {}).items():
        vr = _rasterizer(Path(vp))
        if vr is not None:
            vf, vl = step_pages([vr[2](i) for i in range(vr[0])])
            if vl - vf == last - first:            # the same steps, maybe other end matter
                books[name] = (Path(vp), vr[1], vf, vl)
    fan = fan_plan(first, last, set(flip["final"]), flip_end, frames, beat, list(books))
    for sh in fan["sheets"]:                        # into each colourway booklet's numbering
        book, _, num = sh["page"].rpartition(":")
        if book:
            sh["page"] = f"{book}:{int(num) - first + books[book][2]}"
    work.mkdir(parents=True, exist_ok=True)
    need = {str(x) for lf in flip["leaves"] for x in (lf["front"], lf["back"], lf.get("next", 0))
            if x} | {"1"} | {s["page"] for s in fan["sheets"]}
    pages, aspect, stamp = {}, None, []
    for key in sorted(need):
        book, _, num = key.rpartition(":")
        src, rend = books[book][:2]
        st = f"{src.stat().st_mtime_ns}-{src.stat().st_size}-{page_px}"
        stamp.append(st)
        f = work / f"{book + '_' if book else ''}page{int(num):03d}_{page_px}.png"
        meta = f.with_suffix(".stamp")
        if not f.exists() or not meta.exists() or meta.read_text() != st:
            rend(int(num) - 1, page_px).save(f)
            meta.write_text(st)
        pages[key] = str(f)
        if aspect is None:
            from PIL import Image
            with Image.open(f) as im:
                aspect = im.width / im.height
    plan = {"pdf": str(pdf), "stamp": "|".join(sorted(set(stamp))), "n_pages": n_pages,
            "step_pages": [first, last], "pages": pages, "aspect": aspect or 297 / 210,
            "flip": {**flip, "end": flip_end}, "fan": fan, "frames": frames, "fps": fps,
            "leaves_total": (n_pages + 1) // 2, "books": list(books)}
    plan["blur"] = {str(k): v for k, v in blur_frames(plan).items()}
    # the old keys the video's graphics and sound read
    plan["leaves"] = flip["leaves"]
    plan["turn"] = COVER_TURN
    return plan


# ============================================================================ Blender side
def _blender():
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "render"))
    import blender_scene as bs
    return bpy, np, Matrix, Vector, bs


PAGE_H = 0.21            # metres (A4 short side); the width follows the PDF's aspect
NX, NY = 40, 10          # turning page mesh segments (across, along the spine)
CURL = 1.5               # radians of bend at mid-turn
TWIST = 0.07             # the lower corner leads the turn by this much at mid-turn
TABLE = "#FFDB06"        # brand yellow
BOOK_ROT = 30.0          # degrees: the booklet lies diagonally across the square frame
KEY = 16.0               # key light (W); fill and rim follow
WORLD = 0.22
AIR = 8                  # page meshes (pages in the air at once)


class Book:
    def __init__(self, plan, job):
        bpy, np, Matrix, Vector, bs = _blender()
        self.bpy, self.np, self.Matrix, self.Vector, self.bs = bpy, np, Matrix, Vector, bs
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
                         ("use_fast_gi", True), ("fast_gi_method", "GLOBAL_ILLUMINATION"),
                         ("use_shadows", True), ("shadow_ray_count", 3),
                         ("shadow_step_count", 10)):
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
        # Standard keeps the table the brand yellow of the cards
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = float(job.get("exposure", 0.0))
        self.H = PAGE_H
        self.W = PAGE_H * float(plan["aspect"])
        self.images = {}
        self.root = bpy.data.objects.new("book", None)
        sc.collection.objects.link(self.root)
        self.root.rotation_euler = (0, 0, math.radians(BOOK_ROT))
        self._world()
        self._table()
        self._stacks()
        self._pages()
        self._staples()
        self._fan()
        self._lights()
        self._camera()

    # materials -------------------------------------------------------------------------------
    def image(self, key):
        path = self.plan["pages"].get(str(key)) if key else None
        if path is None:
            return None
        if path not in self.images:
            img = self.bpy.data.images.load(path)
            img.colorspace_settings.name = "sRGB"
            self.images[path] = img
        return self.images[path]

    def paper(self, b, gloss=False):
        """Satin paper: a little sheen, soft highlights."""
        b.inputs["Roughness"].default_value = 0.3 if gloss else 0.46
        for name, v in (("Specular IOR Level", 0.45 if gloss else 0.32), ("Sheen Weight", 0.25),
                        ("Coat Weight", 0.15 if gloss else 0.0), ("Coat Roughness", 0.2)):
            if name in b.inputs:
                b.inputs[name].default_value = v

    def page_material(self, name, two_sided, gloss=False):
        bpy = self.bpy
        m = bpy.data.materials.new(name)
        b = self.bs.principled(m)
        nt = m.node_tree
        self.paper(b, gloss)
        uv = nt.nodes.new("ShaderNodeTexCoord")
        front = nt.nodes.new("ShaderNodeTexImage")
        front.extension = "EXTEND"
        nt.links.new(uv.outputs["UV"], front.inputs["Vector"])
        tint = nt.nodes.new("ShaderNodeMix")
        tint.data_type = "RGBA"
        tint.blend_type = "MULTIPLY"
        tint.inputs["Factor"].default_value = 1.0
        tint.inputs["B"].default_value = (0.93, 0.93, 0.91, 1)
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

    def edge_material(self):
        """The side of a stack of sheets: fine lines, one per sheet or so."""
        bpy, bs = self.bpy, self.bs
        m = bpy.data.materials.new("paper_edge")
        b = bs.principled(m)
        nt = m.node_tree
        b.inputs["Roughness"].default_value = 0.7
        co = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(co.outputs["Object"], sep.inputs[0])
        k = nt.nodes.new("ShaderNodeMath")
        k.operation = "MULTIPLY"
        k.inputs[1].default_value = 1.0 / LEAF * 0.5            # a line every two leaves
        nt.links.new(sep.outputs["Z"], k.inputs[0])
        fr = nt.nodes.new("ShaderNodeMath")
        fr.operation = "FRACT"
        nt.links.new(k.outputs[0], fr.inputs[0])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*bs.hex_to_linear("#D6D2C8"), 1)
        ramp.color_ramp.elements[1].position = 0.35
        ramp.color_ramp.elements[1].color = (*bs.hex_to_linear("#F4F2EC"), 1)
        nt.links.new(fr.outputs[0], ramp.inputs[0])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        return m

    def set_image(self, node, key):
        img = self.image(key)
        if img is None:                      # a blank page when the booklet has no such page
            if "blank_page" not in self.bpy.data.images:
                blank = self.bpy.data.images.new("blank_page", 4, 4)
                blank.pixels.foreach_set([1.0] * 64)
            img = self.bpy.data.images["blank_page"]
        if node.image != img:
            node.image = img

    # scene -----------------------------------------------------------------------------------
    def link(self, ob, parent=True):
        self.sc.collection.objects.link(ob)
        if parent:
            ob.parent = self.root
        return ob

    def _world(self):
        bpy = self.bpy
        w = bpy.data.worlds.new("book_world")
        self.sc.world = w
        bg = self.bs.principled_world(w)
        bg.inputs[0].default_value = (1.0, 0.97, 0.9, 1)
        bg.inputs[1].default_value = WORLD

    def _table(self):
        bpy, bs = self.bpy, self.bs
        me = bpy.data.meshes.new("table")
        me.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)], [], [(0, 1, 2, 3)])
        m = bpy.data.materials.new("table")
        b = bs.principled(m)
        b.inputs["Base Color"].default_value = (*bs.hex_to_linear(TABLE), 1)
        b.inputs["Roughness"].default_value = 0.72
        me.materials.append(m)
        self.link(bpy.data.objects.new("table", me), parent=False)

    def _box(self, name, x0, x1, mat):
        bpy = self.bpy
        me = bpy.data.meshes.new(name)
        H = self.H / 2
        v = [(x0, -H, 0), (x1, -H, 0), (x1, H, 0), (x0, H, 0),
             (x0, -H, 1), (x1, -H, 1), (x1, H, 1), (x0, H, 1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(v, [], f)
        me.materials.append(mat)
        return self.link(bpy.data.objects.new(name, me))

    def _plane(self, name, x0, x1, mat, parent=True):
        bpy = self.bpy
        me = bpy.data.meshes.new(name)
        H = self.H / 2
        me.from_pydata([(x0, -H, 0), (x1, -H, 0), (x1, H, 0), (x0, H, 0)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new()
        for li, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
            uv.data[li].uv = (u, v)
        me.materials.append(mat)
        return self.link(bpy.data.objects.new(name, me), parent)

    def _stacks(self):
        edge = self.edge_material()
        W = self.W
        self.right_stack = self._box("right_stack", 0, W, edge)
        self.left_stack = self._box("left_stack", -W, 0, edge)
        mr, self.right_tex, _ = self.page_material("right_top", False)
        ml, self.left_tex, _ = self.page_material("left_top", False)
        self.right_top = self._plane("right_top", 0, W, mr)
        self.left_top = self._plane("left_top", -W, 0, ml)

    def _grid(self, name, nx, ny, mat):
        bpy, np = self.bpy, self.np
        me = bpy.data.meshes.new(name)
        verts = [(0.0, 0.0, 0.0)] * ((nx + 1) * (ny + 1))
        faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1,
                  (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new()
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                i, j = vi % (nx + 1), vi // (nx + 1)
                uv.data[li].uv = (i / nx, j / ny)
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
        me.materials.append(mat)
        return me

    def _pages(self):
        """Reusable page meshes for the leaves in the air."""
        bpy, np = self.bpy, self.np
        self.turners = []
        for k in range(AIR):
            mat, front, back = self.page_material(f"turn{k}", True, gloss=(k == 0))
            me = self._grid(f"page{k}", NX, NY, mat)
            ob = self.link(bpy.data.objects.new(f"page{k}", me))
            ob.hide_render = True
            self.turners.append((ob, front, back))
        self.ys = np.linspace(-self.H / 2, self.H / 2, NY + 1)

    def _staples(self):
        """Two staples down the gutter: saddle-stitched."""
        bpy, bs = self.bpy, self.bs
        m = bpy.data.materials.new("staple")
        b = bs.principled(m)
        b.inputs["Base Color"].default_value = (0.8, 0.8, 0.82, 1)
        b.inputs["Metallic"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.25
        self.staples = []
        for y in (-self.H / 4, self.H / 4):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.00035, depth=0.013, vertices=10,
                                                location=(0, y, 0))
            ob = bpy.context.object
            ob.rotation_euler = (math.radians(90), 0, 0)
            ob.data.materials.append(m)
            ob.parent = self.root
            self.staples.append(ob)

    def _fan(self):
        """The loose sheets for the fan."""
        bpy = self.bpy
        self.fan = []
        for k, sh in enumerate(self.plan["fan"]["sheets"]):
            mat, front, _ = self.page_material(f"sheet{k}", False)
            self.set_image(front, sh["page"])
            me = self._grid(f"sheet{k}", 20, 2, mat)
            ob = self.link(bpy.data.objects.new(f"sheet{k}", me), parent=False)
            ob.hide_render = True
            self.fan.append(ob)

    def _lights(self):
        bpy, Vector = self.bpy, self.Vector
        for name, loc, energy, size in (("key", (-0.6, -0.55, 1.15), KEY, 1.2),
                                        ("fill", (0.9, -0.3, 0.7), KEY * 0.22, 1.4),
                                        ("rim", (0.25, 0.95, 0.85), KEY * 0.2, 0.9)):
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
    def leaf_mesh(self, ob, u, lift):
        """Bend a page mesh for turn progress u; the lower corner leads (a diagonal curl)."""
        np = self.np
        co = np.zeros((NY + 1, NX + 1, 3))
        for j, y in enumerate(self.ys):
            lead = TWIST * math.sin(math.pi * u) * (0.5 - (y / self.H + 0.5))
            uj = min(1.0, max(0.0, u + lead))
            x, z = page_curve(uj, self.W, NX, CURL * (1 + 0.15 * (0.5 - y / self.H)))
            co[j, :, 0] = x
            co[j, :, 1] = y
            co[j, :, 2] = z + lift
        ob.data.vertices.foreach_set("co", co.reshape(-1))
        ob.data.update()

    def apply(self, f):
        np, Vector = self.np, self.Vector
        plan = self.plan
        flip, fan = plan["flip"], plan["fan"]
        in_flip = f < fan["start"]
        # --- the booklet
        for ob in (self.right_stack, self.left_stack, self.right_top, self.left_top,
                   *self.staples):
            ob.hide_render = not in_flip
        leaves = flip["leaves"]
        started = [lf for lf in leaves if lf["start"] <= f]
        finished = [lf for lf in leaves if lf["start"] + lf["dur"] <= f]
        flying = [lf for lf in started if lf not in finished]
        total = plan["leaves_total"]
        # how many leaves lie on each side: the spread reached by the last finished leaf
        spread = (finished[-1]["back"] // 2) if finished else 0
        left_n = min(total, max(0, spread))
        right_n = max(1, total - left_n)
        hl, hr = max(LEAF, left_n * LEAF), right_n * LEAF
        self.left_stack.scale = (1, 1, hl)
        self.right_stack.scale = (1, 1, hr)
        self.left_top.location.z = hl + 0.00004
        self.right_top.location.z = hr + 0.00004
        for st in self.staples:
            st.location.z = max(hl, hr) * 0.5 + 0.0004
            st.hide_render = not (in_flip and finished)
        nxt = leaves[len(started)]["front"] if len(started) < len(leaves) else leaves[-1].get("next", 0)
        self.set_image(self.right_tex, nxt)
        opened = bool(finished)
        self.left_stack.hide_render = not (in_flip and opened)
        self.left_top.hide_render = not (in_flip and opened)
        if opened:
            self.set_image(self.left_tex, finished[-1]["back"])
        for k, (ob, front, back) in enumerate(self.turners):
            if not in_flip or k >= len(flying):
                ob.hide_render = True
                continue
            lf = flying[k]
            u = min(1.0, max(0.0, (f - lf["start"]) / lf["dur"]))
            u = u * u * (3 - 2 * u)
            lift = (1 - u) * hr + u * (hl + LEAF) + 0.00015 * (k + 1)
            self.leaf_mesh(ob, u, lift)
            self.set_image(front, lf["front"])
            self.set_image(back, lf["back"])
            ob.hide_render = False
        # --- the fan
        W, H = self.W, self.H
        R = 0.36                                        # pivot below the fan
        for k, (ob, sh) in enumerate(zip(self.fan, fan["sheets"])):
            q = (f - sh["t0"]) / sh["dur"]
            if in_flip or q < 0:
                ob.hide_render = True
                continue
            ob.hide_render = False
            q = min(1.0, q)
            e = 1 - (1 - q) ** 3
            a_end = math.radians(sh["angle"])
            a0 = a_end + math.radians(55 + 12 * k)
            a = a0 + (a_end - a0) * e
            # the sheet's centre: on its arc round the pivot, arriving from the lower right
            cx, cy = R * math.sin(-a), -R + R * math.cos(a)
            sx, sy = 0.55 + 0.1 * k, -0.62
            px = sx + (cx - sx) * e
            py = sy + (cy - sy) * e
            pz = 0.13 * math.sin(math.pi * min(1.0, q * 1.15)) * (1 - e) + 0.00022 * (k + 1)
            # bend while it flies, flat when it lands
            nx_, ny_ = 20, 2
            s = np.linspace(-W / 2, W / 2, nx_ + 1)
            bend = 0.035 * (1 - e) * math.sin(math.pi * min(1.0, q * 1.3))
            zz = bend * (1 - (s / (W / 2)) ** 2)
            co = np.zeros((ny_ + 1, nx_ + 1, 3))
            for j, y in enumerate(np.linspace(-H / 2, H / 2, ny_ + 1)):
                co[j, :, 0] = s
                co[j, :, 1] = y
                co[j, :, 2] = zz
            ob.data.vertices.foreach_set("co", co.reshape(-1))
            ob.data.update()
            ob.location = (px, py, pz)
            ob.rotation_euler = (0.0, 0.0, a)
        # --- the camera
        self.camera_at(f)

    def camera_at(self, f):
        """Flip: from the closed cover the camera dollies across to the open spread, then
        pushes in slowly. Fan: a slow push-in on the fanned sheets."""
        Vector = self.Vector
        plan = self.plan
        fan = plan["fan"]
        rot = math.radians(BOOK_ROT)

        def world(x, y):
            return Vector((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot), 0))

        def ease(x):
            x = min(1.0, max(0.0, x))
            return x * x * (3 - 2 * x)
        W = self.W
        if f < fan["start"]:
            open_q = ease((f - HOLD) / (COVER_TURN + 6))
            push = ease((f - HOLD) / max(1.0, fan["start"] - HOLD))
            land = ease((f - (fan["start"] - 26)) / 20)        # close in on the final spread
            tgt = world(W * (0.5 - 0.46 * open_q + 0.12 * land), 0.0)
            tgt.z = 0.01
            dist = (0.64 + 0.32 * open_q - 0.1 * push - 0.2 * land) * (W / 0.297)
            az, el = math.radians(-6 + 4 * push), math.radians(56 + 4 * push)
        else:
            q = ease((f - fan["start"]) / max(1.0, plan["frames"] - fan["start"]))
            tgt = Vector((0.0, 0.0, 0.0))
            dist = (1.22 - 0.1 * q) * (W / 0.297)
            az, el = math.radians(-4 + 3 * q), math.radians(62 + 3 * q)
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        self.cam.location = tgt + d * dist
        self.cam.rotation_euler = (tgt - self.cam.location).to_track_quat("-Z", "Y").to_euler()

    def render(self, frames):
        bpy = self.bpy
        for f, path in frames:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                continue
            t = time.time()
            self.apply(float(f))
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
