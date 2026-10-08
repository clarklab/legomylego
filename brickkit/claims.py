"""Who is working on which model, so that agents on different tools do not collide.

    brickkit claim SLUG --as NAME [--stage "1-3"] [--note "..."] [--take]
    brickkit release SLUG --as NAME [--force]

A claim is the file models/SLUG/CLAIM. It is made with an exclusive create, so of two agents
in the same checkout only one can get it. Agents in different clones share it through git:
commit and push the CLAIM file alone before starting, and a rejected push means someone else
was first (docs/new-model.md). Claiming again under the same name renews it. A claim nobody
has renewed for STALE_HOURS is stale and can be taken over with --take."""
from __future__ import annotations

import os
import socket
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from . import paths

STALE_HOURS = 24.0
NAME = "CLAIM"


class Claimed(Exception):
    """Someone else has it."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def read(slug: str, models_dir: Path | None = None) -> dict | None:
    """The claim on a model: {who, when, stage, host, note, hours (its age), stale}, or None."""
    f = (models_dir or paths.MODELS_DIR) / slug / NAME
    try:
        c = tomllib.loads(f.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None
    try:
        when = datetime.fromisoformat(str(c.get("when", "")).replace("Z", "+00:00"))
        c["hours"] = max(0.0, (_now() - when).total_seconds() / 3600.0)
    except ValueError:
        c["hours"] = 1e9
    c["stale"] = c["hours"] > STALE_HOURS
    return c


def _text(who: str, stage: str, note: str) -> str:
    q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'   # noqa: E731
    return (f"who = {q(who)}\nwhen = {q(_now().strftime('%Y-%m-%dT%H:%M:%SZ'))}\n"
            f"stage = {q(stage)}\nhost = {q(socket.gethostname())}\nnote = {q(note)}\n")


def claim(slug: str, who: str, stage: str = "", note: str = "", take: bool = False,
          models_dir: Path | None = None) -> dict:
    """Claim a model for `who`. Claimed (with the holder's claim) if someone else has it -
    unless theirs is stale and `take` is set."""
    d = (models_dir or paths.MODELS_DIR) / slug
    if not d.is_dir():
        raise FileNotFoundError(f"no model {slug}: brickkit new {slug} --quick --as {who}")
    f = d / NAME
    for _ in range(3):
        try:
            fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            held = read(slug, models_dir)
            if held is None or held.get("who") == who or (take and held["stale"]):
                try:                                   # renew ours, or take a stale one: the
                    f.unlink()                         # exclusive create decides who gets it
                except FileNotFoundError:
                    pass
                continue
            raise Claimed(held)
        with os.fdopen(fd, "w") as fh:
            fh.write(_text(who, stage, note))
        return read(slug, models_dir)
    raise Claimed(read(slug, models_dir) or {})


def release(slug: str, who: str, force: bool = False, models_dir: Path | None = None) -> bool:
    """Give a model back. False if there was no claim; Claimed if it is someone else's (and
    not `force`)."""
    held = read(slug, models_dir)
    if held is None:
        return False
    if held.get("who") != who and not force:
        raise Claimed(held)
    ((models_dir or paths.MODELS_DIR) / slug / NAME).unlink(missing_ok=True)
    return True


def label(c: dict | None) -> str:
    """A claim for a table: "name 3h", "name STALE 30h" or "-"."""
    if c is None:
        return "-"
    h = c["hours"]
    age = f"{h * 60:.0f}m" if h < 1 else f"{h:.0f}h"
    return f"{c.get('who', '?')} {'STALE ' if c['stale'] else ''}{age}"
