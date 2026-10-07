# Birthday Cake

A standalone Quick Bricks reconstruction of the **20-piece cake** from LEGO Classic
11039 Creative Food Friends. Source: [official PDF 6555451](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555451.pdf),
printed pages 6-11. Pages 12-13 show an alternate rebuild, excluded from this model.

The independent transcription is `reference/inventory.json`; its element IDs come from
pages 46-47. The six illustrated source pages are kept alongside it. `design.py` preserves
all 11 numbered steps, including the two-piece candle callout. The repo expands that
callout into one additional instruction entry, giving 12 generated entries.

| Source step | Page | New pieces |
|---:|---:|---:|
| 1 | 6 | 1 |
| 2 | 7 | 1 |
| 3 | 7 | 2 |
| 4 | 8 | 1 |
| 5 | 8 | 2 |
| 6 | 9 | 3 |
| 7 | 9 | 2 |
| 8 | 10 | 2 |
| 9 | 10 | 3 |
| 10 | 11 | 1 |
| 11 | 11 | 2 |

The smile is LEGO 6522847 (LDraw `3004p0g`, Rebrickable `3004pr0103`); the sleepy eyes
are 6434345 (`98138p2l`, `98138pr9976`). The flame is Trans-Orange, not opaque yellow.
The exact 76959 inverted slope (6425510) is not in the cached complete LDraw release:
its upstream unofficial part and subpart are vendored unchanged under
`brickkit/data/ldraw/`, with URLs, authors, license and hashes in `ldraw_sources.json`.
The MPD embeds both files so it opens independently. No mould substitutions are used.

The candle pin seats into the dome's blind vented stud, with its shoulder 4 LDU above the
stud top. `brickkit/data/shadow/parts/3262.dat` adds the missing radius-4, depth-4 socket
from the existing mesh; it does not waive collisions or connections.

`brickkit all birthday_cake` checks every connection, collision, insertion and stability.
Only the exact white smile's catalogue rarity is a warning (two sets); no physical check
fails. The model uses all eight standard checks, without exemptions.

The parsed model includes the repo's normal Quick Bricks settings for later use.
Its saved static preview matches the official finished-model page.
