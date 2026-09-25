"""Screenshot each .page of a booklet HTML (for checking the layout without a PDF rasterizer).

    python tools/page_shots.py models/<slug>/out/booklet/booklet.html OUT_DIR [first] [last]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html, out = Path(sys.argv[1]), Path(sys.argv[2])
first = int(sys.argv[3]) if len(sys.argv) > 3 else 1
last = int(sys.argv[4]) if len(sys.argv) > 4 else 9999
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1123, "height": 794})
    pg.goto(html.resolve().as_uri(), wait_until="networkidle")
    pages = pg.query_selector_all(".page")
    print(len(pages), "pages")
    for n, el in enumerate(pages, 1):
        if first <= n <= last:
            el.screenshot(path=str(out / f"page_{n:03d}.png"))
    b.close()
