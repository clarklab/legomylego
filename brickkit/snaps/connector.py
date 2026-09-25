"""A connection point. Cylinder sections run from the origin along the frame's -Y axis."""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np


@dataclass
class Connector:
    kind: str                  # cyl | clp | fgr | gen
    gender: str                # M | F (fgr: gender of first finger)
    M: np.ndarray              # 4x4 orthonormal frame
    secs: tuple = ()           # ((shape, radius, length), ...); shape in R A S _L L_
    caps: str = "one"
    center: bool = False
    slide: bool = False
    group: str = ""
    cid: str = ""
    radius: float = 0.0        # clp / fgr
    length: float = 0.0        # clp
    seq: tuple = ()            # fgr finger widths
    bounding: tuple = ()       # gen
    scale_rule: str = "none"
    mirror_rule: str = "none"

    @property
    def origin(self) -> np.ndarray:
        return self.M[:3, 3]

    @property
    def axis(self) -> np.ndarray:
        return -self.M[:3, 1]

    def total_length(self) -> float:
        if self.kind == "cyl":
            return float(sum(s[2] for s in self.secs))
        if self.kind == "clp":
            return self.length
        if self.kind == "fgr":
            return float(sum(self.seq))
        return 0.0

    def intervals(self) -> list[tuple[float, float, str, float]]:
        """(t0, t1, shape, radius) along `axis`, measured from `origin`."""
        L = self.total_length()
        t = -L / 2 if self.center else 0.0
        if self.kind == "cyl":
            out = []
            for shape, r, ln in self.secs:
                out.append((t, t + ln, shape, r))
                t += ln
            return out
        if self.kind == "clp":
            return [(t, t + L, "R", self.radius)]
        if self.kind == "fgr":
            return [(t, t + L, "F", self.radius)]
        return []

    def transformed(self, W: np.ndarray) -> "Connector":
        return replace(self, M=W @ self.M)
