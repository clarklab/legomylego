"""Build-video sound: the showreel's music bed and SFX, synthesised from the edit plan's cue sheet.

    render_audio(cues, out_wav, sr=48000, lufs=-16.0) -> {"lufs", "true_peak_db", "seconds"}
    measure_lufs(x, sr)     ITU-R BS.1770-4 integrated loudness (K-weighted, gated)
    true_peak_db(x, sr)     4x-oversampled peak, dBTP

Everything is made here with numpy/scipy: band-limited oscillators, biquads, a noise-based
convolution reverb, a small drum machine and a handful of melodic voices (plucks, FM bells,
marimba, Karplus-Strong, pads, whistle), arranged section by section in one of four styles, plus
the SFX events, then mastered to `lufs` with a lookahead true-peak limiter (<= -1 dBTP).
No samples, no external audio, no licensed music.

Cue sheet (the video's edit plan produces it):
    fps, frames     frame rate and video length; the WAV is exactly round(frames / fps * sr) samples
    beat_frames     frames per beat (bpm = 60 * fps / beat_frames); beat 0 is at frame 0
    style           "brand" | "scan" | "tape" | "playful"
    seed            every random choice derives from it: the same cue sheet gives identical samples
    key             optional {"root": MIDI note, "mode": "major" | "minor"} (else a style default)
    sections        [{name, start, end, mood}] contiguous frames covering [0, frames); moods:
                    intro, rise, groove_light, groove, breakdown, halftime, feature, end
                    (every section start is a cut: it gets a crash/impact and a fresh phrase)
    events          [{frame, type, gain?, pitch?, dur?, pan?}] SFX placed sample-accurately at
                    frame / fps; types in SFX.LEVEL, unknown types are ignored

Layout: utilities - loudness and mastering - instruments (Voices) - SFX - arrangement (STYLES,
Arranger) - render_audio - demo:  python -m brickkit.video.audio playful out.wav [seconds]
"""
from __future__ import annotations

import collections
import sys
import time
import wave
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, uniform_filter1d

TP_CEILING = -1.5      # dBTP: AAC adds up to ~0.5 dB of overshoot, so -1 still holds after encoding
MUSIC_REF = -20.0      # LUFS the music bed is balanced to before the SFX go on top
_TINY = 1e-12


# ================================================================================ utilities
def db2amp(db):
    return 10.0 ** (np.asarray(db, dtype=float) / 20.0)


def amp2db(a):
    return 20.0 * np.log10(np.maximum(np.abs(a), _TINY))


def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def _ramp(n: int) -> np.ndarray:
    """Raised-cosine 0 -> 1 over n samples."""
    n = max(int(n), 0)
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / max(n, 1))


def _fade(x: np.ndarray, sr: int, fin: float = 0.0, fout: float = 0.004) -> np.ndarray:
    """Raised-cosine fade in/out (seconds), in place; returns x."""
    ni, no = min(len(x), int(fin * sr)), min(len(x), int(fout * sr))
    if ni:
        r = _ramp(ni)
        x[:ni] *= r if x.ndim == 1 else r[:, None]
    if no:
        r = _ramp(no)[::-1]
        x[len(x) - no:] *= r if x.ndim == 1 else r[:, None]
    return x


def _norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    m = np.abs(x).max() if len(x) else 0.0
    return x * (peak / m) if m > 0 else x


# ------------------------------------------------------------------ envelopes
def env_perc(n: int, sr: int, decay: float, attack: float = 0.0005, hold: float = 0.0):
    """Raised-cosine attack, optional hold, exponential decay (time constant `decay` s)."""
    t = np.arange(n) / sr
    e = np.exp(-np.maximum(t - attack - hold, 0.0) / max(decay, 1e-5))
    na = min(n, int(attack * sr))
    e[:na] *= _ramp(na)
    return e


def env_adsr(n: int, sr: int, a: float, d: float, s: float, r: float, gate: float):
    """ADSR over n samples; the gate closes at `gate` s. Decay and release are exponential
    (d, r ~ time to fall most of the way)."""
    a, d, r = max(a, 1e-4), max(d, 1e-4), max(r, 1e-4)

    def level(tt):
        att = 0.5 - 0.5 * np.cos(np.pi * np.clip(tt / a, 0.0, 1.0))
        dec = s + (1.0 - s) * np.exp(-np.maximum(tt - a, 0.0) / (d / 3.0))
        return np.where(tt < a, att, dec)

    t = np.arange(n) / sr
    e = level(t)
    g = max(0.0, gate)
    rel = t >= g
    e[rel] = float(level(np.array(g))) * np.exp(-(t[rel] - g) / (r / 4.0))
    return _fade(e, sr, 0.0, 0.003)


# ------------------------------------------------------------------ oscillators
def _phase(freq, n: int, sr: int, phase0: float = 0.0):
    """Phase in cycles (unbounded) for a constant or per-sample frequency."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return phase0 + (np.cumsum(f) - f) / sr, f


def _blep(t, dt):
    """PolyBLEP residual for a unit step at phase 0 (t, dt in cycles)."""
    y = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    y[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    y[m] = x * x + x + x + 1.0
    return y


def osc_saw(freq, n, sr, phase0=0.0):
    ph, f = _phase(freq, n, sr, phase0)
    t = ph % 1.0
    return 2.0 * t - 1.0 - _blep(t, np.minimum(f / sr, 0.5))


def osc_square(freq, n, sr, phase0=0.0, pw=0.5):
    ph, f = _phase(freq, n, sr, phase0)
    t = ph % 1.0
    dt = np.minimum(f / sr, 0.5)
    return np.where(t < pw, 1.0, -1.0) + _blep(t, dt) - _blep((t - pw) % 1.0, dt)


def osc_sine(freq, n, sr, phase0=0.0):
    ph, _ = _phase(freq, n, sr, phase0)
    return np.sin(2.0 * np.pi * ph)


def osc_tri(freq, n, sr, phase0=0.0):
    ph, _ = _phase(freq, n, sr, phase0)
    return 4.0 * np.abs(ph % 1.0 - 0.5) - 1.0


_PINK = ([0.049922035, -0.095993537, 0.050612699, -0.004408786],
         [1.0, -2.494956002, 2.017265875, -0.522189400])


def pink(rng, shape) -> np.ndarray:
    """Pink noise (Kellet's filter), unit RMS."""
    y = signal.lfilter(*_PINK, rng.standard_normal(shape), axis=0)
    return y / (y.std() + _TINY)


# ------------------------------------------------------------------ filters
def rbj(kind: str, f0, sr: int, q=0.7071, gain_db: float = 0.0):
    """RBJ-cookbook biquad (b, a); f0 and q may be arrays (-> coefficient arrays (3, m))."""
    f0 = np.clip(np.asarray(f0, dtype=float), 5.0, 0.49 * sr)
    w = 2.0 * np.pi * f0 / sr
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2.0 * np.asarray(q, dtype=float))
    A = 10.0 ** (gain_db / 40.0)
    if kind == "lp":
        b, a = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2], [1 + al, -2 * cw, 1 - al]
    elif kind == "hp":
        b, a = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2], [1 + al, -2 * cw, 1 - al]
    elif kind == "bp":        # 0 dB peak gain
        b, a = [al, 0.0 * cw, -al], [1 + al, -2 * cw, 1 - al]
    elif kind == "peak":
        b, a = [1 + al * A, -2 * cw, 1 - al * A], [1 + al / A, -2 * cw, 1 - al / A]
    elif kind in ("lowshelf", "highshelf"):
        sa, s = 2 * np.sqrt(A) * al, (1 if kind == "lowshelf" else -1)
        b = [A * ((A + 1) - s * (A - 1) * cw + sa), s * 2 * A * ((A - 1) - s * (A + 1) * cw),
             A * ((A + 1) - s * (A - 1) * cw - sa)]
        a = [(A + 1) + s * (A - 1) * cw + sa, -s * 2 * ((A - 1) + s * (A + 1) * cw),
             (A + 1) + s * (A - 1) * cw - sa]
    else:
        raise ValueError(kind)
    b, a = np.array(np.broadcast_arrays(*b)), np.array(np.broadcast_arrays(*a))
    return b / a[0], a / a[0]


def filt(x, kind, f0, sr, q=0.7071, gain_db=0.0):
    b, a = rbj(kind, f0, sr, q, gain_db)
    return signal.lfilter(b, a, x, axis=0)


@lru_cache(maxsize=512)
def _sos(kind: str, f, sr: int, order: int):
    return signal.butter(order, f, btype=kind, fs=sr, output="sos")


def bw(x, kind: str, f, sr: int, order: int = 2):
    """Butterworth filter: kind 'low' | 'high' | 'band' (f = (lo, hi))."""
    top = 0.47 * sr
    f = tuple(min(float(v), top) for v in f) if np.ndim(f) else min(float(f), top)
    return signal.sosfilt(_sos(kind, f, sr, order), x, axis=0)


