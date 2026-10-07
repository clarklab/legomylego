# Bat

A Quick Bricks model: 22 pieces, 10 studs (8 cm) across the wings, 4.5 cm tall. It's built
from four phone screenshots of an instructions app, kept in `reference/`. The design is
another builder's: the app credits it to the creator vladosique.

- `screen_01.png`: the page overview, pages 1-4 (and the top edge of 5 and 6);
- `screen_02.png`: the page overview, pages 7-10;
- `screen_03.png`: the app's parts list, the "In sets" tab (18 pieces);
- `screen_04.png`: the "Missing" tab (4 pieces), which also names the design's creator in the
  app, vladosique.

All checks pass except stability, which is switched off: the bat stands on two 1 x 1 clip
plates, one stud deep. It's made to hang by its clips from a bar, not to stand.

## The plans, page by page

Columns run left to right as you face it: x = -30, -10, 10, 30 for the head; the wings reach
three studs further each side. Everything is one stud deep.

| Page | Pieces | Where |
|---:|---|---|
| 1 | 1x Brick 1 x 2 (3004), Black | The middle of the head. |
| 2 | 2x Plate 1 x 1 with Tooth (15070), White, and 2x Inverted Slope 45 2 x 1 (3665), Black | Fang plates under the brick, teeth hanging in front. Under them the two inverted slopes, tips out: the V-shaped chin. |
| 3 | 2x Plate 1 x 1 (3024), Black | On the chin's two tips, beside the fangs. |
| 4 | 2x Brick 1 x 1 with Stud on 1 Side (87087), Black | On those plates, studs facing front, for the eyes. |
| 5, 6 | (not in the screenshots) | See below. |
| 7 | 2x Tile 1 x 4 (2431) and 2x Inverted Slope 33 3 x 1 (4287c), Black | The wings. Each tile covers a side brick and reaches three studs out; the slope hangs under those three. |
| 8 | 2x Tile 1 x 2 Half Round (1748), Yellow, and 1x Plate 1 x 2 (3023), Black | Eyes on the front studs, each on its middle and tipped about 30 degrees in towards the nose. The plate goes on top of the brick, between the tiles. |
| 9 | 2x Slope 45 2 x 1 (3040) and 2x Slope 30 1 x 1 x 2/3 (54200), Black | The ears. Each 2 x 1 slope sits on a stud of the top plate with its high end out over the wing tile; a small slope goes on its stud. |
| 10 | 2x Plate 1 x 1 with Clip (61252), Black | Under the chin, clips forward: the feet. |

## What had to be worked out

- **Pages 5 and 6** are cut off between the two overview screenshots. Page 7 highlights both
  whole wings (tile and slope), and nothing else changes between pages 4 and 7. So pages 5
  and 6 are most likely the two wings being put together on their own.
- **Four pieces weren't on the first parts list.** That list was the "In sets" tab: 18
  pieces the builder already owns. The drawings needed four more, worked out before the
  "Missing" tab was to hand, which then confirmed both (18 + 4 = 22, as the app says):
  - 2x Inverted Slope 45 2 x 1 (3665) for the chin. The chin's halves are two studs long and
    slope at 45 degrees, so they can't be the 3 x 1 inverted slopes, which are the wings.
  - 2x Slope 45 2 x 1 (3040B) under the ears' small slopes.
- **The eyes** sit on a single stud each, through the half-round tile's middle socket, which
  is what lets them turn to the angry tilt.
- **Build order:** the plans start at the head's brick and add above and below it, the feet
  last, as you would in the hand. `design.py` builds from the feet up, so every piece lands
  on something. Each wing's tile goes on first and its slope presses up under it.

## Parts and price

- 22 pieces in 12 lines; every part has a LEGO element ID.
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1-$3. Pick a Brick prices haven't been checked live.

## Quick Bricks

- Under 25 pieces, so the video starts with every piece laid out in a grid behind the build
  spot, then they float in one at a time (`layout` in the guide).
- `[quick]` in `model.toml`: a green cutting mat in the night workshop, soft evening light,
  14 seconds, clicks only.
- `collection = "quick_bricks"` marks it for the site's Quick Bricks section, which isn't
  built yet.
