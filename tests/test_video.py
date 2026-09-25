"""Build-video timeline (no rendering)."""
import math

import numpy as np
import pytest

from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.project import Project
from brickkit.video import timeline as T
from brickkit.video.booklet_flip import page_curve, schedule


@pytest.fixture(scope="module")
def sample(engine):
    return Project("_sample").build(engine.catalog)


def _contiguous(tl):
    segs = tl["segments"]
    assert segs[0]["start"] == 0 and segs[-1]["end"] == tl["frames"]
    for a, b in zip(segs, segs[1:]):
        assert a["end"] == b["start"] and a["end"] > a["start"]


def test_sample_timeline(engine, sample):
    tl = T.build_timeline(engine, sample)
    names = [s["name"] for s in tl["segments"]]
    # no mechanism, lights, lift or booklet: those segments are skipped
    assert names == ["title", "build", "showcase", "end"]
    _contiguous(tl)
    assert 35 <= tl["frames"] / tl["fps"] <= 45
    build = next(s for s in tl["segments"] if s["name"] == "build")
    n = len(sample.flatten())
    appear = np.array(tl["build"]["appear"])
    assert len(appear) == n == len(tl["scene"]["instances"]) == tl["model"]["parts"]
    assert tl["model"]["pieces"] == 6          # the parts list: no extras, nothing left out
    # every part appears exactly once, and lands inside the build segment
    assert sorted(tl["build"]["order"]) == list(range(n))
    assert (appear >= build["start"]).all()
    assert (appear + tl["build"]["drop"] <= build["end"]).all()
    # in instruction order: a part never appears before one from an earlier step
    placed = sample.flatten()
    for i in range(n):
        for j in range(n):
            if placed[i].build_order < placed[j].build_order:
                assert appear[i] < appear[j]
    # default drop is from above (-Y), about a stud
    for off in tl["build"]["offset"]:
        assert off[1] < -15 and abs(off[0]) < 1e-9 and abs(off[2]) < 1e-9
    # per-frame camera for every scene frame; no poses, no lift, lights never on
    s0, s1 = tl["scene_range"]
    assert len(tl["camera"]["pos"]) == s1 - s0 == len(tl["lights"]["dim"])
    assert not tl["groups"]["frames"] and not tl["lift"]["frames"]
    assert max(tl["lights"]["led"]) == 0 and min(tl["lights"]["dim"]) == 1
    # the camera frames the finished model at the end of the build: all corners in view
    cam = tl["camera"]
    k = build["end"] - 1 - s0
    pos, tgt = np.array(cam["pos"][k]), np.array(cam["target"][k])
    f = (tgt - pos) / np.linalg.norm(tgt - pos)
    pts = T.corners(engine, placed).reshape(-1, 3)
    cosang = ((pts - pos) @ f) / np.linalg.norm(pts - pos, axis=1)
    assert (np.degrees(np.arccos(cosang)) < math.degrees(math.atan(18 / cam["lens"][k]))).all()


def test_mechanism_lights_lift_timeline(engine):
    model = Project("_sample").build(engine.catalog)
    hinge = (0, -72, -20)

    def pose(t):
        R = transform((0, 0, 0), rot(x=-60 * t))
        return {"roof": translate(*hinge) @ R @ translate(*(-np.array(hinge)))}

    model.moving_group("roof", "roof")
    model.main.items[-1].tag = "roof"
    model.pose = pose
    model.light("lamp", "left", color="#FF0000", power=1.0)
    model.glow("right", 2.0)
    model.meta["video"] = {"lift": {"exclude_tag": "left", "height": 40}}
    tl = T.build_timeline(engine, model, booklet=True)
    names = [s["name"] for s in tl["segments"]]
    assert names == ["title", "build", "showcase", "mechanism", "lights", "lift", "booklet", "end"]
    _contiguous(tl)
    assert 35 <= tl["frames"] / tl["fps"] <= 45
    seg = {s["name"]: s for s in tl["segments"]}
    # pose keyframes: one per mechanism frame, pose(0) -> pose(1) -> pose(0)
    g = tl["groups"]
    assert g["names"] == ["roof"] and g["start"] == seg["mechanism"]["start"]
    frames = [np.array(row[0]).reshape(4, 4) for row in g["frames"]]
    assert len(frames) == seg["mechanism"]["end"] - seg["mechanism"]["start"]
    assert np.allclose(frames[0], pose(0.0)["roof"]) and np.allclose(frames[-1], pose(0.0)["roof"])
    assert any(np.allclose(M, pose(1.0)["roof"], atol=1e-6) for M in frames)
    roof = [i for i, gi in enumerate(g["instance"]) if gi == 0]
    assert len(roof) == 1
    # lights: dim and LEDs on during the lights segment
    s0 = tl["scene_range"][0]
    k = seg["lights"]["end"] - 1 - s0
    assert tl["lights"]["dim"][k] < 0.5 and tl["lights"]["led"][k] > 0.99
    assert tl["lights"]["leds"] and tl["lights"]["leds"][0]["instance"] in range(6)
    # lift: the excluded parts stay, the rest rise
    lifted = tl["lift"]["instance"]
    assert sum(lifted) == 4
    top = np.array(tl["lift"]["frames"][-1]).reshape(4, 4)
    assert top[1, 3] < -20


def test_booklet_schedule():
    leaves = schedule(40, 150)
    assert leaves[0]["front"] == 1 and leaves[0]["back"] == 2
    for a, b in zip(leaves, leaves[1:]):
        assert b["start"] > a["start"] and b["front"] == a["back"] + 1
    assert leaves[-1]["start"] + 30 <= 150
    assert schedule(1, 150) == []
    x, z = page_curve(0.0, 1.0)
    assert np.allclose(z, 0) and np.isclose(x[-1], 1.0)
    x, z = page_curve(1.0, 1.0)
    assert np.allclose(z, 0, atol=1e-9) and np.isclose(x[-1], -1.0)
    x, z = page_curve(0.5, 1.0)
    assert z.max() > 0.5
