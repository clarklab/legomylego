"""Case-insensitive index of an LDraw-style library tree, plus LDConfig colours."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

SUBDIRS = (("parts", ""), ("parts/s", "s/"), ("p", ""), ("p/48", "48/"), ("p/8", "8/"),
           ("models", ""))


def normalize(name: str) -> str:
    n = name.strip().strip('"').replace("\\", "/").lower()
    if not n.endswith((".dat", ".ldr", ".mpd")):
        n += ".dat"
    return n


def part_id(name: str) -> str:
    n = normalize(name)
    return n[:-4] if n.endswith(".dat") else n


class FileIndex:
    def __init__(self, root, extra_roots=()):
        self.root = Path(root)
        self.files: dict[str, Path] = {}
        self.extra: set[str] = set()        # names found only under an extra root
        for n, r in enumerate([self.root, *map(Path, extra_roots)]):
            for sub, prefix in SUBDIRS:
                d = r / sub
                if not d.is_dir():
                    continue
                for f in os.listdir(d):
                    fl = f.lower()
                    if fl.endswith((".dat", ".ldr")) and prefix + fl not in self.files:
                        self.files[prefix + fl] = d / f
                        if n:
                            self.extra.add(prefix + fl)

    def resolve(self, name: str) -> Path | None:
        return self.files.get(normalize(name))

    def __contains__(self, name: str) -> bool:
        return normalize(name) in self.files


@dataclass(frozen=True)
class LDrawColor:
    code: int
    name: str
    rgb: str
    edge: str
    alpha: int
    material: str

    @property
    def is_trans(self) -> bool:
        return self.alpha < 255


COLOUR_RE = re.compile(
    r"^0\s+!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+(#[0-9A-Fa-f]{6})\s+EDGE\s+(\S+)(.*)$")
MATERIALS = ("CHROME", "PEARLESCENT", "RUBBER", "MATTE_METALLIC", "METAL", "GLITTER", "SPECKLE")


def parse_ldconfig(path) -> dict[int, LDrawColor]:
    out: dict[int, LDrawColor] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = COLOUR_RE.match(line.strip())
        if not m:
            continue
        name, code, value, edge, rest = m.groups()
        alpha = re.search(r"ALPHA\s+(\d+)", rest)
        material = next((w.lower() for w in MATERIALS if w in rest), "")
        out[int(code)] = LDrawColor(int(code), name, value.upper(), edge,
                                    int(alpha.group(1)) if alpha else 255, material)
    return out


class LDrawLibrary(FileIndex):
    """The LDraw library, plus `extra_roots` laid out the same way (parts/, parts/s/) for
    brickkit's own stand-in parts: non-LEGO hardware such as a clock insert
    (brickkit/data/ldraw). The library's own files win on a name clash."""

    def __init__(self, root, extra_roots=()):
        super().__init__(root, extra_roots)
        self.colors = parse_ldconfig(self.root / "LDConfig.ldr")

    def is_custom(self, name: str) -> bool:
        """True for a part that comes from an extra root, not the LDraw library."""
        return normalize(name) in self.extra

    def description(self, name: str) -> str:
        p = self.resolve(name)
        if not p:
            return ""
        with open(p, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
        return first[1:].strip() if first.startswith("0") else first
