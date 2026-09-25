"""Build video planning: segments, the 3D timeline, the reel plan and cue sheet (no Blender,
no browser)."""
import json
import math

import numpy as np
import pytest

from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.project import Project
from brickkit.video import reel as R
from brickkit.video import themes
from brickkit.video import timeline as T
from brickkit.video.booklet_flip import page_curve, schedule

BEAT = 15


@pytest.fixture(scope="module")
def sample(engine):
    return Project("_sample").build(engine.catalog)


def _rigged(engine):
    """The sample tower with a hinged roof, a lamp, a glowing part and a lift."""
    model = Project("_sample").build(engine.catalog)
    hinge = (0, -72, -20)

    def pose(t):
        R_ = transform((0, 0, 0), rot(x=-60 * t))
        return {"roof": translate(*hinge) @ R_ @ translate(*(-np.array(hinge)))}

    model.moving_group("roof", "roof")
    model.main.items[-1].tag = "roof"
    model.pose = pose
    model.light("lamp", "left", color="#FF0000", power=1.0)
    model.glow("right", 2.0)
    model.meta["video"] = {"lift": {"exclude_tag": "left", "height": 40}}
    return model


def _contiguous(segs, total=None):
    assert segs[0]["start"] == 0
    for a, b in zip(segs, segs[1:]):
        assert a["end"] == b["start"] and a["end"] > a["start"]
    if total is not None:
        assert segs[-1]["end"] == total


# ---------------------------------------------------------------------------- segments
def test_segments_follow_the_model(sample):
    segs = T.plan_segments(sample, booklet=False, beat=BEAT)
    assert [s["name"] for s in segs] == ["open", "title", "palette", "build", "scan", "outro"]
    _contiguous(segs)
    for s in segs:                                 # every cut on the beat
        assert s["start"] % BEAT == 0 and s["end"] % BEAT == 0
    kinds = {s["name"]: s["kind"] for s in segs}
    assert kinds["open"] == kinds["title"] == kinds["outro"] == "gfx" and kinds["build"] == "scene"


def test_segments_with_everything(engine):
    model = _rigged(engine)
    segs = T.plan_segments(model, booklet=True, beat=16, variants=["a", "b"])
    assert [s["name"] for s in segs] == list(T.ORDER)
    _contiguous(segs)
    cw = next(s for s in segs if s["name"] == "colourways")
    assert cw["beats"] == T.BEATS["colourway"] * 3
    # config: beats override, skipping a segment
    segs = T.plan_segments(model, booklet=True, beat=16, cfg={"beats": {"build": 20},
                                                              "skip": ["palette"]})
    names = [s["name"] for s in segs]
    assert "palette" not in names and "lift" not in names      # cfg replaces meta here
    assert next(s for s in segs if s["name"] == "build")["beats"] == 20
    seconds = sum(s["end"] - s["start"] for s in T.plan_segments(model, booklet=True, beat=BEAT,
                                                                variants=["a"])) / T.FPS
    assert 45 <= seconds <= 60                     # a showreel, not a feature


# ---------------------------------------------------------------------------- timeline
def test_sample_timeline(engine, sample):
    segs = T.plan_segments(sample, booklet=False, beat=BEAT)
    tl = T.build_timeline(engine, sample, segs, beat=BEAT)
    build = next(s for s in segs if s["name"] == "build")
    n = len(sample.flatten())
    appear = np.array(tl["build"]["appear"])
    assert len(appear) == n == len(tl["scene"]["instances"]) == tl["model"]["parts"]
    assert tl["model"]["pieces"] == 6
    assert sorted(tl["build"]["order"]) == list(range(n))
    land = appear + tl["build"]["drop"]
    assert (appear >= build["start"]).all() and (land <= build["end"]).all()
    # the last piece lands on a beat, two beats before the cut
    assert math.isclose(land.max(), tl["build"]["land_last"], abs_tol=1e-6)
    assert tl["build"]["land_last"] % BEAT == 0 and build["end"] - tl["build"]["land_last"] == 2 * BEAT
    # instruction order: a part never appears before one from an earlier step
    placed = sample.flatten()
    for i in range(n):
        for j in range(n):
            if placed[i].build_order < placed[j].build_order:
                assert appear[i] < appear[j]
    # sections cover the build, start on beats and in order
    secs = tl["build"]["sections"]
    assert secs[0]["start"] == build["start"] and secs[-1]["end"] == build["end"]
    assert sum(s["parts"] for s in secs) == n
    for a, b in zip(secs, secs[1:]):
        assert a["end"] == b["start"] and (b["start"] - build["start"]) % BEAT == 0
    # the steps shown never go backwards along the video order
    steps = np.array(tl["build"]["step"])[tl["build"]["order"]]
    assert (np.diff(steps) >= 0).all() and steps[-1] == len(sample.instruction_order())
    # per-frame camera for every scene frame; nothing moves; lights never on
    s0, s1 = tl["scene_range"]
    assert len(tl["camera"]["pos"]) == s1 - s0 == len(tl["lights"]["dim"])
    assert not tl["groups"]["frames"] and not tl["lift"]["frames"]
    assert max(tl["lights"]["led"]) == 0 and min(tl["lights"]["dim"]) == 1
    # the camera frames the finished model at the end of the build: all corners in view
    cam = tl["camera"]
    k = build["end"] - 1 - s0
    pts = T.corners(engine, placed).reshape(-1, 3)
    P = T.project(pts, cam["pos"][k], cam["target"][k], cam["lens"][k], 1080)
    assert (P[:, 0] > 0).all() and (P[:, 0] < 1080).all() and (P[:, 1] > 0).all() and (P[:, 1] < 1080).all()
    # the scan shot leaves room for the checks panel
    assert tl["shots"]["scan"]["layout"] in ("side", "bottom")


