"""The sizzle reel (brickkit.video.sizzle, video.beats): the beat grid, the shot maths, the
plan's sections, cuts and sounds on the beats, the footage copy, the CLI."""
import copy
import json

import numpy as np
import pytest

from brickkit.video import audio as A
from brickkit.video import beats as Bt
from brickkit.video import sizzle as Z

SR = 48000
YELLOW, RED = "#FEDB05", "#A34C32"


# ---------------------------------------------------------------------------- helpers
def _info(slug, pieces=500, plates=None, first=None):
    plates = plates or {"build": 300, "cold_open": 240, "mechanism": 180}
    first = first or {}
    return {"slug": slug, "name": slug.replace("_", " ").title(), "pieces": pieces, "steps": 40,
            "colours": 5, "headline": ["12", "cm tall"], "notice": "",
            "plates": {k: {"n": n, "first": first.get(k, 0)} for k, n in plates.items()},
            "work": "/nowhere", "turntable": "/nowhere/turntable.mp4", "hero": None}


def _cfg(tmp_path, n_models=4, whoosh=True):
    (tmp_path / "boom.wav").write_bytes(b"not decoded by the plan, only hashed")
    (tmp_path / "whoosh.wav").write_bytes(b"whoosh")
    models = []
    for k in range(n_models):
        models.append({"slug": f"m{k}", "bars": 3 if k != 2 else 2, "shot": [
            {"source": "build", "from": 0.2, "to": 1.0, "beats": 3},
            {"source": "cold_open", "at": 60, "lead": 2, "beats": 3, "caption": "Boom",
             "sfx": "boom.wav", "sfx_align": "peak", "sfx_level": -3.0},
            {"source": "turntable", "from": 0.5, "speed": 2.0, "beats": 3},
            {"source": "mechanism", "at": 90, "lead": 1, "speed": 1.5, "beats": 3}]})
    cfg = {"_dir": str(tmp_path), "title": "Bricks", "url": "bricks.example", "bpm": 128,
           "line": "{n} models · {pieces} pieces|every brick checked", "disclaimer": "fan models",
           "timeline": {"open": 4, "finale": 3, "outro": 2,
                        "open_words": [["Real", 4], ["LEGO.", 6], ["Checked", 8]]},
           "model": models}
    if whoosh:
        cfg["whoosh"] = "whoosh.wav"
    return cfg


def _synth_grid(cfg, tmp_path):
    return Z.music_grid(cfg, tmp_path / "work", log=lambda *_: None)


def _click_track(bpm=128.0, t0=0.3, seconds=20.0, sr=SR, hat=0.1):
    """Kick on every beat, a clap on beats 2 and 4, a hat on the off-beats (as in house)."""
    rng = np.random.default_rng(3)
    y = np.zeros(int(seconds * sr))
    per = 60.0 / bpm
    beats = np.arange(t0, seconds - 0.3, per)
    for i, b in enumerate(beats):
        a = int(b * sr)
        t = np.arange(int(0.12 * sr)) / sr
        y[a:a + len(t)] += 0.8 * np.sin(2 * np.pi * (60 + 90 * np.exp(-t * 40)) * t) * np.exp(-t * 30)
        if i % 4 in (1, 3):
            n = int(0.08 * sr)
            y[a:a + n] += 0.5 * rng.standard_normal(n) * np.exp(-np.arange(n) / sr * 40)
        h = int((b + per / 2) * sr)
        n = int(0.02 * sr)
        y[h:h + n] += hat * rng.standard_normal(n)[:len(y[h:h + n])]
    return 0.5 * np.stack([y, y], 1), beats


# ---------------------------------------------------------------------------- beats
@pytest.mark.parametrize("bpm,hat", [(128.0, 0.1), (128.0, 0.6), (100.0, 0.1), (150.0, 0.3)])
def test_beat_tracker_finds_tempo_beats_and_bars(bpm, hat):
    """On the kicks (not the off-beat hats, however loud), within 10 ms, every one; the bar
    starts on a kick-only beat (claps on 2 and 4)."""
    x, truth = _click_track(bpm=bpm, hat=hat)
    r = Bt.track(x, SR, prefer=bpm)
    assert r["bpm"] == pytest.approx(bpm, abs=0.5)
    b = np.array(r["beats"])
    near = np.abs(b[:, None] - truth[None, :]).min(axis=1)
    assert near.max() < 0.010 and len(b) == len(truth)
    first = int(np.argmin(np.abs(truth - b[r["downbeat"]])))
    assert first % 4 == 0
    assert 0 < r["strength"] <= 1


