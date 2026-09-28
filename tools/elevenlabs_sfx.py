"""Sound effects for a model's showreel, generated with ElevenLabs' sound-generation API.

    .venv/bin/python tools/elevenlabs_sfx.py SLUG             # make the files that are missing
    .venv/bin/python tools/elevenlabs_sfx.py SLUG --dry-run   # list what it would make
    .venv/bin/python tools/elevenlabs_sfx.py SLUG --analyse   # measure every file, rank them

Reads models/SLUG/audio/sfx.toml:

    [defaults]                  prompt_influence, model_id, output_format (optional)
    [[sfx]]                     name, prompt, seconds, variants (default 1), loop (default
                                false), prompt_influence (overrides the default)

and writes models/SLUG/audio/NAME_K.mp3 for K = 1..variants, with sfx_generated.json beside
them recording the prompt and settings that made each file. Files that exist are skipped, so a
rerun only fills gaps (delete a file to make it again); at most MAX_FILES files in all. The
files are meant to be committed: the video (brickkit/video/audio.py, [video.audio] in
model.toml) uses them without calling the API.

API: POST https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192 with a JSON
body {text, duration_seconds (0.5..30), prompt_influence (0..1), loop, model_id}; the response
is the audio file. mp3_44100_192 needs the Creator plan or above.

The API key comes from ELEVENLABS_API_KEY in the environment or ~/.config/brickkit/elevenlabs.env
(`ELEVENLABS_API_KEY=...`). It is only ever sent to the API in the request header: never
printed, logged or written anywhere.

--analyse decodes every file and prints, per sound, what matters for picking one without
listening: length against what was asked, loudness, true peak, silence (leading, total), how
cleanly it ends, where its energy sits (low / mid / high bands), how periodic it is (an engine
fires evenly; speech and music don't), the engine's fastest firing rate (a screaming rev is
fast), the attack; then ranks the variants of each sound.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

API = "https://api.elevenlabs.io/v1/sound-generation"
KEY_FILE = Path.home() / ".config" / "brickkit" / "elevenlabs.env"
MAX_FILES = 25
DEFAULTS = {"prompt_influence": 0.3, "model_id": "eleven_text_to_sound_v2",
            "output_format": "mp3_44100_192"}


# ---------------------------------------------------------------------------- the manifest
def manifest(slug: str) -> tuple[Path, list[dict]]:
    """(audio dir, [{file, name, k, prompt, seconds, loop, prompt_influence, model_id,
    output_format}]) for every file the model's sfx.toml asks for."""
    d = ROOT / "models" / slug / "audio"
    cfg = tomllib.loads((d / "sfx.toml").read_text())
    base = dict(DEFAULTS, **(cfg.get("defaults") or {}))
    out = []
    for s in cfg.get("sfx", []):
        for k in range(1, int(s.get("variants", 1)) + 1):
            ext = "mp3" if str(base["output_format"]).startswith("mp3") else "bin"
            out.append({"file": f"{s['name']}_{k}.{ext}", "name": s["name"], "k": k,
                        "prompt": " ".join(str(s["prompt"]).split()),
                        "seconds": float(s["seconds"]), "loop": bool(s.get("loop", False)),
                        "prompt_influence": float(s.get("prompt_influence",
                                                        base["prompt_influence"])),
                        "model_id": base["model_id"], "output_format": base["output_format"]})
    if len(out) > MAX_FILES:
        raise SystemExit(f"sfx.toml asks for {len(out)} files; keep it to {MAX_FILES}")
    return d, out


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if line.startswith("ELEVENLABS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit(f"no ElevenLabs API key: set ELEVENLABS_API_KEY or put it in {KEY_FILE}")
    return key


def generate(item: dict, key: str, tries: int = 3) -> bytes:
    body = {"text": item["prompt"], "duration_seconds": item["seconds"],
            "prompt_influence": item["prompt_influence"], "model_id": item["model_id"]}
    if item["loop"]:
        body["loop"] = True
    url = f"{API}?output_format={item['output_format']}"
    for attempt in range(tries):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json",
                                              "Accept": "audio/mpeg"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if len(data) < 1000:
                raise RuntimeError(f"suspiciously small response ({len(data)} bytes)")
            return data
        except urllib.error.HTTPError as e:        # the API's own message (it never echoes keys)
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503) and attempt + 1 < tries:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"{item['file']}: HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt + 1 < tries:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"{item['file']}: {e}") from None
    raise SystemExit(f"{item['file']}: failed")


