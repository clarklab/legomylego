"""Download and unpack the part libraries into the cache (idempotent)."""
from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

from . import paths

LDRAW_URL = "https://library.ldraw.org/library/updates/complete.zip"
SHADOW_URL = "https://github.com/RolandMelkert/LDCadShadowLibrary/archive/refs/heads/master.zip"
REBRICKABLE_URL = "https://cdn.rebrickable.com/media/downloads/{}.csv.gz"
REBRICKABLE_TABLES = ("elements", "parts", "colors", "inventory_parts", "inventories", "sets",
                      "part_relationships", "part_categories")


def _download(url: str, dst: Path, log) -> Path:
    log(f"downloading {url}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh)
    tmp.replace(dst)
    return dst


def fetch(cache: Path | None = None, force: bool = False, log=print) -> None:
    cache = Path(cache) if cache else paths.CACHE
    cache.mkdir(parents=True, exist_ok=True)
    if force or not (cache / "ldraw" / "LDConfig.ldr").exists():
        z = _download(LDRAW_URL, cache / "ldraw_complete.zip", log)
        zipfile.ZipFile(z).extractall(cache)
    if force or not (cache / "ldcad_shadow" / "LDCadShadowLibrary-main").exists():
        z = _download(SHADOW_URL, cache / "ldcad_shadow.zip", log)
        zipfile.ZipFile(z).extractall(cache / "ldcad_shadow")
    for table in REBRICKABLE_TABLES:
        dst = cache / "rebrickable" / f"{table}.csv.gz"
        if force or not dst.exists():
            _download(REBRICKABLE_URL.format(table), dst, log)
    log(f"libraries ready in {cache}")
