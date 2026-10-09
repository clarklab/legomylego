"""Quick Bricks planning (brickkit/video/quick.py): the schedule, the parts' flights, the
camera, the close-ups and the sound's cues (no Blender)."""
import numpy as np
import pytest

from brickkit import paths
from brickkit.project import Project
from brickkit.video import assemble as A
from brickkit.video import quick as Q
from brickkit.video import timeline as T


def _project(cam, f, pts, size=Q.SIZE):
    """Normalised image coordinates (-1..1, y up) and depth of points (n, 3) at frame f."""
    pos, tgt = np.array(cam["pos"][f]), np.array(cam["target"][f])
    d = (pos - tgt) / np.linalg.norm(pos - tgt)
    r, u = Q.basis(d)
    tx, ty = Q.tangents(cam["lens"][f], size)
    c = np.asarray(pts, float) - pos
    z = c @ -d
    return np.stack([(c @ r) / (z * tx), (c @ u) / (z * ty), z], -1)


def test_quick_config():
    """[quick] over the defaults, the command line over that; an unknown set, a loop under 6 s
    are errors; close_ups kept to 0..3."""
    cfg = Q.quick_config({"quick": {"set": "linen", "close_ups": 7}}, {"seconds": 12.0, "set": None})
    assert cfg["set"] == "linen" and cfg["seconds"] == 12.0 and cfg["close_ups"] == 3
    assert Q.quick_config({})["set"] == "cutting_mat"
    assert Q.quick_config({})["music"] is False                     # just the clicks by default
    assert Q.quick_config({"quick": {"music": True}})["music"] is True
    assert Q.quick_config({})["watermark"] is False                 # just the render by default
    assert Q.quick_config({})["view"] == "filmic"                   # the parts' colours true
    for bad in ({"set": "beach"}, {"seconds": 4}, {"room": "garage"}, {"surface": "sand"},
                {"light": "noon"}, {"view": "technicolor"}):
        with pytest.raises(SystemExit):
            Q.quick_config({"quick": bad})


def test_quick_layers():
    """The workshop's layers: a preset is a surface, a room and a light; any of them over it;
    every preset's layers exist; set = "random" picks one of each by `seed` (else by the
    model): the same seed the same set, a series of seeds a variety of them."""
    c = Q.quick_config({"quick": {"set": "linen"}})
    assert (c["surface"], c["room"], c["light"]) == Q.PRESETS["linen"] == ("kraft", "window", "day")
    c = Q.quick_config({"quick": {"set": "linen", "room": "bookshelf", "light": "evening"}})
    assert (c["surface"], c["room"], c["light"]) == ("kraft", "bookshelf", "evening")
    for surface, room, light in Q.PRESETS.values():
        assert surface in Q.SURFACES and room in Q.ROOMS and light in Q.LIGHTS
    assert {r for _, r, _ in Q.PRESETS.values()} == set(Q.ROOMS)        # each room in a preset
    assert {s_ for s_, _, _ in Q.PRESETS.values()} == set(Q.SURFACES)  # and each surface
    picks = [Q.quick_config({"quick": {"set": "random", "seed": k}}) for k in range(12)]
    trio = [(c["surface"], c["room"], c["light"]) for c in picks]
    assert trio[3] == (lambda c: (c["surface"], c["room"], c["light"]))(
        Q.quick_config({"quick": {"set": "random", "seed": 3}}))
    assert len(set(trio)) >= 6 and len({t[0] for t in trio}) >= 3 and len({t[1] for t in trio}) >= 3
    a = Q.quick_config({"quick": {"set": "random"}}, slug="caldwell_mini")
    b = Q.quick_config({"quick": {"set": "random"}}, slug="caldwell_mini")
    assert (a["surface"], a["room"], a["light"]) == (b["surface"], b["room"], b["light"])