def test_mechanism_lights_lift_timeline(engine):
    model = _rigged(engine)
    segs = T.plan_segments(model, booklet=True, beat=BEAT)
    tl = T.build_timeline(engine, model, segs, beat=BEAT)
    seg = {s["name"]: s for s in segs}
    g = tl["groups"]
    assert g["names"] == ["roof"] and g["start"] == seg["mechanism"]["start"]
    frames = [np.array(row[0]).reshape(4, 4) for row in g["frames"]]
    assert len(frames) == seg["mechanism"]["end"] - seg["mechanism"]["start"]
    # rest (as built) -> open -> rest
    assert tl["mechanism"]["rest"] == pytest.approx(0.0, abs=1e-6)
    assert np.allclose(frames[0], np.eye(4)) and np.allclose(frames[-1], np.eye(4))
    assert any(np.allclose(M, model.pose(1.0)["roof"], atol=1e-6) for M in frames)
    assert tl["mechanism"]["angles"]["roof"] == pytest.approx(60.0, abs=0.5)
    # lights: dark first, then on (with a flicker) and held
    s0 = tl["scene_range"][0]
    on = tl["lights"]["power_on"]
    L = seg["lights"]
    assert L["start"] < on < L["end"]
    assert tl["lights"]["dim"][on - 1 - s0] < 0.1 and tl["lights"]["led"][on - 1 - s0] == 0
    assert tl["lights"]["led"][L["end"] - 1 - s0] == 1.0
    assert tl["lights"]["leds"][0]["instance"] in range(6)
    lifted = tl["lift"]["instance"]
    assert sum(lifted) == 4
    assert np.array(tl["lift"]["frames"][-1]).reshape(4, 4)[1, 3] < -20


def test_rest_parameter_and_curve():
    class M:
        @staticmethod
        def pose(t):                                # built at t = 0.25
            return {"g": transform((0, 0, 0), rot(y=80 * (t - 0.25)))}
    assert T.rest_parameter(M) == pytest.approx(0.25, abs=1e-4)
    u = T.mech_curve(120, 0.25)
    assert u[0] == pytest.approx(0.25) and u[-1] == pytest.approx(0.25)
    assert u.min() == pytest.approx(0.0, abs=1e-3) and u.max() == pytest.approx(1.0, abs=1e-3)

    class N:
        @staticmethod
        def pose(t):                                # never back where it was built
            return {"g": translate(10 + t, 0, 0)}
    assert T.rest_parameter(N) is None


def test_projection_matches_camera():
    pos, tgt, lens = np.array([0.0, -100.0, -500.0]), np.array([0.0, -100.0, 0.0]), 70.0
    c = T.project(np.array([tgt, tgt + [10, 0, 0], tgt + [0, -10, 0]]), pos, tgt, lens, 1080)
    assert np.allclose(c[0, :2], [540, 540])
    assert c[1, 0] > 540            # from the front (-Z) LDraw +X is to the right
    assert c[2, 1] < 540            # LDraw -Y is up
    # the focal length: 36 mm across the frame
    x = c[1, 0] - 540
    assert x == pytest.approx(10 / 500 * 70 / 36 * 1080, rel=1e-6)
    # fit puts every point inside the window
    pts = np.random.default_rng(1).uniform(-50, 50, (200, 3))
    for win in ((-1, 1, -1, 1), (-0.9, 0.1, -0.8, 0.8)):
        t, d = T.fit(pts, 30, 20, window=win, margin=1.0)
        dvec, _, _ = T.view_basis(30, 20)
        P = T.project(pts, t + dvec * d, t, T.LENS, 2.0)       # image of size 2: -1..1
        x, y = P[:, 0] - 1, 1 - P[:, 1]
        assert x.min() >= win[0] - 0.03 and x.max() <= win[1] + 0.03
        assert y.min() >= win[2] - 0.03 and y.max() <= win[3] + 0.03


