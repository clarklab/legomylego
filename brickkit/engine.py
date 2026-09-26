"""Lazily-built shared services (part library, caches, catalog) for one session."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path

from . import paths


class Engine:
    def __init__(self, cache: Path | None = None):
        self.cache = Path(cache) if cache else paths.CACHE

    @cached_property
    def lib(self):
        from .ldraw.library import LDrawLibrary
        return LDrawLibrary(self.cache / "ldraw")

    @cached_property
    def geom(self):
        from .ldraw.geometry import GeometryCache
        return GeometryCache(self.lib, self.cache / "geom")

    @cached_property
    def shadow(self):
        from .snaps.shadow import ShadowLibrary
        return ShadowLibrary(self.cache / "ldcad_shadow" / "LDCadShadowLibrary-main", self.lib,
                             overlays=[paths.DATA_DIR / "shadow"])

    @cached_property
    def catalog(self):
        from .catalog.catalog import Catalog
        return Catalog.load(self.lib, self.cache / "rebrickable", self.cache / "rb_index.pkl")

    @cached_property
    def collide(self):
        """Collision engine. Meshing gear teeth are allowed to touch (they are put into mesh
        with a slight turn, which a straight insertion sweep can't model); gear spacing is
        checked separately by the mechanism check."""
        from .geometry.collide import CollisionEngine
        return CollisionEngine(self.geom, skip_pair=self.gears_touch)

    def is_gear(self, part: str) -> bool:
        cache = self.__dict__.setdefault("_gear_cache", {})
        if part not in cache:
            name = self.catalog.part_name(part).lower()
            cache[part] = ("gear" in name or "worm" in name) and "technic" in name
        return cache[part]

    def gears_touch(self, pa: str, pb: str) -> bool:
        return self.is_gear(pa) and self.is_gear(pb)

    def context(self, model, config: dict | None = None):
        from .checks.base import CheckContext
        return CheckContext(model, self, config or {})
