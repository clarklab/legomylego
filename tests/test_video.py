"""Build video planning: segments, the 3D timeline, the reel plan and cue sheet (no Blender,
no browser)."""
import json
import math
import re

import numpy as np
import pytest

from brickkit.ldraw.matrix import rot, transform, translate
from brickkit.project import Project
from brickkit.video import reel as R
from brickkit.video import themes
from brickkit.video import timeline as T
from brickkit.video.booklet_flip import BLUR, blur_frames, fan_plan, flip_schedule, page_curve, step_pages

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
    assert [s["name"] for s in segs] == ["open", "title", "build", "scan", "outro"]
    _contiguous(segs)
    for s in segs:                                 # every cut on the beat
        assert s["start"] % BEAT == 0 and s["end"] % BEAT == 0
    kinds = {s["name"]: s["kind"] for s in segs}
    assert kinds["open"] == kinds["title"] == kinds["outro"] == "gfx" and kinds["build"] == "scene"


def test_segments_with_everything(engine):
    model = _rigged(engine)
    segs = T.plan_segments(model, booklet=True, beat=16, variants=["a", "b"])
    assert [s["name"] for s in segs] == [n for n in T.ORDER                    # opt-in
                                         if n not in ("cold_open", "coda", "companions")]
    _contiguous(segs)
    cw = next(s for s in segs if s["name"] == "colourways")
    assert cw["beats"] == T.BEATS["colourway"] * 3
    # config: beats override, skipping a segment
    segs = T.plan_segments(model, booklet=True, beat=16, cfg={"beats": {"build": 20},
                                                              "skip": ["scan"]})
    names = [s["name"] for s in segs]
    assert "scan" not in names and "lift" not in names         # cfg replaces meta here
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
    # ground up: the first part stands on the table; every later part has something it
    # connects to already there, or nothing lower is left; each drops straight down
    placed = sample.flatten()
    C = T.corners(engine, placed)
    low = C[:, :, 1].max(1)
    order = tl["build"]["order"]
    assert low[order[0]] == low.max()
    nbrs = {i: set() for i in range(n)}
    for c in engine.context(sample).connections:
        nbrs[c.a].add(c.b)
        nbrs[c.b].add(c.a)
    for k, i in enumerate(order[1:], 1):
        before = set(order[:k])
        on_table = abs(low[i] - low.max()) < T.LAYER / 2
        assert on_table or nbrs[i] & before or all(low[j] <= low[i] + 1e-6 for j in order[k:])
    for off in tl["build"]["offset"]:
        assert off[0] == 0 and off[1] < -15 and off[2] == 0
    assert np.allclose(sorted(tl["build"]["top_mm"])[-1],
                       (C[:, :, 1].max() - C[:, :, 1].min()) * 0.4)
    # sections cover the build, start on beats and in order
    secs = tl["build"]["sections"]
    assert secs[0]["start"] == build["start"] and secs[-1]["end"] == build["end"]
    assert sum(s["parts"] for s in secs) == n
    for a, b in zip(secs, secs[1:]):
        assert a["end"] == b["start"] and (b["start"] - build["start"]) % BEAT == 0
    # instruction order is still there on request
    sample.meta["video"] = {"build_order": "instructions"}
    tl2 = T.build_timeline(engine, sample, segs, beat=BEAT)
    sample.meta.pop("video")
    ap2 = np.array(tl2["build"]["appear"])
    for i in range(n):
        for j in range(n):
            if placed[i].build_order < placed[j].build_order:
                assert ap2[i] < ap2[j]
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
    assert rp["model"]["pieces"] == 6 and rp["model"]["url"] == "bricks.superfun.games"
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
    from brickkit.video.compose import WEB
    assert (WEB / "fonts" / "InterVariable.woff2").exists()
    for name in themes.THEMES:
        th = themes.theme_for({"theme": name})
        assert need <= set(th) and th["name"] == name
        # every theme sets the site's type: Inter, monospace caps for the labels
        assert (th["display"], th["mono"], th["brand_mono"]) == ("Inter", "Menlo, monospace",
                                                                 "Menlo, monospace")
        assert 60 * T.FPS / th["beat"] > 90          # upbeat tempos
    assert themes.theme_for({"theme": "tape", "theme_overrides": {"accent": "#000000"}})["accent"] == "#000000"
    with pytest.raises(SystemExit):
        themes.theme_for({"theme": "nope"})


def test_grindhouse_theme():
    th = themes.theme_for({"theme": "grindhouse"})
    for name, other in themes.THEMES.items():
        assert set(other) <= set(th), name                  # every token the others have
        assert set(other["grade"]) <= set(th["grade"])
    assert (th["transition"], th["title"], th["callout"], th["overlay"], th["music"]) == (
        "burn", "stamp", "tag", "film", "grindhouse")
    assert th["display"] == themes.SITE_DISPLAY and th["mono"] == themes.SITE_MONO
    from brickkit.video import audio as A
    assert th["music"] in A.STYLES and th["music"] in A.PROG
    assert 90 < 60 * T.FPS / th["beat"] < 110                 # a slower, heavier pulse


