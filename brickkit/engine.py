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
        return ShadowLibrary(self.cache / "ldcad_shadow" / "LDCadShadowLibrary-main", self.lib)

    @cached_property
    def catalog(self):
        from .catalog.catalog import Catalog
        return Catalog.load(self.lib, self.cache / "rebrickable", self.cache / "rb_index.pkl")

    @cached_property
    def collide(self):
        from .geometry.collide import CollisionEngine
        return CollisionEngine(self.geom)

    def context(self, model, config: dict | None = None):
        from .checks.base import CheckContext
        return CheckContext(model, self, config or {})