def tv_filter(x, kind: str, f0, sr: int, q=0.7071, block: int = 256):
    """Biquad with a time-varying cutoff (per-sample array or scalar), coefficients updated
    every `block` samples; the filter state carries across blocks."""
    n = len(x)
    if n == 0:
        return x.copy()
    f0 = np.broadcast_to(np.asarray(f0, dtype=float), (n,))
    centres = np.minimum(np.arange(0, n, block) + block // 2, n - 1)
    b, a = rbj(kind, f0[centres], sr, q)
    zi = np.zeros((2,) + x.shape[1:])
    y = np.empty_like(x, dtype=float)
    for i, s in enumerate(range(0, n, block)):
        y[s:s + block], zi = signal.lfilter(b[:, i], a[:, i], x[s:s + block], axis=0, zi=zi)
    return y


def two_state_lp(x, sr, lo, hi, env, q=0.8):
    """Cheap filter envelope: crossfade a dark and a bright low-pass of the same signal."""
    d = filt(x, "lp", lo, sr, q)
    return d + (filt(x, "lp", hi, sr, q) - d) * env


# ------------------------------------------------------------------ space: reverb, delay, chorus
_IRS: dict = {}


def reverb_ir(sr: int, rt60: float, pre: float = 0.012, damp: float = 0.5, seed: int = 7):
    """Stereo impulse response: decorrelated noise, exponentially decaying (-60 dB at rt60),
    highs dying faster (damp 0..1); unit energy per channel."""
    key = (sr, round(rt60, 3), round(pre, 4), round(damp, 3), seed)
    if key in _IRS:
        return _IRS[key]
    rng = np.random.default_rng(seed)
    n = int((pre + rt60 * 1.05) * sr)
    t = np.arange(n) / sr
    noise = rng.standard_normal((n, 2))
    lo = bw(noise, "low", 2500.0, sr)
    hi = noise - lo
    ir = (lo * (10.0 ** (-3.0 * t / rt60))[:, None]
          + hi * (10.0 ** (-3.0 * t / (rt60 * (1.0 - 0.7 * damp))))[:, None] * (1 - 0.5 * damp))
    ir *= (1.0 - np.exp(-t / 0.006))[:, None]        # diffuse build-up
    npre = int(pre * sr)
    ir = np.concatenate([np.zeros((npre, 2)), ir[:n - npre]])
    ir = bw(ir, "high", 120.0, sr)
    _fade(ir, sr, 0.0, 0.05 * rt60)
    ir /= np.sqrt((ir ** 2).sum(axis=0)) + _TINY
    _IRS[key] = ir
    return ir


def convolve(x, ir, n: int | None = None):
    """Mono sum of x through a stereo IR -> (n, 2)."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    n = len(mono) if n is None else n
    return np.stack([signal.oaconvolve(mono, ir[:, c])[:n] for c in range(2)], axis=1)


def pingpong(x, sr, delay_s: float, fb: float = 0.42, taps: int = 6, lp: float = 4500.0):
    """Ping-pong echo of the mono sum (first repeat left); returns only the echoes."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    mono = bw(bw(mono, "low", lp, sr), "high", 250.0, sr)
    n, d = len(mono), max(1, int(delay_s * sr))
    y = np.zeros((n, 2))
    for k in range(1, taps + 1):
        off = k * d
        if off >= n:
            break
        y[off:, (k - 1) % 2] += fb ** (k - 1) * mono[:n - off]
    return y


def chorus(x, sr, rate=0.5, depth=0.0022, base=0.011, mix=0.45):
    """Stereo chorus: one modulated delay tap per channel, LFOs in quadrature."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    dry = x if x.ndim == 2 else np.stack([x, x], axis=1)
    n = len(mono)
    idx = np.arange(n, dtype=float)
    out = np.empty((n, 2))
    for c, ph in enumerate((0.0, np.pi / 2)):
        d = (base + depth * np.sin(2 * np.pi * rate * idx / sr + ph)) * sr
        out[:, c] = dry[:, c] * (1 - mix) + np.interp(idx - d, idx, mono, left=0.0) * mix
    return out


def wow_flutter(x, sr, rng, wow=0.0005, wow_hz=0.55, flutter=1.5e-5, flutter_hz=6.3):
    """Tape speed wobble: a slowly modulated delay (wow ~0.15 % pitch, a little flutter)."""
    n = len(x)
    idx = np.arange(n, dtype=float)
    t = idx / sr
    drift = bw(rng.standard_normal(n), "low", 0.8, sr, 1)
    drift *= 0.3 * wow / (np.abs(drift).max() + _TINY)
    d = (0.004 + wow * np.sin(2 * np.pi * wow_hz * t + rng.uniform(0, 6.28)) + drift
         + flutter * np.sin(2 * np.pi * flutter_hz * t)) * sr
    return np.stack([np.interp(idx - d, idx, x[:, c], left=0.0) for c in range(x.shape[1])],
                    axis=1)


def pan_gains(p: float) -> np.ndarray:
    """Equal-power pan, unity in the centre."""
    th = (np.clip(p, -1.0, 1.0) + 1.0) * np.pi / 4.0
    return np.array([np.cos(th), np.sin(th)]) * np.sqrt(2.0)


def add(bus: np.ndarray, buf: np.ndarray, at: int, gain=1.0) -> None:
    """Mix buf (mono or stereo) into the stereo bus at sample `at`, clipped to the bus."""
    s0, e = max(0, -at), min(len(buf), len(bus) - at)
    if e <= s0:
        return
    seg = buf[s0:e]
    if seg.ndim == 1:
        seg = seg[:, None]
    bus[at + s0:at + e] += seg * gain


# ================================================================================ loudness, mastering
def _kweight(sr: int):
    """BS.1770-4 K-weighting: high-shelf pre-filter + RLB high-pass (the standard's 48 kHz
    coefficients, re-derived for any rate as libebur128 does)."""
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr)
    Vh = 10.0 ** (G / 20.0)
    Vb = Vh ** 0.4996667741545416
    a0 = 1.0 + K / Q + K * K
    b1 = np.array([(Vh + Vb * K / Q + K * K) / a0, 2.0 * (K * K - Vh) / a0,
                   (Vh - Vb * K / Q + K * K) / a0])
    a1 = np.array([1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    a0 = 1.0 + K / Q + K * K
    b2 = np.array([1.0, -2.0, 1.0])
    a2 = np.array([1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    return b1, a1, b2, a2


def _as2d(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x[:, None] if x.ndim == 1 else x


def block_loudness(x, sr: int, block: float = 0.4, hop: float = 0.1) -> np.ndarray:
    """Per-block K-weighted power summed over channels (L/R weight 1), 400 ms / 75 % overlap."""
    x = _as2d(x)
    nb, nh = int(round(block * sr)), int(round(hop * sr))
    if len(x) < nb:
        return np.zeros(0)
    b1, a1, b2, a2 = _kweight(sr)
    y = signal.sosfilt(np.array([np.r_[b1, a1], np.r_[b2, a2]]), np.ascontiguousarray(x.T), axis=-1)
    cs = np.concatenate([np.zeros(1), np.cumsum((y * y).sum(axis=0))])
    starts = np.arange(0, y.shape[1] - nb + 1, nh)
    return (cs[starts + nb] - cs[starts]) / nb


def measure_lufs(x: np.ndarray, sr: int) -> float:
    """ITU-R BS.1770-4 integrated loudness (LUFS) of x, (n,) or (n, channels); -70 LUFS absolute
    and -10 LU relative gates. Returns -inf for silence or anything shorter than one block."""
    p = block_loudness(x, sr)
    if len(p) == 0:
        return float("-inf")
    lk = -0.691 + 10.0 * np.log10(p + _TINY)
    m = lk > -70.0
    if not m.any():
        return float("-inf")
    rel = -0.691 + 10.0 * np.log10(p[m].mean()) - 10.0
    m &= lk > rel
    return float(-0.691 + 10.0 * np.log10(p[m].mean()))


def _tp_env(x: np.ndarray) -> np.ndarray:
    """Per-sample true-peak envelope of (n, ch): max |x| over channels and over the 4x-oversampled
    (polyphase, Kaiser-windowed sinc) points round each sample. One channel at a time."""
    env = np.abs(x).max(axis=1)
    for c in range(x.shape[1]):
        up = signal.resample_poly(np.ascontiguousarray(x[:, c]), 4, 1)
        np.maximum(env, np.abs(up[:4 * len(x)]).reshape(-1, 4).max(axis=1), out=env)
    return env


def true_peak_db(x: np.ndarray, sr: int) -> float:
    """True peak (dBTP): max |x| of the 4x-oversampled signal (BS.1770-4 annex 2)."""
    x = _as2d(x)
    return float(amp2db(_tp_env(x).max())) if len(x) else float("-inf")


def limit(x: np.ndarray, sr: int, ceiling_db: float = -1.3, lookahead: float = 0.005,
          release_db_s: float = 30.0) -> np.ndarray:
    """Lookahead true-peak limiter. The gain reduction needed at each sample (from the 4x-oversampled
    peak) is held with a linear-in-dB release, spread +-lookahead and smoothed, so the gain is
    already down when a peak arrives and never rises above what any nearby peak allows."""
    gr = np.maximum(amp2db(_tp_env(x)) - ceiling_db, 0.0)
    if not gr.any():
        return x.copy()
    c = release_db_s / sr
    ramp = np.arange(len(gr)) * c
    gr = np.maximum.accumulate(gr + ramp) - ramp            # hold, then release at c dB/sample
    L = max(1, int(lookahead * sr))
    gr = maximum_filter1d(gr, size=2 * L + 1, mode="nearest")
    gr = uniform_filter1d(gr, size=L | 1, mode="nearest")   # attack smoothing, still >= needed
    return x * db2amp(-gr)[:, None]


def glue(x: np.ndarray, knee: float = 0.9) -> np.ndarray:
    """Gentle bus saturation: transparent at low level, rounds the loudest peaks."""
    return knee * np.tanh(x / knee)


def master(mix: np.ndarray, sr: int, lufs: float = -16.0, tp: float = TP_CEILING):
    """mix -> glue -> gain to `lufs` -> true-peak limiter, iterated so the limiter's loss is made
    up (lands within ~0.1 LU when the material allows). Returns (y, lufs, true_peak_db)."""
    l0 = measure_lufs(mix, sr)
    if not np.isfinite(l0):             # silent, or shorter than one 400 ms block
        if not np.any(mix):
            return np.zeros_like(mix), float("-inf"), float("-inf")
        y = mix * db2amp(tp - 0.5 - true_peak_db(mix, sr))
        return y, measure_lufs(y, sr), true_peak_db(y, sr)
    x = glue(mix * db2amp(lufs - 2.0 - l0))
    gain = lufs - measure_lufs(x, sr)
    ceiling = tp - 0.3
    best = None
    for _ in range(8):
        y = limit(x * db2amp(gain), sr, ceiling)
        tpk = true_peak_db(y, sr)
        if tpk > tp - 0.02:                     # intersample overshoot: tighten and retry
            ceiling -= tpk - tp + 0.05
            continue
        lv = measure_lufs(y, sr)
        if best is None or abs(lv - lufs) < abs(best[1] - lufs):
            best = (y, lv, tpk)
        if abs(lv - lufs) <= 0.1:
            break
        gain += (lufs - lv) * (1.25 if lv < lufs else 1.0)   # limiting eats part of a boost
    if best is None:                            # never expected: fall back to a static trim
        y = y * db2amp(tp - 0.05 - tpk)
        best = (y, measure_lufs(y, sr), true_peak_db(y, sr))
    return best


def write_wav(path: Path, x: np.ndarray, sr: int, bits: int = 24) -> np.ndarray:
    """Write stereo PCM (16- or 24-bit); returns the quantised signal as float."""
    x = np.clip(np.asarray(x, dtype=float), -1.0, 1.0)
    full = 2 ** (bits - 1) - 1
    q = np.round(x * full).astype("<i4")
    if bits == 16:
        data = q.astype("<i2").tobytes()
    elif bits == 24:
        data = np.ascontiguousarray(q).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    else:
        raise ValueError("bits must be 16 or 24")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(bits // 8)
        w.setframerate(sr)
        w.writeframes(data)
    return q / full


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read a 16/24-bit PCM WAV -> (float (n, channels), sr)."""
    with wave.open(str(path), "rb") as w:
        ch, width, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 2:
        v = np.frombuffer(raw, "<i2").astype(float) / 32767.0
    elif width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8)
             | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v).astype(float) / (2 ** 23 - 1)
    else:
        raise ValueError(f"unsupported sample width {width}")
    return v.reshape(-1, ch), sr


