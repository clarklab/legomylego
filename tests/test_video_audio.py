"""Build-video sound (brickkit.video.audio): loudness meter, true peak, mastering, rendering."""
import wave

import numpy as np
import pytest

from brickkit.video import audio as A

SR = 48000
FPS = 30
MOODS = ["intro", "rise", "groove_light", "groove", "breakdown", "halftime", "feature", "end"]


def _sine(freq, seconds, sr=SR, db=0.0, phase=0.0):
    t = np.arange(int(seconds * sr)) / sr
    return A.db2amp(db) * np.sin(2 * np.pi * freq * t + phase)


def _cues(style, seed=7):
    """12 s at 30 fps, 120 BPM (15 frames a beat): every mood, two beats each, except groove
    (eight) and breakdown (four); every SFX type plus an unknown one."""
    bounds = [0, 30, 60, 90, 210, 270, 300, 330, 360]
    sections = [{"name": m, "start": a, "end": b, "mood": m}
                for m, a, b in zip(MOODS, bounds, bounds[1:])]
    events = [{"frame": 3.0, "type": "snap"}, {"frame": 30, "type": "hit"},
              {"frame": 22, "type": "whoosh", "dur": 8}, {"frame": 64.5, "type": "pop", "pitch": 2},
              {"frame": 70, "type": "tick"}, {"frame": 75, "type": "type"},
              {"frame": 180, "type": "riser", "dur": 30}, {"frame": 212, "type": "scan", "dur": 40},
              {"frame": 244, "type": "warn"}, {"frame": 256, "type": "pass"},
              {"frame": 272, "type": "motor", "dur": 24}, {"frame": 300, "type": "power", "dur": 20},
              {"frame": 318, "type": "glitch"}, {"frame": 334, "type": "boing", "pitch": 3},
              {"frame": 340, "type": "page"}, {"frame": 345, "type": "no-such-sound"}]
    events += [{"frame": 94 + 5.5 * k, "type": "click", "gain": 0.5, "pitch": k % 7} for k in range(20)]
    events += [{"frame": 216 + 6 * k, "type": "blip", "pitch": k} for k in range(4)]
    return {"fps": FPS, "frames": bounds[-1], "beat_frames": 15, "style": style, "seed": seed,
            "sections": sections, "events": events}


# ---------------------------------------------------------------------------- meter
def test_kweighting_matches_the_standard_at_48k():
    b1, a1, b2, a2 = A._kweight(48000)
    np.testing.assert_allclose(b1, [1.53512485958697, -2.69169618940638, 1.19839281085285], atol=1e-9)
    np.testing.assert_allclose(a1, [1.0, -1.69065929318241, 0.73248077421585], atol=1e-9)
    np.testing.assert_allclose(b2, [1.0, -2.0, 1.0])
    np.testing.assert_allclose(a2, [1.0, -1.99004745483398, 0.99007225036621], atol=1e-9)


def test_lufs_reference_tones():
    s = _sine(997, 5.0)
    silent = np.zeros_like(s)
    # BS.1770-4: a 0 dBFS 997 Hz sine in one channel of a stereo pair reads -3.01 LKFS
    assert A.measure_lufs(np.stack([s, silent], 1), SR) == pytest.approx(-3.01, abs=0.3)
    assert A.measure_lufs(np.stack([s, silent], 1), SR) == pytest.approx(-3.01, abs=0.02)
    # both channels at -20 dBFS: channel powers add (+3.01 dB), so -20.0 LUFS
    assert A.measure_lufs(np.stack([s, s], 1) * A.db2amp(-20), SR) == pytest.approx(-20.0, abs=0.3)
    # a mono (n,) signal is one channel
    assert A.measure_lufs(s * A.db2amp(-20), SR) == pytest.approx(-23.01, abs=0.05)
    # other rates: coefficients re-derived
    s44 = _sine(997, 5.0, sr=44100)
    assert A.measure_lufs(np.stack([s44, 0 * s44], 1), 44100) == pytest.approx(-3.01, abs=0.05)