def test_schedule():
    """Empty for PRE s, then a landing every so often, faster and faster (about RATE_RAMP
    times as often at the end), a pause before the last piece, room round a highlighted
    landing; the hero after the last landing, the cut TAIL s before the end."""
    s = Q.schedule(60, 14.0, [40])
    land, fl = s["land"], s["flight"]
    assert s["frames"] == 14 * Q.FPS and np.all(np.diff(land) > 0)
    assert land[0] == pytest.approx(Q.PRE + Q.FLIGHT[0]) and s["launch"][0] == pytest.approx(Q.PRE)
    assert s["cut"] == pytest.approx(land[-1] + Q.HERO) and s["end"] - s["cut"] == pytest.approx(Q.TAIL)
    g = np.diff(land)
    assert np.mean(g[:8]) > 2.5 * np.mean(g[48:56])                       # it speeds up
    assert g[39] >= Q.CLOSE[0] - 1e-9 and g[40] >= Q.CLOSE[1] - 1e-9      # room round 40
    assert g[-1] > 2 * g[-3]                                              # a beat before the last
    assert fl[0] > fl[30] > fl[50] and fl[40] >= 0.42
    with pytest.raises(SystemExit):
        Q.schedule(400, 8.0)


@pytest.fixture(scope="module")
def sample_plan(engine):
    model = Project("_sample").build(engine.catalog)
    cfg = Q.quick_config({"quick": {"seconds": 8, "close_ups": 1, "highlight": ["right"],
                                    "layout": False}})          # (few parts: laid out by default)
    return model, cfg, Q.plan(engine, model, cfg)


def _ways(engine, model, placed):
    """Every part's way in (the world direction it comes from), from the build's script."""
    return A.assemble(engine, model, placed, Q.build_sequence(model, placed))["axis"]


def test_quick_plan_flights(engine, sample_plan):
    """Parts in instruction order; each flies in from just outside the frame, runs straight in
    along its way in, lines up CLICK short of its place and is pressed home - no bounce - and
    nothing passes through anything on the way."""
    model, cfg, pl = sample_plan
    placed = model.flatten()
    roof = placed[pl["order"][-1]]                                     # base, pillars, roof
    assert pl["order"][0] == 0 and roof.part == "3001.dat" and roof.M[1, 3] == -72
    assert len(pl["close_ups"]) == 1 and "right" in placed[pl["close_ups"][0]["part"]].tags
    assert pl["frames"] == 8 * Q.FPS and pl["cut"] < pl["frames"]
    axes = _ways(engine, model, placed)
    for k, i in enumerate(pl["order"]):
        p = pl["parts"][i]
        fr = np.array(p["frames"]).reshape(-1, 4, 4)
        settle = max(2, round(Q.SETTLE * pl["fps"]))
        span = p["land"] - p["launch"]
        assert len(fr) == span + settle and p["land"] == pl["land"][k] and p["moves"] == []
        rest = np.asarray(placed[i].M, float)
        assert np.allclose(fr[span:], rest, atol=1e-3)                 # in its place, and still
        x, y, _ = _project(pl["camera"], p["launch"], fr[0][:3, 3][None])[0]
        assert max(abs(x), abs(y)) > 0.85                               # from (just) off frame
        off = fr[:span, :3, 3] - rest[:3, 3]
        dist = np.linalg.norm(off, axis=1)
        assert (np.diff(dist) < 1e-6).all()                            # always nearer: no bounce
        near = dist < 10.0                                             # its straight run in
        assert near.sum() >= 3 and (off[near] @ axes[i] > 0.999 * dist[near]).all()
        assert np.allclose(fr[:span][near][:, :3, :3], rest[:3, :3], atol=1e-6)    # and upright
        lined_up = dist[int(np.ceil(Q.PRESS * span))]                  # then pressed home
        assert 0 < lined_up <= Q.CLICK + 0.5 and dist[-1] < lined_up
    assert Q.clashes(engine, placed, pl) == [] and pl["notes"] == []


def test_quick_plan_camera(engine, sample_plan):
    """The camera stays low, keeps the model in the frame through the hero spin, and its
    last frames (the empty set after the cut) run on into the first."""
    model, cfg, pl = sample_plan
    cam = pl["camera"]
    placed = model.flatten()
    C = T.corners(engine, placed).reshape(-1, 3)
    pos, tgt = np.array(cam["pos"]), np.array(cam["target"])
    el = np.degrees(np.arcsin((tgt[:, 1] - pos[:, 1]) / np.linalg.norm(pos - tgt, axis=1)))
    assert el.min() > 5 and el.max() < 30
    for f in range(pl["land"][-1] + 15, pl["cut"], 5):
        xy = _project(cam, f, C)
        assert np.abs(xy[:, :2]).max() < 1.0 and xy[:, 2].min() > 0
    cut = pl["cut"]
    v = pos[1] - pos[0]
    assert np.allclose(pos[-1] + v, pos[0], atol=1e-3) and np.allclose(tgt[cut:], tgt[0], atol=1e-3)
    assert all(2.8 <= s <= 6.3 for s in cam["fstop"])
    mid = (C.min(0) + C.max(0)) / 2                 # the set keeps its props out past this
    assert pl["reach"] == pytest.approx(np.linalg.norm((pos - mid) * [1, 0, 1], axis=1).max() * 0.0004,
                                        abs=1e-3)


