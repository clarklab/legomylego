"""Compositor driver: runs web/reel.html in headless Chromium (Playwright) and pulls frames.

The page draws each frame on a canvas from the reel plan and the Blender plates (see
web/core.js). Files reach the page through Playwright routes on http://reel.local/:

    /             web/ (reel.html, the scripts, fonts/)
    /out/...      the model's out/ directory (hero still, booklet part pictures)
    /frames/...   this quality's work directory (plates, wire.bin)
    /logo.png     the site logo
    /reel.json    the plan

Several pages render interleaved frames in parallel; frames come back in order.
"""
from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
from pathlib import Path

import numpy as np

WEB = Path(__file__).resolve().with_name("web")
HOST = "http://reel.local"
ARGS = ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist",
        "--enable-unsafe-swiftshader", "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding"]


def _resolver(roots: dict[str, Path], reel_bytes: bytes):
    """url -> (file path | bytes | None, content type). `roots` maps a first path segment to a
    directory ("" is the default root) or a file name to a file."""
    def resolve(url: str):
        path = url[len(HOST):].split("?", 1)[0].lstrip("/")
        if path == "reel.json":
            return reel_bytes, "application/json"
        root, rel = roots[""], path
        head, _, rest = path.partition("/")
        if head in roots and head:
            if roots[head].is_file() and not rest:
                root, rel = roots[head].parent, roots[head].name
            elif rest:
                root, rel = roots[head], rest
        f = (root / rel).resolve()
        if not f.is_file():
            return None, None
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix == ".ttf":
            ctype = "font/ttf"
        return f, ctype
    return resolve


async def _page(browser, size: int, resolve, reel: dict, log):
    page = await browser.new_page(viewport={"width": size, "height": size},
                                  device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    quiet = ("willReadFrequently", "status of 404")        # expected: readback, missing plates

    def console(m):
        if m.type in ("error", "warning") and not any(q in m.text for q in quiet):
            log(f"  [page] {m.text}")
    page.on("console", console)

    async def route(r):
        body, ctype = resolve(r.request.url)
        if body is None:
            await r.fulfill(status=404, body="")
        elif isinstance(body, bytes):
            await r.fulfill(body=body, content_type=ctype)
        else:
            await r.fulfill(path=str(body), content_type=ctype)
    await page.route(f"{HOST}/**", route)
    await page.goto(f"{HOST}/reel.html")
    await page.evaluate("async ([size]) => { const r = await fetch('reel.json'); "
                        "return init(size, await r.json()); }", [size])
    if errors:
        raise RuntimeError("compositor failed to start: " + "; ".join(errors))
    page._errors = errors                     # noqa: SLF001
    return page


async def _render(frames: list[int], size: int, roots, reel: dict, sink, workers: int, log):
    from playwright.async_api import async_playwright
    reel_bytes = json.dumps(reel).encode()
    resolve = _resolver(roots, reel_bytes)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=ARGS)
        try:
            pages = await asyncio.gather(*[_page(browser, size, resolve, reel, log)
                                           for _ in range(workers)])
            done: dict[int, np.ndarray] = {}
            cond = asyncio.Condition()
            written = 0

            async def work(w, page):
                for i in range(w, len(frames), workers):
                    async with cond:              # don't run far ahead of the writer
                        await cond.wait_for(lambda: i - written < 4 * workers)
                    await page.evaluate("f => renderFrame(f)", frames[i])
                    if page._errors:              # noqa: SLF001
                        raise RuntimeError(f"frame {frames[i]}: {page._errors[0]}")
                    b64 = await page.evaluate("() => grab()")
                    a = np.frombuffer(base64.b64decode(b64), np.uint8).reshape(size, size, 4)
                    async with cond:
                        done[i] = a[:, :, :3]
                        cond.notify_all()

            async def write():
                nonlocal written
                while written < len(frames):
                    async with cond:
                        await cond.wait_for(lambda: written in done)
                        a = done.pop(written)
                    sink(frames[written], a)
                    async with cond:
                        written += 1
                        cond.notify_all()

            tasks = [asyncio.create_task(work(w, pg)) for w, pg in enumerate(pages)]
            writer = asyncio.create_task(write())
            await asyncio.gather(*tasks, writer)
        finally:
            await browser.close()


def compose(frames: list[int], size: int, reel: dict, roots: dict[str, Path], sink,
            workers: int = 4, log=print) -> None:
    """Render `frames` at size x size; call sink(frame, rgb uint8 array) in order."""
    roots = {"": WEB, **roots}
    asyncio.run(_render(frames, size, roots, reel, sink, max(1, workers), log))
