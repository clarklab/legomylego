"""Showreel themes: the per-model skin over the one reel structure (see reel.py).

A theme is a flat dict of tokens the compositor (web/reel.js) and the sound (audio.py) read:
tempo (`beat` frames per beat at 30 fps), colours (`backdrop` is the 3D studio's), fonts, the
transition and title styles, the overlay and the music style. Pick one in model.toml and
override any token:

    [video]
    theme = "tape"
    [video.theme_overrides]
    accent = "#FF3EA5"
"""
from __future__ import annotations

BRAND = {"yellow": "#FEDB05", "red": "#EB152C", "black": "#111010", "cream": "#FFFCF3"}

THEMES: dict[str, dict] = {
    # the house style: cream and brand yellow, red accents, stud wipes
    "brand": {
        "backdrop": "#D9DDE3",
        "beat": 15, "music": "brand",
        "bg": "#FFFCF3", "bg2": "#FEDB05", "ink": "#111010", "muted": "#6B6660",
        "accent": "#EB152C", "accent2": "#FEDB05", "ok": "#1FA35C", "warn": "#F29A0B",
        "hud": "#111010", "hud_ink": "#FFFCF3", "panel": "rgba(255,252,243,0.93)",
        "panel_ink": "#111010", "line": "#111010",
        "display": "Fredoka", "mono": "Space Mono",
        "transition": "studs", "title": "slam", "callout": "pill", "overlay": "none",
        "grain": 0.035, "xray": "#EB152C", "xray_bg": "#111010",
        "grade": {"tint": None, "amount": 0.0, "contrast": 1.0, "saturate": 1.0},
    },
    # sci-fi scan visor: teal and cyan on deep navy, bracket reticles, scan lines
    "scan": {
        "backdrop": "#1A2A33",
        "beat": 15, "music": "scan",
        "bg": "#03101A", "bg2": "#072634", "ink": "#E3FCFF", "muted": "#6FA6B2",
        "accent": "#35F2E0", "accent2": "#18B7FF", "ok": "#35F2E0", "warn": "#FFB547",
        "hud": "#5CF2FF", "hud_ink": "#03101A", "panel": "rgba(3,16,26,0.78)",
        "panel_ink": "#E3FCFF", "line": "#5CF2FF",
        "display": "Fredoka", "mono": "Share Tech Mono",
        "transition": "shutter", "title": "decode", "callout": "bracket", "overlay": "scanlines",
        "grain": 0.05, "xray": "#35F2E0", "xray_bg": "#021018",
        "grade": {"tint": "#0B3A46", "amount": 0.16, "contrast": 1.06, "saturate": 0.95},
    },
    # 80s/90s tape: purple dark, magenta and cyan, VCR on-screen display, tracking glitches
    "tape": {
        "backdrop": "#6B5C88",
        "beat": 16, "music": "tape",
        "bg": "#140A24", "bg2": "#2B0F47", "ink": "#F5F1FF", "muted": "#A79BC4",
        "accent": "#FF3EA5", "accent2": "#29E3FF", "ok": "#7CFFB2", "warn": "#FFD23F",
        "hud": "#F5F1FF", "hud_ink": "#140A24", "panel": "rgba(16,6,30,0.8)",
        "panel_ink": "#F5F1FF", "line": "#F5F1FF",
        "display": "Fredoka", "mono": "VT323",
        "transition": "glitch", "title": "osd", "callout": "osd", "overlay": "vhs",
        "grain": 0.07, "xray": "#29E3FF", "xray_bg": "#0E0620",
        "grade": {"tint": "#3A1650", "amount": 0.1, "contrast": 1.04, "saturate": 1.08},
    },
    # playful: warm cream, bouncy squash-and-stretch type, paw-print slides
    "playful": {
        "backdrop": "#BFDCEB",
        "beat": 14, "music": "playful",
        "bg": "#FFF3DC", "bg2": "#FEDB05", "ink": "#2A1A12", "muted": "#8C7466",
        "accent": "#EB152C", "accent2": "#FF8A3D", "ok": "#2BB673", "warn": "#F29A0B",
        "hud": "#2A1A12", "hud_ink": "#FFF3DC", "panel": "rgba(255,249,236,0.95)",
        "panel_ink": "#2A1A12", "line": "#2A1A12",
        "display": "Fredoka", "mono": "Fredoka",
        "transition": "paws", "title": "bounce", "callout": "pill", "overlay": "none",
        "grain": 0.03, "xray": "#FF6B3D", "xray_bg": "#2A1A12",
        "grade": {"tint": "#FFE2B8", "amount": 0.05, "contrast": 1.03, "saturate": 1.06},
    },
}


def theme_for(cfg: dict) -> dict:
    """The model's theme: THEMES[cfg["theme"]] (default "brand") with cfg["theme_overrides"]."""
    name = str(cfg.get("theme", "brand"))
    if name not in THEMES:
        raise SystemExit(f"unknown video theme {name!r}; choose from {', '.join(THEMES)}")
    th = dict(THEMES[name], name=name, brand=dict(BRAND))
    th.update(cfg.get("theme_overrides") or {})
    return th
