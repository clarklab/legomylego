"""Screenshot the site's 3D viewer in headless Chromium with software WebGL (SwiftShader).

    python tools/viewer_shots.py OUT_DIR slug [slug ...]   (serves site/ on port 4411)
"""
import http.server
import socketserver
import sys
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path(sys.argv[1])
ZOOM = 12                                  # wheel steps for the close-up
out.mkdir(parents=True, exist_ok=True)
site = Path(__file__).resolve().parents[1] / "site"
handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
handler.log_message = lambda *a, **k: None
srv = socketserver.TCPServer(("127.0.0.1", 4411), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                    "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        for slug in sys.argv[2:]:
            pg.goto(f"http://127.0.0.1:4411/m/{slug}/?q=high", wait_until="networkidle")
            pg.wait_for_timeout(9000)
            el = pg.query_selector("#viewer") or pg.query_selector("canvas")
            (el or pg).screenshot(path=str(out / f"{slug}.png"))
            box = pg.query_selector("canvas").bounding_box()
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.4)
            for _ in range(ZOOM):
                pg.mouse.wheel(0, -120)
                pg.wait_for_timeout(120)
            pg.wait_for_timeout(2500)
            (el or pg).screenshot(path=str(out / f"{slug}_close.png"))
            print("shot", slug)
        b.close()
finally:
    srv.shutdown()