def test_grid_from_beats_extends_back_and_keeps_the_bar():
    per = 60.0 / 128
    beats = [0.706 + i * per for i in range(40)]
    g = Z.grid_from_beats(beats, 1, 128.0, 20.0, "t.mp3")
    assert g["beats"][0] < per * Z.FPS and g["beats"][0] >= 0          # back to the start
    assert round(beats[1] * Z.FPS) in g["beats"][g["bar0"]::4]          # the downbeat kept
    assert g["bar0"] == 2 and g["length"] == 600 and g["track"] == "t.mp3"
    assert Z._bar(g, 0) == g["beats"][2] and Z._bar(g, 1) == g["beats"][6]
    assert Z._beat(g, 1, 2) == g["beats"][8]
    mid = Z._beat(g, 0, 0.5)
    assert g["beats"][2] < mid < g["beats"][3]
    last = len(g["beats"]) - 1                                    # past the end: by the period
    assert Z._beat(g, 0, last - 2 + 4) == pytest.approx(g["beats"][-1] + 4 * per * Z.FPS, abs=2)


def test_music_grid_synth_and_cached_track(tmp_path, monkeypatch):
    cfg = {"_dir": str(tmp_path), "bpm": 120}
    g = Z.music_grid(cfg, tmp_path / "work", log=lambda *_: None)
    assert g["track"] is None and g["bar0"] == 0 and g["beats"][:3] == [0, 15, 30]
    x, _ = _click_track(seconds=12.0)
    A.write_wav(tmp_path / "t.wav", x, SR)
    cfg["music"] = "t.wav"
    g = Z.music_grid(cfg, tmp_path / "work", log=lambda *_: None)
    assert g["track"] == str(tmp_path / "t.wav") and g["length"] == 360
    assert json.loads((tmp_path / "work" / "beats.json").read_text())["sha1"]
    monkeypatch.setattr(Bt, "track", lambda *a, **k: pytest.fail("the cache should be used"))
    assert Z.music_grid(cfg, tmp_path / "work", log=lambda *_: None) == g


# ---------------------------------------------------------------------------- shots
def test_frame_of_rounds_like_the_page_and_clamps():
    sh = {"from": 2.5, "speed": 0.0, "start": 0, "n": 10}
    assert Z.frame_of(sh, 5) == 3                                  # Math.round, not banker's
    assert Z.frame_of(dict(sh, **{"from": -4.0}), 0) == 0
    assert Z.frame_of(dict(sh, **{"from": 50.0}), 0) == 9


def test_plan_shot_lands_the_key_frame_on_the_beat():
    info = _info("m", plates={"cold_open": 240, "colourways@x": 100}, first={"colourways@x": 480})
    p = Z.plan_shot(info, {"source": "cold_open", "at": 60, "lead": 2, "speed": 1.5}, 100, 160, 14.0)
    assert p["key"] == 128 and Z.frame_of(p, 128) == 60 and Z.frame_of(p, 138) == 75
    p = Z.plan_shot(info, {"source": "cold_open", "at": 60, "lead": 2}, 100, 160, 14.0, key=129)
    assert p["key"] == 129 and Z.frame_of(p, 129) == 60              # the grid's beat wins
    # a colourway's plates are numbered from its span: `at` counts from there too
    p = Z.plan_shot(info, {"source": "colourways@x", "at": 500, "lead": 1}, 0, 40, 14.0)
    assert p["first"] == 480 and Z.frame_of(p, 14) == 20
    p = Z.plan_shot(info, {"source": "colourways@x", "from": 0.2, "to": 0.9}, 10, 70, 14.0)
    assert Z.frame_of(p, 10) == round(0.2 * 99) and abs(Z.frame_of(p, 69) - 0.9 * 99) <= 2
    p = Z.plan_shot(info, {"source": "turntable", "from": 0.5, "speed": 2.0}, 0, 30, 14.0)
    assert p["n"] == 360 and Z.frame_of(p, 10) == round(0.5 * 359) + 20
    with pytest.raises(SystemExit):
        Z.plan_shot(info, {"source": "booklet"}, 0, 30, 14.0)