# ================================================================================ instruments
class Voices:
    """Instrument voices: `get(name, midi, dur, var, **params)` renders one note/hit (mono, or
    stereo (n, 2) for cymbals and the gated snare), cached by its arguments since patterns repeat.
    Each voice's randomness comes from an rng seeded by (seed, its arguments), so a voice is the
    same whatever order it is first asked for in."""

    def __init__(self, sr: int, seed: int):
        self.sr, self.seed, self.cache = sr, int(seed) % (2 ** 63), {}

    def rng(self, *key) -> np.random.Generator:
        return np.random.default_rng([self.seed] + [zlib.crc32(repr(k).encode()) for k in key])

    def get(self, name: str, midi=None, dur: float = 0.0, var: int = 0, **kw) -> np.ndarray:
        key = (name, midi, round(float(dur), 3), var, tuple(sorted(kw.items())))
        if key not in self.cache:
            self.cache[key] = getattr(self, name)(midi, float(dur), self.rng(*key), **kw)
        return self.cache[key]

    def _t(self, seconds: float):
        n = max(1, int(seconds * self.sr))
        return n, np.arange(n) / self.sr

    # ---------------------------------------------------------------- drums
    def kick(self, midi, dur, rng, f_hi=160.0, f_lo=48.0, sweep=0.032, decay=0.28, click=0.45,
             drive=2.2):
        sr = self.sr
        n, t = self._t(0.6)
        f = f_lo + (f_hi - f_lo) * np.exp(-t / sweep)
        body = np.sin(2 * np.pi * (np.cumsum(f) - f) / sr) * env_perc(n, sr, decay, 0.0006, 0.018)
        body = np.tanh(drive * body) / np.tanh(drive)
        ck = bw(rng.standard_normal(n), "band", (1500.0, 8000.0), sr) * env_perc(n, sr, 0.003, 0.0002)
        return _norm(_fade(bw(body, "high", 32.0, sr) + click * _norm(ck) * 0.5, sr, 0.0, 0.03))

    def snare(self, midi, dur, rng, tone=190.0, decay=0.15, bright=7500.0, body=0.55):
        sr = self.sr
        n, t = self._t(0.55)
        f = tone * (1.0 + 0.25 * np.exp(-t / 0.012))
        ph = 2 * np.pi * (np.cumsum(f) - f) / sr
        shell = (np.sin(ph) + 0.45 * np.sin(1.63 * ph)) * env_perc(n, sr, 0.05, 0.0005)
        nz = bw(rng.standard_normal(n), "band", (1400.0, bright), sr) * env_perc(n, sr, decay, 0.0004)
        return _norm(_fade(body * _norm(shell) + _norm(nz), sr, 0.0, 0.03))

    def gated(self, midi, dur, rng):
        """80s gated-reverb snare (stereo): a dense room, chopped off after ~0.2 s."""
        sr = self.sr
        dry = self.get("snare", tone=205.0, decay=0.11, bright=9000.0, body=0.7)
        n, t = self._t(0.45)
        dry = np.pad(dry, (0, max(0, n - len(dry))))[:n]
        wet = convolve(dry, reverb_ir(sr, 1.1, pre=0.003, damp=0.25, seed=11))
        gate = np.where(t < 0.19, 1.0, np.exp(-(t - 0.19) / 0.012))
        wet = _norm(wet) * gate[:, None]
        return _norm(dry[:, None] * 0.8 + wet * 0.9)

    def clap(self, midi, dur, rng):
        sr = self.sr
        n, t = self._t(0.4)
        nz = filt(rng.standard_normal(n), "bp", 1150.0, sr, 0.9)
        nz += 0.35 * bw(rng.standard_normal(n), "band", (3000.0, 12000.0), sr)
        e = np.zeros(n)
        for off, a in ((0.0, 0.8), (0.009, 0.7), (0.019, 0.85), (0.029, 1.0)):
            e += a * (t >= off) * np.exp(-np.maximum(t - off, 0.0) / 0.004)
        e += 0.5 * (t >= 0.029) * np.exp(-np.maximum(t - 0.029, 0.0) / 0.09)
        return _norm(_fade(nz * e, sr, 0.0, 0.02))

    def fsnap(self, midi, dur, rng):
        """Finger snap."""
        sr = self.sr
        n, t = self._t(0.14)
        y = filt(rng.standard_normal(n), "bp", 2300.0, sr, 2.2) * env_perc(n, sr, 0.016, 0.0003)
        y += 0.35 * bw(rng.standard_normal(n), "band", (6000.0, 13000.0), sr) * env_perc(n, sr, 0.002, 0.0002)
        y += 0.25 * np.sin(2 * np.pi * 1150.0 * t) * env_perc(n, sr, 0.008, 0.0005)
        return _norm(_fade(y, sr, 0.0, 0.01))

    def hat(self, midi, dur, rng, decay=0.035, metal=0.5, lo=7000.0):
        """808-style hat: six detuned square waves plus noise, high-passed."""
        sr = self.sr
        n, t = self._t(decay * 7 + 0.01)
        sq = sum(osc_square(f * rng.uniform(0.99, 1.01), n, sr, rng.random())
                 for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
        m = bw(sq, "band", (lo, 14000.0), sr)
        nz = bw(rng.standard_normal(n), "band", (lo, 14000.0), sr)
        y = (metal * _norm(m) + (1 - metal) * _norm(nz)) * env_perc(n, sr, decay, 0.0003)
        return _norm(_fade(y, sr, 0.0, 0.004))

    def tick(self, midi, dur, rng, decay=0.012):
        """Metallic, ticky hat for the sci-fi style (ring-modulated partials)."""
        sr = self.sr
        n, t = self._t(0.06)
        ring = np.sin(2 * np.pi * 5230.0 * t) * np.sin(2 * np.pi * 7410.0 * t + rng.random() * 6)
        y = 0.6 * ring + 0.5 * bw(rng.standard_normal(n), "band", (6000.0, 14000.0), sr)
        return _norm(_fade(y * env_perc(n, sr, decay, 0.0002), sr, 0.0, 0.004))

    def shaker(self, midi, dur, rng, decay=0.04):
        sr = self.sr
        n, t = self._t(0.16)
        y = bw(rng.standard_normal(n), "band", (4000.0, 13000.0), sr) * env_perc(n, sr, decay, 0.007)
        return _norm(_fade(y, sr, 0.0, 0.01))

    def tom(self, midi, dur, rng):
        sr = self.sr
        f0 = float(mtof(midi if midi is not None else 45))
        n, t = self._t(0.5)
        f = f0 * (1 + 0.5 * np.exp(-t / 0.03))
        y = np.sin(2 * np.pi * (np.cumsum(f) - f) / sr) * env_perc(n, sr, 0.18, 0.0005)
        y += 0.2 * bw(rng.standard_normal(n), "band", (500.0, 4000.0), sr) * env_perc(n, sr, 0.02)
        return _norm(_fade(y, sr, 0.0, 0.02))

    def crash(self, midi, dur, rng, length=2.6, decay=0.8):
        """Crash cymbal, stereo (independent noise per side)."""
        sr = self.sr
        n, t = self._t(length)
        out = np.zeros((n, 2))
        e = (0.55 * np.exp(-t / 0.1) + 0.45 * np.exp(-t / decay)) * _fade(np.ones(n), sr, 0.001, 0.3)
        for c in range(2):
            sq = sum(osc_square(f, n, sr, rng.random()) for f in rng.uniform(340.0, 1100.0, 6))
            y = 0.55 * _norm(bw(rng.standard_normal(n), "band", (3500.0, 13000.0), sr))
            y += 0.35 * _norm(bw(sq, "band", (3000.0, 13000.0), sr))
            y += 0.25 * _norm(bw(rng.standard_normal(n), "band", (700.0, 3000.0), sr)) * np.exp(-t / 0.25)
            out[:, c] = y * e
        return _norm(out)

    def rev_crash(self, midi, dur, rng):
        """Reversed cymbal swelling into a cut (ends at its loudest)."""
        c = self.get("crash", length=max(0.3, dur) + 0.4, decay=1.2)[::-1]
        n = int(dur * self.sr)
        c = np.array(c[len(c) - n:]) if n <= len(c) else np.pad(c, ((n - len(c), 0), (0, 0)))
        return _norm(_fade(c, self.sr, 0.01, 0.003))

    def boom(self, midi, dur, rng, length=2.4):
        """Low cinematic boom: sub sine drop + low noise."""
        sr = self.sr
        n, t = self._t(length)
        f = 40.0 + 40.0 * np.exp(-t / 0.12)
        sub = np.sin(2 * np.pi * (np.cumsum(f) - f) / sr) * env_perc(n, sr, 0.5, 0.002, 0.04)
        nz = bw(rng.standard_normal(n), "low", 260.0, sr) * env_perc(n, sr, 0.3, 0.003)
        return _norm(_fade(np.tanh(1.4 * (sub + 0.6 * _norm(nz))), sr, 0.0, 0.2))

    def uplift(self, midi, dur, rng):
        """Noise riser (stereo) with a rising band-pass, peaking at its end."""
        sr = self.sr
        n, t = self._t(max(dur, 0.1))
        u = t / t[-1] if n > 1 else t
        fc = 300.0 * (7000.0 / 300.0) ** (u ** 1.3)
        y = tv_filter(rng.standard_normal((n, 2)), "bp", fc, sr, q=1.1)
        tone = osc_saw(180.0 * (1100.0 / 180.0) ** (u ** 1.5), n, sr)
        y += 0.15 * bw(tone, "low", 5000.0, sr)[:, None]
        return _norm(_fade(y * (u ** 2)[:, None], sr, 0.0, 0.006))

    # ---------------------------------------------------------------- bass
    def bass_pluck(self, midi, dur, rng):
        """Pop-house bass: saw + square through a plucked filter, sine sub."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.08)
        x = 0.55 * osc_saw(f, n, sr) + 0.45 * osc_square(f, n, sr, 0.25)
        y = two_state_lp(x, sr, 180.0 + f, 2600.0, env_perc(n, sr, 0.07, 0.001))
        y = y + 0.5 * osc_sine(f, n, sr)
        return np.tanh(1.3 * y * env_adsr(n, sr, 0.002, 0.18, 0.55, 0.05, dur)) / np.tanh(1.3)

    def bass_sub(self, midi, dur, rng):
        """Sci-fi pulse: saw with a short filter blip over a sine sub."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.05)
        y = two_state_lp(osc_saw(f, n, sr), sr, 120.0 + 0.8 * f, 1300.0, env_perc(n, sr, 0.04, 0.001))
        y = y + 0.7 * osc_sine(f, n, sr)
        return y * env_adsr(n, sr, 0.002, 0.1, 0.45, 0.03, dur) * 0.8

    def bass_octave(self, midi, dur, rng):
        """80s driving bass: two detuned saws, warm filter."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.06)
        x = 0.5 * (osc_saw(f * 2 ** (6 / 1200), n, sr, rng.random())
                   + osc_saw(f * 2 ** (-6 / 1200), n, sr, rng.random()))
        y = two_state_lp(x, sr, 230.0 + f, 1800.0, env_perc(n, sr, 0.11, 0.001))
        y = y + 0.35 * osc_sine(f, n, sr)
        return y * env_adsr(n, sr, 0.003, 0.25, 0.75, 0.04, dur)

    def bass_bouncy(self, midi, dur, rng):
        """Staccato, bouncy bass: triangle + sine with a little pitch blip."""
        sr, f0 = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.06)
        f = f0 * (1.0 + 0.3 * np.exp(-t / 0.008))
        y = 0.6 * osc_tri(f, n, sr) + 0.7 * osc_sine(f, n, sr)
        y = bw(np.tanh(1.6 * y), "low", 2200.0, sr)
        return y * env_adsr(n, sr, 0.002, 0.12, 0.35, 0.035, dur)

    # ---------------------------------------------------------------- pads
    def pad(self, midi, dur, rng, detune=9.0, voices=3, attack=0.3, release=0.9, bright=3200.0,
            sub=0.0):
        """Detuned saw pad (the bus filter and chorus shape it further)."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + release)
        y = sum(osc_saw(f * 2 ** (c / 1200), n, sr, rng.random())
                for c in np.linspace(-detune, detune, voices)) / voices
        if sub:
            y = y + sub * osc_sine(f / 2, n, sr)
        y = bw(y, "low", bright, sr)
        return y * env_adsr(n, sr, attack, 0.8, 0.85, release, dur)

    def soft_pad(self, midi, dur, rng, attack=0.25, release=0.8, bright=2600.0):
        """Round pad for the playful style: triangles and a sine."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + release)
        y = (osc_tri(f * 2 ** (5 / 1200), n, sr, rng.random())
             + osc_tri(f * 2 ** (-5 / 1200), n, sr, rng.random()) + 0.8 * osc_sine(f, n, sr)) / 2.8
        y = bw(y, "low", bright, sr)
        return y * env_adsr(n, sr, attack, 0.8, 0.9, release, dur)

    # ---------------------------------------------------------------- plucks, keys, leads
    def pluck(self, midi, dur, rng, decay=0.22, bright=6500.0):
        """Bright synth pluck (detuned saws, snappy filter)."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(min(dur, 1.5) + 0.12 + decay)
        x = 0.5 * (osc_saw(f * 2 ** (7 / 1200), n, sr, rng.random())
                   + osc_saw(f * 2 ** (-7 / 1200), n, sr, rng.random()))
        x += 0.25 * osc_square(2 * f, n, sr, rng.random())
        y = two_state_lp(x, sr, 400.0 + f, bright, env_perc(n, sr, 0.05, 0.001))
        return y * env_perc(n, sr, decay, 0.001) * env_adsr(n, sr, 0.001, 0.1, 1.0, 0.1, dur)

    def bell(self, midi, dur, rng, ratio=3.5, index=3.0, decay=0.8):
        """FM bell: inharmonic modulator, index falling fast."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(min(dur + decay * 3.5, 4.0))
        ie = index * np.exp(-t / 0.1) + 0.35
        y = np.sin(2 * np.pi * f * t + ie * np.sin(2 * np.pi * f * ratio * t))
        y += 0.2 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / (decay * 0.3))
        return _fade(y * env_perc(n, sr, decay, 0.0015), sr, 0.0, 0.05)

    def marimba(self, midi, dur, rng):
        """Modal marimba: a fundamental and the bar's 3.9x and 9.2x partials, plus the mallet."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(1.2)
        dec = 0.42 * (261.6 / f) ** 0.4
        y = (np.sin(2 * np.pi * f * t) * np.exp(-t / dec)
             + 0.3 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t / (dec * 0.2))
             + 0.08 * np.sin(2 * np.pi * min(9.2 * f, 0.45 * sr) * t) * np.exp(-t / (dec * 0.07)))
        y += 0.15 * bw(rng.standard_normal(n), "low", 3000.0, sr) * env_perc(n, sr, 0.003, 0.0002)
        return _fade(y * env_perc(n, sr, 10.0, 0.001), sr, 0.0, 0.05)

    def ks(self, midi, dur, rng, t60=0.9, bright=0.55):
        """Karplus-Strong plucked string, one period per numpy step, tuned by resampling."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(min(dur + 0.5, 2.0))
        P = max(2, int(sr / f))
        fg = sr / (P + 0.5)                       # what the integer loop actually plays
        need = int(n * f / fg) + 2
        d = 10.0 ** (-3.0 / (t60 * f))
        shape = np.interp(np.arange(P), [0, 0.3 * P, P], [0.0, 1.0, 0.0])   # plucked near one end
        exc = 1.4 * shape + bw(rng.uniform(-1, 1, P), "low", 1500.0 + 9000.0 * bright, sr) * 0.6
        exc -= exc.mean()                         # no DC: the loop would hold it forever
        nb = need // P + 2
        out = np.empty(nb * P)
        out[:P] = cur = exc
        for k in range(1, nb):
            prev = out[k * P - P - 1] if k > 1 else 0.0
            cur = d * 0.5 * (cur + np.concatenate(([prev], cur[:-1])))
            out[k * P:(k + 1) * P] = cur
        y = np.interp(np.arange(n) * (f / fg), np.arange(len(out)), out)
        return _norm(y * env_adsr(n, sr, 0.0005, 0.2, 1.0, 0.12, dur))

    def sqarp(self, midi, dur, rng):
        """80s arpeggio voice: narrow square, plucked filter."""
        sr, f = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.2)
        y = two_state_lp(osc_square(f, n, sr, 0.0, 0.32), sr, 600.0 + f, 4800.0,
                         env_perc(n, sr, 0.06, 0.001))
        return y * env_perc(n, sr, 0.17, 0.001, 0.02) * env_adsr(n, sr, 0.001, 0.1, 1.0, 0.05, dur)

    def saw_lead(self, midi, dur, rng):
        """Soft 80s lead: two detuned saws, delayed vibrato."""
        sr, f0 = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.3)
        vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.15) / 0.25, 0.0, 1.0)
        f = f0 * vib
        y = 0.5 * (osc_saw(f * 2 ** (5 / 1200), n, sr, rng.random())
                   + osc_saw(f * 2 ** (-5 / 1200), n, sr, rng.random()))
        y = bw(y, "low", 2800.0, sr)
        return y * env_adsr(n, sr, 0.012, 0.3, 0.7, 0.2, dur)

    def whistle(self, midi, dur, rng):
        """Whistle-like lead: sine with a scoop, delayed vibrato and a little breath."""
        sr, f0 = self.sr, float(mtof(midi))
        n, t = self._t(dur + 0.1)
        vib = 1.0 + 0.006 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - 0.12) / 0.2, 0.0, 1.0)
        f = f0 * vib * 2.0 ** (-0.7 / 12.0 * np.exp(-t / 0.03))
        y = osc_sine(f, n, sr) + 0.03 * osc_sine(2 * f, n, sr)
        y += 0.1 * _norm(filt(rng.standard_normal(n), "bp", f0, sr, 7.0))
        return y * env_adsr(n, sr, 0.035, 0.1, 0.85, 0.08, dur)


# ================================================================================ SFX
class SFX:
    """Sound effects for cue-sheet events. Each `fx_<type>(ev, rng)` returns a buffer that starts
    exactly at the event's frame (transients at sample 0; whoosh/riser build towards frame + dur).
    Levels are dBFS peaks against a music bed at MUSIC_REF LUFS; `gain` scales on top."""

    LEVEL = {"snap": -6.0, "click": -17.0, "whoosh": -14.0, "riser": -16.0, "hit": -6.0,
             "blip": -19.0, "tick": -21.0, "warn": -22.0, "pass": -16.0, "scan": -20.0,
             "power": -11.0, "motor": -19.0, "glitch": -17.0, "boing": -16.0, "page": -16.0,
             "type": -21.0, "pop": -17.0, "riffle": -17.0, "flick": -19.0, "slap": -12.0}
    DUR = {"whoosh": 8, "riser": 30, "scan": 30, "power": 36, "motor": 30, "glitch": 6,
           "riffle": 60}
    DUCK = {"hit": (7.0, 0.7), "power": (5.0, 0.9), "snap": (4.0, 0.35)}   # dB, release s
    ROOM = {"snap": 0.12, "blip": 0.25, "pass": 0.35, "type": 0.15, "pop": 0.2, "warn": 0.2,
            "boing": 0.2, "tick": 0.1, "click": 0.08, "slap": 0.18, "flick": 0.08}

    def __init__(self, sr: int, fps: float, seed: int):
        self.sr, self.fps, self.seed = sr, float(fps), int(seed) % (2 ** 63)

    def _t(self, seconds: float):
        n = max(1, int(seconds * self.sr))
        return n, np.arange(n) / self.sr

    def _dur(self, ev) -> float:
        return max(1.0, float(ev.get("dur", self.DUR.get(ev["type"], 8)))) / self.fps

    def render(self, events, n: int):
        """-> (stereo SFX track of n samples, music duck in dB per sample)."""
        sr = self.sr
        out, duck = np.zeros((n, 2)), np.zeros(n)
        evs = sorted((e for e in events or [] if hasattr(self, "fx_" + str(e.get("type")))),
                     key=lambda e: float(e["frame"]))
        clicks = np.array([float(e["frame"]) / self.fps for e in evs if e["type"] == "click"])
        room = reverb_ir(sr, 0.45, pre=0.004, damp=0.6, seed=21)
        for k, ev in enumerate(evs):
            at = int(round(float(ev["frame"]) / self.fps * sr))
            if at >= n:
                continue
            typ = ev["type"]
            rng = np.random.default_rng([self.seed, zlib.crc32(typ.encode()), k])
            buf = getattr(self, "fx_" + typ)(ev, rng)
            gain = float(db2amp(self.LEVEL[typ])) * float(np.clip(ev.get("gain", 1.0), 0.0, 1.0))
            if typ == "click" and len(clicks):      # dense runs: thinner, so they never buzz
                near = np.count_nonzero(np.abs(clicks - at / sr) < 0.25)
                gain /= np.sqrt(max(1.0, near / 2.0))
            if buf.ndim == 1:
                p = ev.get("pan")
                if p is None:
                    p = rng.uniform(-0.35, 0.35) if typ in ("click", "tick", "type", "pop") else 0.0
                buf = buf[:, None] * pan_gains(float(p))[None, :]
            if typ in self.ROOM:
                buf = np.concatenate([buf, np.zeros((int(0.3 * sr), 2))])
                buf = buf + self.ROOM[typ] * _norm(convolve(buf, room), np.abs(buf).max())
            add(out, _fade(buf, sr, 0.0, 0.004), at, gain)
            if typ in self.DUCK:
                depth, rel = self.DUCK[typ]
                depth *= float(np.clip(ev.get("gain", 1.0), 0.0, 1.0))
                a0 = max(0, at - int(0.004 * sr))
                m = min(n - a0, int((rel * 5 + 0.05) * sr))
                tt = np.arange(m) / sr
                d = depth * np.where(tt < 0.012, tt / 0.012, np.exp(-(tt - 0.012) / rel))
                duck[a0:a0 + m] = np.maximum(duck[a0:a0 + m], d)
        return out, duck

    # ------------------------------------------------------------ the effects
    def fx_snap(self, ev, rng):
        """LEGO brick clicking home: two sharp plastic clicks (studs seating) over a low thump."""
        sr = self.sr
        n, t = self._t(0.3)
        c1 = filt(rng.standard_normal(n), "bp", 3400.0 * 2 ** rng.normal(0, 0.05), sr, 1.5)
        c1 *= np.exp(-t / 0.0022)
        t2 = t - 0.0017
        c2 = filt(rng.standard_normal(n), "bp", 2300.0, sr, 2.0)
        c2 *= np.where(t2 >= 0, np.exp(-np.maximum(t2, 0) / 0.0035), 0.0)
        ping = np.sin(2 * np.pi * 4200.0 * t) * np.exp(-t / 0.005)
        f = 80.0 + 70.0 * np.exp(-t / 0.012)
        thump = np.sin(2 * np.pi * (np.cumsum(f) - f) / sr) * env_perc(n, sr, 0.04, 0.0008)
        return _norm(_norm(c1) + 0.7 * _norm(c2) + 0.25 * ping + 0.8 * thump)

    def fx_click(self, ev, rng):
        """Brick landing in the time-lapse: a tiny plastic tick, pitch/timbre varied."""
        sr = self.sr
        n, t = self._t(0.04)
        f = float(np.clip(2900.0 * 2 ** ((float(ev.get("pitch", 0)) * 0.5 + rng.normal(0, 1.5)) / 12),
                          1500.0, 7000.0))
        y = filt(rng.standard_normal(n), "bp", f, sr, rng.uniform(1.8, 3.5))
        y *= np.exp(-t / rng.uniform(0.0012, 0.0028))
        y = _norm(y) + 0.3 * np.sin(2 * np.pi * f * rng.uniform(0.28, 0.4) * t) * np.exp(-t / 0.005)
        y += 0.25 * np.sin(2 * np.pi * rng.uniform(150, 230) * t) * env_perc(n, sr, 0.006, 0.0005)
        return _norm(y)

    def fx_whoosh(self, ev, rng):
        """Transition swish: band-passed noise sweeping up and across, peaking at frame + dur."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T + 0.15)
        u = np.clip(t / T, 0.0, 1.0)
        fc = np.where(t < T, 350.0 * (3800.0 / 350.0) ** u, 3800.0 * np.exp(-(t - T) / 0.08))
        y = tv_filter(rng.standard_normal(n), "bp", np.maximum(fc, 400.0), sr, q=0.8, block=64)
        y *= np.where(t < T, u ** 2.2, np.exp(-(t - T) / 0.035))
        p0 = float(ev.get("pan", -0.6))
        pos = p0 + (-2 * p0) * np.clip(t / (T + 0.05), 0.0, 1.0)
        th = (np.clip(pos, -1, 1) + 1) * np.pi / 4
        return _norm(np.stack([y * np.cos(th), y * np.sin(th)], axis=1))

    def fx_riser(self, ev, rng):
        """Tension riser: noise + a pitch sweep, ending at frame + dur."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T + 0.05)
        u = np.clip(t / T, 0.0, 1.0)
        nz = tv_filter(rng.standard_normal((n, 2)), "bp", 400.0 * (8000.0 / 400.0) ** u, sr, q=1.0)
        f = 170.0 * (1400.0 / 170.0) ** (u ** 1.3)
        tone = bw(osc_saw(f, n, sr) + osc_saw(f * 1.5, n, sr), "low", 5000.0, sr)
        y = _norm(nz) + 0.35 * _norm(tone)[:, None]
        amp = np.where(t < T, u ** 2, np.exp(-(t - T) / 0.012))
        return _norm(y * amp[:, None])

    def fx_hit(self, ev, rng):
        """Big impact: sub drop, body, noise burst and a hall tail."""
        sr = self.sr
        n, t = self._t(3.0)
        f = 44.0 + 70.0 * np.exp(-t / 0.07)
        sub = np.sin(2 * np.pi * (np.cumsum(f) - f) / sr) * env_perc(n, sr, 0.3, 0.0008, 0.02)
        f2 = 62.0 + 150.0 * np.exp(-t / 0.02)
        body = np.sin(2 * np.pi * (np.cumsum(f2) - f2) / sr) * env_perc(n, sr, 0.1, 0.0005)
        nb = (bw(rng.standard_normal(n), "low", 6000.0, sr) * env_perc(n, sr, 0.08, 0.0003)
              + 0.5 * bw(rng.standard_normal(n), "band", (2000.0, 9000.0), sr) * env_perc(n, sr, 0.015, 0.0002))
        dry = np.tanh(1.6 * (sub + 0.6 * body + 0.5 * _norm(nb)))
        wet = convolve(bw(dry, "high", 250.0, sr), reverb_ir(sr, 2.6, pre=0.018, damp=0.45, seed=3))
        return _norm(dry[:, None] + 0.35 * _norm(wet))

    def fx_blip(self, ev, rng):
        """UI blip; `pitch` indexes a rising pentatonic scale."""
        sr = self.sr
        i = int(ev.get("pitch", 0))
        f = 880.0 * 2 ** ((12 * (i // 5) + (0, 2, 4, 7, 9)[i % 5]) / 12)
        n, t = self._t(0.2)
        y = np.tanh(1.8 * osc_sine(f, n, sr)) + 0.15 * osc_sine(2 * f, n, sr)
        y *= env_perc(n, sr, 0.04, 0.002, 0.035)
        return _norm(y)

    def fx_tick(self, ev, rng):
        """Tiny odometer tick."""
        sr = self.sr
        n, t = self._t(0.03)
        y = _norm(filt(rng.standard_normal(n), "bp", 5500.0, sr, 3.0) * np.exp(-t / 0.0012))
        y += 0.45 * np.sin(2 * np.pi * rng.uniform(2400, 2800) * t) * np.exp(-t / 0.004)
        return _norm(y)

    def fx_warn(self, ev, rng):
        """Lower two-tone caution blip."""
        sr = self.sr
        n, t = self._t(0.34)
        f = np.where(t < 0.135, 370.0, 277.2)
        y = bw(osc_square(f, n, sr, 0.0, 0.4), "low", 2400.0, sr)

        def gate(a, b, r=0.005):                  # on over [a, b] with short linear ramps
            return np.clip(np.minimum((t - a) / r, (b - t) / r), 0.0, 1.0)

        e = gate(0.0, 0.125) + gate(0.145, 0.33, 0.02) * np.exp(-np.maximum(t - 0.2, 0) / 0.08)
        return _norm(y * e)

    def fx_pass(self, ev, rng):
        """Success chime: a quick rising major arpeggio of FM bells."""
        sr = self.sr
        n, t = self._t(1.4)
        y = np.zeros(n)
        for k, semi in enumerate((0, 4, 7, 12)):
            f, off = 1046.5 * 2 ** (semi / 12), int(k * 0.055 * sr)
            m = n - off
            tt = t[:m]
            y[off:] += (np.sin(2 * np.pi * f * tt + (1.2 * np.exp(-tt / 0.05) + 0.2)
                               * np.sin(2 * np.pi * 2 * f * tt)) * env_perc(m, sr, 0.35, 0.002))
        return _norm(_fade(y, sr, 0.0, 0.1))

    def fx_scan(self, ev, rng):
        """Scanner sweep: resonant noise sweeping up and back, a rising sine, a low hum."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T + 0.08)
        u = np.clip(t / T, 0.0, 1.0)
        sweep = 0.5 - 0.5 * np.cos(2 * np.pi * u)
        nz = tv_filter(rng.standard_normal(n), "bp", 600.0 * (4500.0 / 600.0) ** sweep, sr, q=4.0)
        tone = osc_sine(300.0 * 4.0 ** u, n, sr)
        hum = bw(osc_saw(100.0, n, sr), "low", 700.0, sr)
        y = _norm(nz) + 0.3 * tone + 0.35 * _norm(hum)
        y = _fade(y, sr, 0.04, 0.08)
        th = (np.clip(-0.6 + 1.2 * u, -1, 1) + 1) * np.pi / 4
        return _norm(np.stack([y * np.cos(th), y * np.sin(th)], axis=1))

    def fx_power(self, ev, rng):
        """Lights on: a zap at the frame, then electrical hum rising and a bright swell."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T + 1.4)
        u = np.clip(t / T, 0.0, 1.0)
        fz = 90.0 + 1400.0 * np.exp(-t / 0.018)
        zap = osc_saw(fz, n, sr) * env_perc(n, sr, 0.04, 0.0005)
        crushed = np.repeat(rng.uniform(-1, 1, n // 12 + 1), 12)[:n] * env_perc(n, sr, 0.025, 0.0003)
        hum = bw(osc_saw(50.0 * (1 + 0.08 * u), n, sr) + 0.5 * osc_square(100.0, n, sr), "low", 1400.0, sr)
        hum *= np.where(t < T, 0.15 + 0.85 * u ** 1.5, np.exp(-(t - T) / 0.35))
        sw = sum(np.sin(2 * np.pi * f * t) for f in (523.3, 659.3, 784.0, 1046.5, 1568.0))
        sw *= np.where(t < T, u ** 2.5, np.exp(-(t - T) / 0.5)) * (1 + 0.3 * np.sin(2 * np.pi * 7 * t))
        y = 0.7 * _norm(zap + 0.6 * crushed) + 0.45 * _norm(hum) + 0.45 * _norm(sw)
        y = _norm(_fade(y, sr, 0.0, 0.2))
        return np.stack([y, np.roll(y, int(0.007 * sr)) * 0.9 + y * 0.1], axis=1)

    def fx_motor(self, ev, rng):
        """Mechanism: servo whirr plus a soft gear ratchet, for dur frames."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T)
        f = 140.0 * (1 + 0.12 * np.sin(2 * np.pi * 2.7 * t)) * (1 + 0.1 * np.minimum(t / 0.2, 1))
        whirr = filt(osc_saw(f, n, sr), "bp", 900.0, sr, 1.3)
        clicks = np.zeros(n)
        pos = np.cumsum(rng.uniform(0.85, 1.15, int(T * 26) + 2) / 26.0)
        idx = (pos[pos < T] * sr).astype(int)
        clicks[idx] = rng.uniform(0.5, 1.0, len(idx))
        m, tk = self._t(0.012)
        kern = filt(rng.standard_normal(m), "bp", 3000.0, sr, 2.0) * np.exp(-tk / 0.002)
        ratchet = signal.fftconvolve(clicks, kern)[:n]
        return _norm(_fade(_norm(whirr) + 0.6 * _norm(ratchet), sr, 0.03, 0.05))

    def fx_glitch(self, ev, rng):
        """VHS tracking glitch: bit-crushed, stuttering noise and buzz with pitch wobble."""
        sr, T = self.sr, self._dur(ev)
        n, t = self._t(T)
        y, pos = np.zeros(n), 0
        while pos < n:
            m = min(n - pos, int(rng.uniform(0.008, 0.035) * sr))
            kind = rng.integers(3)
            if kind == 0:
                hold = int(rng.integers(6, 40))
                seg = np.repeat(rng.uniform(-1, 1, m // hold + 1), hold)[:m]
                levels = float(2 ** rng.integers(2, 5))
                seg = np.round(seg * levels) / levels
            elif kind == 1:
                f0 = rng.uniform(60, 900)
                seg = osc_square(f0 * (1 + 0.3 * np.sin(2 * np.pi * 30 * t[:m])), m, sr)
            else:
                seg = 0.2 * rng.standard_normal(m)
            y[pos:pos + m] = _fade(seg * rng.uniform(0.4, 1.0), sr, 0.001, 0.001)
            pos += m
        return _norm(_fade(bw(y, "band", (150.0, 9000.0), sr), sr, 0.002, 0.004))

    def fx_boing(self, ev, rng):
        """Playful spring bounce; `pitch` in semitones."""
        sr = self.sr
        f0 = 200.0 * 2 ** (float(ev.get("pitch", 0)) / 12)
        n, t = self._t(0.6)
        f = f0 * (1 + 0.9 * (1 - np.exp(-t / 0.09))) * (1 + 0.12 * np.sin(2 * np.pi * 16 * t) * np.exp(-t / 0.18))
        y = np.tanh(1.8 * osc_sine(f, n, sr)) * env_perc(n, sr, 0.16, 0.002)
        return _norm(_fade(y, sr, 0.0, 0.05))

    def fx_page(self, ev, rng):
        """Paper page turn: rustle bursts over a soft swish."""
        sr = self.sr
        n, t = self._t(0.5)
        e = np.zeros(n)
        for c in rng.uniform(0.0, 0.32, 9):
            e += rng.uniform(0.3, 1.0) * (t >= c) * np.exp(-np.maximum(t - c, 0) / rng.uniform(0.008, 0.03))
        hump = np.sin(np.pi * np.clip(t / 0.4, 0, 1)) ** 2
        rustle = bw(rng.standard_normal(n), "band", (1800.0, 7000.0), sr) * (0.4 * hump + e)
        swish = filt(rng.standard_normal(n), "bp", 500.0, sr, 0.7) * hump
        y = _norm(_norm(rustle) + 0.5 * _norm(swish))
        th = (np.clip(0.5 - 1.0 * np.clip(t / 0.4, 0, 1), -1, 1) + 1) * np.pi / 4
        return _norm(_fade(np.stack([y * np.cos(th), y * np.sin(th)], axis=1), sr, 0.005, 0.05))

    def fx_riffle(self, ev, rng):
        """A thumb-flip: paper flutter whose rate falls from fast to slow over `dur`, as the
        pages slow down; soft swell in, quick tail out."""
        sr = self.sr
        dur = self._dur(ev)
        n, t = self._t(dur + 0.25)
        x = np.clip(t / dur, 0.0, 1.0)
        rate = 26.0 * (1 - x) ** 1.3 + 6.0                    # flicks per second
        ph = np.cumsum(rate) / sr
        flut = 0.5 + 0.5 * np.cos(2 * np.pi * ph) ** 7        # sharp paper edges
        noise = bw(rng.standard_normal(n), "band", (1500.0, 8000.0), sr)
        body = filt(rng.standard_normal(n), "bp", 700.0, sr, 0.8)
        swell = np.clip(t / 0.12, 0, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))
        y = (_norm(noise) * (0.25 + 0.75 * flut) + 0.35 * _norm(body) * flut) * swell
        pan = 0.3 * np.sin(2 * np.pi * 0.7 * t)
        th = (pan + 1) * np.pi / 4
        return _norm(_fade(np.stack([y * np.cos(th), y * np.sin(th)], axis=1), sr, 0.01, 0.05))

    def fx_flick(self, ev, rng):
        """One page flicking over in the riffle: a short papery snap."""
        sr = self.sr
        n, t = self._t(0.09)
        f = 3200.0 * 2 ** rng.normal(0, 0.15)
        y = bw(rng.standard_normal(n), "band", (f * 0.5, f * 2.0), sr) * np.exp(-t / 0.012)
        y += 0.4 * filt(rng.standard_normal(n), "bp", 900.0, sr, 1.0) * np.exp(-t / 0.02)
        return _norm(_fade(y, sr, 0.0008, 0.01))

    def fx_slap(self, ev, rng):
        """A sheet of paper landing flat on the table: a soft slap with a papery top."""
        sr = self.sr
        n, t = self._t(0.35)
        f = 150.0 * np.exp(-t / 0.03) + 70.0
        thump = np.sin(2 * np.pi * np.cumsum(f) / sr) * env_perc(n, sr, 0.05, 0.001)
        slap = bw(rng.standard_normal(n), "band", (500.0, 3500.0), sr) * np.exp(-t / 0.018)
        air = bw(rng.standard_normal(n), "band", (3000.0, 9000.0), sr) * np.exp(-t / 0.035)
        return _norm(_fade(0.8 * _norm(thump) + _norm(slap) + 0.3 * _norm(air), sr, 0.0005, 0.02))

    def fx_type(self, ev, rng):
        """OSD typing blip."""
        sr = self.sr
        n, t = self._t(0.05)
        y = bw(osc_square(rng.uniform(1700, 2100), n, sr), "low", 5000.0, sr) * np.exp(-t / 0.01)
        y += 0.4 * bw(rng.standard_normal(n), "high", 4000.0, sr) * np.exp(-t / 0.0015)
        return _norm(_fade(y, sr, 0.0005, 0.005))

    def fx_pop(self, ev, rng):
        """Bubble pop: a fast upward sine chirp."""
        sr = self.sr
        f0 = 480.0 * 2 ** ((float(ev.get("pitch", 0)) + rng.normal(0, 0.5)) / 12)
        n, t = self._t(0.12)
        f = f0 * (1 + 2.0 * (1 - np.exp(-t / 0.012)))
        y = osc_sine(f, n, sr) * env_perc(n, sr, 0.03, 0.0008)
        y += 0.2 * bw(rng.standard_normal(n), "high", 3000.0, sr) * np.exp(-t / 0.002)
        return _norm(_fade(y, sr, 0.0, 0.01))


# ================================================================================ arrangement
MOODS = ("intro", "rise", "groove_light", "groove", "breakdown", "halftime", "feature", "end")
DRIVE = ("groove", "feature")
SLOW = ("intro", "breakdown", "halftime", "end")          # chords change every 2 bars
BUSES = ("kick", "back", "hats", "perc", "bass", "pad", "keys", "arp", "lead", "lead2", "fx", "tex")
SENDS = {"kick": (0.04, 0.0, 0.0), "back": (0.3, 0.12, 0.0), "hats": (0.08, 0.0, 0.0),   # room, hall, delay
         "perc": (0.15, 0.05, 0.0), "pad": (0.0, 0.35, 0.0), "keys": (0.15, 0.2, 0.18),
         "arp": (0.1, 0.3, 0.3), "lead": (0.1, 0.22, 0.22), "lead2": (0.1, 0.3, 0.25),
         "fx": (0.0, 0.3, 0.0), "tex": (0.0, 0.3, 0.0)}
HALL = {"intro": 1.3, "rise": 1.0, "groove_light": 0.9, "groove": 0.8, "breakdown": 1.6,
        "halftime": 2.0, "feature": 0.85, "end": 2.4}                   # hall send per mood
BRIGHT = {"intro": (550.0, 1900.0), "rise": (900.0, 8000.0), "groove_light": (3500.0, 3500.0),
          "groove": (9000.0, 9000.0), "breakdown": (800.0, 2600.0), "halftime": (2800.0, 2800.0),
          "feature": (13000.0, 13000.0), "end": (5000.0, 500.0)}    # pad/arp low-pass (start, end) Hz
BASS_CUT = {"intro": (260.0, 260.0), "rise": (320.0, 4000.0), "breakdown": (500.0, 900.0),
            "end": (2500.0, 300.0)}
PAD_VEL = {"intro": 1.0, "rise": 0.9, "groove_light": 0.6, "groove": 0.7, "breakdown": 1.0,
           "halftime": 1.0, "feature": 0.75, "end": 1.0}
CRASH_VEL = {"groove": 1.0, "feature": 1.0, "halftime": 0.95, "groove_light": 0.75, "rise": 0.6,
             "breakdown": 0.55, "end": 1.0, "intro": 0.5}
HATS = {"hat": ("hats", "hat", {}), "hat_open": ("hats", "hat", {"decay": 0.2}),
        "tick": ("hats", "tick", {}), "shaker": ("perc", "shaker", {})}
HAT_PAN = {"hat": 0.25, "hat_open": 0.3, "tick": -0.3, "shaker": -0.35}

# one chord per bar (per 2 bars in SLOW moods): (root offset from the key, chord intervals)
PROG = {
    "brand": {"major": [(0, (0, 4, 7, 14)), (9, (0, 3, 7, 10)), (5, (0, 4, 7, 11)), (7, (0, 4, 7))],
              "minor": [(0, (0, 3, 7, 10)), (8, (0, 4, 7, 11)), (3, (0, 4, 7)), (10, (0, 4, 7))]},
    "scan": {"minor": [(0, (0, 3, 7)), (8, (0, 4, 7)), (1, (0, 4, 7)), (7, (0, 3, 7))],   # i bVI bII v
             "major": [(0, (0, 4, 7)), (8, (0, 4, 7)), (5, (0, 3, 7)), (0, (0, 4, 7))]},
    "tape": {"minor": [(0, (0, 3, 7)), (8, (0, 4, 7)), (3, (0, 4, 7)), (10, (0, 4, 7))],
             "major": [(0, (0, 4, 7)), (9, (0, 3, 7)), (5, (0, 4, 7)), (7, (0, 4, 7))]},
    "playful": {"major": [(0, (0, 4, 7)), (9, (0, 3, 7)), (2, (0, 3, 7)), (7, (0, 4, 7, 10))],
                "minor": [(0, (0, 3, 7)), (5, (0, 3, 7)), (10, (0, 4, 7)), (3, (0, 4, 7))]},
}


def _eighths(fn):
    return tuple(fn(k) for k in range(8))


# Style profiles. hats: {mood: ((name, steps "16" | "8" | (step, ...), vels cycled), ...)};
# bass_pat: {kind: ((step, len16, interval, vel), ...)}; keys: (inst, low note, {mood: steps}, kw);
# arp: (inst, centre note, chord-tone pattern, {mood: (every n 16ths, vel)}, kw);
# lead/lead2: (inst, centre note, {mood: vel}, kw); hooks: 2-bar rhythms ((pos16, len16), ...);
# mix: bus loudness in LU relative to the music bed.
STYLES = {
    "brand": dict(
        key=(53, "major"), swing=0.0, pump=4.0, rt=(0.8, 2.2), delay=0.75, bright=1.0, booms=False,
        kick=dict(f_hi=175.0, f_lo=56.0, sweep=0.028, decay=0.19, click=0.55, drive=2.4),
        back=(("clap", 1.0, {}), ("snare", 0.3, {})), light_back=(), fill=("clap", None),
        hats={"groove": (("hat_open", (2, 6, 10, 14), (0.75,)), ("hat", (0, 4, 8, 12), (0.35,)),
                         ("shaker", "16", (0.9, 0.45, 0.7, 0.45))),
              "groove_light": (("hat", (2, 6, 10, 14), (0.8,)), ("shaker", "8", (0.7, 0.45))),
              "rise": (("hat", (2, 6, 10, 14), (0.7,)),),
              "halftime": (("hat", "8", (0.7, 0.4)), ("shaker", "16", (0.5, 0.3)))},
        bass="bass_pluck", break_bass=False,
        bass_pat={"drive": ((2, 2, 0, 1.0), (6, 2, 0, 1.0), (10, 2, 0, 1.0), (14, 1, 12, 0.8),
                            (15, 1, 0, 0.7)),
                  "light": ((2, 2, 0, 0.9), (6, 2, 0, 0.9), (10, 2, 0, 0.9), (14, 2, 0, 0.9)),
                  "half": ((0, 6, 0, 1.0), (8, 4, 0, 0.9), (12, 2, 7, 0.8))},
        pad=("pad", dict(detune=10.0, bright=4200.0)), pad_lo=55,
        keys=("pluck", 60, {"groove": (2, 6, 10, 14), "feature": (2, 6, 10, 14),
                            "groove_light": (6, 14), "halftime": (0, 8)}, dict(decay=0.16)),
        strum=False,
        arp=("pluck", 72, (0, 1, 2, 3, 2, 1, 2, 3),
             {"breakdown": (2, 0.7), "rise": (2, 0.5), "feature": (1, 0.45)}, dict(decay=0.12)),
        lead=("pluck", 76, {"groove": 1.0, "feature": 1.0, "groove_light": 0.6},
              dict(decay=0.3, bright=8000.0)),
        lead2=None,
        hooks=(((0, 2), (3, 2), (6, 2), (8, 2), (11, 2), (14, 2), (16, 2), (19, 2), (22, 4), (28, 2)),
               ((0, 3), (3, 3), (6, 2), (10, 2), (12, 2), (16, 3), (19, 3), (22, 2), (26, 4))),
        tex=1.0, tape=False,
        mix=dict(kick=-5, back=-7, hats=-14, perc=-15, bass=-5, pad=-12, keys=-8, arp=-10, lead=-6,
                 fx=-10, tex=-22)),
    "scan": dict(
        key=(50, "minor"), swing=0.0, pump=2.0, rt=(1.0, 3.6), delay=0.75, bright=0.7, booms=True,
        kick=dict(f_hi=140.0, f_lo=50.0, sweep=0.04, decay=0.26, click=0.35, drive=2.0),
        back=(("snare", 1.0, dict(tone=160.0, decay=0.22, bright=6000.0, body=0.7)),
              ("clap", 0.35, {})), light_back=(), fill=("snare", None),
        hats={"groove": (("tick", "16", (1.0, 0.45, 0.7, 0.45)), ("hat", (2, 6, 10, 14), (0.4,))),
              "groove_light": (("tick", "8", (0.8, 0.5)),),
              "rise": (("tick", "8", (0.6, 0.4)),),
              "breakdown": (("tick", "16", (0.35, 0.15, 0.25, 0.15)),),
              "halftime": (("tick", "16", (0.6, 0.25, 0.4, 0.25)),)},
        bass="bass_sub", break_bass=True,
        bass_pat={"drive": tuple((k, 1, (0, 0, 12, 0, 0, 7, 0, 12)[k % 8], (1.0, 0.6, 0.8, 0.6)[k % 4])
                                 for k in range(16)),
                  "light": tuple((k, 1, 0, (1.0, 0.55, 0.75, 0.55)[k % 4]) for k in range(16)),
                  "half": ((0, 8, 0, 1.0), (8, 8, 0, 0.9)),
                  "break": tuple((2 * k, 1, 0, 0.45) for k in range(8))},
        pad=("pad", dict(detune=12.0, bright=2600.0, attack=0.6, release=1.6, sub=0.15)), pad_lo=50,
        keys=("bell", 67, {"halftime": (0,)}, dict(decay=1.2)), strum=False,
        arp=("bell", 74, (0, 2, 1, 3, 2, 4, 3, 1),
             {"intro": (4, 0.5), "groove": (2, 0.7), "feature": (2, 0.8), "breakdown": (1, 0.6),
              "rise": (2, 0.5), "groove_light": (4, 0.6)}, dict(decay=0.35, index=2.5)),
        lead=("bell", 79, {"groove": 0.8, "feature": 1.0}, dict(decay=1.0, ratio=1.4, index=2.0)),
        lead2=None,
        hooks=(((0, 4), (6, 2), (8, 6), (16, 4), (22, 2), (24, 8)),
               ((0, 3), (3, 3), (6, 4), (12, 4), (16, 3), (19, 3), (22, 10))),
        tex=1.0, tape=False,
        mix=dict(kick=-5, back=-7, hats=-14, perc=-16, bass=-4, pad=-7, keys=-10, arp=-9, lead=-8,
                 fx=-8, tex=-16)),
    "tape": dict(
        key=(45, "minor"), swing=0.0, pump=3.0, rt=(0.9, 2.8), delay=0.75, bright=0.75, booms=False,
        kick=dict(f_hi=150.0, f_lo=54.0, sweep=0.03, decay=0.2, click=0.4, drive=1.8),
        back=(("gated", 1.0, {}),), light_back=(), fill=("tom", (52, 48, 45, 40)),
        hats={"groove": (("hat", "16", (0.8, 0.35, 0.6, 0.35)), ("hat_open", (14,), (0.6,))),
              "groove_light": (("hat", "8", (0.8, 0.5)),),
              "rise": (("hat", "8", (0.6, 0.4)),),
              "halftime": (("hat", "8", (0.7, 0.4)),)},
        bass="bass_octave", break_bass=False,
        bass_pat={"drive": _eighths(lambda k: (2 * k, 2, 12 * (k % 2), 0.85 if k % 2 else 1.0)),
                  "light": _eighths(lambda k: (2 * k, 2, 12 * (k % 2), 0.85)),
                  "half": ((0, 8, 0, 1.0), (8, 6, 0, 0.9), (14, 2, 12, 0.8))},
        pad=("pad", dict(detune=16.0, bright=3000.0, attack=0.4, release=1.2)), pad_lo=52,
        keys=None, strum=False,
        arp=("sqarp", 69, (0, 1, 2, 3, 4, 3, 2, 1),
             {"intro": (2, 0.35), "rise": (1, 0.5), "groove_light": (1, 0.55), "groove": (1, 0.75),
              "feature": (1, 0.85), "breakdown": (1, 0.7), "halftime": (2, 0.5)}, {}),
        lead=("saw_lead", 74, {"groove": 1.0, "feature": 1.0}, {}),
        lead2=None,
        hooks=(((0, 6), (6, 2), (8, 4), (12, 4), (16, 6), (22, 2), (24, 8)),
               ((0, 3), (3, 3), (6, 2), (8, 8), (16, 3), (19, 3), (22, 2), (24, 8))),
        tex=0.6, tape=True,
        mix=dict(kick=-5, back=-5, hats=-14, perc=-16, bass=-5, pad=-7, keys=-10, arp=-9, lead=-6,
                 fx=-10, tex=-20)),
    "playful": dict(
        key=(55, "major"), swing=0.2, pump=1.5, rt=(0.6, 1.8), delay=0.5, bright=0.9, booms=False,
        kick=dict(f_hi=130.0, f_lo=62.0, sweep=0.02, decay=0.13, click=0.3, drive=1.4),
        back=(("clap", 0.9, {}), ("fsnap", 0.6, {})), light_back=(("fsnap", 0.8, {}),),
        fill=("clap", None),
        hats={"groove": (("shaker", "16", (0.8, 0.4, 0.6, 0.4)), ("hat", (2, 6, 10, 14), (0.55,))),
              "groove_light": (("shaker", "8", (0.7, 0.45)),),
              "rise": (("shaker", "16", (0.6, 0.3, 0.45, 0.3)),),
              "halftime": (("shaker", "8", (0.6, 0.35)),)},
        bass="bass_bouncy", break_bass=False,
        bass_pat={"drive": ((0, 1, 0, 1.0), (3, 1, 12, 0.7), (4, 1, 7, 0.9), (6, 1, 0, 0.75),
                            (8, 1, 0, 1.0), (10, 1, 12, 0.7), (12, 1, 7, 0.9), (14, 1, 7, 0.75)),
                  "light": ((0, 1, 0, 1.0), (4, 1, 7, 0.85), (8, 1, 0, 1.0), (12, 1, 7, 0.85)),
                  "half": ((0, 2, 0, 1.0), (8, 2, 7, 0.9), (11, 1, 12, 0.7))},
        pad=("soft_pad", {}), pad_lo=55,
        keys=("ks", 57, {"groove": (2, 6, 10, 14), "feature": (2, 6, 10, 14),
                         "groove_light": (6, 14), "halftime": (0, 8)}, dict(t60=0.6)),
        strum=True,
        arp=("marimba", 67, (0, 1, 2, 1),
             {"intro": (4, 0.6), "breakdown": (2, 0.8), "rise": (2, 0.6), "halftime": (4, 0.7)}, {}),
        lead=("marimba", 74, {"groove": 1.0, "feature": 1.0, "groove_light": 0.75}, {}),
        lead2=("whistle", 81, {"groove": 0.8, "feature": 1.0}, {}),
        hooks=(((0, 1), (2, 1), (4, 2), (6, 1), (8, 1), (10, 2), (12, 2), (16, 1), (18, 1), (20, 2),
                (22, 1), (24, 4)),
               ((0, 2), (3, 1), (4, 2), (7, 1), (8, 2), (12, 1), (14, 1), (16, 2), (19, 1), (20, 2),
                (23, 1), (24, 4), (30, 1))),
        tex=0.5, tape=False,
        mix=dict(kick=-7, back=-8, hats=-15, perc=-12, bass=-6, pad=-14, keys=-9, arp=-8, lead=-5,
                 lead2=-9, fx=-11, tex=-24)),
}


def _vel(steps, vels, step):
    i = step if steps == "16" else step // 2 if steps == "8" else steps.index(step)
    return vels[i % len(vels)]


def _hits(steps, step) -> bool:
    return steps == "16" or (steps == "8" and step % 2 == 0) or (
        isinstance(steps, tuple) and step in steps)


class Arranger:
    """Writes the music bed: one pass per section (drums, bass, harmony, top lines, texture, the
    cut into it and the approach to the next), into per-instrument buses, then `mix()`."""

    def __init__(self, cues: dict, sr: int):
        self.sr = sr
        self.fps = float(cues["fps"])
        self.frames = int(cues["frames"])
        self.bf = float(cues.get("beat_frames") or 15)
        self.spb = self.bf / self.fps                       # seconds per beat
        self.n = int(round(self.frames / self.fps * sr))
        style = str(cues.get("style", "brand"))
        self.style = style if style in STYLES else "brand"
        self.P = P = STYLES[self.style]
        self.seed = int(cues.get("seed", 0)) % (2 ** 63)
        key = cues.get("key") or {}
        root = int(key.get("root", P["key"][0]))
        mode = key.get("mode", P["key"][1])
        self.prog = PROG[self.style][mode if mode in ("major", "minor") else P["key"][1]]
        self.root_pc = root % 12
        self.bass_lo = 33 + (root - 33) % 12                # key root, 33..44 (A1..G#2)
        self.V = Voices(sr, self.seed)
        self.rng = np.random.default_rng([self.seed, 2])    # humanising, in arrangement order
        # buses are made when first played into; float32 (24-bit mantissa) halves their memory
        self.bus = collections.defaultdict(lambda: np.zeros((self.n, 2), np.float32))
        self.kicks: list[int] = []
        self.levels: dict[str, float] = {}                  # bus loudness before balancing
        self.secs = self._sections(cues.get("sections"))
        self.hook = self._make_hook(np.random.default_rng([self.seed, 1]))

    # ------------------------------------------------------------ time, harmony helpers
    def _sections(self, secs):
        if not secs:
            secs = [{"name": "all", "start": 0, "end": self.frames, "mood": "groove"}]
        out = []
        for s in sorted(secs, key=lambda s: float(s["start"])):
            f0, f1 = max(0.0, float(s["start"])), min(float(self.frames), float(s["end"]))
            if f1 > f0:
                mood = s.get("mood", "groove")
                out.append(dict(name=s.get("name", ""), mood=mood if mood in MOODS else "groove",
                                f0=f0, f1=f1, b0=f0 / self.bf, b1=f1 / self.bf))
        return out

    def b2s(self, beat: float) -> int:
        return int(round(beat * self.spb * self.sr))

    def f2s(self, frame: float) -> int:
        return int(round(frame / self.fps * self.sr))

    def steps(self, sec, every: int = 1):
        """(bar, step, beat) for every `every`-th 16th of the section (bars count from its start)."""
        for k in range(0, int(np.ceil((sec["b1"] - sec["b0"]) * 4 - 1e-6)), every):
            bar, step = divmod(k, 16)
            yield bar, step, sec["b0"] + k / 4

    def swing(self, step: int) -> float:
        return self.P["swing"] * 0.25 if step % 2 else 0.0

    def chord(self, sec, bar: int):
        return self.prog[(bar // 2 if sec["mood"] in SLOW else bar) % len(self.prog)]

    def bass_note(self, chord, interval: int) -> int:
        m = self.bass_lo + chord[0] % 12
        return (m - 12 if m > 44 else m) + interval

    def voicing(self, chord, lo: int) -> list[int]:
        return sorted({lo + (self.root_pc + chord[0] + iv - lo) % 12 for iv in chord[1]})

    def tone(self, chord, center: int, idx: int) -> int:
        """The idx-th chord tone counting up from `center` (negative: below)."""
        pcs = {(self.root_pc + chord[0] + iv) % 12 for iv in chord[1]}
        notes = np.array([m for m in range(24, 110) if m % 12 in pcs])
        i0 = int(np.searchsorted(notes, center))
        return int(notes[int(np.clip(i0 + idx, 0, len(notes) - 1))])

    def _make_hook(self, rng):
        """A 2-bar call and its answer, as chord-tone indices over one of the style's rhythms."""
        rhythm = self.P["hooks"][int(rng.integers(len(self.P["hooks"])))]

        def walk(line, n):              # mostly stepwise, reflecting inside ~an octave (-1..3)
            while len(line) < n:
                cur = line[-1]
                d = int(rng.choice([-2, -1, -1, -1, 0, 1, 1, 1, 2]))
                nxt = cur + d if -1 <= cur + d <= 3 else cur - d
                if len(line) >= 2 and line[-2] == cur == nxt:
                    nxt = cur + (1 if cur < 3 else -1)          # no note three times running
                line.append(nxt)
            return line

        idx = walk([int(rng.integers(0, 3))], len(rhythm))
        answer = walk(idx[:2 * len(idx) // 3], len(rhythm))
        answer[-1] = 0                                          # the answer comes home
        return rhythm, idx, answer

    def play(self, bus, inst, beat, dur_beats=0.25, midi=None, vel=1.0, pan=0.0, var=0,
             shift=0.0, end=False, **kw):
        """Render one voice into a bus at `beat` (+shift seconds); end=True: it ends there."""
        if vel <= 0.0:
            return
        buf = self.V.get(inst, midi, dur_beats * self.spb, var, **kw)
        at = self.b2s(beat) + int(round(shift * self.sr)) - (len(buf) if end else 0)
        add(self.bus[bus], buf, at, vel if buf.ndim == 2 else vel * pan_gains(pan))
        if inst == "kick":
            self.kicks.append(at)

    def _chord(self, bus, inst, chord, beat, dur, vel, lo, kw, strum=False):
        notes = self.voicing(chord, lo)
        k = len(notes)
        for j, m in enumerate(notes):
            self.play(bus, inst, beat, dur, midi=m, vel=vel / np.sqrt(k),
                      pan=(j / max(1, k - 1) - 0.5) * 0.7, shift=0.011 * j if strum else 0.0, **kw)

    # ------------------------------------------------------------ layers
    def arrange(self):
        for i, sec in enumerate(self.secs):
            nxt = self.secs[i + 1]["mood"] if i + 1 < len(self.secs) else None
            if i > 0:
                self._cut(sec)
            self._drums(sec, nxt)
            self._bass(sec)
            self._harmony(sec)
            self._top(sec)
            self._texture(sec)
            if nxt is not None:
                self._approach(sec, nxt)

    def _cut(self, sec):
        """Every section start is a video cut: crash, and a boom/kick where it should hit hard."""
        mood, b, P = sec["mood"], sec["b0"], self.P
        self.play("fx", "crash", b, vel=CRASH_VEL[mood])
        if mood in ("breakdown", "halftime", "end", "feature") or (P["booms"] and mood != "rise"):
            self.play("fx", "boom", b, vel=0.6 if mood == "breakdown" else 0.85)
        if mood == "end":
            self.play("kick", "kick", b, vel=1.0, **P["kick"])

    def _approach(self, sec, nxt):
        """The last beats before a cut: a riser into bigger sections, else a reversed cymbal."""
        mood, b0, b1 = sec["mood"], sec["b0"], sec["b1"]
        if (nxt in DRIVE and mood not in DRIVE) or (nxt == "groove_light" and mood in ("intro", "rise")):
            L = min(8.0 if mood == "rise" else 4.0, b1 - b0)
            self.play("fx", "uplift", b1, L, vel=0.8, end=True)
        elif nxt != mood:
            self.play("fx", "rev_crash", b1, min(1.5, b1 - b0), vel=0.45, end=True)

    def _drums(self, sec, nxt):
        mood, P = sec["mood"], self.P
        if mood in ("intro", "end"):
            return
        b0, b1 = sec["b0"], sec["b1"]
        drop = nxt is not None and nxt != mood and (nxt in DRIVE or nxt in ("breakdown", "end"))
        fill = nxt is not None and mood in ("groove", "feature", "groove_light", "halftime", "rise")
        fill_from = b1 - 1.0 if fill and b1 - b0 >= 2 else b1 + 1
        four = (0, 4, 8, 12)
        kicks = {"rise": four, "groove_light": four, "groove": four, "feature": four,
                 "halftime": (0, 11)}.get(mood, ())
        backs = {"groove": (4, 12), "feature": (4, 12), "halftime": (8,)}.get(mood, ())
        lights = (4, 12) if mood == "groove_light" else ()
        hats = P["hats"].get("groove" if mood == "feature" else mood, ())
        nbars = int(np.ceil((b1 - b0) / 4 - 1e-9))
        for bar, step, beat in self.steps(sec):
            t = beat + self.swing(step)
            in_fill = beat >= fill_from - 1e-9
            if step in kicks and not (drop and beat >= b1 - 1 - 1e-9):
                v = 0.7 + 0.3 * (beat - b0) / max(1.0, b1 - b0) if mood == "rise" else 1.0
                self.play("kick", "kick", t, vel=0.6 if step == 11 else v, **P["kick"])
            if step in backs and not in_fill:
                for inst, v, kw in P["back"]:
                    self.play("back", inst, t, vel=v, **kw)
            if step in lights and not in_fill:
                for inst, v, kw in P["light_back"]:
                    self.play("perc", inst, t, vel=v, **kw)
            if not (mood == "rise" and beat < (b0 + b1) / 2) and not (in_fill and mood != "rise"):
                for name, st, vels in hats:
                    if _hits(st, step):
                        bus, inst, kw = HATS[name]
                        self.play(bus, inst, t, vel=_vel(st, vels, step) * self.rng.uniform(0.88, 1.05),
                                  pan=HAT_PAN[name], var=int(self.rng.integers(4)), **kw)
            if mood in DRIVE and bar % 4 == 3 and bar < nbars - 1 and step in (14, 15):
                if step == 14:                               # phrase-end lift
                    self.play("hats", "hat", t, vel=0.7, pan=0.3, decay=0.2)
                else:
                    inst, v, kw = P["back"][0]
                    self.play("back", inst, t, vel=0.35 * v, **kw)
            if in_fill:                                      # roll / tom fill into the cut
                inst, notes = P["fill"]
                k = int(round((beat - fill_from) * 4))
                v = 0.45 + 0.17 * k
                if notes:
                    self.play("back", inst, t, midi=notes[k % len(notes)], vel=v, pan=0.35 - 0.23 * k)
                else:
                    self.play("back", inst, t, vel=v, **(P["back"][0][2] if P["back"][0][0] == inst else {}))

    def _bass(self, sec):
        mood, P = sec["mood"], self.P
        b0, b1 = sec["b0"], sec["b1"]
        if mood == "end":
            self.play("bass", P["bass"], b0, 2.0, midi=self.bass_note(self.prog[0], 0))
            return
        kind = {"groove": "drive", "feature": "drive", "groove_light": "light", "rise": "light",
                "halftime": "half"}.get(mood)
        if mood == "breakdown" and P["break_bass"]:
            kind = "break"
        if kind is None:
            return
        for bar in range(int(np.ceil((b1 - b0) / 4 - 1e-9))):
            chord = self.chord(sec, bar)
            for step, ln, iv, v in P["bass_pat"][kind]:
                beat = b0 + 4 * bar + step / 4
                if beat >= b1 - 1e-9:
                    continue
                if mood == "rise":
                    v *= 0.6 + 0.4 * (beat - b0) / max(1.0, b1 - b0)
                self.play("bass", P["bass"], beat + self.swing(step), min(ln / 4, b1 - beat) * 0.85,
                          midi=self.bass_note(chord, iv), vel=v)

    def _harmony(self, sec):
        mood, P = sec["mood"], self.P
        b0, b1 = sec["b0"], sec["b1"]
        inst, kw = P["pad"]
        vel = PAD_VEL[mood]
        keys = P.get("keys")
        if mood == "end":                                    # final chord, left to ring out
            self._chord("pad", inst, self.prog[0], b0, b1 - b0, vel, P["pad_lo"],
                        dict(kw, attack=0.02, release=2.0))
            if keys:
                self._chord("keys", keys[0], self.prog[0], b0, 2.0, 1.0, keys[1], keys[3], P["strum"])
            return
        span = 8.0 if mood in SLOW else 4.0
        c, bar = b0, 0
        while c < b1 - 1e-9:
            kw2 = dict(kw)
            if mood == "intro":
                kw2["attack"] = float(min(2.0, 0.5 * (b1 - b0) * self.spb))
            if c + span >= b1 - 1e-9:
                kw2["release"] = 0.35                        # clear the way for the cut
            self._chord("pad", inst, self.chord(sec, bar), c, min(span, b1 - c), vel, P["pad_lo"], kw2)
            c += span
            bar += int(span // 4)
        if mood in ("intro", "breakdown"):                   # drone: root and fifth
            for iv, v in ((12, 0.5), (19, 0.3)):
                self.play("pad", inst, b0, b1 - b0, midi=self.bass_note(self.prog[0], iv),
                          vel=v * vel, **dict(kw, attack=float(min(2.0, 0.4 * (b1 - b0) * self.spb)),
                                              release=0.5))
        if keys and mood in keys[2]:
            kinst, lo, moods, kkw = keys
            for bar, step, beat in self.steps(sec):
                if step in moods[mood]:
                    ln = 8.0 if mood == "halftime" else 0.4
                    self._chord("keys", kinst, self.chord(sec, bar), beat + self.swing(step),
                                min(ln, b1 - beat), 1.0 if step % 4 == 2 else 0.85, lo, kkw, P["strum"])

    def _top(self, sec):
        mood, P = sec["mood"], self.P
        b0, b1 = sec["b0"], sec["b1"]
        arp = P.get("arp")
        if arp and mood in arp[3]:
            inst, center, pattern, moods, kw = arp
            every, vel = moods[mood]
            for k, (bar, step, beat) in enumerate(self.steps(sec, every)):
                acc = 1.0 if step % 4 == 0 else 0.8
                if mood == "rise":
                    acc *= 0.5 + 0.5 * (beat - b0) / max(1.0, b1 - b0)
                self.play("arp", inst, beat + self.swing(step), every * 0.25 * 0.9,
                          midi=self.tone(self.chord(sec, bar), center, pattern[k % len(pattern)]),
                          vel=vel * acc, pan=0.35 if k % 2 else -0.35, **kw)
        for bus in ("lead", "lead2"):
            spec = P.get(bus)
            if spec and mood in spec[2]:
                self._hook(sec, bus, *spec)

    def _hook(self, sec, bus, inst, center, moods, kw):
        mood = sec["mood"]
        b0, b1 = sec["b0"], sec["b1"]
        rhythm, call, answer = self.hook
        light = mood == "groove_light"
        up = 12 if mood == "feature" and bus == "lead" else 0
        units = int(np.ceil((b1 - b0) / 8 - 1e-9))
        for u in range(units):
            if bus == "lead2" and mood == "groove" and u < units // 2:
                continue                                     # the whistle joins halfway
            for k, ((pos, ln), idx) in enumerate(zip(rhythm, call if u % 2 == 0 else answer)):
                if (light and k % 2) or (bus == "lead2" and ln < 2):
                    continue
                beat = b0 + 8 * u + pos / 4
                if beat >= b1 - 1e-9:
                    break
                if bus == "lead2":                           # legato to the next long note
                    ln = next((p for p, q in rhythm[k + 1:] if q >= 2), 32) - pos
                m = self.tone(self.chord(sec, 2 * u + pos // 16), center + up, idx)
                self.play(bus, inst, beat + self.swing(pos), min(ln / 4 * 0.92, b1 - beat), midi=m,
                          vel=moods[mood] * (1.0 if pos % 4 == 0 else 0.85),
                          pan=0.1 if bus == "lead" else -0.15, **kw)

    def _texture(self, sec):
        mood, P, sr = sec["mood"], self.P, self.sr
        if P["booms"] and mood in ("intro", "breakdown"):
            for b in np.arange(sec["b0"], sec["b1"] - 1e-9, 8.0):
                if b > sec["b0"] or sec["f0"] == 0:
                    self.play("fx", "boom", float(b), vel=0.55)
        if mood not in ("intro", "breakdown") and not (mood == "halftime" and P["booms"]):
            return
        s0, s1 = self.f2s(sec["f0"]), self.f2s(sec["f1"])
        n = s1 - s0 + int(0.5 * sr)
        rng = self.V.rng("tex", s0)
        t = np.arange(n) / sr
        fc = 1200.0 * 2.0 ** (1.3 * np.sin(2 * np.pi * 0.21 * t + rng.uniform(0, 6.3)))
        y = tv_filter(pink(rng, (n, 2)), "bp", fc, sr, q=1.4)
        add(self.bus["tex"], _fade(y, sr, min(1.0, (s1 - s0) / sr / 3), 0.5), s0, P["tex"])

    # ------------------------------------------------------------ mix
    def _curve(self, table, default, scale=1.0, smooth=0.03):
        """Per-sample automation from per-mood (start, end) values, log-interpolated, smoothed."""
        c = np.full(self.n, np.log(default[0] * scale))
        for sec in self.secs:
            s0, s1 = self.f2s(sec["f0"]), min(self.n, self.f2s(sec["f1"]))
            a, b = table.get(sec["mood"], default)
            c[s0:s1] = np.log(a * scale) + np.log(b / a) * np.linspace(0, 1, s1 - s0, endpoint=False)
        return np.exp(uniform_filter1d(c, int(smooth * self.sr) | 1, mode="nearest"))

    def _pump(self, depth_db: float) -> np.ndarray:
        """Sidechain gain from the kicks: dips depth_db, recovers within the beat."""
        L = int(min(0.95 * self.spb, 0.6) * self.sr)
        t = np.arange(L) / self.sr
        shape = np.where(t < 0.003, t / 0.003, np.exp(-(t - 0.003) / (0.12 * self.spb)))
        env = np.zeros(self.n)
        for s in sorted(set(self.kicks)):
            m = min(L, self.n - max(s, 0))
            if m > 0 and s >= 0:
                env[s:s + m] = np.maximum(env[s:s + m], shape[:m])
        return db2amp(-depth_db * env)

    def end_fade(self, whole_mix: bool = False) -> np.ndarray:
        """Music: fades from 30 % into an 'end' section to silence 0.3 s before the last frame.
        Whole mix (SFX too): after an 'end', a 0.25 s fade to silence 0.3 s before the last
        frame; otherwise a 20 ms fade-out so the file doesn't end on a click."""
        g = np.ones(self.n)
        sr, n = self.sr, self.n
        is_end = bool(self.secs) and self.secs[-1]["mood"] == "end"
        if not is_end:
            m = min(n, int(0.02 * sr))
            g[n - m:] = _ramp(m)[::-1]
            return g
        if whole_mix:
            b = max(0, n - int(0.3 * sr))
            a = max(0, b - int(0.25 * sr))
            g[a:b] = _ramp(b - a)[::-1]
            g[b:] = 0.0
            return g
        s0 = self.f2s(self.secs[-1]["f0"])
        b = max(0, n - int(0.3 * sr))
        a = min(s0 + int(0.3 * (n - s0)), max(0, b - 1))
        g[a:b] = 0.5 + 0.5 * np.cos(np.pi * np.arange(b - a) / max(1, b - a))
        g[b:] = 0.0
        return g

    def mix(self) -> np.ndarray:
        """Bus processing (filters, chorus, pump), loudness auto-balance, sends, style master."""
        sr, P, B = self.sr, self.P, self.bus
        bright = self._curve(BRIGHT, (9000.0, 9000.0), P["bright"])
        if "pad" in B:
            B["pad"] = tv_filter(chorus(B["pad"], sr), "lp", bright, sr, q=0.8)
        if "arp" in B:
            B["arp"] = tv_filter(B["arp"], "lp", np.minimum(bright * 1.8, 0.45 * sr), sr, q=0.7)
        if "keys" in B:
            B["keys"] = tv_filter(B["keys"], "lp", np.minimum(bright * 2.5, 0.45 * sr), sr, q=0.7)
        if "bass" in B:
            mono = tv_filter(B["bass"].mean(axis=1), "lp", self._curve(BASS_CUT, (8000.0, 8000.0)),
                             sr, q=0.9)
            B["bass"] = np.stack([mono, mono], axis=1)
        pump = self._pump(P["pump"]) if P["pump"] and self.kicks else None
        hall = self._curve({m: (v, v) for m, v in HALL.items()}, (1.0, 1.0))
        music, send = np.zeros((self.n, 2)), [np.zeros((self.n, 2)) for _ in range(3)]
        for name in BUSES:                   # one bus at a time: pump, balance, sum, send
            x = B.pop(name, None)
            if x is None or not x.any():
                continue
            x = x.astype(float)
            if pump is not None and name in ("pad", "keys", "arp", "tex", "bass"):
                x *= (np.sqrt(pump) if name == "bass" else pump)[:, None]
            lv = measure_lufs(x, sr)
            if np.isfinite(lv):
                x *= db2amp(MUSIC_REF + P["mix"].get(name, -12.0) - lv)
            music += x
            for i, amt in enumerate(SENDS.get(name, (0.0, 0.0, 0.0))):
                if amt:
                    send[i] += amt * x
            self.levels[name] = lv
        room_rt, hall_rt = P["rt"]
        music += convolve(send[0], reverb_ir(sr, room_rt, 0.008, 0.55, seed=31))
        music += convolve(send[1] * hall[:, None], reverb_ir(sr, hall_rt, 0.025, 0.45, seed=37))
        music += pingpong(send[2], sr, P["delay"] * self.spb)
        del send
        if P["tape"]:                                        # VHS: wobble, warmth, hiss
            rng = self.V.rng("tape")
            music = bw(wow_flutter(music, sr, rng), "low", 11000.0, sr)
            hiss = bw(bw(pink(rng, (self.n, 2)), "high", 1500.0, sr), "low", 12000.0, sr)
            music += hiss * db2amp(MUSIC_REF - 50.0)
        music = bw(bw(music, "high", 30.0, sr, 4), "low", 18000.0, sr) * self.end_fade()[:, None]
        lv = measure_lufs(music, sr)
        return music * db2amp(MUSIC_REF - lv) if np.isfinite(lv) else music

    def render(self) -> np.ndarray:
        self.arrange()
        return self.mix()


# ================================================================================ render
def render_stems(cues: dict, sr: int = 48000) -> dict:
    """Unmastered stems: {'music' (ducked under big SFX, at MUSIC_REF LUFS), 'sfx', 'duck_db',
    'arranger'}, each (n, 2) with n = round(frames / fps * sr)."""
    A = Arranger(cues, sr)
    music = A.render()
    sfx, duck = SFX(sr, A.fps, A.seed).render(cues.get("events") or [], A.n)
    return {"music": music * db2amp(-duck)[:, None], "sfx": sfx, "duck_db": duck, "arranger": A}


def render_audio(cues: dict, out_wav: Path, *, sr: int = 48000, lufs: float = -16.0) -> dict:
    """Synthesise and master the track; write a 24-bit PCM stereo WAV of exactly
    round(cues['frames'] / cues['fps'] * sr) samples. Returns {'lufs': float,
    'true_peak_db': float, 'seconds': float} measured on the written samples."""
    st = render_stems(cues, sr)
    A = st["arranger"]
    mix = (st["music"] + st["sfx"]) * A.end_fade(whole_mix=True)[:, None]
    y, _, _ = master(mix, sr, lufs)
    q = write_wav(Path(out_wav), y, sr, bits=24)
    return {"lufs": measure_lufs(q, sr), "true_peak_db": true_peak_db(q, sr), "seconds": A.n / sr}


# ================================================================================ demo
EXAMPLE_SECTIONS = [("open", 0, 84, "intro"), ("title", 84, 196, "rise"),
                    ("palette", 196, 308, "groove_light"), ("build", 308, 756, "groove"),
                    ("scan", 756, 924, "breakdown"), ("mechanism", 924, 1092, "halftime"),
                    ("colourways", 1092, 1260, "groove"), ("booklet", 1260, 1372, "groove_light"),
                    ("outro", 1372, 1456, "end")]


def example_cues(style: str = "playful", seconds: float | None = None, seed: int = 1234) -> dict:
    """The built-in cue sheet (48.5 s at 30 fps, 128.6 BPM), optionally stretched to `seconds`
    (section boundaries stay on beats); uses every SFX type."""
    fps, bf, base = 30, 14, 1456
    frames = base if seconds is None else int(round(seconds * fps))
    k = frames / base

    def at(f):                              # scaled frame, snapped to a beat
        return min(frames, int(round(f * k / bf)) * bf)

    sections = []
    for i, (name, a, b, mood) in enumerate(EXAMPLE_SECTIONS):
        sections.append({"name": name, "start": at(a), "end": frames if i == len(EXAMPLE_SECTIONS) - 1
                         else at(b), "mood": mood})
    S = {s["name"]: s for s in sections}
    rng = np.random.default_rng(seed)
    ev = [{"frame": 21.0 * k, "type": "snap"}, {"frame": S["title"]["start"], "type": "hit"},
          {"frame": S["title"]["start"] - 8, "type": "whoosh", "dur": 8}]
    ev += [{"frame": S["title"]["start"] + 14 + 3 * j, "type": "tick", "gain": 0.6} for j in range(14)]
    ev += [{"frame": S["palette"]["start"] + 6 + 14 * j, "type": "pop", "pitch": j} for j in range(5)]
    ev += [{"frame": S["build"]["start"] - 8, "type": "whoosh", "dur": 8}]
    f = S["build"]["start"] + 3.0
    while f < S["build"]["end"] - 14:
        ev.append({"frame": round(f, 2), "type": "click", "gain": float(rng.uniform(0.3, 0.6)),
                   "pitch": int(rng.integers(0, 12))})
        f += float(rng.uniform(3.0, 6.5))
    ev += [{"frame": S["build"]["end"] - 10, "type": "snap"},
           {"frame": S["scan"]["start"] - 30, "type": "riser", "dur": 30}]
    s0 = S["scan"]["start"]
    ev += [{"frame": s0 + 4, "type": "scan", "dur": 60}]
    ev += [{"frame": s0 + 10 + 3 * j, "type": "type"} for j in range(5)]
    ev += [{"frame": s0 + 34 + 10 * j, "type": "blip", "pitch": j} for j in range(5)]
    ev += [{"frame": s0 + 94, "type": "warn"}, {"frame": s0 + 114, "type": "blip", "pitch": 5},
           {"frame": s0 + 144, "type": "pass"}]
    m0 = S["mechanism"]["start"]
    ev += [{"frame": m0 + 6, "type": "motor", "dur": 60}, {"frame": m0 + 84, "type": "motor", "dur": 60}]
    c0 = S["colourways"]["start"]
    ev += [{"frame": c0, "type": "power", "dur": 36}, {"frame": c0 + 56, "type": "glitch", "dur": 6},
           {"frame": c0 + 112, "type": "glitch", "dur": 5}]
    ev += [{"frame": S["booklet"]["start"] + 8 + 20 * j, "type": "page"} for j in range(5)]
    o0 = S["outro"]["start"]
    ev += [{"frame": o0, "type": "hit", "gain": 0.8}, {"frame": o0 + 20, "type": "boing", "pitch": 3}]
    ev = [e for e in ev if 0 <= e["frame"] < frames]
    return {"fps": fps, "frames": frames, "beat_frames": bf, "style": style, "seed": seed,
            "sections": sections, "events": ev}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in STYLES:
        print(f"usage: python -m brickkit.video.audio {{{'|'.join(STYLES)}}} OUT.wav [seconds]")
        return 2
    cues = example_cues(argv[0], float(argv[2]) if len(argv) > 2 else None)
    t0 = time.time()
    info = render_audio(cues, Path(argv[1]))
    print(f"{argv[0]}: {info['seconds']:.2f} s -> {argv[1]}  {info['lufs']:.2f} LUFS, "
          f"{info['true_peak_db']:.2f} dBTP, rendered in {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
