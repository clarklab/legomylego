# Caldwell County Courthouse Mini

A Quick Bricks model: 64 pieces, a 6 x 6 stud building on an 8 x 8 lawn (64 mm square), 104 mm
to the top of its spire. A small, quick kids' build of the 1894 courthouse in Lockhart, Texas:
buff stone walls with a red band, slate roofs on the four corner pavilions, and the clock
tower with a clock on each side. Its clockmaster, a minifigure, stands beside the lawn.

All 8 checks pass.

## Source

- **From:** our own design. It is the small version of the big display model,
  `models/caldwell_courthouse`, and keeps what makes that one the courthouse.
- **Designer / credit:** ours. The building is the Caldwell County Courthouse in Lockhart,
  Texas.
- **Saved in `reference/`:** nothing; there were no plans to copy. The big model's notes hold
  the references for the building itself.
- **Also on the site as:** a section of the big courthouse's page (`#mini`), as well as its
  own Quick Bricks page.

## The build, step by step

| Step | Pieces | What goes on |
|---:|---|---|
| 1 | 1x Plate 8 x 8 (41539), Green; 1x Tile 1 x 2 (3069b), Light Bluish Gray | The lawn and the front walk. |
| 2 | 3x Brick 1 x 2 with Masonry Profile (98283), Tan; 3x Brick 1 x 4 with Masonry Profile (15533), Tan; 1x Brick 1 x 2 with Grille (2877), Reddish Brown | The first floor's stone walls; the grille brick is the front doors. |
| 3 | 2x Plate 1 x 6 (3666), Dark Red; 2x Plate 1 x 4 (3710), Dark Red | The red band, all the way round. |
| 4 | 4x Brick 1 x 4 with Masonry Profile (15533), Tan; 2x Brick 1 x 2 with Masonry Profile (98283), Tan | The second floor. |
| 5 | 1x Plate 4 x 6 (3032), Dark Red; 1x Plate 2 x 6 (3795), Dark Red | The red cornice: the roof deck. |
| 6 | 4x Brick 2 x 2 (3003), Tan; 4x Slope 45 2 x 2 Double Convex (3045), Black; 4x Cone 1 x 1 (59900), Dark Red | The four corner pavilions, their slate hip roofs and finials. |
| 7 | 4x Slope 45 2 x 2 (3039), Black; 4x Tile 1 x 2 (3069b), Black | The slate roofs between the pavilions, a tile on each ridge. |
| 8 | 3x Brick 2 x 2 (3003), Tan; 1x Plate 2 x 2 (3022), Dark Red | The clock tower's shaft and its band. |
| 9 | 4x Brick 1 x 1 with Studs on 2 Adjacent Sides (26604), Tan | The clock stage: a stud facing out on every side. |
| 10 | 4x Jumper Plate 1 x 2 (15573), Dark Red; 4x Tile Round 2 x 2 with Clock (14769p0m), White | A jumper on each side stud, and a clock on each jumper. |
| 11 to 14 | the clockmaster: legs, torso with arms, head, top hat | Built beside the lawn. His legs and his torso each come assembled. |
| 15 | 1x Plate 2 x 2 (3022), Dark Red; 1x Slope 75 2 x 2 x 2 Quadruple Convex (3688), Black; 1x Cone 1 x 1 (59900), Dark Red | The spire and its red finial. |

## What had to be decided

- **Size:** 6 x 6 studs for the building and 2 x 2 for the tower, so a clock tile (2 x 2
  round) covers a whole side of the clock stage.
- **The clocks** sit on jumper plates on the side studs, which centres each clock on its side.
- **The clockmaster stands on the table beside the lawn,** not on it. The lawn's border is
  one stud deep, too close to the walls for his hips. He is allowed to stand apart
  (`[checks.connections] allow_separate_tags`).
- **Two builds** (`model.toml` variants):
  - the standard one, 64 pieces;
  - *budget*, 56 pieces: the clocks pressed straight onto the side studs, and a curved 2 x 2
    slope between the pavilions instead of a slope with a tile on its ridge.
- **Two colourways:** Dark Red trim (the default) and Reddish Brown trim (*brownstone*).
- The model has 70 LDraw parts but 64 pieces: the minifigure's legs (3 parts) and his torso
  with arms and hands (5 parts) are each sold as one.

## Parts and price

- 64 pieces in 23 lines, one minifigure among them. Every part is real in its colour.
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload; the `_x5` files
  are the same lists for five kits.
- The rough estimate is $5 to $21 (budget build: $5 to $20). The minifigure is most of the
  top of that range. Prices have not been checked live.

## Quick Bricks

- `[quick]` in `model.toml`: the blue cutting mat at the workbench in morning light (the
  `cutting_mat` preset), 14 seconds, close-ups as a clock and the spire land.
- `view = "agx"`: the softer film response its video was first approved with.
- The clock tower's bell (`audio/bell_2.mp3`) tolls three times: as the tower's first brick
  lands, as the clock in the close-up goes on, and on the last piece.
- With 64 pieces it is over the 25-piece limit for laying the parts out first, so they fly in.
