# Dracula

A Quick Bricks model: 32 pieces, 3 x 2 studs, about 4.5 cm tall. It's built from a 12-page set
of plans (screenshots of a phone instructions app). The plans are kept in `reference/`
(`page_01.png` to `page_12.png`).

`design.py` has one step per page for pages 1-11; page 12 is the finished figure. All 8 checks
pass.

## The plans, page by page

Columns are left, middle and right as you face him. Every piece of the body is one stud deep.

| Page | Pieces | Where |
|---:|---|---|
| 1 | 2x Plate 1 x 2 (3023), Black | Side by side, front to back, with a stud's gap between them: the feet. |
| 2 | 1x Brick 1 x 3 (3622), Black | Across the back studs of both plates: the legs. |
| 3 | 2x Slope 30 1 x 1 x 2/3 "cheese" (54200), Black | On the two front studs, sloping forward: the shoes. |
| 4 | 3x Plate 1 x 1 (3024), Black | On the 1 x 3 brick. |
| 5 | 3x Plate 1 x 1 (3024): Black, White, Black | White in the middle: the shirt front. |
| 6 | 2x Plate 1 x 1 with Vertical Tooth (15070), White, and 1x Plate 1 x 1 (3024), Red | Fang plates left and right, teeth hanging down in front. Red in the middle: the mouth. |
| 7 | 2x Plate 1 x 1 (3024), Light Bluish Gray, and 1x Brick 1 x 1 with Stud on 1 Side (87087), Light Bluish Gray | Plates left and right. The brick goes in the middle with its stud facing forward, for the nose. |
| 8 | 2x Brick 1 x 1 with Studs on 2 Adjacent Sides (26604), Light Bluish Gray, and 1x Plate 1 x 1 (3024), Light Bluish Gray | Bricks left and right, studs facing forward and outward. The plate goes on the middle brick to level it. |
| 9 | 4x Plate 1 x 1 (3024), Black | One on each side, two in the middle. The higher middle is the widow's peak. |
| 10 | 4x Slope 30 1 x 1 x 2/3 (54200), Black, and 1x Tile 1 x 1 (3070b), Black | Two slopes on top, falling away to each side. Two on the side studs, the thick end down, for the swept-back hair. The tile goes on the middle. |
| 11 | 2x Tile Round 1 x 1 with Eye (98138pb007), White, and 1x Slope 30 1 x 1 x 2/3 (54200), Light Bluish Gray | Eyes on the front studs of the side bricks, the glint at top left. The nose goes on the middle stud, the thick end down. |
| 12 | (finished) | |

## How the plans were read

- The app's part icons were blank on pages 10 and 11. Those parts were worked out from the
  drawings and confirmed by the fit (all 8 checks pass):
  - page 10: the four slopes and the tile;
  - page 11: the eyes and the nose.
- **The eyes:** the plans draw them a little bigger than a stud, about 1.3 studs across. That
  isn't a real LEGO size. A 2 x 2 round tile wouldn't fit between the nose and the side hair,
  so the eyes are the usual 1 x 1 printed eye tile, 98138pb007. On that tile the white glint is
  a round dot. The plans draw a square glint and a second, smaller dot.
- **Colours:**
  - Light Bluish Gray for the face. The plans show a mid grey; Dark Bluish Gray would also
    work.
  - Red for the mouth.

## Parts and price

- 32 pieces in 13 lines; every part has a LEGO element ID.
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1-$3. Pick a Brick prices haven't been checked live yet.

## Quick Bricks

- `[quick]` in `model.toml` sets up the video:
  - the night_shift workshop: an oak desk in a dark room under string lights, in soft evening
    light;
  - 14 seconds, clicks only (no music);
  - close-ups as a fang and an eye land.
- The camera makes one smooth turn, always the same way:
  - across his front while the feet, cape and fangs go on;
  - round his back while the head and hair go on;
  - back to his face for the eyes and nose, ending on his front.
- `collection = "quick_bricks"` marks it for the site's Quick Bricks section, which isn't
  built yet.
