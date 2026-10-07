# Taco

Standalone 23-piece Quick Bricks reconstruction of the taco in LEGO Classic
11039 Creative Food Friends. Source: [official LEGO instructions, 6555451.pdf](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555451.pdf),
pages 34–40, numbered steps 1–12; page 41 turns the finished taco upright. The
alternative taco builds on pages 42–43 are not part of this model. Source-page
images and the machine-readable piece and step manifest are in `reference/`.

## Source step audit

| LEGO step | PDF page | Pieces added |
|---:|---:|---|
| 1 | 34 | 1 yellow round-corner 4 x 4 plate |
| 2 | 34 | 1 yellow 1 x 8 brick |
| 3 | 35 | 1 yellow round-corner 4 x 4 plate |
| 4 | 35 | 1 lime 1 x 4 brick + 2 red round open-stud plates |
| 5 | 36 | 2 white side-stud bricks + 1 coral 1 x 2 brick |
| 6 | 37 | 1 lime and 1 reddish-brown curved 1 x 1 brick |
| 7 | 37 | 1 red curved 1 x 2 brick |
| 8 | 38 | 2 bright-green three-leaf plates |
| 9 | 39 | 2 white round open-stud plates |
| 10 | 39 | 2 bright-green three-leaf plates |
| 11 | 40 | 2 yellow round-corner 4 x 4 plates |
| 12 | 40 | 1 yellow jumper plate + 2 white closed-eye tiles |

All 12 source steps are main-model steps in the repo. The coral brick, white
side-stud bricks and two white round plates remain included even though the
finished shell hides them. There are four shell plates, four leaf plates, and
four round open-stud plates in total. All 23 placed pieces are accounted for in
the manifest and BOM.

## Exact catalogue identities and orientation

The eye print is LEGO element **6433502**, Rebrickable `98138pr9977`, LDraw
`98138p2n`, BrickLink `98138pb364`, in White. The nose uses the source's actual
`15573` jumper mould (element **6092583**), rather than the older `3794b`.
The hidden 1 x 2 brick is Coral (element **6258572**), not Dark Pink.

The source builds the shell horizontally and turns it up only on page 41. The
model is stored upright with its front facing -Z. `design.py` applies one rigid
90-degree rotation to all source-build coordinates, preserving every step and
connection axis. The green and brown 1 x 1 curved fillings mount on side studs;
the red curved 1 x 2 filling mounts on the shell. Each leaf plate is one full
plate high at its attachment, making the leaf/white-plate/leaf sandwich three
plates high beneath the front shell.

## Verification and outputs

`brickkit all taco` passes all eight checks: real elements, connections,
collisions, buildability, stability, mechanism, electrics and technique. There
are 13 part/colour combinations, one connected model, zero overlaps and zero
technique notes. The generated BOM contains 23 pieces and no rare elements.
`model.toml` marks the model as `quick_bricks` and includes the normal Quick
Bricks and booklet metadata for later use through the repo's existing tools.
Video generation and booklet image rendering are not needed to validate or use
the parsed model.

The saved static preview was checked against the official finished-model page.
The curved tomato and brown-left/lime-right filling match the upright model
on page 41; the thin closed-eye print is oriented as shown.
