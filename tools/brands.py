"""The logo cards on the Quick Bricks page: brands/*.svg -> site/assets/js/brands.js.

Each logo is a theme a model can belong to (`brands = ["pokemon"]` in its model.toml's [model];
tools/quick_site.py passes that on, and the page's cards filter by it). The logos arrive from
anywhere, each drawn its own way, so here every one is made alike:

- cut to its ink: a white square behind it is dropped, and the viewBox is the drawing's own box
- one colour: whatever was drawn dark becomes `currentColor` (the card's text colour, so it
  works on the light and the dark theme), whatever was drawn white on top of that becomes
  `var(--brand-paper)` (the card's own background: the PEZ letters' bricks)
- one size: `w` and `h` (px in a card) give every logo the same area, so a wide wordmark and a
  squat one carry the same weight; neither wider nor taller than the card allows
- nothing else: editors' metadata, ids, classes and styles are thrown away

    .venv/bin/python tools/brands.py          # after adding or changing a logo

A new logo: drop NAME.svg into brands/ (lower case, dashes), add its name below if the file
name does not say it, and run this."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "brands"
OUT = ROOT / "site" / "assets" / "js" / "brands.js"

NAMES = {"pez": "PEZ", "pokemon": "Pokémon", "spooky": "Spooky Season"}     # else: Title Case
ORDER = ["pokemon", "nintendo", "star-wars", "pez", "adventure-time", "spooky", "snacks"]   # the cards' order
AREA = 2700.0             # px2 of card every logo gets
MOST = (104.0, 38.0)      # ... but never wider or taller than this

NORMALISE = r"""
(text) => {
  const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
  const src = doc.documentElement;
  const svg = document.importNode(src, true);
  svg.removeAttribute('width'); svg.removeAttribute('height');
  document.body.replaceChildren(svg);
  const shapes = [...svg.querySelectorAll('path, rect, circle, ellipse, polygon, polyline, line')];
  const view = svg.viewBox.baseVal;
  const rgb = el => getComputedStyle(el).fill.match(/[\d.]+/g).map(Number);
  const white = el => { const c = rgb(el); return c.length >= 3 && c[0] > 240 && c[1] > 240 && c[2] > 240; };
  const paper = new Set();
  for (const el of shapes) {
    if (!white(el)) continue;
    const b = el.getBBox();
    if (view.width && b.width * b.height > 0.9 * view.width * view.height) el.remove();   // a background
    else paper.add(el);
  }
  const live = shapes.filter(el => el.isConnected);
  // the ink's own box, in the svg's units (through any transforms on the way up)
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const inv = svg.getScreenCTM().inverse();
  for (const el of live) {
    if (paper.has(el)) continue;
    const b = el.getBBox(), m = inv.multiply(el.getScreenCTM());
    for (const [px, py] of [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]) {
      const p = new DOMPoint(px, py).matrixTransform(m);
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y);
    }
  }
  for (const el of live) {
    const rule = getComputedStyle(el).fillRule;
    el.setAttribute('fill', paper.has(el) ? 'var(--brand-paper)' : 'currentColor');
    if (rule === 'evenodd') el.setAttribute('fill-rule', 'evenodd');
  }
  const keep = new Set(['d', 'points', 'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry', 'x1', 'y1', 'x2', 'y2',
                        'transform', 'fill', 'fill-rule']);
  const strip = el => {
    for (const a of [...el.attributes]) if (!keep.has(a.name)) el.removeAttribute(a.name);
    for (const c of [...el.children]) {
      if (['defs', 'style', 'title', 'desc', 'metadata'].includes(c.localName) || c.namespaceURI !== 'http://www.w3.org/2000/svg') c.remove();
      else strip(c);
    }
  };
  strip(svg);
  svg.removeAttribute('fill'); svg.removeAttribute('transform');
  for (const g of [...svg.querySelectorAll('g')].reverse())            // groups that do nothing
    if (!g.attributes.length) g.replaceWith(...g.childNodes);
  const r = v => +v.toFixed(2);
  svg.setAttribute('viewBox', [r(x0), r(y0), r(x1 - x0), r(y1 - y0)].join(' '));
  let out = new XMLSerializer().serializeToString(svg).replace(/\s+xmlns(:\w+)?="[^"]*"/g, '').replace(/>\s+</g, '><');
  return {svg: out, w: x1 - x0, h: y1 - y0, shapes: live.length, paper: paper.size};
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright
    files = sorted(SRC.glob("*.svg"))
    if not files:
        print(f"no logos in {SRC}")
        return 1
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("<!doctype html><body style='margin:0'></body>")
        for f in files:
            got = page.evaluate(NORMALISE, f.read_text())
            ratio = got["w"] / got["h"]
            w, h = (AREA * ratio) ** 0.5, (AREA / ratio) ** 0.5
            k = min(1.0, MOST[0] / w, MOST[1] / h)
            rows.append({"id": f.stem, "name": NAMES.get(f.stem, f.stem.replace("-", " ").title()),
                         "w": round(w * k, 1), "h": round(h * k, 1), "svg": got["svg"]})
            print(f"  {f.stem:16s} {got['shapes']:3d} shapes ({got['paper']} white on top), "
                  f"{ratio:4.2f} : 1 -> {rows[-1]['w']} x {rows[-1]['h']} px, {len(got['svg']) / 1024:.1f} KB")
        browser.close()
    rows.sort(key=lambda r: (ORDER.index(r["id"]) if r["id"] in ORDER else len(ORDER), r["id"]))
    OUT.write_text(
        "// The Quick Bricks page's logo cards. Made by tools/brands.py from brands/*.svg (each logo cut\n"
        "// to its ink, in one colour, at one size): change a logo there and run it again.\n"
        "export const brands = " + json.dumps(rows, ensure_ascii=False, indent=1) + ";\n")
    print(f"{len(rows)} logos -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
