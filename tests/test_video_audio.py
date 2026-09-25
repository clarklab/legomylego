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


def test_minimal_cues_and_unknown_things(tmp_path):
    cues = {"fps": 25, "frames": 60, "beat_frames": 12, "style": "no-such-style",
            "events": [{"frame": 5, "type": "mystery"}, {"frame": 500, "type": "snap"}]}
    info = A.render_audio(cues, tmp_path / "min.wav", lufs=-18.0)
    x, sr = A.read_wav(tmp_path / "min.wav")
    assert x.shape == (round(60 / 25 * SR), 2)
    assert info["lufs"] == pytest.approx(-18.0, abs=1.0) and info["true_peak_db"] <= -1.0
