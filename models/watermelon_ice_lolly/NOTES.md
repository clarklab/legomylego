# Watermelon Ice Lolly

A standalone Quick Bricks transcription of the watermelon ice lolly in LEGO Classic
Creative Food Friends, set **11039**: **23 physical pieces**, **11 official numbered
steps**, four studs wide and two studs deep, about 7.2 cm tall including the top studs.

Source: [official LEGO instruction PDF 6555451](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555451.pdf),
pages **14–19**. Page images are retained in `reference/`; `reference/inventory.json`
records the PDF SHA-256, each official step's page, exact LEGO element ID, LDraw part,
colour and quantity. The unnumbered alternate rebuilds on pages 20–21 are excluded.

## Numbered steps and complete inventory

| Official step | PDF page | Pieces introduced |
|---:|---:|---|
| 1 | 14 | 1× Lime 2×4 brick (4165967 / 3001); 1× White 2×4 plate (302001 / 3020). |
| 2 | 14 | 1× Coral 1×4 brick (6422918 / 3010), across the back row. |
| 3 | 15 | 2× Coral 1×2 bricks with centred side stud (6523861 / 86876), each with 1× Black round 1×1 tile (6284070 / 98138). |
| 4 | 15 | 1× Coral centred-side-stud brick (6523861 / 86876) and 1× Black round tile (6284070 / 98138), centred above the first seeds. |
| 5 | 16 | 3× Coral 1×2 bricks (6258572 / 3004), completing the second row. |
| 6 | 16 | 1× Coral 1×4 brick (6422918 / 3010) and the Coral printed smile brick (6522845 / 3004p0g). |
| 7 | 17 | 2× Coral 1×1 bricks with a side stud (6261292 / 87087), for the eyes. |
| 8 | 17 | 2× White printed two-highlight eye tiles (6431716 / 98138p2j). |
| 9 | 18 | 1× Coral 2×2 brick (6422920 / 3003), centred on top. |
| 10 | 18 | 2× Coral curved-top 1×2 bricks (6261293 / 37352), sloping outward. |
| 11 | 19 | 2× Tan round 2×2 bricks (4125220 / 3941), stacked and attached underneath. |

The build preserves the yellow inset subassemblies: a seed is a coral brick with its
black tile already attached, and the stick is the pair of tan round bricks. The parsed model therefore has **13 instruction entries**: eleven main steps, one seed recipe
reused three times, and one stick recipe. This does not add pieces or alter the official
eleven-step sequence. The final step's camera looks underneath for the stick attachment.

## Exact parts and orientation

- The body is **Coral**, not Dark Pink. Its official element IDs map to Rebrickable colour
  1050. The rind is Lime; the stick is Tan.
- The smile is the exact print: LEGO 6522845 → Rebrickable 3004pr0103 → LDraw 3004p0g
  → BrickLink 3004pb302. It is not a plain brick or a similar face.
- The eyes are the exact print: LEGO 6431716 → Rebrickable 98138pr9981 → LDraw 98138p2j
  → BrickLink 98138pb367. The larger white highlight is upper left; the smaller one is
  lower right, matching the official drawings.
- The seed bricks are **86876**, with the bottom stud holder, matching the official
  element. All twelve inventory lines have real LEGO element IDs.
- No geometry approximations, added parts, hidden supports, collision exemptions,
  loose-part exemptions or disabled checks are used.

## Validation

`brickkit all watermelon_ice_lolly` verifies all 23 pieces and generates the MPD,
parts CSV, BrickLink wanted list, Pick a Brick list and price estimate.

- All eleven main steps were independently compared with `reference/inventory.json`,
  recursively counting the seed and stick subassemblies. Every exact part, colour and
  quantity matches; every listed LEGO element ID resolves in the catalogue.
- Connections: 57 stud connections, one connected assembly.
- Collisions: no overlaps. Buildability: no insertion problems.
- Stability: 97% support margin, estimated tipping angle 10.2°, satisfying the default 10°
  threshold. As expected for the official narrow-stick design, it is less stable than a
  model standing on its full body width.
- Mechanism, electrics and technique checks pass. The only warning is that the exact
  Coral printed smile is rare in the cached catalogue (two sets, last seen 2025).

The model includes the repo's normal Quick Bricks and booklet metadata for later use.
The two-brick stick callout is preserved, and its pieces are attached underneath in
official step 11. A saved static preview matches the official finished-model page.
