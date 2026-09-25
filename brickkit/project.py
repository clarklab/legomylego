"""A model package: models/<slug>/model.toml + design.py (defining build(model))."""
from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

from . import paths
from .model.builder import Model


class Project:
    def __init__(self, slug: str, models_dir: Path | None = None):
        self.slug = slug
        self.dir = (models_dir or paths.MODELS_DIR) / slug
        if not (self.dir / "model.toml").exists():
            raise FileNotFoundError(f"no model.toml in {self.dir}")
        self.config = tomllib.loads((self.dir / "model.toml").read_text())

    @property
    def out(self) -> Path:
        d = self.dir / "out"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def checks_config(self) -> dict:
        return self.config.get("checks", {})

    def build(self, catalog) -> Model:
        cfg = self.config["model"]
        model = Model(cfg["name"], self.slug, self.config.get("palette", {}), catalog)
        model.meta = dict(cfg)
        design = self.dir / cfg.get("design", "design.py")
        spec = importlib.util.spec_from_file_location(f"brickkit_model_{self.slug}", design)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build(model)
        return model