def test_end_on_views_avoided():
    ferret = {"end_on": [0.0, 180.0]}
    assert abs(T.avoid_end_on(10, ferret)) >= 46 and abs(T.avoid_end_on(-170, ferret) + 180) >= 46
    assert T.avoid_end_on(70, ferret) == 70 and T.avoid_end_on(70, {"end_on": []}) == 70


def test_colourway_plan():
    seg = {"start": 300, "end": 300 + 12 * BEAT}
    cw = T.colourway_plan(seg, ["a", "b", "c"], BEAT)
    assert cw["frames"]["a"][0] == 300 and cw["frames"]["c"][1] == seg["end"]
    for w in cw["wipes"]:
        assert (w[0] - 300) % BEAT == 0 and w[1] - w[0] == T.WIPE_BEATS * BEAT
    # each colourway is rendered across its wipes, no more
    assert cw["frames"]["b"] == [cw["wipes"][0][0], cw["wipes"][1][1]]


def test_sections_from_captions(engine, sample):
    placed = sample.flatten()
    seq, step = T.build_order(sample, placed, {})
    auto = T.build_sections(sample, placed, seq, step, {})
    assert sum(len(s["parts"]) for s in auto) == len(placed) and len(auto) <= T.MAX_SECTIONS
    first_cap = sample.main.captions[0] or "x"
    conf = {"sections": [[1, "Start"], [first_cap[:3] if first_cap != "x" else 1, "Also start"],
                         ["no such caption", "Never"]]}
    secs = T.build_sections(sample, placed, seq, step, conf)
    assert all(s["title"] != "Never" for s in secs)


# ---------------------------------------------------------------------------- reel plan
def test_checks_rows(tmp_path):
    rep = {"status": "warn", "checks": [
        {"name": "real_elements", "status": "warn", "summary": "",
         "stats": {"combinations": 65, "not_real": 0, "rare": 1}},
        {"name": "connections", "status": "pass", "summary": "",
         "stats": {"connections": 4201, "by_kind": {"stud": 4057, "pin": 69, "axle": 75}}},
        {"name": "collisions", "status": "pass", "summary": "", "stats": {"pairs": 0}},
        {"name": "stability", "status": "pass", "summary": "",
         "stats": {"tip_angle_deg": 20.87, "mass_g": 1518.8}},
        {"name": "electrics", "status": "pass", "summary": "no electrics in this model", "stats": {}},
    ]}
    (tmp_path / "report.json").write_text(json.dumps(rep))
    c = R.checks(tmp_path)
    rows = {r["name"]: r for r in c["rows"]}
    assert rows["real_elements"]["big"] == "65" and "1 rare" in rows["real_elements"]["small"]
    assert rows["connections"]["big"] == "4,201" and rows["connections"]["small"].startswith("4,057 stud")
    assert rows["stability"]["big"] == "21°" and "1,519 g" in rows["stability"]["small"]
    assert rows["electrics"]["na"]
    assert c["summary"] == "4 passed · 1 warning"
    assert R.checks(tmp_path / "nowhere")["summary"] == "no report"


