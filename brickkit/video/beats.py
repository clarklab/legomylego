"""Beats of a piece of music, to cut a video on (numpy/scipy only).

    track(x, sr) -> {"bpm", "beats" (s), "downbeat" (index of the first bar's first beat),
                     "strength" (how clearly the onsets fall on the grid, 0..1)}

Onsets: half-wave rectified flux of a log-magnitude spectrogram pooled into log-spaced bands
(10.7 ms hops at 48 kHz), low-passed; bands, not bins, so a kick (a few low bins) counts as
much as a hi-hat (hundreds of high ones). Tempo: the envelope's autocorrelation peak in
`bpm_range`, weighted towards `prefer` (a known target tempo). Beats: dynamic programming over
the onset envelope (Ellis 2007): each beat takes the best predecessor about one period back,
penalised by how far the gap strays from the period in log terms, so the grid follows small
drifts without jumping to off-beats. Phase: dance music puts the kick on the beat and often an
open hat between, so the grid is moved half a period when the kick band's onsets sit there.
Bars: the phase (mod 4) whose beats 2 and 4 carry the most snare/clap energy (1.5-6 kHz); a
backbeat can't tell beat 1 from beat 3, so the earlier of the two wins."""
from __future__ import annotations

import numpy as np
from scipy import signal

NPERSEG = 2048


def onset_envelope(x: np.ndarray, sr: int, hop: int = 512, band=(30.0, 16000.0),
                   n_bands: int = 48) -> tuple[np.ndarray, float, float]:
    """(onset strength per hop, hops per second, time of the first value in s)."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    f, _, S = signal.stft(m, sr, nperseg=NPERSEG, noverlap=NPERSEG - hop, boundary=None, padded=False)
    P = np.abs(S)
    edges = np.geomspace(band[0], min(band[1], 0.49 * sr), n_bands + 1)
    lo = np.minimum(np.searchsorted(f, edges[:-1]), len(f) - 1)
    hi = np.maximum(np.searchsorted(f, edges[1:]), lo + 1)
    mag = np.log1p(1000.0 * np.stack([P[a:b].mean(axis=0) for a, b in zip(lo, hi)]))
    flux = np.maximum(np.diff(mag, axis=1), 0.0).mean(axis=0)
    flux = np.concatenate([[0.0], flux])
    env = signal.filtfilt(*signal.butter(2, 0.35), flux) if len(flux) > 12 else flux
    env = env - np.median(env)
    # value i is the change from frame i-1 to frame i; measured on clicks, the flux of an onset
    # peaks half a hop after the two windows' centres meet it
    return np.maximum(env, 0.0) / (env.std() + 1e-12), sr / hop, (NPERSEG / 2 + hop / 2) / sr


def tempo(env: np.ndarray, rate: float, bpm_range=(80.0, 180.0), prefer: float | None = None) -> float:
    ac = np.correlate(env - env.mean(), env - env.mean(), "full")[len(env) - 1:]
    lags = np.arange(len(ac)) / rate
    ok = (lags >= 60.0 / bpm_range[1]) & (lags <= 60.0 / bpm_range[0])
    w = ac.copy()
    if prefer:                                     # a gentle pull towards the asked-for tempo
        w = w * np.exp(-0.5 * (np.log2(60.0 / np.maximum(lags, 1e-6) / prefer) / 0.2) ** 2)
    k = int(np.argmax(np.where(ok, w, -np.inf)))
    # refine the peak by parabolic interpolation
    if 0 < k < len(ac) - 1:
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        k = k + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return 60.0 * rate / k


def _on(env: np.ndarray, idx: np.ndarray) -> float:
    """Mean onset strength at these (fractional) hops, allowing +-2 hops."""
    idx = np.round(idx).astype(int)
    idx = idx[(idx >= 2) & (idx < len(env) - 2)]
    if not len(idx):
        return 0.0
    return float(np.max(np.stack([env[idx + d] for d in range(-2, 3)]), axis=0).mean())


def track(x: np.ndarray, sr: int, prefer: float | None = None, tightness: float = 400.0) -> dict:
    env, rate, t0 = onset_envelope(x, sr)
    bpm = tempo(env, rate, prefer=prefer)
    period = 60.0 / bpm * rate
    n = len(env)
    score = env.copy()
    back = -np.ones(n, int)
    lo, hi = int(round(0.5 * period)), int(round(2.0 * period))
    for t in range(lo, n):
        tau = np.arange(max(0, t - hi), t - lo + 1)
        if not len(tau):
            continue
        pen = -tightness * np.log((t - tau) / period) ** 2
        cand = score[tau] + pen
        j = int(np.argmax(cand))
        if cand[j] > 0:
            score[t] += cand[j]
            back[t] = tau[j]
    # the last beat: the best score within the last period
    t = int(np.argmax(score[max(0, n - int(period)):])) + max(0, n - int(period))
    beats = []
    while t >= 0:
        beats.append(t)
        t = back[t]
    beats = np.array(beats[::-1], float)
    # a beat after the music stops scores as well as the last real one: drop the silent tail
    near = np.array([env[max(0, int(b) - 2):int(b) + 3].max() for b in beats])
    while len(beats) > 2 and near[len(beats) - 1] < 0.15 * np.median(near):
        beats = beats[:-1]
    # the kick is on the beat: half a period over if the kick band's onsets are there instead
    low, _, _ = onset_envelope(x, sr, band=(30.0, 160.0), n_bands=8)
    if _on(low, beats + period / 2) > 1.25 * _on(low, beats):
        beats = beats + period / 2
        beats = beats[beats < n]
    # beats can't start before the music does: prepend by the period while there's room
    while len(beats) and beats[0] - period >= 0 and env[int(beats[0] - period)] > 0.5:
        beats = np.concatenate([[beats[0] - period], beats])
    secs = beats / rate + t0
    # how clearly the onsets sit on the beats
    on = env[beats.astype(int)]
    strength = float(np.clip(on.mean() / (env.mean() * 3 + 1e-9), 0, 1))
    # bars: claps on 2 and 4
    m = x.mean(axis=1) if x.ndim == 2 else x
    hp = signal.sosfilt(signal.butter(4, (1500.0, 6000.0), "band", fs=sr, output="sos"), m)
    e = np.array([np.sqrt((hp[max(0, int(s * sr) - 480):int(s * sr) + 2400] ** 2).mean()) for s in secs])
    phase = 0
    if len(e) >= 8:
        best = None
        for p in range(4):
            idx = np.arange(len(e))
            on_back = e[(idx - p) % 4 % 2 == 1].mean()      # beats 2 and 4 of each bar
            off_back = e[(idx - p) % 4 % 2 == 0].mean()
            if best is None or on_back - off_back > best[0]:
                best = (on_back - off_back, p)
        phase = best[1]
    return {"bpm": float(bpm), "beats": secs.tolist(), "downbeat": int(phase), "strength": strength}