def test_abyss_theme():
    """The deep-sea theme: every token the other themes have, the site's type, deep blues with
    brass and aqua, its own wipe, title, callouts, overlay and music, a slow pulse."""
    th = themes.theme_for({"theme": "abyss"})
    for name, other in themes.THEMES.items():
        assert set(other) <= set(th), name
        assert set(other["grade"]) <= set(th["grade"])
    assert (th["transition"], th["title"], th["callout"], th["overlay"], th["music"]) == (
        "porthole", "plaque", "porthole", "caustics", "abyss")
    assert th["display"] == themes.SITE_DISPLAY and th["mono"] == themes.SITE_MONO
    from brickkit.video import audio as A
    assert th["music"] in A.STYLES and th["music"] in A.PROG
    assert 95 < 60 * T.FPS / th["beat"] < 115                 # slow, but it still drives

    def rgb(h):
        return [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    for key in ("backdrop", "bg", "bg2"):                     # deep blue-green, dark
        r, g, b = rgb(th[key])
        assert b > r and g > r and (r + g + b) / 3 < 110, key
    r, g, b = rgb(th["accent"])                               # brass: warm
    assert r > g > b
    r, g, b = rgb(th["accent2"])                              # aqua: cool and bright
    assert g > r and b > r and g > 180


def test_the_page_knows_every_theme():
    """Each theme's wipe is one of the compositor's WIPES, its title style is drawn, its band,
    post look and brick palette exist (a typo there would fall back without a word)."""
    from brickkit.video.compose import WEB
    fx = (WEB / "fx.js").read_text()
    seg = (WEB / "segments.js").read_text()
    for name, th in themes.THEMES.items():
        tr = th["transition"]
        assert re.search(rf"^  {tr}\(f, p, t\) {{|^WIPES\.{tr} = function", fx, re.M), (name, tr)
        assert th["title"] == "slam" or f"=== '{th['title']}'" in seg, (name, th["title"])
        if name != "brand":
            assert f"t === '{name}'" in fx or f"TH.name === '{name}'" in fx, name


def test_trial_theme():
    """`brickkit video --theme`: another theme for one run, the model's overrides left out; over
    the model's rendered plates it keeps their tempo and backdrop."""
    cfg = {"theme": "playful", "theme_overrides": {"accent": "#000000"}}
    for name in (None, "playful"):
        c, th, trial = themes.trial_theme(cfg, name)
        assert not trial and c is cfg and th["accent"] == "#000000"
    c, th, trial = themes.trial_theme(cfg, "grindhouse")
    assert trial and c["theme"] == "grindhouse" and th["name"] == "grindhouse"
    assert th == dict(themes.theme_for({"theme": "grindhouse"}))
    _, kept, _ = themes.trial_theme(cfg, "grindhouse", keep_plates=True)
    own = themes.THEMES["playful"]
    assert (kept["beat"], kept["backdrop"]) == (own["beat"], own["backdrop"])
    assert kept["transition"] == "burn" and kept["accent"] == th["accent"]
    with pytest.raises(SystemExit):
        themes.trial_theme(cfg, "nope")


def test_grindhouse_cues(engine, tmp_path):
    """The grindhouse edit: burns on its cuts, the name stamped on the title's hero beat and the
    chainsaw after it, labels typed and results stamped instead of blips and chimes."""
    model = _rigged(engine)
    theme = themes.theme_for({"theme": "grindhouse"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    tl = T.build_timeline(engine, model, segs, beat=theme["beat"], backdrop=theme["backdrop"])
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    cues = rp["cues"]
    ev, hero = cues["events"], rp["marks"]["title"]["hero"]
    assert cues["style"] == "grindhouse" and cues["beat_frames"] == 18
    assert [e["frame"] for e in ev if e["type"] == "chainsaw"] == [hero + 3]
    assert any(e["type"] == "slap" and e["frame"] == hero for e in ev)
    burns = [t for t in rp["transitions"] if t["type"] == "burn"]
    assert burns
    for t in burns:
        assert any(e["type"] == "burn" and e["frame"] == t["frame"] - t["half"] for e in ev)
    types = {e["type"] for e in ev}
    assert "typewriter" in types and not types & {"blip", "pop", "type", "pass"}
    # the other themes keep their sound
    other = R.cue_sheet(rp, tl, themes.theme_for({"theme": "brand"}))
    assert not {e["type"] for e in other["events"]} & {"chainsaw", "burn", "typewriter"}


def test_abyss_edit(engine, tmp_path):
    """The abyss edit: a porthole over the cuts between segments (bricks into the build, the
    house studs into the outro), a sonar band between build sections, the abyss score on its
    own beat; the plan's sounds are the house ones (the score carries the theme)."""
    model = _rigged(engine)
    theme = themes.theme_for({"theme": "abyss"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    tl = T.build_timeline(engine, model, segs, beat=theme["beat"], backdrop=theme["backdrop"])
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    cues = rp["cues"]
    assert cues["style"] == "abyss" and cues["beat_frames"] == 17
    kinds = {t["to"]: t["type"] for t in rp["transitions"] if t["type"] != "band"}
    assert kinds.pop("build") == "bricks" and kinds.pop("outro") == "studs"
    assert set(kinds.values()) == {"porthole"}
    bands = [t for t in rp["transitions"] if t["type"] == "band"]
    assert len(bands) == len(tl["build"]["sections"]) - 1
    brand = R.cue_sheet(rp, tl, themes.theme_for({"theme": "brand"}))
    assert sorted(e["type"] for e in cues["events"]) == sorted(e["type"] for e in brand["events"])


# ---------------------------------------------------------------------------- cold open
def test_cold_open_segments(sample):
    """Opt-in: first, a whole number of beats (the performance, then a beat of black); without
    it the edit is unchanged."""
    plain = T.plan_segments(sample, booklet=False, beat=18, cfg={})
    cold = T.plan_segments(sample, booklet=False, beat=18,
                           cfg={"cold_open": {"scene": "sunset_road", "seconds": 7}})
    assert cold[0]["name"] == "cold_open" and cold[0]["kind"] == "cold"
    n = cold[0]["end"]
    assert n == (round(7 * T.FPS / 18) + T.COLD_BLACK_BEATS) * 18
    _contiguous(cold)
    assert [dict(s, start=s["start"] + n, end=s["end"] + n) for s in plain] == cold[1:]
    with pytest.raises(SystemExit):
        T.plan_segments(sample, booklet=False, cfg={"cold_open": {"scene": "moon"}})


def _cold_timeline(engine, performance=False):
    model = _rigged(engine)
    model.meta["video"] = {"cold_open": {"scene": "sunset_road", "seconds": 4, "spin_turns": 1.5,
                                         "hide_tags": ["left"]}}
    if performance:                         # a loop: the roof flaps twice per cycle
        from brickkit.ldraw.matrix import rot, transform

        def perf(u):
            h = np.array([0.0, -72.0, -20.0])
            R_ = transform((0, 0, 0), rot(x=-30 * (1 - math.cos(4 * math.pi * u))))
            return {"roof": translate(*h) @ R_ @ translate(*(-h))}
        model.meta["performance"] = perf
        model.meta["performance_info"] = {"ground_y": 0.0, "pivot": [5.0, -3.0], "cycle_s": 2.0}
    theme = themes.theme_for({"theme": "grindhouse"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    return model, theme, segs, T.build_timeline(engine, model, segs, beat=theme["beat"],
                                                backdrop=theme["backdrop"])


def test_cold_open_plan(engine):
    model, theme, segs, tl = _cold_timeline(engine)
    co, seg = tl["cold_open"], segs[0]
    m = co["cut"] - co["start"]
    assert co["cut"] == seg["end"] - T.COLD_BLACK_BEATS * theme["beat"]
    assert len(co["frames"]) == len(co["spin"]) == len(co["u"]) == len(co["rev"]) == m
    assert len(co["camera"]["pos"]) == m
    placed = model.flatten()
    assert co["hidden"] == [p.index for p in placed if "left" in p.tags] and co["hidden"]
    assert co["groups"]["names"] == ["roof"]
    assert all(co["groups"]["instance"][i] == -1 for i in co["hidden"])
    # without a performance the pose swings 0..1..0; it comes up to speed after the catch
    u = np.array(co["u"])
    assert u.min() >= 0 and u.max() <= 1 and u.max() > 0.9
    assert np.allclose(u[:int(T.COLD_START * T.FPS)], 0.0)
    # the spin: staggered, easing in and out, 1.5 turns about the pivot (which stays put)
    yaw = np.array(co["yaw"])
    assert yaw[0] == 0 and yaw[-1] == pytest.approx(540.0) and (np.diff(yaw) >= -1e-9).all()
    px, pz = co["pivot"]
    for M in co["spin"][::20]:
        M = np.array(M).reshape(4, 4)
        assert np.allclose(M @ [px, co["ground_y"], pz, 1.0], [px, co["ground_y"], pz, 1.0])
    # the engine idles until it catches; the revs follow the swing
    rev = np.array(co["rev"])
    catch = co["catch"] - co["start"]
    assert (rev[:catch] == 0).all() and 0 <= rev.min() and rev.max() <= 1 and rev.max() > 0.5
    # three shots, hard cuts: long lens wide, then closer and wider; the figure stays in frame
    assert [n for _, n in co["shots"]] == ["wide", "low", "close"]
    lens = [co["camera"]["lens"][f] for f, _ in co["shots"]]
    assert lens == sorted(lens, reverse=True) and lens[0] >= 200
    H = co["height"]
    for k in range(0, m, 7):
        c = co["camera"]
        feet, head = T.project(np.array([[px, co["ground_y"], pz], [px, co["ground_y"] - H, pz]]),
                               c["pos"][k], c["target"][k], c["lens"][k], 1080.0)
        assert 0 < feet[0] < 1080 and 1080 * co["letterbox"] < feet[1] < 1080 * (1 - co["letterbox"])
        assert head[1] > 0 and head[2] > 0
        assert c["pos"][k][1] > co["ground_y"] - 0.5 * H          # a low camera (LDraw -Y up)
    # the wide shot: the sun above the figure, the figure under it
    g = R.cold_open_graphics(tl)
    assert len(g["sun"]) == m
    x, y = g["sun"][0]
    head = T.project(np.array([[px, co["ground_y"] - H, pz]]), co["camera"]["pos"][0],
                     co["camera"]["target"][0], co["camera"]["lens"][0], 1080.0)[0]
    assert abs(x - 540) < 60 and y < head[1] and y > 1080 * co["letterbox"]
    json.dumps(co)


def test_cold_open_performance(engine):
    """meta["performance"] loops at its own speed (cycle_s), about performance_info's pivot."""
    model, theme, segs, tl = _cold_timeline(engine, performance=True)
    co = tl["cold_open"]
    assert co["pivot"] == [5.0, -3.0] and co["ground_y"] == 0.0
    u = np.array(co["u"])
    assert (np.diff(u) < -0.5).sum() >= 1                 # it wraps round: a loop, not a swing
    t = np.arange(len(u)) / T.FPS
    tp = np.cumsum(T.smootherstep((t - T.COLD_START) / T.COLD_RAMP)) / T.FPS
    assert np.allclose(u, (tp / 2.0) % 1.0, atol=1e-4)
    M = np.array(co["frames"][40][0]).reshape(4, 4)
    assert not np.allclose(M, np.eye(4))


def test_cold_open_look(engine):
    """[video.cold_open]'s look keys reach the set (and its plates' cache key); nothing else
    does, and without them the look is empty (the set's defaults)."""
    model, theme, segs, tl = _cold_timeline(engine)
    assert tl["cold_open"]["look"] == {}
    cfg = {"cold_open": {"scene": "sunset_road", "seconds": 4, "haze": 900.0,
                         "sky_tint": "#FF9050", "spin_turns": 1.0}}
    co = T.cold_open_config(model, cfg)
    placed = model.flatten()
    look = T.cold_open_plan(engine, model, placed, T.corners(engine, placed), segs[0], co,
                            T.FPS, theme["beat"])["look"]
    assert look == {"haze": 900.0, "sky_tint": "#FF9050"}
    assert set(T.COLD_LOOK) >= set(look)
    json.dumps(look)
    from brickkit.video import segment_digest
    q = {"size": 64, "samples": 1, "engine": "eevee", "device": "gpu"}
    tl2 = dict(tl, cold_open=dict(tl["cold_open"], look=look))
    assert segment_digest(tl2, segs[0], q) != segment_digest(tl, segs[0], q)


def test_cold_open_reel_and_cues(engine, tmp_path):
    model, theme, segs, tl = _cold_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    co = tl["cold_open"]
    # a straight cut out of the black into the reel; the reel's own marks move along
    assert all(t["from"] != "cold_open" for t in rp["transitions"])
    assert rp["marks"]["cold_open"]["cut"] == co["cut"]
    assert rp["marks"]["open"]["drop"] == segs[1]["start"] + theme["beat"] // 4
    cues = rp["cues"]
    assert cues["sections"][0] == {"name": "cold_open", "start": 0, "end": segs[0]["end"],
                                   "mood": "cold"}
    bed = [e for e in cues["events"] if e["type"] == "chainsaw_bed"]
    assert len(bed) == 1 and bed[0]["frame"] == 0 and bed[0]["dur"] == co["cut"]
    assert bed[0]["curve"] == co["rev"] and bed[0]["catch"] == co["catch"]
    assert any(e["type"] == "wind" and e["dur"] == co["cut"] for e in cues["events"])
    # nothing sounds in the black
    assert not [e for e in cues["events"] if co["cut"] <= e["frame"] < segs[0]["end"]]
    # its plates are keyed to the cold open and its set, not the studio's backdrop
    from brickkit.video import segment_digest
    q = {"size": 64, "samples": 1, "engine": "eevee", "device": "gpu"}
    d = segment_digest(tl, segs[0], q)
    tl2 = dict(tl, scene=dict(tl["scene"], backdrop="#000000", ground_color="#000000"))
    assert segment_digest(tl2, segs[0], q) == d
    tl3 = dict(tl, cold_open=dict(co, sun=dict(co["sun"], elevation=3.0)))
    assert segment_digest(tl3, segs[0], q) != d


def test_tap_program():
    """A tap lamp: presses clicking at the bottom of their travel on the taps' beats, the
    lights toggling there (on with a flash that settles, off within a few frames), a jolt."""
    taps, u, led, kick = T.tap_program(200, 30, 15)
    assert taps == [[30, "on"], [90, "off"], [120, "on"]]
    assert u[0] == 0 and u[20] == 0 and all(u[c] == 1.0 for c, _ in taps)
    assert u[40] < 0.2 and u.max() <= 1 and u.min() >= 0
    assert (led[:30] == 0).all() and led[30] > 1.5 and led[31] > 1.2
    assert led[60] == pytest.approx(1.0, abs=0.01) and (led[95:120] == 0).all()
    assert led[199] == pytest.approx(1.0, abs=0.01)
    assert kick[29] > 0 and kick[30] == 1.0 and kick[25] == 0 and kick[60] < 0.01
    taps, *_ = T.tap_program(100, 30, 15, taps=[0.5, 1.5, 9.0])    # seconds; past the end: out
    assert taps == [[15, "on"], [45, "off"]]


def _tap_timeline(engine, **cold):
    model = _rigged(engine)
    model.meta["video"] = {"cold_open": dict({"scene": "night_desk", "motion": "tap",
                                              "seconds": 5}, **cold)}
    theme = themes.theme_for({"theme": "scan"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    return model, theme, segs, T.build_timeline(engine, model, segs, beat=theme["beat"],
                                                backdrop=theme["backdrop"])


def test_cold_open_tap(engine):
    """motion "tap" in the night_desk set: the lamp stays put (no spin) and is pressed on the
    taps, its lights on/off/on, the room shot cut to the close one in the dark between the
    second and third taps, the camera punching in on each click; the plan says what the set and
    the compositor need (the taps, the lights' level, the LEDs, which way the model faces)."""
    model, theme, segs, tl = _tap_timeline(engine)
    co = tl["cold_open"]
    m = co["cut"] - co["start"]
    assert co["cut"] == segs[0]["end"] - T.COLD_BLACK_BEATS * theme["beat"]
    assert co["scene"] == "night_desk" and co["motion"] == "tap"
    assert [st for _, st in co["taps"]] == ["on", "off", "on"]
    assert all(co["start"] <= f < co["cut"] for f, _ in co["taps"])
    assert len(co["led"]) == len(co["u"]) == len(co["frames"]) == m
    assert co["leds"] and co["leds"][0]["color"] == "#FF0000" and co["hidden"] == []
    assert co["front"] == model.meta.get("azimuth_offset", 0.0)
    assert all(np.allclose(np.array(M).reshape(4, 4), np.eye(4)) for M in co["spin"])
    assert max(co["rev"]) == 0 and co["catch"] == co["start"]
    (c1, _), (c2, _), (c3, _) = [(f - co["start"], st) for f, st in co["taps"]]
    assert [n for _, n in co["shots"]] == ["room", "close"] and c2 < co["shots"][1][0] < c3
    assert max(co["u"]) == 1.0 and co["u"][c1] == 1.0 and co["u"][0] == 0.0
    lens = co["camera"]["lens"]
    assert lens[c1] > lens[c1 - 3] * 1.03 and lens[c1 + 20] == pytest.approx(lens[c1 - 3], rel=0.02)
    # the model in frame the whole time (its feet and head)
    px, pz = co["pivot"]
    H = co["height"]
    for k in range(0, m, 5):
        c = co["camera"]
        pts = T.project(np.array([[px, co["ground_y"], pz], [px, co["ground_y"] - H * 0.8, pz]]),
                        c["pos"][k], c["target"][k], c["lens"][k], 1080.0)
        assert (pts[:, 0] > 0).all() and (pts[:, 0] < 1080).all() and (pts[:, 2] > 0).all()
        assert 1080 * co["letterbox"] < pts[1, 1] < 1080 * (1 - co["letterbox"])
    json.dumps(co)
    # the taps from the config, in seconds; a performance cold open carries none of this
    _, _, _, tl2 = _tap_timeline(engine, taps=[0.5, 2.0, 2.5])
    assert [f - tl2["cold_open"]["start"] for f, _ in tl2["cold_open"]["taps"]] == [15, 60, 75]
    _, _, _, tl3 = _cold_timeline(engine)
    assert not {"taps", "led", "leds", "motion", "front", "glide"} & set(tl3["cold_open"])
    with pytest.raises(SystemExit):
        T.cold_open_config(model, {"cold_open": {"motion": "wiggle"}})


def test_cold_open_tap_reel_and_cues(engine, tmp_path):
    """The compositor gets the taps, the lights' level and where the lamp's head is (and no
    sun indoors); the sound: a click on every tap, a pop as it comes on and a softer one as it
    goes off, the night under it and a hum while it's lit, all stopped at the cut. Recorded
    sounds take the clicks, the pops and the night when the model has them."""
    from types import SimpleNamespace
    from brickkit.video import audio as A
    model, theme, segs, tl = _tap_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    co, g = tl["cold_open"], rp["cold_open"]
    assert g["taps"] == co["taps"] and g["led"] == co["led"] and g["scene"] == "night_desk"
    assert all(s is None for s in g["sun"]) and len(g["lamp"]) == len(g["sun"])
    assert all(0 < x < 1080 and 0 < y < 1080 for x, y in g["lamp"])
    cut = co["cut"]
    ev = [e for e in rp["cues"]["events"] if e["frame"] < segs[0]["end"]]
    kinds = [(e["frame"], e["type"]) for e in ev]
    on = [f for f, st in co["taps"] if st == "on"]
    off = [f for f, st in co["taps"] if st == "off"]
    assert all((f, "snap") in kinds for f, _ in co["taps"])
    assert all((f, "power") in kinds for f in on) and all((f, "power_off") in kinds for f in off)
    hum = [e for e in ev if e["type"] == "hum"]
    assert len(hum) == 1 and hum[0]["dur"] == cut - co["start"]
    assert max(hum[0]["curve"]) == 1.0 and hum[0]["curve"][0] == 0.0
    assert any(e["type"] == "wind" for e in ev)
    assert not {"chainsaw_bed", "chainsaw", "sample"} & {e["type"] for e in ev}
    assert not [e for e in ev if cut <= e["frame"] < segs[0]["end"] and e["type"] != "whoosh"]
    # recorded
    d = tmp_path / "audio"
    for k, n in enumerate(["c1.wav", "c2.wav", "on.wav", "off.wav", "night.wav"]):
        A.write_wav(d / n, np.full((4800, 2), 0.1 * (k + 1)), 48000)
    assets = R.audio_assets(SimpleNamespace(dir=tmp_path), {"audio": {
        "clicks": ["c1.wav", "c2.wav"], "snaps_on": "on.wav", "snaps_off": ["off.wav"],
        "room": "night.wav"}})
    assert assets["roles"]["snaps_on"] == ["on.wav"] and assets["roles"]["room"] == ["night.wav"]
    cues = R.cue_sheet(rp, tl, theme, assets)
    smp = [e for e in cues["events"] if e["type"] == "sample" and e["frame"] < cut]
    at = {(e["frame"], e["file"]) for e in smp}
    assert {(f, ["c1.wav", "c2.wav"][i % 2]) for i, (f, _) in enumerate(co["taps"])} <= at
    assert {(f, "on.wav") for f in on} <= at and {(f, "off.wav") for f in off} <= at
    night = [e for e in smp if e["file"] == "night.wav"]
    assert len(night) == 1 and night[0]["loop"] and night[0]["until"] == cut
    assert all(e["until"] == cut for e in smp)
    assert not {"snap", "power", "power_off", "wind"} & {e["type"] for e in cues["events"]
                                                         if e["frame"] < cut}
    assert cues["events"] != rp["cues"]["events"]


def _glide_timeline(engine, model=None, **cold):
    model = model or _rigged(engine)
    model.meta["video"] = {"cold_open": dict({"scene": "deep_sea", "seconds": 5}, **cold)}
    theme = themes.theme_for({"theme": "scan"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    return model, theme, segs, T.build_timeline(engine, model, segs, beat=theme["beat"],
                                                backdrop=theme["backdrop"])


def test_cold_open_glide(engine):
    """deep_sea's motion is a glide (unless told otherwise): the whole model carried forward
    along its long axis (GLIDE_LENGTHS of its length, through its centre at mid-performance),
    tilting a few degrees, its pose playing; a display stand hidden; three shots - approach,
    side, bow - all keeping it in front of the camera; its LEDs lit throughout."""
    model, theme, segs, tl = _glide_timeline(engine)
    co = tl["cold_open"]
    m = co["cut"] - co["start"]
    assert co["motion"] == "glide" and co["scene"] == "deep_sea" and "stand" in T.COLD_HIDE["deep_sea"]
    assert [n for _, n in co["shots"]] == ["approach", "side", "bow"]
    g = co["glide"]
    path = np.array(g["path"])
    F = np.array(g["forward"])
    assert len(path) == len(co["spin"]) == len(co["camera"]["focus"]) == m
    assert np.dot(path[-1] - path[0], F) == pytest.approx(T.GLIDE_LENGTHS * g["length"], rel=0.02)
    assert abs(np.dot(F, g["side"])) < 1e-6 and F[1] == 0
    centres = []                                    # the spin carries one point along the path
    for k in (0, m // 3, m // 2, m - 1):
        M = np.array(co["spin"][k]).reshape(4, 4)
        R_ = M[:3, :3]
        centres.append(np.linalg.solve(R_, path[k] - M[:3, 3]))
        assert np.degrees(np.arccos(np.clip((np.trace(R_) - 1) / 2, -1, 1))) < 8
    assert np.allclose(centres, centres[0], atol=1e-3 * g["length"])
    assert np.ptp(co["u"]) > 0.5                    # the pose plays
    assert co["leds"] and co["led"] == [1.0] * m and max(co["rev"]) == 0
    c = co["camera"]
    bow = co["shots"][2][0]
    for k in range(0, m, 4):                        # in frame (till its bow sweeps past)
        x, y, z = T.project(path[k][None], c["pos"][k], c["target"][k], c["lens"][k], 1080.0)[0]
        assert z > 0 and (k >= bow or (0 < x < 1080 and 0 < y < 1080))
        assert np.linalg.norm(np.array(c["pos"][k]) - path[k]) > g["extent"]["half"]
    json.dumps(co)
    # a stand is hidden; a motion given in the config wins
    model.main.items[0].tag = "stand"
    co2 = T.cold_open_config(model, {"cold_open": {"scene": "deep_sea", "motion": "pose"}})
    assert co2["motion"] == "pose" and "stand" in co2["hide_tags"]


def test_cold_open_glide_reel_and_cues(engine, tmp_path):
    """The compositor gets no sun underwater; the sound is the set's own recordings (shared,
    brickkit/data/audio/deep_sea) unless the model brings its own: the deep under it all, a
    ping at the start and after each cut, bubbles on the cuts and as the bow passes, a groan,
    the propeller churning louder as the stern nears; all stopped at the cut."""
    from types import SimpleNamespace
    model, theme, segs, tl = _glide_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    co, g = tl["cold_open"], rp["cold_open"]
    assert g["scene"] == "deep_sea" and all(s is None for s in g["sun"])
    cut = co["cut"]
    cues = rp["cues"]
    smp = [e for e in cues["events"] if e["type"] == "sample" and e["frame"] < segs[0]["end"]]
    files = {e["file"] for e in smp}
    assert set(cues["samples"]) >= files and all(
        "brickkit/data/audio/deep_sea" in cues["samples"][f]["path"] for f in files)
    roles = R.SCENE_SOUNDS["deep_sea"]
    amb = [e for e in smp if e["file"] == roles["ambience"]]
    assert len(amb) == 1 and amb[0]["loop"] and amb[0]["until"] == cut
    shots = [co["start"] + f for f, _ in co["shots"]]
    pings = sorted(e["frame"] for e in smp if e["file"] in roles["pings"])
    assert len(pings) == 3 and pings[0] < shots[1] and shots[1] < pings[1] < shots[2] < pings[2]
    assert {e["frame"] for e in smp if e["file"] in roles["bubbles"]} >= set(shots[1:])
    churn = [e for e in smp if e["file"] == roles["churn"]]
    assert len(churn) == 1 and len(churn[0]["gain_curve"]) == cut - co["start"]
    assert max(churn[0]["gain_curve"]) <= 1 and min(churn[0]["gain_curve"]) >= 0.25
    assert all(e["until"] == cut for e in smp)
    # a model's own sound for a role wins over the set's; no set, no sounds of its own: None
    from brickkit.video import audio as A
    A.write_wav(tmp_path / "audio" / "deep.wav", np.full((4800, 2), 0.1), 48000)
    own = R.audio_assets(SimpleNamespace(dir=tmp_path), {"audio": {"ambience": "deep.wav"}},
                         "deep_sea")
    assert own["roles"]["ambience"] == ["deep.wav"] and own["roles"]["pings"] == roles["pings"]
    assert R.audio_assets(SimpleNamespace(dir=tmp_path), {}, "sunset_road") is None
    assert R.audio_assets(SimpleNamespace(dir=tmp_path), {}) is None


# a flythrough of the sample tower: in at its back (-Z) through its left half, out at its front
FLY = {"enter": [-20, -38, -40], "exit": [-20, -38, 40], "path": [[-20, -40, 0]],
       "look": [[30, -40, 10]], "interior": {"bounds": [[-40, -52, -20], [40, -24, 20]],
                                             "tags": ["right"]}}


def _fly_timeline(engine, meta=FLY, **cold):
    model = _rigged(engine)
    if meta is not None:
        model.meta["flythrough"] = meta
    return _glide_timeline(engine, model=model, motion="flythrough", seconds=6, **cold)


def test_cold_open_flythrough(engine):
    """A flythrough (deep_sea): the model carried along as in a glide, the stand hidden; two
    shots outside, then one take that pushes in at its `enter`, through its room and out at its
    `exit` into the dark (murk) and away; the hull parts near the camera hidden while it passes
    (never the room's own, `interior.tags`); something huge waiting out there (lurk)."""
    model, theme, segs, tl = _fly_timeline(engine)
    co = tl["cold_open"]
    a, m = co["start"], co["cut"] - co["start"]
    fl = co["flythrough"]
    assert co["motion"] == "flythrough" and co["scene"] == "deep_sea"
    assert [n for _, n in co["shots"]] == ["under", "silhouette", "flythrough"]
    take = co["shots"][2][0]
    k_in, k_out = fl["enter"] - a, fl["exit"] - a
    assert fl["inside"] == [fl["enter"], fl["exit"]] and take < k_in < k_out < m
    c = co["camera"]
    length = co["glide"]["length"]

    def in_model(k):                                # the camera in the model's own frame
        M = np.array(co["spin"][k]).reshape(4, 4)
        return np.linalg.solve(M[:3, :3], np.array(c["pos"][k]) - M[:3, 3])
    assert np.linalg.norm(in_model(k_in) - FLY["enter"]) < 0.15 * length
    assert np.linalg.norm(in_model(k_out) - FLY["exit"]) < 0.15 * length
    lo, hi = np.array(FLY["interior"]["bounds"])
    for k in range(k_in + 3, k_out - 3):            # in the room between the crossings
        p = in_model(k)
        assert np.all(p[[0, 1]] > lo[[0, 1]] - 1) and np.all(p[[0, 1]] < hi[[0, 1]] + 1)
    for k in range(0, m, 3):                        # the camera looks ahead, never at itself
        assert np.linalg.norm(np.array(c["target"][k]) - c["pos"][k]) > 1.0
    # hidden near the camera: the left half it flies through, never the room's own (right)
    right = {p.index for p in model.flatten() if "right" in p.tags}
    hide = {int(k): v for k, v in fl["hide"].items()}
    assert hide and all(take <= k < m for k in hide)
    assert all(not right & set(v) for v in hide.values())
    assert any({1, 2} & set(v) for k, v in hide.items() if k_in - 15 <= k <= k_out + 15)
    assert set(fl["keep"]) >= right
    # in the room's lamplight between the crossings, then the dark after the far wall
    room, murk = np.array(fl["room"]), np.array(fl["murk"])
    assert len(room) == len(murk) == m
    assert room[(k_in + k_out) // 2] > 0.99 and room[0] == 0 and room[-1] < 0.01
    assert murk[k_in] == 0 and murk[-1] > 0.99 and np.all(np.diff(murk) >= -1e-9)
    assert fl["lurk"]["from"] == k_out and 0.5 * length < fl["lurk"]["size"] < 1.2 * length
    centre = np.array(co["glide"]["path"][-1])
    assert np.linalg.norm(np.array(fl["lurk"]["pos"]) - centre) > 0.8 * length
    json.dumps(co)


def test_cold_open_flythrough_config(engine):
    """The flythrough's points come from the model's meta, the cold open's config over it (in
    the model's frame, plus `origin`); without them it's an error."""
    model = _rigged(engine)
    model.meta["flythrough"] = dict(FLY, origin=[0, 10, 0])
    f = T.flythrough_config(model, {"flythrough": {"exit": [20, -38, 40], "slow": [2.0]}})
    assert np.allclose(f["enter"], [-20, -28, -40]) and np.allclose(f["exit"], [20, -28, 40])
    assert np.allclose(f["bounds"], [[-40, -42, -20], [40, -14, 20]]) and f["tags"] == {"right"}
    assert len(f["look"]) == len(f["path"]) == 1 and f["slow"][0] == 2.0
    with pytest.raises(SystemExit):
        _fly_timeline(engine, meta=None)


def test_cold_open_flythrough_cues(engine, tmp_path):
    """The flythrough's sound: the deep (hushed in the room), pings at the start, on the wide
    shot and once far off in the dark; bubbles through the hull going in and out; the organ
    from the wide shot to the cut, muffled outside and open in the room; the dread out in the
    dark with a moan in it."""
    model, theme, segs, tl = _fly_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    co = tl["cold_open"]
    a, cut = co["start"], co["cut"]
    fl = co["flythrough"]
    k_in, k_out = fl["enter"], fl["exit"]
    shots = [a + f for f, _ in co["shots"]]
    ev = [e for e in rp["cues"]["events"] if e["frame"] < cut]
    smp = [e for e in ev if e["type"] == "sample"]
    roles = R.SCENE_SOUNDS["deep_sea"]
    pings = sorted(e["frame"] for e in smp if e["file"] in roles["pings"])
    assert len(pings) == 3 and pings[0] < shots[1] < pings[1] < shots[2] and pings[2] > k_out
    bub = {e["frame"] for e in smp if e["file"] in roles["bubbles"]}
    assert bub >= {k_in - 4, k_out - 2}
    amb = [e for e in smp if e["file"] == roles["ambience"]][0]["gain_curve"]
    assert amb[(k_in + k_out) // 2 - a] < 0.5 * amb[0]
    assert all(e["until"] == cut for e in smp)
    organ = [e for e in ev if e["type"] == "organ"]
    assert len(organ) == 1
    o = organ[0]
    f0 = int(o["frame"])
    assert shots[1] <= f0 < k_in and len(o["curve"]) == len(o["muffle"]) == o["dur"] == cut - f0
    mu = np.array(o["muffle"])
    assert mu[0] > 0.99 and mu[(k_in + k_out) // 2 - f0] < 0.01 and mu[-1] > 0.99
    g = np.array(o["curve"])
    assert g[0] < 0.3 and g[(k_in + k_out) // 2 - f0] == pytest.approx(1.0, abs=0.01)
    assert o["offset"] == pytest.approx(R.FLY_ORGAN_IN - (k_in - f0) / tl["fps"])
    dread = [e for e in ev if e["type"] == "dread"]
    assert len(dread) == 1 and k_in < dread[0]["frame"] < k_out and dread[0]["call"] > 0
    assert dread[0]["frame"] + dread[0]["call"] > k_out and len(dread[0]["curve"]) == cut - dread[0]["frame"]


def test_flythrough_recorded_organ(engine, tmp_path):
    """[video.audio] organ: a recording plays in the synthesised organ's place, from the same
    frame and shaped the same (faint through the hull, open in the room: gain_curve and muffle),
    `organ_in` s of it reaching the window, stopped at the cut."""
    from types import SimpleNamespace

    from brickkit.video import audio as A
    model, theme, segs, tl = _fly_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    A.write_wav(tmp_path / "audio" / "organ.wav", np.full((48000 * 12, 2), 0.1), 48000)
    assets = R.audio_assets(SimpleNamespace(dir=tmp_path),
                            {"audio": {"organ": "organ.wav", "organ_in": 1.5}}, ["deep_sea"])
    assert assets["roles"]["organ"] == ["organ.wav"] and assets["organ_in"] == 1.5
    assert assets["roles"]["pings"] == R.SCENE_SOUNDS["deep_sea"]["pings"]   # the set's own
    cues = R.cue_sheet(rp, tl, theme, assets)
    co = tl["cold_open"]
    cut = co["cut"]
    synth = [e for e in rp["cues"]["events"] if e["type"] == "organ"][0]
    assert not [e for e in cues["events"] if e["type"] == "organ"]
    rec = [e for e in cues["events"] if e.get("file") == "organ.wav"]
    assert len(rec) == 1
    o = rec[0]
    assert o["frame"] == synth["frame"] and o["dur"] == synth["dur"] and o["until"] == cut
    assert o["gain_curve"] == synth["curve"] and o["muffle"] == synth["muffle"]
    k_in = co["flythrough"]["enter"]
    assert o["offset"] == pytest.approx(max(0.0, 1.5 - (k_in - o["frame"]) / tl["fps"]))
    assert o["level"] == R.SAMPLE_LEVEL["organ"]


def test_recorded_score(engine, tmp_path):
    """[video.audio] music: a recorded score instead of the synthesised music (every section
    cold, so the synth is silent), from the cut out of the cold open (`music_offset` s into
    it) into the coda for `music_tail` s, fading out there."""
    from types import SimpleNamespace

    from brickkit.video import audio as A
    model = _rigged(engine)
    model.meta["flythrough"] = FLY
    model.meta["video"] = {"cold_open": {"scene": "deep_sea", "motion": "flythrough", "seconds": 6},
                           "coda": {"seconds": 4}}
    theme = themes.theme_for({"theme": "abyss"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    tl = T.build_timeline(engine, model, segs, beat=theme["beat"], backdrop=theme["backdrop"])
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    assert "track" not in rp["cues"]
    A.write_wav(tmp_path / "audio" / "score.wav", np.full((48000 * 30, 2), 0.1), 48000)
    assets = R.audio_assets(SimpleNamespace(dir=tmp_path), {"audio": {
        "music": "score.wav", "music_offset": 0.5, "music_tail": 2.0}}, ["deep_sea"])
    cues = R.cue_sheet(rp, tl, theme, assets)
    seg = {s["name"]: s for s in segs}
    tr = cues["track"]
    assert tr["path"] == str(tmp_path / "audio" / "score.wav") and tr["offset"] == 0.5
    assert tr["at"] == seg["open"]["start"] == seg["cold_open"]["end"]
    assert tr["until"] == seg["coda"]["start"] + 2 * tl["fps"] and tr["fade_out"] == pytest.approx(1.6)
    assert all(s["mood"] == "cold" for s in cues["sections"])
    assert [e for e in cues["events"] if e["type"] == "organ"]       # the cold open's own sound
    assert {e["type"] for e in cues["events"]} == {e["type"] for e in rp["cues"]["events"]}


# ---------------------------------------------------------------------------- companions
SAMPLE_COMPANION = {"slug": "_sample", "eyebrow": "Kids' build", "heading": "The mini tower",
                    "price": {"pick_a_brick": 9.87}, "video": True}


def test_companions_config(sample):
    """[[companions]] with video = true are the video's companions (configure), unless [video]
    says companions = false; a companion segment of COMPANION_BEATS beats each goes after the
    booklet and before the outro."""
    from types import SimpleNamespace
    proj = SimpleNamespace(config={"companions": [dict(SAMPLE_COMPANION), {"slug": "other"}],
                                   "video": {}})
    cfg = R.configure(proj, sample)
    assert [c["slug"] for c in cfg["companions"]] == ["_sample"]
    off = R.configure(SimpleNamespace(config=dict(proj.config, video={"companions": False})), sample)
    assert off["companions"] is False
    sample.meta.pop("_video_toml", None)
    segs = T.plan_segments(sample, booklet=True, beat=BEAT, cfg=cfg)
    names = [s["name"] for s in segs]
    assert names[-3:] == ["booklet", "companions", "outro"]
    c = segs[-2]
    assert c["kind"] == "gfx" and c["beats"] == T.BEATS["companion"] == 10
    _contiguous(segs)
    two = T.plan_segments(sample, booklet=False, beat=BEAT,
                          cfg=dict(cfg, companions=[SAMPLE_COMPANION] * 2))
    assert next(s for s in two if s["name"] == "companions")["beats"] == 20
    assert "companions" not in [s["name"] for s in T.plan_segments(
        sample, booklet=False, beat=BEAT, cfg=dict(cfg, companions=False))]


def test_companion_reel_and_cues(engine, tmp_path):
    """The companion segment in the reel: the companion's heading, chips (its pieces, steps and
    about what it costs on Pick a Brick), the scale beat's heights (the model's and its own,
    labelled), marks inside the segment in order, and its sounds (whoosh, pop, blips, a snap
    as it lands) on them; the music grooves under it."""
    from brickkit.video import companions as Cmp
    model = _rigged(engine)
    model.meta["video"] = {"companions": [SAMPLE_COMPANION]}
    theme = themes.theme_for({"theme": "brand"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    tl = T.build_timeline(engine, model, segs, beat=theme["beat"], backdrop=theme["backdrop"])
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    seg = next(s for s in segs if s["name"] == "companions")
    (c,) = rp["companions"]
    sample = Project("_sample").build(engine.catalog)
    pieces = sum(line.qty for line in __import__("brickkit.bom.bom", fromlist=["x"]).build_bom(
        sample.flatten(), engine.catalog, getattr(sample, "extras", ())))
    assert c["heading"] == "The mini tower" and c["eyebrow"] == "Kids' build"
    assert c["chips"] == [{"value": f"{pieces:,}", "label": "pieces"},
                          {"value": f"{len(sample.instruction_order())}", "label": "steps"},
                          {"value": "~$10", "label": "Pick a Brick"}]
    sc = c["scale"]
    assert sc["big_mm"] == rp["model"]["dims_mm"][2] and 0 < sc["small_mm"]
    assert sc["big"] == Cmp.size_label(sc["big_mm"]) and sc["small"].endswith(("cm", "mm"))
    m = rp["marks"]["companions"]["items"][0]
    assert m["start"] == seg["start"] and m["end"] == seg["end"]
    order = [m["head"], m["card"], *m["chips"], m["scale"], m["drop"], m["measure"]]
    assert order == sorted(order) and seg["start"] < order[0] and order[-1] + 15 < seg["end"]
    ev = [e for e in rp["cues"]["events"] if seg["start"] <= e["frame"] < seg["end"]]
    assert {"pop", "blip", "snap", "tick"} <= {e["type"] for e in ev}
    assert any(e["type"] == "snap" and e["frame"] == m["drop"] + 6 for e in ev)
    assert {"name": "companions", "start": seg["start"], "end": seg["end"],
            "mood": "groove"} in rp["cues"]["sections"]
    assert [t for t in rp["transitions"] if t["from"] == "companions"][0]["to"] == "outro"


def test_companion_footage_helpers(tmp_path):
    """A cut-out's solid box (not its shadow); its clean copy (the shadow catcher's faint veil
    and the picture's edges gone, the model kept); the labels; a turntable loop as frames at
    the video's rate (made again only when it changes)."""
    import shutil
    import subprocess

    from PIL import Image

    from brickkit.video import companions as Cmp
    from brickkit.video.sizzle import turntable_frames
    a = np.zeros((100, 100, 4), np.uint8)
    a[:, :, 3] = 6                                    # the veil over the whole picture
    a[60:90, 10:90, 3] = 40                           # the shadow
    a[20:80, 30:70] = (200, 30, 30, 255)              # the model
    Image.fromarray(a, "RGBA").save(tmp_path / "cut.png")
    assert Cmp.solid_box(tmp_path / "cut.png") == [0.3, 0.2, 0.7, 0.8]
    b = np.asarray(Image.open(Cmp.clean_cutout(tmp_path / "cut.png", tmp_path / "clean.png")))
    assert b[5, 5, 3] == 0 and b[50, 50, 3] == 255 and 0 < b[85, 50, 3] < 40
    assert Cmp.size_label(654.2) == "65 cm" and Cmp.size_label(64.0) == "6.4 cm"
    assert Cmp.size_label(104) == "10 cm" and Cmp.size_label(8) == "8 mm"
    assert Cmp.price_label(9.87) == "$10" and Cmp.price_label(4.5) == "$4.50"
    if not shutil.which("ffmpeg"):
        return
    tt = tmp_path / "tt.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc=size=64x64:rate=24:duration=1", "-pix_fmt", "yuv420p", str(tt)],
                   check=True)
    d = tmp_path / "frames"
    assert turntable_frames(tt, d, 32) == 30           # 24 fps -> 30
    assert Image.open(d / "00000.jpg").size == (32, 32)
    stamp = (d / ".source").read_text()
    assert turntable_frames(tt, d, 32) == 30 and (d / ".source").read_text() == stamp


# ---------------------------------------------------------------------------- the coda
def _coda_timeline(engine, **coda):
    model = _rigged(engine)
    model.meta["video"] = {"coda": dict({"seconds": 4}, **coda)}
    theme = themes.theme_for({"theme": "abyss"})
    segs = T.plan_segments(model, booklet=False, beat=theme["beat"])
    return model, theme, segs, T.build_timeline(engine, model, segs, beat=theme["beat"],
                                                backdrop=theme["backdrop"])


def test_coda(engine):
    """[video.coda]: the last segment, after the outro, in a set of its own like a cold open
    (kind "cold") but with no black cut: the model cruising slowly (a stand hidden), one shot
    from off its side; the squid about the model's size, coming out of the murk beyond it, low
    on the right, and closing on it - both in frame at the end, its arms pointing at the model,
    its tentacles reaching out, its edges and eyes lighting up; the sea dark (murk); the last
    `fade` s fade to black (the compositor's). model = false hides the model; an unknown scene
    or creature is an error."""
    model, theme, segs, tl = _coda_timeline(engine)
    assert [s["name"] for s in segs][-2:] == ["outro", "coda"]
    s = segs[-1]
    assert s["kind"] == "cold" and s["beats"] == round(4 * 30 / theme["beat"])
    _contiguous(segs)
    co = tl["coda"]
    m = s["end"] - s["start"]
    assert co["start"] == s["start"] and co["cut"] == co["end"] == s["end"]
    assert co["scene"] == "deep_sea" and co["shots"] == [[0, "coda"]] and co["motion"] == "glide"
    g = co["glide"]
    path, F = np.array(g["path"]), np.array(g["forward"])
    assert len(path) == len(co["spin"]) == len(co["camera"]["pos"]) == len(co["camera"]["focus"]) == m
    assert np.dot(path[-1] - path[0], F) == pytest.approx(T.CODA["glide_lengths"] * g["length"],
                                                          rel=0.02)
    sq = co["coda"]["squid"]
    assert co["coda"]["creature"] == "squid"
    assert sq["size"] == pytest.approx(T.CODA["size"] * g["length"])
    assert all(len(sq[k]) == m for k in ("pos", "axis", "back", "reach", "rim", "glint"))
    c = co["camera"]

    def screen(p, k):
        return T.project(np.asarray(p, float)[None], c["pos"][k], c["target"][k], c["lens"][k], 1.0)[0]
    L_ = g["length"]
    ends = [path[-1] + F * g["extent"]["ahead"], path[-1] - F * g["extent"]["behind"]]
    for p in ends:                                   # the whole model in frame, at the end
        x, y, _ = screen(p, m - 1)
        assert 0.05 < x < 0.95 and 0.2 < y < 0.8
    x, y, z = screen(path[-1], m - 1)
    h0, h1 = screen(sq["pos"][0], 0), screen(sq["pos"][-1], m - 1)
    assert h0[0] > 0.9 and h0[2] > z                         # out of the murk beyond it...
    assert 0.5 < h1[0] < 0.8 and y < h1[1] < 0.75            # ...closing on it, low and right
    assert abs(h1[2] - z) < 0.3 * L_                          # at about its distance: its size
    assert 3.5 * sq["size"] == pytest.approx(T.CODA["size"] * 3.5 * L_) and \
        0.7 * L_ < 3.5 * sq["size"] < 1.4 * L_               # mantle to tentacle tips ~ the model
    assert co["coda"]["fade"] == round(T.CODA["fade"] * 30) < m / 2
    aim = path[-1] - np.array(sq["pos"][-1])
    assert np.dot(aim / np.linalg.norm(aim), sq["axis"][-1]) > 0.7     # its arms at the model
    assert abs(np.dot(sq["axis"][-1], sq["back"][-1])) < 1e-3
    reach, rim, glint = (np.array(sq[k]) for k in ("reach", "rim", "glint"))
    assert reach[0] < 0.2 and reach[-1] > 0.99 and np.all(np.diff(reach) >= -1e-9)
    assert rim[0] == 0 and rim[-1] == pytest.approx(1.0) and glint[0] == 0 and glint.max() > 0.5
    murk = np.array(co["coda"]["murk"])
    assert len(murk) == m and np.allclose(murk, T.CODA["murk"])
    assert co["leds"] and not co["hidden"]
    json.dumps(co)
    _, _, _, tl2 = _coda_timeline(engine, model=False)
    assert len(tl2["coda"]["hidden"]) == len(model.flatten()) and tl2["coda"]["leds"] == []
    for bad in ({"creature": "kraken"}, {"scene": "sunset_road"}):
        with pytest.raises(SystemExit):
            T.coda_config(model, {"coda": bad})
    assert T.coda_config(model, {}) is None
    assert T.coda_config(model, {"coda": True})["creature"] == "squid"


def test_coda_reel_and_cues(engine, tmp_path):
    """The coda in the reel: its frames and letterbox for the compositor, the theme's wipe into
    it from the outro, no music under it (mood cold); its sound the deep_sea set's: the deep, a
    ping and a fainter one later, the dread swelling, the creature moaning as its eye catches
    the light (its loudest on that frame), everything faded away by the last frame."""
    model, theme, segs, tl = _coda_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    s = segs[-1]
    assert rp["coda"] == {"start": s["start"], "end": s["end"], "letterbox": tl["coda"]["letterbox"],
                          "scene": "deep_sea", "creature": "squid", "fade": tl["coda"]["coda"]["fade"]}
    cues = rp["cues"]
    assert cues["sections"][-1] == {"name": "coda", "start": s["start"], "end": s["end"],
                                    "mood": "cold"}
    wipe = [t for t in rp["transitions"] if t["to"] == "coda"]
    assert len(wipe) == 1 and wipe[0]["type"] == theme["transition"] == "porthole"
    assert wipe[0]["frame"] == s["start"] and wipe[0]["from"] == "outro"
    ev = [e for e in cues["events"] if e["frame"] >= s["start"]]
    roles = R.SCENE_SOUNDS["deep_sea"]
    smp = [e for e in ev if e["type"] == "sample"]
    assert smp and all(e["until"] == s["end"] for e in smp)
    assert all(e["gain_curve"][-1] < 0.05 for e in smp)          # faded away by the end
    fade0 = s["end"] - tl["coda"]["coda"]["fade"]                 # with the picture
    amb = [e for e in smp if e["file"] == R.SCENE_SOUNDS["deep_sea"]["ambience"]][0]["gain_curve"]
    assert amb[fade0 - s["start"] - 2] > 0.95 > amb[fade0 - s["start"] + 10]
    glint = rp["marks"]["coda"]["glint"]
    assert glint == s["start"] + R.coda_glint(tl["coda"]) and s["start"] < glint < s["end"]
    moan = [e for e in smp if e["file"] == roles["creature"]]
    assert len(moan) == 1 and moan[0]["frame"] == glint and moan[0]["align"] == "peak"
    assert len([e for e in smp if e["file"] in roles["pings"]]) == 2
    assert len([e for e in smp if e["file"] == roles["ambience"]]) == 1
    dread = [e for e in ev if e["type"] == "dread"]
    assert len(dread) == 1 and dread[0]["dur"] == s["end"] - s["start"]
    assert dread[0]["curve"][-1] < 0.05 and "call" not in dread[0]   # the recorded moan instead
    assert set(cues["samples"]) >= {e["file"] for e in smp}



def test_outro_small_print(engine, sample, tmp_path):
    """[video] outro_small_print = false: the outro without its small print (the disclaimer and
    the model's notice; the compositor checks reel["outro"]); on by default. The model's own
    notice stays in the plan (the sizzle reel reads it)."""
    theme = themes.theme_for({"theme": "brand"})
    for cfg, want in (({}, True), ({"outro_small_print": False}, False)):
        sample.meta["video"] = dict(cfg)
        segs = T.plan_segments(sample, booklet=False, beat=theme["beat"])
        tl = T.build_timeline(engine, sample, segs, beat=theme["beat"], backdrop=theme["backdrop"])
        rp = R.plan_reel(engine, Project("_sample"), sample, tl, theme, tmp_path, tmp_path,
                         log=lambda m: None)
        assert rp["outro"] == {"small_print": want}
        assert rp["model"]["disclaimer"] == R.DISCLAIMER
    sample.meta.pop("video", None)

# ---------------------------------------------------------------------------- recorded sounds
def test_rev_peaks():
    c = np.zeros(300)
    for at, h in ((40, 0.9), (60, 1.0), (150, 0.7), (200, 0.5), (260, 0.95)):
        c[at - 5:at + 6] = h * np.hanning(11)
    assert R.rev_peaks(c, 30.0) == [60, 150, 260]        # 40 is too close to 60, 200 too low
    assert R.rev_peaks(c, 30.0, after=100) == [150, 260]


def _assets(tmp_path):
    from types import SimpleNamespace
    from brickkit.video import audio as A
    d = tmp_path / "audio"
    names = ["pull.wav", "idle.wav", "s1.wav", "s2.wav", "burst.wav", "st1.wav", "st2.wav",
             "hit.wav", "boom.wav"]
    for k, n in enumerate(names):
        A.write_wav(d / n, np.full((4800, 2), 0.1 * (k + 1) / len(names)), 48000)
    cfg = {"audio": {"pull_start": "pull.wav", "catch": 0.5, "idle": "idle.wav",
                     "screams": ["s1.wav", "s2.wav"], "burst": "burst.wav",
                     "stings": ["st1.wav", "st2.wav"], "hits": ["hit.wav"], "booms": ["boom.wav"],
                     "levels": {"boom": -3.0}}}
    return R.audio_assets(SimpleNamespace(dir=tmp_path), cfg), cfg


def test_audio_assets(tmp_path):
    from types import SimpleNamespace
    assets, cfg = _assets(tmp_path)
    assert set(assets["samples"]) == {"pull.wav", "idle.wav", "s1.wav", "s2.wav", "burst.wav",
                                      "st1.wav", "st2.wav", "hit.wav", "boom.wav"}
    assert all(len(v["sha1"]) == 40 for v in assets["samples"].values())
    assert assets["roles"]["screams"] == ["s1.wav", "s2.wav"] and assets["catch"] == 0.5
    assert assets["levels"]["boom"] == -3.0 and assets["levels"]["scream"] == R.SAMPLE_LEVEL["scream"]
    assert R.audio_assets(SimpleNamespace(dir=tmp_path), {}) is None
    bad = {"audio": dict(cfg["audio"], idle="nope.wav")}
    with pytest.raises(SystemExit):
        R.audio_assets(SimpleNamespace(dir=tmp_path), bad)


def test_recorded_sound_cues(engine, tmp_path):
    """The real chainsaw in the cold open (pull, the engine from the catch, screams on the
    swing's peaks, all stopped at the cut), a sting and a rev burst on the title's stamp, stings
    on the big cuts (a boom instead of the synthesised hit), revs on the build's section
    changes; without assets the cue sheet is exactly what it was."""
    model, theme, segs, tl = _cold_timeline(engine)
    rp = R.plan_reel(engine, Project("_sample"), model, tl, theme, tmp_path, tmp_path,
                     log=lambda m: None)
    build = next(s_ for s_ in segs if s_["name"] == "build")     # (the sample builds in one band)
    rp["transitions"] = sorted(rp["transitions"] + [{"frame": build["start"] + 90, "type": "band",
                                                     "half": 9, "from": "build", "to": "build"}],
                               key=lambda t: t["frame"])
    rp["cues"] = R.cue_sheet(rp, tl, theme)
    assets, _ = _assets(tmp_path)
    plain = R.cue_sheet(rp, tl, theme)
    assert R.cue_sheet(rp, tl, theme, None) == plain == rp["cues"]
    assert "samples" not in plain and not [e for e in plain["events"] if e["type"] == "sample"]
    cues = R.cue_sheet(rp, tl, theme, assets)
    assert cues["samples"] == assets["samples"]
    fps, co = tl["fps"], tl["cold_open"]
    cut = co["cut"]
    smp = [e for e in cues["events"] if e["type"] == "sample"]
    types = {e["type"] for e in cues["events"]}
    assert "chainsaw_bed" not in types and "chainsaw" not in types and "wind" in types
    # the cold open
    cold = [e for e in smp if e["frame"] < cut]
    pull = [e for e in cold if e["file"] == "pull.wav"]
    assert len(pull) == 1 and pull[0]["frame"] == co["start"] and pull[0]["until"] <= cut
    idle = [e for e in cold if e["file"] == "idle.wav"]
    catch = co["start"] + round(0.5 * fps)
    assert len(idle) == 1 and idle[0]["frame"] == catch and idle[0]["loop"]
    assert idle[0]["until"] == cut and idle[0]["dur"] == cut - catch
    assert len(idle[0]["gain_curve"]) == cut - catch and min(idle[0]["gain_curve"]) < 0.5
    screams = [e for e in cold if e["file"] in ("s1.wav", "s2.wav")]
    peaks = R.rev_peaks(co["rev"][:cut - co["start"]], fps, after=catch - co["start"] + int(0.3 * fps))
    assert [e["frame"] - co["start"] for e in screams] == peaks and peaks
    assert all(e["align"] == "peak" and e["until"] == cut for e in screams)
    assert np.all(np.diff(peaks) >= R.SCREAM_GAP * fps)
    assert not [e for e in cues["events"] if cut <= e["frame"] < segs[0]["end"]]   # black: silent
    # the title's stamp: the first sting on it, then the burst; no sting on the cut into it
    hero = rp["marks"]["title"]["hero"]
    assert any(e["file"] == "st1.wav" and e["frame"] == hero and e["align"] == "peak" for e in smp)
    assert any(e["file"] == "burst.wav" and e["frame"] == hero + 2 for e in smp)
    into_title = next(t for t in rp["transitions"] if t["to"] == "title")
    assert not [e for e in smp if e["frame"] == into_title["frame"]]
    # the other big cuts: hit, boom, the second sting, ... (a boom replaces the synthesised hit)
    big = [t for t in rp["transitions"] if t["type"] != "band" and t["to"] != "title"]
    on_cuts = [next(e["file"] for e in smp if e["frame"] == t["frame"]) for t in big]
    assert on_cuts == (["hit.wav", "boom.wav", "st2.wav"] * 3)[:len(big)]
    for t, f in zip(big, on_cuts):
        hits = [e for e in cues["events"] if e["type"] == "hit" and e["frame"] == t["frame"]]
        assert not hits if f == "boom.wav" else len(hits) == (t["to"] in ("build", "scan", "outro"))
    bands = [t for t in rp["transitions"] if t["type"] == "band"]
    assert bands and all(any(e["frame"] == t["frame"] and e["file"] in ("s1.wav", "s2.wav")
                             for e in smp) for t in bands)
    json.dumps(cues)


def test_booklet_step_pages():
    texts = ["Cover", "Before you start", "How to read the steps", "Build overview\nx",
             "Base\n1", "Base\n3", "Dome\n5", "It works!\n", "Parts inventory", "About this model"]
    assert step_pages(texts) == (5, 7)
    assert step_pages(["a", "b", "c", "d"]) == (2, 3)          # no markers: all but the ends


def test_booklet_flip_and_fan():
    fl = flip_schedule(n_pages=118, first=5, last=114, end=90)
    leaves = fl["leaves"]
    assert leaves[0]["front"] == 1 and leaves[0]["back"] == 2          # opens on the cover
    assert len(leaves) - 1 >= 10                                       # a real thumb-flip
    for a, b in zip(leaves, leaves[1:]):
        assert b["start"] >= a["start"] and b["front"] == a["back"] + 1   # real spreads
    gaps = [b["start"] - a["start"] for a, b in zip(leaves[1:], leaves[2:])]
    assert gaps[0] < gaps[-1]                                          # fast, then slowing
    assert leaves[-1]["start"] + leaves[-1]["dur"] <= 90
    left, right = fl["final"]
    assert 5 <= left < right <= 114                                    # lands on step pages
    fan = fan_plan(5, 114, {left, right}, 90, 180, 15, ["", "albino", "cinnamon"])
    sheets = fan["sheets"]
    assert len(sheets) == 6 and fan["settle"] <= 180
    assert [s["page"].split(":")[0] if ":" in s["page"] else "" for s in sheets][:3] == ["", "albino", "cinnamon"]
    angles = [s["angle"] for s in sheets]
    assert angles == sorted(angles) and angles[0] < 0 < angles[-1]
    plan = {"frames": 180, "flip": fl, "fan": fan}
    blur = blur_frames(plan)
    assert blur and all(len(v) == len(BLUR) for v in blur.values())
    assert min(blur) >= leaves[0]["start"]                              # not on the still cover


def test_page_curve():
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



def test_lights_off_again(engine):
    model = _rigged(engine)
    model.meta["video"].update(lights_tap=True, lights_off=True)
    segs = T.plan_segments(model, booklet=False, beat=BEAT)
    L = next(s for s in segs if s["name"] == "lights")
    assert L["beats"] == T.BEATS["lights"] + T.LIGHTS_OFF_BEATS
    tl = T.build_timeline(engine, model, segs, beat=BEAT)
    s0 = tl["scene_range"][0]
    on, off = tl["lights"]["power_on"], tl["lights"]["power_off"]
    assert L["start"] < on < off < L["end"]
    led, dim = tl["lights"]["led"], tl["lights"]["dim"]
    assert led[off - 1 - s0] == 1.0 and led[off + 1 - s0] == 0.0
    assert dim[L["end"] - 1 - s0] > 0.9                      # the studio is back
    lift = next(s for s in segs if s["name"] == "lift")
    assert led[lift["start"] - s0] == 0.0                    # lifts off with the lights off
    # the mechanism presses for both taps
    g = tl["groups"]
    rows = [np.array(r[0]).reshape(4, 4) for r in g["frames"]]
    k_on, k_off = on - g["start"], off - g["start"]
    assert not np.allclose(rows[k_on - 2], np.eye(4)) and not np.allclose(rows[k_off - 2], np.eye(4))


def test_plates_survive_a_shifted_edit(engine, sample, tmp_path):
    """Moving segments in the edit renumbers plates instead of re-rendering them."""
    from brickkit.video import migrate_plates, segment_digest
    q = {"size": 64, "samples": 1, "engine": "eevee", "device": "gpu"}
    segs_old = T.plan_segments(sample, booklet=False, beat=BEAT, cfg={"beats": {"title": 8}})
    segs_new = T.plan_segments(sample, booklet=False, beat=BEAT, cfg={"beats": {"title": 10}})
    old = T.build_timeline(engine, sample, segs_old, beat=BEAT)
    new = T.build_timeline(engine, sample, segs_new, beat=BEAT)
    so = next(s for s in segs_old if s["name"] == "scan")
    sn = next(s for s in segs_new if s["name"] == "scan")
    assert so["start"] != sn["start"]
    d = tmp_path / "scan"
    d.mkdir()
    (d / ".hash").write_text(segment_digest(old, so, q, legacy=True))
    for f in range(so["start"], so["end"]):
        (d / f"{f:05d}.png").write_text(str(f))
    migrate_plates(tmp_path, old, new, q, None, lambda m: None)
    assert (d / ".hash").read_text() == segment_digest(new, sn, q)
    assert (d / "00000.png").read_text() == str(so["start"])
    assert len(list(d.glob("*.png"))) == so["end"] - so["start"]
    # a plate set whose stamp doesn't match is left alone (and re-rendered later)
    e = tmp_path / "build"
    e.mkdir()
    (e / ".hash").write_text("something else")
    (e / f"{segs_old[2]['start']:05d}.png").write_text("x")
    migrate_plates(tmp_path, old, new, q, None, lambda m: None)
    assert (e / ".hash").read_text() == "something else"


def test_connection_points_skip_press_fits():
    """Press-fit connections (model.press_fit) have no connector points; the scan's dots skip them."""
    from types import SimpleNamespace as NS
    from brickkit.video.reel import connection_points
    stud = NS(ca=NS(origin=(0.0, 0.0, 0.0)), cb=NS(origin=(20.0, 0.0, 0.0)), kind="stud")
    press = NS(ca=None, cb=None, kind="press")
    engine = NS(context=lambda model: NS(connections=[stud, press]))
    assert connection_points(engine, None) == [[10.0, 0.0, 0.0, "stud"]]