def test_reel_plan_and_cues(engine, sample, tmp_path):
    model = _rigged(engine)
    theme = themes.theme_for({"theme": "playful"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    tl = T.build_timeline(engine, model, segs, beat=theme["beat"])
    proj = Project("_sample")
    model.meta["video"]["callouts"] = [{"label": "Roof", "tag": "roof"},
                                       {"label": "Nothing", "tag": "missing_*"}]
    rp = R.plan_reel(engine, proj, model, tl, theme, tmp_path, tmp_path, log=lambda m: None)
    json.dumps(rp)                                   # all JSON-able
    assert rp["model"]["pieces"] == 6 and rp["model"]["url"].endswith("/m/_sample")
    assert sum(c["qty"] for c in rp["palette"]) == 6
    qty = [c["qty"] for c in rp["palette"]]
    assert qty == sorted(qty, reverse=True)
    # the wire file holds every edge
    n = rp["wire"]["count"]
    assert (tmp_path / "wire.bin").stat().st_size == n * 26
    # callouts: the roof is tracked through the mechanism shot; unmatched ones are dropped
    co = rp["mechanism"]["callouts"]
    assert [c["label"] for c in co] == ["Roof"]
    mech = next(s for s in segs if s["name"] == "mechanism")
    assert len(co[0]["anchors"][0]["track"]) == mech["end"] - mech["start"]
    assert co[0]["sub"] == "turns 60°"
    # every cut has a wipe; marks sit inside their segments
    cuts = {t["frame"] for t in rp["transitions"]}
    assert {s["start"] for s in segs[1:]} <= cuts
    seg = {s["name"]: s for s in segs}
    for name, m in rp["marks"].items():
        vals = [v for v in m.values() if isinstance(v, (int, float))]
        vals += [x for v in m.values() if isinstance(v, list) for x in v if isinstance(x, (int, float))]
        assert all(seg[name]["start"] <= v <= seg[name]["end"] for v in vals), name
    # the cue sheet: moods for every segment, events in order, brick clicks thinned
    cues = rp["cues"]
    assert [s["name"] for s in cues["sections"]] == [s["name"] for s in segs]
    assert cues["style"] == "playful" and cues["beat_frames"] == theme["beat"]
    fr = [e["frame"] for e in cues["events"]]
    assert fr == sorted(fr) and 0 <= fr[0] and fr[-1] <= tl["frames"]
    clicks = [e["frame"] for e in cues["events"] if e["type"] == "click"]
    assert clicks and min(np.diff(clicks), default=3) >= 3
    assert any(e["type"] == "power" for e in cues["events"])


def test_callout_instances(sample):
    placed = sample.flatten()
    placed[0].tags = ("leg_1",)
    placed[1].tags = ("leg_2",)
    inst = R._instances(placed, {"tag": "leg_*"})
    assert inst == [[0], [1]]
    part = placed[2].part.removesuffix(".dat")
    same = [p.index for p in placed if p.part.removesuffix(".dat") == part]
    assert R._instances(placed, {"part": part}) == [[i] for i in same]
    assert R._instances(placed, {"tag": "nope"}) == []


def test_themes():
    need = {"beat", "music", "bg", "ink", "accent", "accent2", "display", "mono", "transition",
            "title", "overlay", "xray", "grade"}
    for name in themes.THEMES:
        th = themes.theme_for({"theme": name})
        assert need <= set(th) and th["name"] == name
        assert 60 * T.FPS / th["beat"] > 90          # upbeat tempos
    assert themes.theme_for({"theme": "tape", "theme_overrides": {"accent": "#000000"}})["accent"] == "#000000"
    with pytest.raises(SystemExit):
        themes.theme_for({"theme": "nope"})


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


def test_callout_layout_stays_in_frame():
    def items(n, y):
        return [{"x": 200.0 + 60 * k, "y": y + (k % 2) * 10, "side": "left"} for k in range(n)]
    # a wide model: rows above and below, never more per row than fit
    out = items(5, 300) + items(1, 700)
    R.layout_callouts(out, [150, 250, 950, 750])
    assert all(c["align"] == "center" for c in out)
    for c in out:
        assert 64 + 150 - 1e-6 <= c["lx"] <= 1080 - 64 - 150 + 1e-6
    rows = {}
    for c in out:
        rows.setdefault(c["ly"], []).append(c["lx"])
    assert len(rows) == 2 and all(len(v) <= 3 for v in rows.values())
    for xs in rows.values():
        xs = sorted(xs)
        assert all(b - a >= 319 for a, b in zip(xs, xs[1:]))
    # a tall model: columns at the edges, labels clear of each other
    out = [{"x": 400.0, "y": 500.0 + k, "side": "left"} for k in range(4)] + \
          [{"x": 700.0, "y": 400.0, "side": "right"}]
    R.layout_callouts(out, [380, 100, 700, 1000])
    left = sorted(c["ly"] for c in out if c["align"] == "left")
    right = [c for c in out if c["align"] == "right"]
    assert (len(left), len(right)) == (3, 2)          # the columns are balanced
    assert all(b - a >= 100 - 1e-6 for a, b in zip(left, left[1:]))
    assert all(c["elbow"] is not None for c in out)


def test_part_label():
    assert R.part_label("Dish 2 x 2 Inverted [Radar]") == "Dish 2×2 inverted"
    assert R.part_label("Technic Gear 24 Tooth [New Style with Single Axle Hole]") == "Technic gear 24 tooth"
