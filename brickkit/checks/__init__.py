"""Verification checks. Importing this package registers every built-in check."""
from . import buildability, collisions, connections, electrics, mechanism, real_elements  # noqa: F401
from . import stability, technique  # noqa: F401
from .base import REGISTRY, CheckContext, CheckResult, register, run_checks

__all__ = ["REGISTRY", "CheckContext", "CheckResult", "register", "run_checks"]