def make(slug: str, dry: bool = False) -> None:
    d, items = manifest(slug)
    log_file = d / "sfx_generated.json"
    record = json.loads(log_file.read_text()) if log_file.exists() else {}
    todo = [it for it in items if not (d / it["file"]).exists()]
    print(f"{len(items)} files in {d.relative_to(ROOT)}/sfx.toml, {len(todo)} to make")
    if dry or not todo:
        for it in todo:
            print(f"  would make {it['file']} ({it['seconds']:g} s{', loop' if it['loop'] else ''})")
        return
    key = api_key()
    for it in todo:
        t0 = time.time()
        data = generate(it, key)
        (d / it["file"]).write_bytes(data)
        record[it["file"]] = {k: it[k] for k in ("name", "prompt", "seconds", "loop",
                                                "prompt_influence", "model_id", "output_format")}
        record[it["file"]].update(generated=date.today().isoformat(), bytes=len(data),
                                  sha1=hashlib.sha1(data).hexdigest(),
                                  source="ElevenLabs sound generation API (Creator plan)")
        log_file.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"  {it['file']}: {len(data) / 1024:.0f} KB in {time.time() - t0:.1f} s")


# ---------------------------------------------------------------------------- analysis
def measure(path: Path, asked: float) -> dict:
    """What can be told about a sound effect without listening to it."""
    import numpy as np
    from scipy import signal

    from brickkit.video import audio as A
    sr = 48000
    x = A.load_sample(path, sr)
    m = x.mean(axis=1)
    n = len(m)
    hop = sr // 100                                  # 10 ms frames
    rms = np.sqrt(np.convolve(m ** 2, np.ones(hop) / hop, "valid")[::hop] + 1e-20)
    db = 20 * np.log10(rms)
    top = db.max()
    lead = int(np.argmax(db > top - 30)) / 100.0      # before it starts
    silent = float((db < top - 45).mean())
    tail = float(db[-5:].mean() - top)               # the last 50 ms against the loudest
    f, P = signal.welch(m, sr, nperseg=4096)
    tot = P.sum() + 1e-30
    bands = {"low": float(P[f < 150].sum() / tot), "mid": float(P[(f >= 150) & (f < 2000)].sum() / tot),
             "high": float(P[(f >= 2000) & (f < 9000)].sum() / tot), "air": float(P[f >= 9000].sum() / tot)}
    centroid = float((f * P).sum() / tot)
    # an engine: a strong, even pulse train. Its rate from the autocorrelation of the band-
    # passed envelope, in 80 ms windows (the fastest one is the scream's pitch)
    env = A.bw(np.abs(A.bw(m, "band", (200.0, 4000.0), sr)), "low", 500.0, sr)
    win, rates, strengths = int(0.08 * sr), [], []
    for i in range(0, n - win, int(0.04 * sr)):
        e = env[i:i + win] - env[i:i + win].mean()
        ac = np.correlate(e, e, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        lo, hi = sr // 320, sr // 15
        k = lo + int(np.argmax(ac[lo:hi]))
        strengths.append(float(ac[k] / ac[0]))
        rates.append(sr / k)
    strengths = np.array(strengths) if strengths else np.zeros(1)
    rates = np.array(rates) if rates else np.zeros(1)
    periodic = float(np.median(strengths))
    loud = db[::4][:len(rates)] if len(rates) else db
    fast = float(np.percentile(rates[strengths > 0.4], 90)) if (strengths > 0.4).any() else 0.0
    # speech leaks in as 3-8 Hz syllable modulation of the 300-3000 Hz band
    sp = A.bw(np.abs(A.bw(m, "band", (300.0, 3000.0), sr)), "low", 30.0, sr)[::sr // 200]
    S = np.abs(np.fft.rfft((sp - sp.mean()) * np.hanning(len(sp))))
    fm = np.fft.rfftfreq(len(sp), 1 / 200.0)
    syll = float(S[(fm >= 3) & (fm <= 8)].sum() / (S[(fm >= 0.5) & (fm <= 20)].sum() + 1e-12))
    attack = float(np.argmax(db > top - 3) / 100.0 - lead)
    return {"file": path.name, "seconds": n / sr, "asked": asked, "lufs": A.measure_lufs(x, sr),
            "true_peak": A.true_peak_db(x, sr), "lead": lead, "silent": silent, "tail": tail,
            "bands": bands, "centroid": centroid, "periodic": periodic, "fastest": fast,
            "syllabic": syll, "attack": attack, "peak_at": float(np.argmax(db) / 100.0),
            "stereo": float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) if x.shape[1] > 1 else 1.0}


# what each sound should be, as a score (higher is better) on top of the common checks
ROLE_SCORE = {
    "pull_start": lambda r: 2 * r["periodic"] + (0.5 if r["attack"] < 0.3 else 0.0),
    "idle": lambda r: 3 * r["periodic"] - 2 * r["silent"] - 0.02 * abs(r["tail"]),
    "scream": lambda r: r["fastest"] / 100.0 + 2 * r["bands"]["high"] + r["periodic"],
    "rev_burst": lambda r: r["fastest"] / 100.0 + 2 * r["bands"]["high"] + r["periodic"],
    "string_stab": lambda r: 3 * r["bands"]["high"] - 2 * r["bands"]["low"] - r["attack"],
    "metal_hit": lambda r: 2 * r["bands"]["high"] + r["bands"]["mid"] - r["attack"],
    "boom": lambda r: 4 * r["bands"]["low"] - r["attack"],
    # a tap lamp: a sharp bright click, a quick pop, a low soft bloop, crickets without gaps
    "click": lambda r: 2 * r["bands"]["high"] - 4 * r["attack"] - 2 * r["lead"],
    "snap_on": lambda r: r["bands"]["high"] + r["bands"]["mid"] - 3 * r["attack"],
    "snap_off": lambda r: r["bands"]["mid"] + r["bands"]["low"] - 3 * r["attack"],
    "crickets": lambda r: 2 * (r["bands"]["high"] + r["bands"]["air"]) - 3 * r["silent"],
}


def score(name: str, r: dict) -> float:
    s = ROLE_SCORE.get(name, lambda r: 0.0)(r)
    s -= 2.0 * max(0.0, abs(r["seconds"] - r["asked"]) - 0.4)     # not what was asked
    s -= 3.0 * max(0.0, r["lead"] - 0.15)                         # starts late
    s -= 2.0 * max(0.0, r["silent"] - 0.15)                       # gaps
    s -= 2.0 * max(0.0, r["syllabic"] - 0.45)                     # speech-like modulation
    s -= 1.0 * max(0.0, r["true_peak"] + 0.5)                     # clipped
    return float(s)


def analyse(slug: str) -> dict:
    d, items = manifest(slug)
    out = {}
    for it in items:
        p = d / it["file"]
        if not p.exists():
            continue
        r = measure(p, it["seconds"])
        r["score"] = score(it["name"], r)
        out.setdefault(it["name"], []).append(r)
    for name, rs in out.items():
        rs.sort(key=lambda r: -r["score"])
        print(f"\n{name}")
        print("  file                 s(asked)  LUFS  dBTP  lead silent  tail  low  mid high  "
              "periodic fastest syll attack peak@  score")
        for r in rs:
            b = r["bands"]
            print(f"  {r['file']:20s} {r['seconds']:4.1f}({r['asked']:3.1f}) {r['lufs']:5.1f} "
                  f"{r['true_peak']:5.1f} {r['lead']:4.2f} {r['silent']:5.2f} {r['tail']:5.0f} "
                  f"{b['low']:4.2f} {b['mid']:4.2f} {b['high']:4.2f}  {r['periodic']:6.2f} "
                  f"{r['fastest']:6.0f}  {r['syllabic']:4.2f} {r['attack']:5.2f} {r['peak_at']:5.2f} "
                  f"{r['score']:6.2f}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true", help="list what would be made")
    ap.add_argument("--analyse", action="store_true", help="measure and rank the files")
    ap.add_argument("--json", help="with --analyse: write the measurements here")
    a = ap.parse_args(argv)
    if a.analyse:
        res = analyse(a.slug)
        if a.json:
            Path(a.json).write_text(json.dumps(res, indent=1))
        return 0
    make(a.slug, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
