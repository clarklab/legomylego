# Avocado

Standalone 23-piece Quick Bricks reconstruction of the avocado in LEGO Classic
11039 Creative Food Friends. Source: [official LEGO instructions, 6555451.pdf](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555451.pdf),
pages 22–31, numbered steps 1–15. The alternative avocado builds on pages 32–33
are not part of this model. Source-page images and the machine-readable piece
and step manifest are in `reference/`.

## Source step audit

| LEGO step | PDF page | Pieces added |
|---:|---:|---|
| 1 | 22 | 1 lime 2 x 4 plate |
| 2 | 23 | 1 lime 2 x 2 brick |
| 3 | 23 | 2 lime 1 x 2 inverted slopes |
| 4 | 24 | 1 lime 1 x 6 brick |
| 5 | 24 | 1 lime 1 x 2 brick with a centred side stud |
| 6 | 25 | 1 lime inverted slope + 1 lime 1 x 2 brick, built separately |
| 7 | 26 | 1 lime inverted slope + 1 lime 1 x 2 brick, built separately |
| 8 | 27 | 1 lime 2 x 2 brick |
| 9 | 27 | 2 lime 2 x 2 slopes |
| 10 | 28 | 1 reddish-brown 3 x 3 round tile |
| 11 | 29 | 1 lime 1 x 4 brick |
| 12 | 29 | 2 lime side-stud 1 x 1 bricks + 1 lime smile brick |
| 13 | 30 | 2 white squeezed-shut eye tiles |
| 14 | 30 | 2 lime 2 x 2 slopes |
| 15 | 31 | 1 bright-green round 2 x 2 jumper plate |

The repo has 15 main steps and two one-step cheek subassemblies, for 17
instruction steps. These preserve both separate build callouts in official
steps 6 and 7. All 23 placed pieces are accounted for in the manifest and BOM.

## Exact catalogue identities

The smile is LEGO element **6432104**, Rebrickable `3004pr0103`, LDraw `3004p0g`,
BrickLink `3004pb302`, in Lime. The eyes are element **6431715**, Rebrickable
`98138pr9980`, LDraw `98138p2o`, BrickLink `98138pb365`, in White. The left eye
is turned 180 degrees so the two chevrons point inward. The stone mount uses the
actual `86876` mould (element **6528558**), and the stone is `67095` (element
**6440768**), not a smaller 2 x 2 tile. The four inverted slopes use LDraw
`3665b`, which maps to the source's Rebrickable/BrickLink `3665`.

## Verification and outputs

`brickkit all avocado` passes all eight checks: real elements, connections,
collisions, buildability, stability, mechanism, electrics and technique. There
are 13 part/colour combinations, one connected model, zero overlaps and zero
technique notes. The generated BOM contains 23 pieces and no rare elements.
`model.toml` marks the model as `quick_bricks` and includes the normal Quick
Bricks and booklet metadata for later use through the repo's existing tools.
Video generation and booklet image rendering are not needed to validate or use
the parsed model.

The saved static preview was checked against the official finished-model page.
The stone, shoulder slopes and inward-facing eye chevrons match the source.
