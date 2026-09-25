from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def overall(results) -> str:
    if any(r.status == "fail" for r in results):
        return "fail"
    return "warn" if any(r.status == "warn" for r in results) else "pass"


def write_report(results, out_dir, title: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = {"title": title, "status": overall(results), "checks": [asdict(r) for r in results]}
    (out / "report.json").write_text(json.dumps(data, indent=2, default=_jsonable))
    colours = {"pass": "#1d7a46", "warn": "#9a6700", "fail": "#b42318"}
    rows = []
    for r in results:
        issues = "".join(f"<li><code>{html.escape(json.dumps(i, default=_jsonable))}</code></li>"
                         for i in r.items[:50])
        more = f"<p>... and {len(r.items) - 50} more</p>" if len(r.items) > 50 else ""
        rows.append(f"<section><h2><span style='color:{colours[r.status]}'>{r.status.upper()}"
                    f"</span> {html.escape(r.name)}</h2><p>{html.escape(r.summary)}</p>"
                    f"<ul>{issues}</ul>{more}</section>")
    (out / "report.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>{html.escape(title)} checks</title>"
        f"<body style='font-family:system-ui;max-width:900px;margin:2rem auto'>"
        f"<h1>{html.escape(title)}: {data['status'].upper()}</h1>{''.join(rows)}</body>")
    return data