def test_chip_values():
    c = Z.chip_values(_info("m", pieces=2903), ["pieces", "headline", "steps", "nope"])
    assert c == [{"value": "2,903", "label": "pieces"}, {"value": "12", "label": "cm tall"},
                 {"value": "40", "label": "steps"}]


# ---------------------------------------------------------------------------- the plan
def test_plan_sections_cuts_and_graphics_sit_on_the_beats(tmp_path):
    cfg = _cfg(tmp_path)
    infos = {f"m{k}": _info(f"m{k}", pieces=1000 + k) for k in range(4)}
    g = _synth_grid(cfg, tmp_path)
    reel = Z.plan(cfg, infos, g)
    beats = set(g["beats"])
    segs = reel["segments"]
    assert [s["name"] for s in segs] == ["sz_open"] + ["sz_model"] * 4 + ["sz_finale", "sz_outro"]
    assert segs[0]["start"] == 0 and reel["frames"] == segs[-1]["end"]
    for a, b in zip(segs, segs[1:]):
        assert b["start"] == a["end"] and b["start"] in beats          # contiguous, on bars
    bars = [(s["end"] - s["start"]) / (4 * 60 / 128 * 30) for s in segs]
    assert [round(b) for b in bars] == [4, 3, 3, 2, 3, 3, 2]
    op = segs[0]
    assert [w for w, _ in op["words"]] == ["Real", "LEGO.", "Checked"]
    assert all(f in beats for _, f in op["words"]) and op["logo"] == 0
    assert len(op["teaser"]) == 4 and op["teaser"][-1]["end"] == op["end"]
    assert all(t["start"] in beats for t in op["teaser"])
    for s in segs[1:5]:
        shots = s["shots"]
        assert shots[0]["start"] == s["start"] and shots[-1]["end"] == s["end"]
        for a, b in zip(shots, shots[1:]):
            assert b["start"] == a["end"] and b["start"] in beats
        for sh in shots:
            if "key" in sh:                                          # the key frame on a beat
                assert sh["key"] in beats and sh["start"] <= sh["key"] < sh["end"]
                at = 60 if sh["src"] == "cold_open" else 90
                assert Z.frame_of(sh, sh["key"]) == at
        assert all(c["at"] in beats for c in s["chips"]) and len(s["chips"]) == 2
    # the ferret-sized section (2 bars) has room for three shots only
    assert len(segs[3]["shots"]) == 3
    fin = segs[5]
    assert all(c["at"] in beats for c in fin["cells"]) and all(f in beats for f in fin["line_at"])
    assert fin["line"] == ["4 models · 4,006 pieces", "every brick checked"] and fin["pieces"] == 4006
    out = segs[6]
    assert out["url"] == "bricks.example" and {out["logo"], out["url_at"], out["fine_at"]} <= beats
    # wipes into every section after the open: the brick wall at the drop, then studs,
    # red and yellow in turn, yellow into the outro
    tr = reel["transitions"]
    assert [t["frame"] for t in tr] == [s["start"] for s in segs[1:]]
    assert tr[0]["type"] == "bricks" and {t["type"] for t in tr[1:]} == {"studs"}
    assert [t["color"] for t in tr[1:]] == [YELLOW, RED, YELLOW, RED, YELLOW]
    assert reel["grid"]["beats"] == [b for b in g["beats"] if b < reel["frames"]]


