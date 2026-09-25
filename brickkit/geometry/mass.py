"""Estimated part mass from mesh volume. 1 LDU = 0.4 mm."""
from __future__ import annotations

import numpy as np

from ..ldraw.geometry import Mesh

LDU3_TO_CM3 = 0.04 ** 3
DENSITY_ABS = 1.05   # g/cm^3, opaque parts
DENSITY_PC = 1.20    # g/cm^3, transparent parts (polycarbonate)


def part_mass(mesh: Mesh, is_trans: bool, override_g: float | None = None
              ) -> tuple[float, np.ndarray, bool]:
    """(grams, local centroid, approximate?)"""
    V, cen = mesh.volume_centroid()
    approx = (not mesh.certified) or V <= 0
    if approx:
        lo, hi = mesh.bbox
        V, cen = float(np.prod(hi - lo)) * 0.35, (lo + hi) / 2
    grams = V * LDU3_TO_CM3 * (DENSITY_PC if is_trans else DENSITY_ABS)
    return (override_g if override_g is not None else grams), np.asarray(cen, float), approx