def test_lufs_gating():
    tone = np.stack([_sine(997, 4.0, db=-20)] * 2, 1)
    quiet = np.stack([_sine(997, 4.0, db=-45)] * 2, 1)      # > 10 LU below: relative gate
    # (blocks straddling the tone's edges pass the relative gate and pull it down a touch)
    assert A.measure_lufs(np.concatenate([tone, np.zeros((4 * SR, 2)), quiet]), SR) == \
        pytest.approx(-20.0, abs=0.3)
    assert A.measure_lufs(np.zeros((SR, 2)), SR) == float("-inf")      # absolute gate
    assert A.measure_lufs(np.ones((100, 2)), SR) == float("-inf")      # shorter than a block


def test_true_peak_sees_intersample_peaks():
    # fs/4 sine at 45 degrees: every sample is +-0.707 (-3.01 dBFS) but the wave peaks at 1.0
    s = _sine(SR / 4, 1.0, phase=np.pi / 4) * np.hanning(SR)
    mid = s[SR // 2 - 2400:SR // 2 + 2400]
    assert A.amp2db(np.abs(mid).max()) == pytest.approx(-3.01, abs=0.05)
    assert A.true_peak_db(mid, SR) == pytest.approx(0.0, abs=0.1)
    assert A.true_peak_db(np.stack([mid, 0.5 * mid], 1), SR) == pytest.approx(0.0, abs=0.1)


def test_master_hits_loudness_under_the_true_peak_ceiling():
    rng = np.random.default_rng(3)
    n = 6 * SR
    x = A.pink(rng, (n, 2)) * 0.05
    x[::SR // 4] += 0.9 * np.sign(rng.standard_normal((len(x[::SR // 4]), 2)))   # sharp peaks
    x = A.bw(x, "low", 12000.0, SR)
    y, lufs, tp = A.master(x, SR, -16.0)
    assert lufs == pytest.approx(-16.0, abs=0.5)
    assert A.measure_lufs(y, SR) == pytest.approx(lufs, abs=1e-6)
    assert tp <= -1.0 and A.true_peak_db(y, SR) <= -1.0
    assert np.abs(y).max() < 1.0


# ---------------------------------------------------------------------------- rendering
def _section_lufs(x, cues, mood):
    """Loudness of a section after its first beat (the cut's crash/impact)."""
    s = cues["sections"][MOODS.index(mood)]
    return A.measure_lufs(x[round((s["start"] + 15) / FPS * SR):round(s["end"] / FPS * SR)], SR)


@pytest.fixture(scope="module")
def stems():
    return {style: A.render_stems(_cues(style), SR) for style in ("brand", "playful")}


@pytest.mark.parametrize("style", ["brand", "playful"])
def test_music_follows_the_moods(stems, style):
    music, cues = stems[style]["music"], _cues(style)
    level = {m: _section_lufs(music, cues, m) for m in MOODS}
    assert level["groove"] > level["intro"] + 3.0
    assert level["groove"] > level["breakdown"] + 2.0                # no kick, filtered
    assert level["groove"] > level["halftime"]
    assert level["groove"] > level["groove_light"]
    kicks = np.array(stems[style]["arranger"].kicks) / SR / 0.5     # in beats (120 BPM)
    assert np.allclose(kicks * 4, np.round(kicks * 4), atol=1e-3)    # on the 16th grid
    s = cues["sections"][MOODS.index("breakdown")]
    assert not ((kicks >= s["start"] / 15) & (kicks < s["end"] / 15)).any()


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    d = tmp_path_factory.mktemp("audio")
    out = {}
    for style in A.STYLES:
        wav = d / f"{style}.wav"
        out[style] = (A.render_audio(_cues(style), wav), wav)
    return out


@pytest.mark.parametrize("style", list(A.STYLES))
def test_render_style(rendered, style):
    info, wav = rendered[style]
    cues = _cues(style)
    n = round(cues["frames"] / cues["fps"] * SR)
    with wave.open(str(wav), "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (2, SR, n)
        assert w.getsampwidth() in (2, 3)
    x, sr = A.read_wav(wav)
    assert x.shape == (n, 2) and sr == SR
    assert np.isfinite(x).all()
    assert info["seconds"] == pytest.approx(n / SR)
    assert info["lufs"] == pytest.approx(-16.0, abs=1.0)
    assert info["lufs"] == pytest.approx(A.measure_lufs(x, SR), abs=1e-6)
    assert info["true_peak_db"] <= -1.0 and A.true_peak_db(x, SR) <= -1.0
    assert np.abs(x).max() < 0.99                                    # no clipping
    assert np.abs(x[:, 0] - x[:, 1]).max() > 1e-3                    # really stereo
    # the sparse intro sits well under the groove, SFX and all
    assert _section_lufs(x, cues, "groove") > _section_lufs(x, cues, "intro") + 3.0
    # 'end' fades out: the last 0.3 s is (near) silent
    assert A.amp2db(np.sqrt((x[-int(0.3 * SR):] ** 2).mean())) < -50.0


def test_render_is_deterministic(rendered, tmp_path):
    info, wav = rendered["playful"]
    again = A.render_audio(_cues("playful"), tmp_path / "again.wav")
    assert (tmp_path / "again.wav").read_bytes() == wav.read_bytes()
    assert again == info

def test_seed_changes_the_music(stems):
    other = A.render_stems(_cues("brand", seed=8))["music"]
    assert not np.allclose(other, stems["brand"]["music"])


def test_events_land_on_their_frames(rendered):
    n = 4 * SR
    sfx = A.SFX(SR, FPS, seed=1)
    for ev in ({"frame": 12.5, "type": "hit"}, {"frame": 70.25, "type": "snap"},
               {"frame": 33.0, "type": "click", "pitch": 4}, {"frame": 41.7, "type": "blip"},
               {"frame": 5.0, "type": "pop"}, {"frame": 9.0, "type": "boing"}):
        y, duck = sfx.render([ev], n)
        at = round(ev["frame"] / FPS * SR)
        first = int(np.argmax(np.abs(y).max(axis=1) > 1e-6))
        assert 0 <= first - at <= 2, (ev, first - at)                # sample-accurate onset
        if ev["type"] in ("hit", "snap"):                           # music ducks under it
            assert duck[at + int(0.02 * SR)] > 3.0 and duck[at - int(0.01 * SR)] == 0.0
    # in the mastered mix the hit (frame 30 of the test cue, a cut into 'rise') is an onset
    info, wav = rendered["scan"]
    x, _ = A.read_wav(wav)
    at = round(30 / FPS * SR)
    w = int(0.01 * SR)
    before = np.sqrt((x[at - w:at] ** 2).mean())
    after = np.sqrt((x[at:at + w] ** 2).mean())
    assert A.amp2db(after) > A.amp2db(before) + 6.0


def test_grindhouse_sound(tmp_path):
    """The grindhouse style: a heartbeat on the kick bus (lub-dubs on the grid, none in the
    breakdown), the moods still build, its effects land on their frames, the chainsaw revs, and
    the render is deterministic at the loudness target."""
    cues = _cues("grindhouse")
    st = A.render_stems(cues, SR)
    level = {m: _section_lufs(st["music"], cues, m) for m in MOODS}
    assert level["groove"] > level["intro"] + 3.0
    assert level["groove"] > level["breakdown"] + 2.0
    assert level["groove"] > level["groove_light"]
    kicks = np.array(st["arranger"].kicks) / SR / 0.5
    assert len(kicks) and np.allclose(kicks * 4, np.round(kicks * 4), atol=1e-3)
    s = cues["sections"][MOODS.index("breakdown")]
    assert not ((kicks >= s["start"] / 15) & (kicks < s["end"] / 15)).any()
    assert "metal" in st["arranger"].levels                 # the scrapes
    sfx = A.SFX(SR, FPS, seed=1)
    for ev in ({"frame": 12.5, "type": "chainsaw"}, {"frame": 20.0, "type": "typewriter"}):
        y, duck = sfx.render([ev], 4 * SR)
        at = round(ev["frame"] / FPS * SR)
        first = int(np.argmax(np.abs(y).max(axis=1) > 1e-6))
        assert 0 <= first - at <= 2, ev
    assert sfx.render([{"frame": 3, "type": "chainsaw"}], 4 * SR)[1].max() > 3.0     # music ducks
    assert sfx.render([{"frame": 3, "type": "typewriter"}], 4 * SR)[1].max() == 0.0
    # a burn swells into its cut (frame + dur) and is gone soon after
    y, _ = sfx.render([{"frame": 30, "type": "burn", "dur": 9}], 4 * SR)
    env = np.convolve(np.abs(y).max(axis=1), np.ones(480) / 480, "same")
    peak = np.argmax(env) / SR * FPS
    assert 34 <= peak <= 41 and env[round(42 / FPS * SR):].max() < 0.5 * env.max()
    # the chainsaw revs: its firing rate climbs from idle to several times faster
    saw = sfx.fx_chainsaw({"frame": 0, "type": "chainsaw"}, np.random.default_rng(1)).mean(axis=1)
    envl = A.bw(np.abs(A.bw(saw, "band", (200.0, 3000.0), SR)), "low", 400.0, SR)

    def rate(t):
        e = envl[int(t * SR):int((t + 0.08) * SR)]
        e = e - e.mean()
        ac = np.correlate(e, e, "full")[len(e) - 1:]
        lo, hi = SR // 250, SR // 12
        return SR / (lo + np.argmax(ac[lo:hi]))
    assert rate(1.1) > 2.5 * rate(0.4)
    cues["events"] += [{"frame": 36, "type": "chainsaw", "gain": 0.9},
                       {"frame": 200, "type": "burn", "dur": 9}, {"frame": 250, "type": "typewriter"}]
    a = A.render_audio(cues, tmp_path / "a.wav")
    b = A.render_audio(cues, tmp_path / "b.wav")
    assert (tmp_path / "a.wav").read_bytes() == (tmp_path / "b.wav").read_bytes() and a == b
    assert a["lufs"] == pytest.approx(-16.0, abs=0.5) and a["true_peak_db"] <= -1.0


def test_abyss_sound(tmp_path, monkeypatch):
    """The abyss style: a heartbeat pulse on the grid (none in the breakdown) that still lifts
    the groove over the quiet moods; sonar pings on the beat, each with its echo; a rush of
    bubbles on every cut and a deep swell ending exactly on it (no crashes, no bright risers);
    pitched bubbles that rise; deterministic at the loudness target."""
    cues = _cues("abyss")
    played = []
    real = A.Arranger.play

    def spy(self, bus, inst, beat, dur_beats=0.25, **kw):
        played.append((bus, inst, float(beat), float(dur_beats), bool(kw.get("end"))))
        return real(self, bus, inst, beat, dur_beats, **kw)
    monkeypatch.setattr(A.Arranger, "play", spy)
    st = A.render_stems(cues, SR)
    monkeypatch.setattr(A.Arranger, "play", real)
    level = {m: _section_lufs(st["music"], cues, m) for m in MOODS}
    assert level["groove"] > level["intro"] + 3.0
    assert level["groove"] > level["breakdown"] + 1.5
    assert level["groove"] > level["groove_light"]
    kicks = np.array(st["arranger"].kicks) / SR / 0.5
    assert len(kicks) and np.allclose(kicks * 4, np.round(kicks * 4), atol=1e-3)
    s = cues["sections"][MOODS.index("breakdown")]
    assert not ((kicks >= s["start"] / 15) & (kicks < s["end"] / 15)).any()
    pings = [b for bus, inst, b, *_ in played if inst == "sonar"]
    assert pings and all(bus == "keys" for bus, inst, *_ in played if inst == "sonar")
    assert np.allclose(pings, np.round(pings))                        # on the beat
    cuts = [sec["start"] / 15 for sec in cues["sections"][1:]]
    rush = [b for bus, inst, b, *_ in played if inst == "bubbles"]
    assert rush == pytest.approx(cuts)
    swells = [(b, end) for bus, inst, b, d, end in played if inst == "undertow"]
    assert [b for b, _ in swells] == pytest.approx(cuts) and all(end for _, end in swells)
    assert not {inst for _, inst, *_ in played} & {"crash", "uplift", "rev_crash"}
    assert {"heart", "hull", "drone", "swell", "bubble", "bass_sub"} <= {inst for _, inst, *_ in played}
    V = A.Voices(SR, 1)
    ping = V.get("sonar", 83, 1.0)                                    # the ping, then its echo
    env = np.convolve(np.abs(ping), np.ones(480) / 480, "same")
    at = int(0.37 * SR)
    assert env[at + int(0.02 * SR)] > 3 * env[at - int(0.02 * SR)]
    blip = V.get("bubble", 76, 0.25, rise=0.45)                       # a bubble's pitch rises
    zc = np.nonzero(np.diff(np.signbit(blip)))[0] / SR

    def hz(t0, t1):
        k = zc[(zc >= t0) & (zc < t1)]
        return (len(k) - 1) / 2 / (k[-1] - k[0])
    assert hz(0.1, 0.2) > 1.2 * hz(0.0, 0.03)
    rush = V.get("bubbles", None, 1.5)
    assert rush.ndim == 2 and np.abs(rush[:, 0] - rush[:, 1]).max() > 0.05      # spread wide
    a = A.render_audio(cues, tmp_path / "a.wav")
    b = A.render_audio(cues, tmp_path / "b.wav")
    assert (tmp_path / "a.wav").read_bytes() == (tmp_path / "b.wav").read_bytes() and a == b
    assert a["lufs"] == pytest.approx(-16.0, abs=0.5) and a["true_peak_db"] <= -1.5


def test_cold_open_sound(tmp_path):
    """A cold open: no music under it, the chainsaw bed (pull, catch, idle, revving with its
    curve) and wind, cut dead at the cut, silence for the black, then the reel as before; the
    mix still masters to the loudness target."""
    cut, end = 180, 195                                  # 6 s of performance, half a second black
    frames = 12 * 30
    t = np.arange(cut) / FPS
    curve = np.where(t < 0.8, 0.0, np.clip(np.sin(2 * np.pi * (t - 0.8) / 2.5) ** 2, 0, 1))
    reel = _cues("grindhouse")
    sections = [{"name": "cold_open", "start": 0, "end": end, "mood": "cold"}]
    for sec in reel["sections"]:
        sections.append(dict(sec, start=end + round(sec["start"] * (frames - end) / reel["frames"]),
                             end=end + round(sec["end"] * (frames - end) / reel["frames"])))
    events = [{"frame": 0, "type": "chainsaw_bed", "dur": cut, "curve": curve.tolist(), "catch": 14},
              {"frame": 0, "type": "wind", "dur": cut, "gain": 0.8},
              {"frame": end + 3, "type": "snap"}]
    cues = {"fps": FPS, "frames": frames, "beat_frames": 15, "style": "grindhouse", "seed": 3,
            "sections": sections, "events": events}
    st = A.render_stems(cues, SR)
    assert not st["music"][:round(end / FPS * SR)].any()             # no music under it
    info = A.render_audio(cues, tmp_path / "cold.wav")
    x, _ = A.read_wav(tmp_path / "cold.wav")
    assert info["lufs"] == pytest.approx(-16.0, abs=0.5) and info["true_peak_db"] <= -1.0
    c, e = round(cut / FPS * SR), round(end / FPS * SR)
    assert not x[c + int(0.005 * SR):e].any()                        # dead at the cut, then silence
    groove = next(s_ for s_ in sections if s_["mood"] == "groove")
    level = A.measure_lufs(x[round(groove["start"] / FPS * SR):round(groove["end"] / FPS * SR)], SR)
    assert abs(A.measure_lufs(x[:c], SR) - level) < 3.0              # about as loud as the groove
    # it follows the swing: loud where the curve peaks, quieter at idle
    env = np.array([np.sqrt((x[round(f / FPS * SR):round((f + 1) / FPS * SR)] ** 2).mean())
                    for f in range(cut)])
    after = slice(40, cut)
    assert np.corrcoef(curve[after], A.amp2db(env[after]))[0, 1] > 0.6
    # the pull-start: something before the catch, quieter than the roar
    assert 0 < env[:14].max() < env[after].max()
    again = A.render_audio(cues, tmp_path / "again.wav")
    assert (tmp_path / "again.wav").read_bytes() == (tmp_path / "cold.wav").read_bytes()
    assert again == info


def test_hum():
    """A lamp's hum follows its curve: silent while the curve is 0, steady where it's 1."""
    sfx = A.SFX(SR, FPS, seed=5)
    curve = [0.0] * 30 + [1.0] * 60 + [0.0] * 30
    y = sfx.fx_hum({"type": "hum", "dur": 120, "curve": curve}, np.random.default_rng(1))
    assert len(y) == round(4.0 * SR)
    per = [np.abs(y[round(f / FPS * SR):round((f + 1) / FPS * SR)]).max() for f in range(120)]
    assert max(per[:29]) == 0 and min(per[35:85]) > 0.5 and max(per[92:]) == 0
    again = sfx.fx_hum({"type": "hum", "dur": 120, "curve": curve}, np.random.default_rng(1))
    assert np.array_equal(y, again)


def test_recorded_samples(tmp_path):
    """"sample" events: the file's loudest moment on the frame (align peak), its peak at
    `level`, looped to `dur`, stopped dead at `until`, from `offset`; the music ducks; an MP3
    decodes like a WAV; the same cues give the same samples."""
    t = np.arange(SR) / SR
    burst = np.where((t > 0.3) & (t < 0.34), 1.0, 0.02) * np.sin(2 * np.pi * 440 * t)
    A.write_wav(tmp_path / "burst.wav", np.stack([burst, burst], 1), SR)
    hum = 0.5 * np.sin(2 * np.pi * 110 * t[:SR // 2])
    A.write_wav(tmp_path / "hum.wav", np.stack([hum, hum], 1), 44100)     # resampled on load
    samples = {"burst.wav": {"path": str(tmp_path / "burst.wav")},
               "hum.wav": {"path": str(tmp_path / "hum.wav")}}
    sfx = A.SFX(SR, FPS, seed=1, samples=samples)
    n = 5 * SR
    y, duck = sfx.render([{"frame": 45, "type": "sample", "file": "burst.wav", "level": -6.0,
                           "align": "peak", "duck": [4.0, 0.5]}], n)
    at = round(45 / FPS * SR)
    loud = int(np.argmax(np.abs(y).max(axis=1)))
    assert abs(loud - at) < 0.03 * SR                                  # the peak on the frame
    assert np.abs(y).max() == pytest.approx(A.db2amp(-6.0), rel=0.05)
    assert duck[at + int(0.02 * SR)] > 3.0
    y, _ = sfx.render([{"frame": 30, "type": "sample", "file": "hum.wav", "loop": True, "dur": 60,
                        "until": 75, "level": -12.0}], n)                 # 2 s asked, cut at 2.5 s
    on = np.nonzero(np.abs(y).max(axis=1) > 1e-6)[0]
    assert abs(on[0] - round(30 / FPS * SR)) <= 2 and abs(on[-1] - round(75 / FPS * SR)) <= 2
    mid = y[round(40 / FPS * SR):round(70 / FPS * SR), 0]              # looped: no gap
    assert np.sqrt((mid.reshape(-1, 480) ** 2).mean(1)).min() > 0.5 * A.db2amp(-12.0) / np.sqrt(2)
    y2, _ = sfx.render([{"frame": 30, "type": "sample", "file": "burst.wav", "offset": 0.25}], n)
    loud = int(np.argmax(np.abs(y2).max(axis=1)))                      # its burst 0.05 s in
    assert abs(loud - (round(30 / FPS * SR) + int(0.05 * SR))) < 0.03 * SR
    with pytest.raises(KeyError):
        sfx.render([{"frame": 1, "type": "sample", "file": "nope.wav"}], n)
    import shutil
    if shutil.which("ffmpeg"):                                          # an MP3 decodes the same way
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp_path / "burst.wav"), "-b:a",
                        "192k", str(tmp_path / "burst.mp3")], check=True)
        x = A.load_sample(tmp_path / "burst.mp3")
        assert x.shape[1] == 2 and abs(len(x) - SR) < 0.06 * SR
        assert abs(int(np.argmax(np.abs(x[:, 0]))) - int(0.32 * SR)) < 0.03 * SR
    cues = {"fps": FPS, "frames": 120, "beat_frames": 15, "style": "brand", "seed": 2,
            "samples": samples, "sections": [{"name": "a", "start": 0, "end": 120, "mood": "groove"}],
            "events": [{"frame": 30, "type": "sample", "file": "burst.wav", "align": "peak"}]}
    a = A.render_audio(cues, tmp_path / "a.wav")
    b = A.render_audio(cues, tmp_path / "b.wav")
    assert (tmp_path / "a.wav").read_bytes() == (tmp_path / "b.wav").read_bytes() and a == b
    assert a["lufs"] == pytest.approx(-16.0, abs=0.5) and a["true_peak_db"] <= -1.0


def test_minimal_cues_and_unknown_things(tmp_path):
    cues = {"fps": 25, "frames": 60, "beat_frames": 12, "style": "no-such-style",
            "events": [{"frame": 5, "type": "mystery"}, {"frame": 500, "type": "snap"}]}
    info = A.render_audio(cues, tmp_path / "min.wav", lufs=-18.0)
    x, sr = A.read_wav(tmp_path / "min.wav")
    assert x.shape == (round(60 / 25 * SR), 2)
    assert info["lufs"] == pytest.approx(-18.0, abs=1.0) and info["true_peak_db"] <= -1.0