def test_plan_cue_sheet(tmp_path):
    cfg = _cfg(tmp_path)
    infos = {f"m{k}": _info(f"m{k}") for k in range(4)}
    g = _synth_grid(cfg, tmp_path)
    reel = Z.plan(cfg, infos, g)
    cues = reel["cues"]
    ev = cues["events"]
    assert [e["frame"] for e in ev] == sorted(e["frame"] for e in ev)
    assert cues["frames"] == reel["frames"] and cues["fps"] == 30
    # the synth: a mood per section, no recorded track
    assert "track" not in cues and [s["mood"] for s in cues["sections"]] == \
        ["rise", "groove", "groove", "groove", "groove", "feature", "end"]
    # a whoosh (the sample, its peak on the cut) and a hit on every wipe
    wh = [e for e in ev if e["type"] == "sample" and e["file"] == "whoosh.wav"]
    assert [e["frame"] for e in wh] == [t["frame"] for t in reel["transitions"]]
    assert all(e["align"] == "peak" for e in wh)
    hits = {e["frame"] for e in ev if e["type"] == "hit"}
    assert {float(t["frame"]) for t in reel["transitions"]} <= hits
    # each model's sound on its key frame, stopped at the section's end, ducking the music
    booms = [e for e in ev if e["type"] == "sample" and e["file"] == "boom.wav"]
    keys = [sh["key"] for s in reel["segments"] if s["name"] == "sz_model"
            for sh in s["shots"] if sh.get("sfx")]
    assert [e["frame"] for e in booms] == keys and len(booms) == 4
    assert all(e["level"] == -3.0 and e["align"] == "peak" and e["duck"] for e in booms)
    ends = [s["end"] for s in reel["segments"] if s["name"] == "sz_model"]
    assert [e["until"] for e in booms] == ends
    assert set(cues["samples"]) == {"boom.wav", "whoosh.wav"}
    assert all(len(v["sha1"]) == 40 for v in cues["samples"].values())
    # no whoosh file: the house whoosh, ending on the cut
    reel = Z.plan(_cfg(tmp_path, whoosh=False), infos, g)
    wh = [e for e in reel["cues"]["events"] if e["type"] == "whoosh"]
    assert [e["frame"] + e["dur"] for e in wh] == [t["frame"] for t in reel["transitions"]]
    # a missing sound is an error, not a silent gap
    cfg["model"][0]["shot"][1]["sfx"] = "gone.wav"
    with pytest.raises(SystemExit):
        Z.plan(cfg, infos, g)


def test_plan_with_a_track_ends_with_the_music(tmp_path):
    cfg = _cfg(tmp_path, n_models=3)
    infos = {f"m{k}": _info(f"m{k}") for k in range(3)}
    per = 60.0 / 128
    g = Z.grid_from_beats([0.2 + i * per for i in range(70)], 0, 128.0, 31.0, "/music/t.mp3")
    reel = Z.plan(cfg, infos, g)
    cues = reel["cues"]
    assert cues["track"] == {"path": "/music/t.mp3", "fade_out": 0.4}
    assert [s["mood"] for s in cues["sections"]] == ["cold"]          # no synth under the track
    assert reel["frames"] == 930                                     # cut where the music ends
    assert len(reel["segments"][-2]["cells"]) == 3 and reel["segments"][-2]["line"][0].startswith("3 models")
    assert len(reel["segments"][0]["teaser"]) == 3


def test_the_house_config_plans(tmp_path):
    """showreel/sizzle.toml: its models exist, its sounds are there, and it plans to a
    30-40 s reel with every model section 3.5-6 s."""
    cfg = Z.load_config(Z.CONFIG)
    slugs = [m["slug"] for m in cfg["model"]]
    assert slugs == ["baby_metroid", "vhs_tape", "ferret", "chainsaw_face"]
    for s in slugs:
        assert (Z.paths.MODELS_DIR / s / "model.toml").exists()
    assert (Z.CONFIG.parent / cfg["music"]).exists() and (Z.CONFIG.parent / cfg["whoosh"]).exists()
    srcs = {sh["source"] for m in cfg["model"] for sh in m["shot"]} - {"turntable"}
    infos = {s: _info(s, plates={k: 400 for k in srcs}, first={"colourways@clear_window": 400})
             for s in slugs}
    for sh in (sh for m in cfg["model"] for sh in m["shot"] if "at" in sh):
        assert sh["at"] < 400 and float(sh["lead"]).is_integer()     # whole beats: sounds on the beat
    cfg.pop("music")
    g = Z.music_grid(cfg, tmp_path, log=lambda *_: None)
    reel = Z.plan(cfg, infos, g)
    assert 30 <= reel["frames"] / 30 <= 40
    for s in reel["segments"]:
        if s["name"] == "sz_model":
            assert 3.5 <= (s["end"] - s["start"]) / 30 <= 6.0
            assert all(sh["end"] > sh["start"] for sh in s["shots"])


# ---------------------------------------------------------------------------- footage, models
def test_model_info_reads_the_last_showreel(tmp_path):
    work = tmp_path / "m" / "out" / "video_frames" / "full"
    for seg, ks in {"build": range(0, 5), "colourways@x": range(480, 484)}.items():
        (work / seg).mkdir(parents=True)
        for k in ks:
            (work / seg / f"{k:05d}.png").write_bytes(b"")
    (work / "empty").mkdir()
    (work / "reel.json").write_text(json.dumps({"model": {
        "name": "M", "pieces": 12, "steps": 3, "colours": 2, "headline": ["4", "cm"], "notice": ""}}))
    info = Z.model_info("m", tmp_path)
    assert info["plates"] == {"build": {"n": 5, "first": 0}, "colourways@x": {"n": 4, "first": 480}}
    assert info["name"] == "M" and info["pieces"] == 12 and info["turntable"] is None
    with pytest.raises(SystemExit):
        Z.model_info("nope", tmp_path)


