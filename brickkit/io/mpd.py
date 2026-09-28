"""LDraw MPD (multi-part) files with STEP metas; opens in BrickLink Studio, LeoCAD, LDCad."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..ldraw.library import normalize
from ..ldraw.matrix import format_type1, parse_type1
from ..model.builder import Model, Placement


def write_mpd(model: Model, path, lib=None) -> Path:
    """Write the model; with `lib` (an LDrawLibrary), brickkit's own stand-in parts (non-LEGO
    hardware, from its extra part roots) are embedded at the end so other LDraw programs can
    show them."""
    path = Path(path)
    lines: list[str] = []
    subs = [model.main] + [s for s in model.submodels.values() if s is not model.main]
    for sub in subs:
        fname = f"{sub.name}.ldr"
        lines += [f"0 FILE {fname}", f"0 {sub.title}", f"0 Name: {fname}",
                  "0 Author: brickkit", ""]
        for s in range(sub.n_steps):
            if sub.captions[s]:
                lines.append(f"0 // {sub.captions[s]}")
            for it in sub.items:
                if it.step != s:
                    continue
                if isinstance(it, Placement):
                    lines.append(format_type1(it.color.ldraw, it.M, it.part))
                else:
                    lines.append(format_type1(16, it.M, f"{it.sub.name}.ldr"))
            lines.append("0 STEP")
        lines += ["0 NOFILE", ""]
    if lib is not None:
        custom = sorted({it.part for sub in subs for it in sub.items
                         if isinstance(it, Placement) and lib.is_custom(it.part)})
        for part in custom:
            body = lib.resolve(part).read_text(encoding="utf-8").splitlines()
            lines += [f"0 FILE {part}"] + body + ["0 NOFILE", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def read_mpd(path) -> list[tuple[str, int, np.ndarray]]:
    """Flatten an MPD into (part, colour, world matrix), expanding internal files."""
    files: dict[str, list[str]] = {}
    order: list[str] = []
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        t = raw.split()
        if len(t) >= 3 and t[0] == "0" and t[1] == "FILE":
            current = normalize(" ".join(t[2:]))
            files[current] = []
            order.append(current)
        elif len(t) >= 2 and t[0] == "0" and t[1] == "NOFILE":
            current = None
        elif current is not None:
            files[current].append(raw)
    out: list[tuple[str, int, np.ndarray]] = []
    # embedded parts (an !LDRAW_ORG ...Part header) stay parts; other files are submodels
    parts = {k for k, body in files.items()
             if any(l.split()[:2] == ["0", "!LDRAW_ORG"] and "part" in l.lower() for l in body)}

    def walk(name: str, W: np.ndarray, color: int):
        for raw in files[name]:
            t = raw.split()
            if len(t) >= 15 and t[0] == "1":
                c, M, sub = parse_type1(t)
                c = color if c == 16 else c
                key = normalize(sub)
                if key in files and key not in parts:
                    walk(key, W @ M, c)
                else:
                    out.append((key, c, W @ M))

    walk(order[0], np.eye(4), 16)
    return out