def test_quick_layout(engine):
    """layout: a model of a few pieces starts with them all laid out on the table in a ring
    round the build - each lying stably, clear of the build and of its neighbours - and the
    camera above them, all in frame; then each floats up and into place, never under the
    table; after the cut they are laid out again (the loop). Bigger models aren't, unless
    asked."""
    proj = Project("bat", paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    cfg = Q.quick_config(proj.config, slug="bat")
    assert cfg["layout"] == "auto"
    pl = Q.plan(engine, model, cfg)
    placed = model.flatten()
    C = T.corners(engine, placed)
    allp = C.reshape(-1, 3)
    lo, hi = allp.min(0), allp.max(0)
    ground = hi[1]
    assert pl["layout"] and len(placed) < Q.LAYOUT_UNDER
    boxes = []
    for i in pl["order"]:
        p = pl["parts"][i]
        S, rest = np.array(p["start"]).reshape(4, 4), np.asarray(placed[i].M, float)
        fr = np.array(p["frames"]).reshape(-1, 4, 4)
        assert np.allclose(fr[0], S, atol=1e-3) and np.allclose(fr[-1], rest, atol=1e-3)
        mesh = engine.geom.mesh(placed[i].part)
        local = np.unique(np.round(mesh.tris.reshape(-1, 3), 2), axis=0)   # the part itself
        q = local @ S[:3, :3].T + S[:3, 3]
        assert q[:, 1].max() == pytest.approx(ground, abs=1.0)           # on the table
        out = np.maximum(lo[[0, 2]] - q[:, [0, 2]].max(0), q[:, [0, 2]].min(0) - hi[[0, 2]]).max()
        assert out > 0.5 * Q.LAYOUT_CLEAR                                # clear of the build
        from scipy.spatial import ConvexHull
        boxes.append(q[ConvexHull(q[:, [0, 2]]).vertices][:, [0, 2]])   # its footprint
        for M in fr[::3]:                                                # never under the table
            assert (local @ M[:3, :3].T + M[:3, 3])[:, 1].max() < ground + 4.5
        com = S[:3, :3] @ np.asarray(mesh.volume_centroid()[1]) + S[:3, 3]   # lying stably
        assert (q[:, [0, 2]].min(0) < com[[0, 2]]).all() and (com[[0, 2]] < q[:, [0, 2]].max(0)).all()
    def apart(A, B):                                 # two convex footprints: a line between them
        for P in (A, B):
            for k in range(len(P)):
                e = P[(k + 1) % len(P)] - P[k]
                nrm = np.array([-e[1], e[0]]) / (np.linalg.norm(e) + 1e-12)
                if (A @ nrm).max() < (B @ nrm).min() - 2 or (B @ nrm).max() < (A @ nrm).min() - 2:
                    return True
        return False
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            assert apart(boxes[a], boxes[b]), (a, b)
    cam = pl["camera"]
    every = np.concatenate([np.array(pl["parts"][i]["start"]).reshape(4, 4)[:3, 3][None]
                            for i in pl["order"]])
    xy = _project(cam, 0, every)
    assert np.abs(xy[:, :2]).max() < 1.0 and xy[:, 2].min() > 0          # all of them in frame
    pos, tgt = np.array(cam["pos"]), np.array(cam["target"])
    el = np.degrees(np.arcsin((tgt[:, 1] - pos[:, 1]) / np.linalg.norm(pos - tgt, axis=1)))
    assert el[0] == pytest.approx(Q.LAYOUT_EL, abs=1.5) and el[pl["land"][-1] + 30] < 25
    assert max(cam["fstop"]) <= Q.LAYOUT_STOP and cam["fstop"][pl["land"][-1] + 30] <= 6.3
    assert Q.lens_room(pl["parts"], {"pos": pos, "target": tgt}) > 0.5   # none past the lens
    assert pl["land_s"][0] > Q.LAYOUT_PRE                                # a look at them first
    assert (np.array(pl["floor"][1]) - pl["floor"][0])[2] > (hi - lo)[2] + 2 * Q.LAYOUT_CLEAR
    big = Project("caldwell_mini", paths.MODELS_DIR)
    assert not Q.plan(engine, big.build(engine.catalog), Q.quick_config(big.config))["layout"]
    off = Q.plan(engine, model, Q.quick_config(proj.config, {"layout": False}))
    assert not off["layout"] and "start" not in off["parts"][0]
    with pytest.raises(SystemExit):
        Q.quick_config({"quick": {"layout": "maybe"}})


@pytest.mark.parametrize("slug", ["caldwell_mini", "dracula", "bat"])
def test_quick_orbit(engine, slug):
    """The camera goes round the model one way only, without a stop or a jolt; it starts and
    ends on the front's three-quarter view; in a close-up it is on the side its part faces
    (a part that goes on sideways: an eye, a clock)."""
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    pl = Q.plan(engine, model, Q.quick_config(proj.config, slug=slug))
    placed = model.flatten()
    C = T.corners(engine, placed)
    axes = _ways(engine, model, placed)
    allp = C.reshape(-1, 3)
    mid = (allp.min(0) + allp.max(0)) / 2
    cut, fps = pl["cut"], pl["fps"]
    d = np.array(pl["camera"]["pos"])[:cut] - mid
    az = np.degrees(np.unwrap(np.arctan2(d[:, 0], -d[:, 2])))
    speed = np.diff(az) * fps
    assert np.abs(np.diff(speed) * fps).max() < 400                     # no jolts (deg/s2)
    assert speed.max() < 1.3 * Q.FASTEST
    if pl["layout"]:           # laid out: in front of the grid till the table is all but clear
        clear = pl["parts"][pl["order"][-3]]["launch"]                  # (its middle isn't the
        assert np.abs(az[:clear]).max() < 60                            # model's till then)
        assert az[0] == pytest.approx(Q.LAYOUT_OPENING, abs=12)
        speed = speed[clear + fps:]                                     # then its turn
    else:
        assert az[0] == pytest.approx(Q.OPENING, abs=3)
    assert speed.min() > 1.0                                            # one way, never still
    last = abs((az[-1] + 180) % 360 - 180)
    assert Q.LAST_LOOK[0] - Q.LAST_LOOK[1] - 3 <= last <= Q.LAST_LOOK[0] + Q.LAST_LOOK[1] + 3
    assert az[-1] - az[0] > 300                                         # all the way round
    for c in pl["close_ups"]:
        face, tol = Q.facing(C[c["part"]], C, axes[c["part"]])
        if tol > Q.FACING[0]:
            continue
        pos, tgt = np.array(pl["camera"]["pos"][c["land"]]), np.array(pl["camera"]["target"][c["land"]])
        v = (pos - tgt) * [1, 0, 1]
        assert np.degrees(np.arccos(face @ v / np.linalg.norm(v))) < Q.FACING[0] + (25 if pl["layout"] else 12)


def test_quick_close_ups(engine):
    """[quick] highlight: a macro close-up on a clock (the one facing the camera as it lands)
    and on the spire, held through the last piece; the part fills the frame there."""
    proj = Project("caldwell_mini", paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    cfg = Q.quick_config(proj.config)
    pl = Q.plan(engine, model, cfg)
    placed = model.flatten()
    C = T.corners(engine, placed)
    cu = pl["close_ups"]
    assert [placed[c["part"]].part for c in cu] == ["14769p0m.dat", "3688.dat"]
    assert cu[-1]["end"] >= pl["land"][-1]                     # held for the last piece
    for c in cu:
        f = c["land"]
        xy = _project(pl["camera"], f, C[c["part"]])
        assert np.abs(xy[:, 0].mean()) < 0.3 and np.abs(xy[:, 1].mean()) < 0.3
        assert np.ptp(xy[:, 0]) > 0.5                          # half the frame's width or more
        assert pl["camera"]["lens"][f] > cfg["lens"]
    clock = cu[0]["part"]
    out = Q.outward(C[clock], C, _ways(engine, model, placed)[clock])
    pos, tgt = np.array(pl["camera"]["pos"][cu[0]["land"]]), np.array(pl["camera"]["target"][cu[0]["land"]])
    d = (pos - tgt) * [1, 0, 1]
    assert np.dot(out, d / np.linalg.norm(d)) > 0.5            # seen face on


def test_quick_close_ups_face_on(engine):
    """A close-up is only made on a part the camera can be in front of when it lands. The orbit
    goes one way and takes its time: of a tile on a brick's side and one on its front, landing
    a moment apart, only the first one asked for gets its close-up - the other would be seen
    edge on."""
    from brickkit.checks import run_checks
    from brickkit.ldraw.matrix import rot
    from brickkit.model.builder import Model
    model = Model("Two faces", "two_faces", {}, engine.catalog)
    m = model.main
    m.place("3001", "White")
    m.step()
    for k in range(12):                                # (enough before them that the two come quickly)
        x, z = [(-30, -10), (-30, 10), (-10, 10), (30, 10)][k % 4]
        m.place("3024", "White", (x, -8 * (1 + k // 4), z))
        m.step()
    m.place("4733", "White", (10, -24, -10))
    m.step()
    m.place("98138", "Red", (28, -14, -10), rot(z=90), tag="side")
    m.step()
    m.place("98138", "Blue", (10, -14, -28), rot(x=90), tag="front")
    assert {c.status for c in run_checks(engine.context(model), ["connections", "collisions", "buildability"])} == {"pass"}
    placed = model.flatten()
    tags = lambda hl: [placed[c["part"]].tags for c in Q.plan(     # noqa: E731
        engine, model, Q.quick_config({"quick": {"highlight": hl, "close_ups": 2}}))["close_ups"]]
    assert tags(["front", "side"]) == [("front",)]
    assert tags(["side", "front"]) == [("side",)]
    assert tags(["side"]) == [("side",)]


def test_quick_cues(sample_plan, tmp_path):
    """A click on every landing (the variants in turn), the snap on the last, a swish into
    each close-up, the music bed to the cut; the files are the shared ones."""
    _, cfg, pl = sample_plan
    c = Q.cues(pl, True)
    smp = [e for e in c["events"] if e["type"] == "sample"]
    lands = [e for e in smp if e["file"] != Q.SOUNDS["swish"]]
    assert np.allclose([e["frame"] / pl["fps"] for e in lands], pl["land_s"])   # in seconds
    assert pl["clicks_s"] == pl["land_s"] and pl["joins"] == []         # (no kits, no units)
    assert lands[-1]["file"] == Q.SOUNDS["snap"]
    assert len({e["file"] for e in lands[:-1]}) == min(len(Q.SOUNDS["click"]), len(lands) - 1)
    assert len([e for e in smp if e["file"] == Q.SOUNDS["swish"]]) == len(pl["close_ups"])
    assert all((paths.DATA_DIR / "audio" / "quick" / f).exists() for f in c["samples"])
    assert c["sections"] == [{"name": "quick", "start": 0, "end": pl["frames"], "mood": "cold"}]
    assert c["track"]["until"] > pl["cut"] and "track" not in Q.cues(pl, False)
    assert c["track"]["gain"] == Q.MUSIC_GAIN < 0                     # under the clicks
    laugh = paths.MODELS_DIR / "dracula" / "audio" / "count_carter_1.mp3"   # a model's own ending
    e = Q.cues(pl, False, ending={"path": laugh, "level": -3.0, "at": 0.25})
    end = [x for x in e["events"] if x["file"] == "ending"]
    assert len(end) == 1 and end[0]["frame"] / pl["fps"] == pytest.approx(pl["land_s"][-1] + 0.25)
    assert e["samples"]["ending"]["path"] == str(laugh) and "ending" not in c["samples"]
    b = Q.cues(pl, False, sounds=[{"path": laugh, "level": -11.0, "times": [2.0, 5.5]}])
    assert [x["frame"] / pl["fps"] for x in b["events"] if x["file"] == "sound_0"] == [2.0, 5.5]
    wm = Q.watermark(tmp_path / "logo.png", 140)
    from PIL import Image
    a = np.asarray(Image.open(wm))
    assert a.shape[1] == 140 and a[0, 0, 3] == 0 and 90 <= a[:, :, 3].max() <= 110


def test_quick_moments(engine):
    """[[quick.sound]] on: a step's caption (its first piece), a part (the one in a close-up),
    "last", or seconds."""
    proj = Project("caldwell_mini", paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    pl = Q.plan(engine, model, Q.quick_config(proj.config))
    placed = model.flatten()
    land, order = pl["land_s"], pl["order"]
    tower = Q.moment(model, placed, pl, "The clock tower")
    k = next(k for k, i in enumerate(order) if model.main.captions[placed[i].local_step] == "The clock tower")
    assert tower == land[k] and land[k - 1] < tower
    clock = next(c for c in pl["close_ups"] if placed[c["part"]].part == "14769p0m.dat")
    assert Q.moment(model, placed, pl, "14769p0m") == pytest.approx(clock["land"] / pl["fps"], abs=0.02)
    assert Q.moment(model, placed, pl, "last") == land[-1] and Q.moment(model, placed, pl, 3.5) == 3.5
    with pytest.raises(SystemExit):
        Q.moment(model, placed, pl, "The moat")
    snd = Q.quick_config(proj.config)["sound"]
    assert snd and (proj.dir / snd[0]["file"]).is_file()


def test_quick_frame_rates(engine):
    """60 fps finals (the top rate Reels and TikTok take), 15 fps previews: every timing is in
    seconds, so the two agree - the landings, the cut, the close-ups, the sound's cues - and
    the camera at the same moment is in the same place."""
    model = Project("_sample").build(engine.catalog)
    cfg = Q.quick_config({"quick": {"seconds": 8, "close_ups": 1, "highlight": ["right"]}})
    assert Q.FPS == 60 and Q.QUALITY["full"]["fps"] == 60 and Q.QUALITY["full"]["size"] == (1080, 1920)
    a = Q.plan(engine, model, cfg, fps=60)
    b = Q.plan(engine, model, cfg, fps=30)
    assert a["frames"] == 2 * b["frames"] == 480 and a["land_s"] == b["land_s"] and a["cut_s"] == b["cut_s"]
    assert [c["start_s"] for c in a["close_ups"]] == [c["start_s"] for c in b["close_ups"]]
    ca, cb = Q.cues(a, True), Q.cues(b, True)
    assert np.allclose([e["frame"] / 60 for e in ca["events"]], [e["frame"] / 30 for e in cb["events"]])
    assert ca["track"]["until"] / 60 == pytest.approx(cb["track"]["until"] / 30)
    pa, pb = np.array(a["camera"]["pos"]), np.array(b["camera"]["pos"])
    size = float(np.ptp(T.corners(engine, model.flatten()).reshape(-1, 3), axis=0).max())
    for k in range(0, b["frames"], 15):
        assert np.linalg.norm(pa[2 * k] - pb[k]) < 0.06 * size


def test_blank_frames(tmp_path):
    """A near-uniform frame (the camera inside a prop or a wall) is flagged before encoding;
    a real frame, even a soft one, isn't."""
    from PIL import Image
    rng = np.random.default_rng(0)
    Image.fromarray(np.full((192, 108, 3), (90, 10, 8), np.uint8)).save(tmp_path / "00000.png")
    soft = np.clip(120 + 40 * np.sin(np.linspace(0, 6, 108))[None, :, None]
                   + rng.normal(0, 3, (192, 108, 3)), 0, 255).astype(np.uint8)
    Image.fromarray(soft).save(tmp_path / "00001.png")
    assert Q.blank_frames(tmp_path, 3) == [0]


def _quick_models() -> list[str]:
    """Every model tagged for the site's Quick Bricks section (a new one is held to it too)."""
    import tomllib
    return sorted(f.parent.name for f in paths.MODELS_DIR.glob("*/model.toml")
                  if tomllib.loads(f.read_text()).get("model", {}).get("collection") == "quick_bricks")


QUICK = _quick_models()


def test_black_patches(tmp_path):
    """A material the GPU failed to draw: a bright patch that is flat black for a run of
    frames. Found (and rendered again); a part that is black anyway, or the cut to the empty
    set, is not."""
    from PIL import Image
    def frame(k, patch, table=(60, 140, 90)):          # noqa: E306
        a = np.zeros((480, 270, 3), np.uint8)
        a[:] = table
        a[200:260, 100:160] = patch
        a[300:330, 30:60] = (2, 2, 2)                  # (a black part, there all along)
        Image.fromarray(a).save(tmp_path / f"{k:05d}.png")
    for k in range(12):
        frame(k, (0, 0, 0) if 4 <= k <= 6 else (250, 205, 30))
    assert Q.black_patches(tmp_path, 12, cut=10) == [(4, 6)]
    for k in range(12):                                # the cut: the model gone, the table bare
        frame(k, (250, 205, 30) if k < 8 else (1, 1, 1), table=(60, 140, 90) if k < 8 else (1, 1, 1))
    assert Q.black_patches(tmp_path, 12, cut=8) == []
    for k in range(12):                                # black to the end of the shot
        frame(k, (250, 205, 30) if k < 5 else (0, 0, 0))
    assert Q.black_patches(tmp_path, 12, cut=10) == [(5, 9)]


@pytest.mark.parametrize("slug", QUICK)
def test_quick_builds_for_real(engine, slug):
    """Every Quick Bricks model goes together the way it really would: in the plan's own
    frames no part is ever in another (but a clip's last flex onto its bar) or under the
    table, each lands on the table or on a part it connects to, a clear way in was found for
    every piece, every part ends in its place - and the instruction order is kept."""
    proj = Project(slug, paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    placed = model.flatten()
    pl = Q.plan(engine, model, Q.quick_config(proj.config, slug=slug))
    assert Q.clashes(engine, placed, pl) == [] and pl["notes"] == []
    assert sorted(pl["order"]) == list(range(len(placed)))
    assert [placed[i].build_order for i in pl["order"]] == sorted(p.build_order for p in placed)
    for i, p in enumerate(placed):
        assert np.allclose(Q.pose_at(pl, i, pl["cut"] - 1), np.asarray(p.M, float), atol=1e-3)
    assert np.all(np.diff(pl["clicks_s"]) > 0) and pl["clicks_s"][-1] < pl["cut_s"] - 1.0


def test_quick_units_and_lifts(engine):
    """The Mini T. rex: its feet are built beside the legs and pushed on from underneath (the
    leg held up, then set down on the foot); its second leg cannot be built in place (its hip
    slides on from where the first leg's is), so it is built beside the model and joined; its
    arms come up from below and clip onto the shoulder bar. A unit joined is a landing too:
    a click, and room in the schedule. The watermelon lolly is built on the table and set
    down on its stick; the courthouse's clockmaster comes as his kits: legs, torso, head."""
    proj = Project("dinosaur", paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    placed = model.flatten()
    seq = Q.build_sequence(model, placed)
    sc = A.assemble(engine, model, placed, seq)
    items = sc["items"]
    assert sc["order"] == seq and sc["warnings"] == [] and not any(it.forced for it in items)
    joins = [it for it in items if it.kind == "join"]
    assert [len(it.parts) for it in joins] == [3, 3, 9]                 # a foot, a foot, a leg
    for foot in joins[:2]:
        assert foot.mode == "under" and foot.axis @ [0, 1, 0] > 0.99 and foot.carry
        for i in foot.parts:                                           # built beside, on the table
            assert np.linalg.norm((foot.source[i] - foot.seat[i])[[0, 2], 3]) > A.MARGIN
        for before, during, after in foot.carry.values():              # held up, then set down
            assert during[1, 3] < after[1, 3] - 8 and during[1, 3] < before[1, 3]
    assert joins[2].mode == "press" and not joins[2].carry
    arms = [it for it in items if "arms" in placed[it.parts[0]].tags]
    assert len(arms) == 2 and all(it.way == "clip^" and it.axis @ [0, 1, 0] > 0.99 for it in arms)
    pl = Q.plan(engine, model, Q.quick_config(proj.config, slug="dinosaur"))
    assert len(pl["joins"]) == 3 and len(pl["clicks_s"]) == len(placed) + 3
    leg = joins[2].parts
    at = int(round(pl["joins"][2]["at_s"] * pl["fps"]))
    was = [Q.pose_at(pl, i, at - 60) for i in leg]                      # the leg, a second before
    assert all(np.linalg.norm((w - np.asarray(placed[i].M, float))[:3, 3]) > A.MARGIN for w, i in zip(was, leg))
    assert all(np.allclose(Q.pose_at(pl, i, at + 15), np.asarray(placed[i].M, float), atol=1e-3) for i in leg)
    lolly = Project("watermelon_ice_lolly", paths.MODELS_DIR)
    m2 = lolly.build(engine.catalog)
    p2 = m2.flatten()
    s2 = A.assemble(engine, m2, p2, Q.build_sequence(m2, p2))
    assert [it.mode for it in s2["items"]][-2:] == ["under", "under"]   # the stick: last, underneath
    assert s2["landed"][s2["order"][0]][1, 3] > p2[s2["order"][0]].M[1, 3] + 30   # built lower: on the table
    mini = Project("caldwell_mini", paths.MODELS_DIR)
    m3 = mini.build(engine.catalog)
    p3 = m3.flatten()
    s3 = A.assemble(engine, m3, p3, Q.build_sequence(m3, p3))
    assert len(p3) == 70 and len(s3["items"]) == 64                     # 64 pieces, as it is sold
    assert sorted(len(it.parts) for it in s3["items"])[-2:] == [3, 5]   # his legs; torso and arms


def test_quick_hero_moves_in(engine):
    """Units built beside the model (the T. rex's legs and arms) widen the shot; for the hero
    the camera moves in again, and the finished model fills the frame as one that was built
    in place does."""
    for slug in ("dinosaur", "bat"):
        proj = Project(slug, paths.MODELS_DIR)
        model = proj.build(engine.catalog)
        pl = Q.plan(engine, model, Q.quick_config(proj.config, slug=slug))
        xy = _project(pl["camera"], pl["cut"] - 2, T.corners(engine, model.flatten()).reshape(-1, 3))
        assert 1.2 < np.ptp(xy[:, 0]) < 1.9 and np.abs(xy[:, :2]).max() < 1.0, slug    # all of it, and big


def test_quick_schedule_slow():
    """A lift or a join gets the table to itself: nothing else lands in its time."""
    plain = Q.schedule(20, 14.0)
    s = Q.schedule(20, 14.0, slow={8: Q.SLOW["join"]})
    before, after, takes = Q.SLOW["join"]
    assert s["land"][8] - s["land"][7] >= before - 1e-6 and s["land"][9] - s["land"][8] >= after - 1e-6
    assert s["flight"][8] >= takes and s["cut"] == pytest.approx(plain["cut"])
    assert plain["land"][8] - plain["land"][7] < before
    # ... and it waits for a close-up on the piece before it: what is built keeps still till
    # the camera has moved off (a unit carried away from under it left an empty frame)
    c = Q.schedule(20, 14.0, highlights=[7], slow={8: Q.SLOW["join"]})
    assert c["launch"][8] >= c["land"][7] + Q.CLOSE[1] - 1e-6
    assert s["launch"][8] < s["land"][7] + Q.CLOSE[1]


def test_route_keeps_clear(engine):
    """A route goes over a wall rather than through it, comes down in line with the way in
    and runs straight in; with no way round it says so."""
    wall = [(k, A.trans([0.0, -24.0 * k, 0.0])) for k in range(4)]     # four 2 x 4 bricks, stacked

    class P:                                                           # (parts by index)
        part = "3001.dat"
    world = A.World(engine, [P] * 4, wall, 0.0)
    seat = A.trans([0.0, -24.0, 60.0])                                 # behind the wall
    start = np.array([0.0, 0.0, -140.0])                               # from in front of it, low
    path = A.route(world, [("3001.dat", seat)], start, None, [(np.array([0.0, -1.0, 0.0]), 20.0)])
    assert path["clear"] and np.allclose(path["p"][-1], 0, atol=1e-6) and np.allclose(path["p"][0], start)
    assert path["p"][:, 1].min() < -24.0 * 3                           # over the top of the wall
    run = path["p"][path["s"] >= path["sure"]]
    assert np.allclose(run[:, [0, 2]], 0, atol=1e-6) and (np.diff(run[:, 1]) > 0).all()
    for p in path["p"][::3]:
        assert world.free(A.poses([("3001.dat", seat)], path["c"], p, np.eye(3)))
    boxed = A.World(engine, [P] * 4, [(0, A.trans([0.0, -24.0 - 24.0, 60.0]))], 0.0)   # a brick on its place
    assert not A.route(boxed, [("3001.dat", seat)], start, None, [(np.array([0.0, -1.0, 0.0]), 20.0)])["clear"]