def test_footage_copies_the_frames_shown(tmp_path):
    from PIL import Image
    src = tmp_path / "plates"
    (src / "colourways@x").mkdir(parents=True)
    for k in range(480, 520):                          # each plate's grey level is its number
        Image.new("RGB", (32, 32), (k - 480,) * 3).save(src / "colourways@x" / f"{k:05d}.png")
    info = dict(_info("m", plates={"colourways@x": 40}, first={"colourways@x": 480}), work=str(src))
    sh = Z.plan_shot(info, {"source": "colourways@x", "from": 0.0, "speed": 2.0}, 0, 10, 14.0)
    reel = {"segments": [{"name": "sz_model", "slug": "m", "shots": [sh]}]}
    Z.footage(reel, {"m": info}, tmp_path / "work", 16, log=lambda *_: None)
    got = sorted(p.name for p in (tmp_path / "work" / "footage" / "m" / "colourways@x").glob("*.jpg"))
    assert got == [f"{k:05d}.jpg" for k in range(0, 20, 2)]       # numbered from the span's start
    im = Image.open(tmp_path / "work" / "footage" / "m" / "colourways@x" / "00006.jpg")
    assert im.size == (16, 16) and abs(im.getpixel((8, 8))[0] - 6) <= 3


def test_music_track_bed_is_balanced_and_faded(tmp_path):
    """cues["track"]: the recorded bed at MUSIC_REF LUFS under a silent ("cold") arrangement,
    cut at the reel's end with a fade, or padded with silence when it's shorter."""
    t = np.arange(6 * SR) / SR
    y = 0.3 * np.sin(2 * np.pi * 220 * t)
    A.write_wav(tmp_path / "bed.wav", np.stack([y, y], 1), SR)
    A.write_wav(tmp_path / "short.wav", np.stack([y, y], 1)[:3 * SR], SR)
    cues = {"fps": 30, "frames": 120, "beat_frames": 15, "style": "brand", "seed": 1,
            "sections": [{"name": "s", "start": 0, "end": 120, "mood": "cold"}],
            "track": {"path": str(tmp_path / "bed.wav"), "fade_out": 0.5}, "events": []}
    m = A.render_stems(copy.deepcopy(cues), SR)["music"]
    assert m.shape == (4 * SR, 2)
    assert A.measure_lufs(m, SR) == pytest.approx(A.MUSIC_REF, abs=0.2)
    top = np.abs(m[:SR]).max()
    assert np.abs(m[int(3.2 * SR):int(3.3 * SR)]).max() > 0.9 * top       # before the fade
    assert np.abs(m[-SR // 100:]).max() < 0.05 * top                       # faded out
    cues["track"] = {"path": str(tmp_path / "short.wav")}
    m = A.render_stems(copy.deepcopy(cues), SR)["music"]
    assert np.abs(m[int(2.9 * SR):3 * SR]).max() > 0.5 * top and np.abs(m[3 * SR + 10:]).max() == 0
    assert np.abs(A.render_stems(dict(cues, track=None), SR)["music"]).max() == 0   # "cold": none


# ---------------------------------------------------------------------------- the command
def test_cli_sizzle_passes_its_options(monkeypatch, tmp_path):
    from brickkit import cli
    seen = {}

    def fake(config, slugs, out, **kw):
        seen.update(config=config, slugs=slugs, out=out, **kw)
        return tmp_path / "sizzle.mp4"
    monkeypatch.setattr(Z, "make_sizzle", fake)
    assert cli.main(["sizzle", "ferret", "vhs_tape", "--stills", "30, 400", "--preview",
                     "--no-audio", "--out", str(tmp_path)]) == 0
    assert seen["config"] == Z.CONFIG and seen["slugs"] == ["ferret", "vhs_tape"]
    assert seen["out"] == tmp_path and seen["stills"] == [30, 400]
    assert seen["preview"] and not seen["audio"]
    assert cli.main(["sizzle"]) == 0 and seen["slugs"] is None and seen["stills"] is None
