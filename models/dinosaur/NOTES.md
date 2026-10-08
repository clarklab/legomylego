# Mini T. rex

A Quick Bricks model: 42 pieces, 32 mm wide, 68 mm tall and 56 mm front to back. A red and
orange T. rex with an open, toothy mouth, black eyes, clip-on red arms, dark-tan feet with
white claws that curve down, and a tapering tail. It was reconstructed from a single picture.

All 8 checks pass.

## Source

- **From:** one reference picture, in an earlier session.
- **Designer / credit:** not recorded.
- **Saved in `reference/`:** nothing. The picture was not saved in the repo. If it turns up,
  put it in `reference/` and say so here.
- **Other records:** `AGENT_BUILD.md` is the earlier agent's own build document for revision
  3 (what was corrected against the picture, and its rules). `agent_steps.json` is every
  part's position and rotation, written by `export_agent.py`.

## The build, step by step

Each leg is its own sub-assembly, and each foot is a sub-assembly of its leg.

| Step | In | Pieces | What goes on |
|---:|---|---|---|
| 1 | Left leg | 1x Brick 1 x 2 with Pin (2458), Tan; 1x Plate 1 x 2 (3023b), Dark Tan | The leg brick, on its side with its pin pointing in; the plate covers its two front studs. |
| 2 | Left leg | 1x Plate Round 1 x 1 with Open Stud (85861), White; 1x Claw, Small (53451), White | The round plate on the lower stud; the claw's bar goes in it, curving down. |
| 3 | Left leg | 1x Brick 1 x 1 with Stud on 1 Side (87087), Orange | The ankle, behind the leg brick. |
| 4 | Left foot | 1x Plate 1 x 3 (3623), Dark Tan | The sole. |
| 5 | Left foot | 1x Plate 1 x 1 (3024), Orange; 1x Tile 1 x 1 (3070b), Orange | The ankle pad at the back, the smooth toe at the front. |
| 6 | Left leg | the finished left foot | Pressed onto the ankle from underneath. |
| 7 | Left leg | 1x Technic Brick 1 x 2 with Pin Hole (3700), Orange | The hip, slid onto the leg's pin from the inside. |
| 8 | Model | the finished left leg | Stood upright on the table. |
| 9 to 15 | Right leg, right foot | the same pieces again | The right leg, a mirror image of the left. |
| 16 | Model | the finished right leg | Stood beside the left one. |
| 17 | Model | 1x Plate 2 x 4 (3020), Orange | Across both hips, reaching back into the tail: it locks the legs together. |
| 18 | Model | 2x Inverted Slope 45 2 x 1 (3665b), Orange; 2x Slope 45 2 x 1 (3040b), Red | The belly, wider towards the chest; the tail slopes taper backward. |
| 19 | Model | 1x Plate 1 x 2 with Side Handle, Free Ends (2540), Red; 1x Plate 1 x 2 (3023b), Red | The shoulder bar, and a plate behind it. |
| 20 | Model | 2x Arm Mechanical with 2 Clips (30377), Red | The arms, clipped onto the ends of the shoulder bar, hands curving forward. |
| 21 | Model | 1x Brick 1 x 2 (3004), Orange | The neck. |
| 22 | Model | 1x Plate 2 x 4 (3020), Red | The lower jaw, reaching forward from the neck. |
| 23 | Model | 2x Plate Round 1 x 1 (6141), White; 2x Plate 1 x 2 (3023b), Orange | One round plate per tooth; the two plates hold up the back of the mouth. |
| 24 | Model | 1x Plate 2 x 4 (3020), Red | The upper jaw. |
| 25 | Model | 1x Plate 2 x 2 (3022), Red; 2x Plate Round 1 x 1 (6141), Black; 1x Plate 1 x 2 (3023b), Orange | The skull's one row: the snout, the eyes, the back of the head. |
| 26 | Model | 1x Plate 1 x 2 (3023b), Red; 1x Brick Curved 2 x 2 x 2/3 (15068), Red; 1x Plate 2 x 2 (3022), Red; 1x Tile 2 x 2 (3068b), Red | The curved forehead on its support, and the low crown. |

## What had to be worked out

This is a reconstruction from one view, not a recovered parts list. No one has built it in
real bricks yet.

- **The hidden ankle and the pinned legs are a guess.** The picture showed separate legs but
  not how they are held. The model uses bricks with a pin moulded on (2458) pushed into
  Technic hip bricks (3700): real pin connections. The pin bricks are Tan and hidden behind
  the Dark Tan leg plates.
- **The feet are three studs long** so that it stands.
- **Corrected against the picture in revision 3:**
  - the head is 56 LDU tall, not 80, and the eye row is one plate high;
  - exactly two white round plates for teeth, one per tooth (the other white round plates are
    the claws' sockets);
  - the claws curve down;
  - the belly is inverted slopes (3665b), wide at the chest and tapering back; plain slopes
    are only in the tail;
  - the arms hang forward from the outer ends of an open-ended handle, 32 LDU apart.
- **The mouth is fixed.** There is no jaw mechanism and no tested range for the hips.

## Parts and price

- 42 pieces in 23 lines. Every part is real in its colour and has a LEGO element ID.
- Use the modern moulds: inverted slope 3665b (the old 3665 was never made in Orange), and
  round plate 6141 for the teeth and eyes.
- `out/pick_a_brick.csv` and `out/bricklink_wanted.xml` are ready to upload.
- The rough estimate is $1.40 to $5.50. Prices have not been checked live.

## Quick Bricks

- `[quick]` in `model.toml`: the night workshop (oak desk, dark room, evening light), 14
  seconds, close-ups on an arm, an eye and a tooth.
- How it goes together in the video:
  - each foot is built beside its leg; the leg is lifted, the foot slides in under it, and the
    leg is set down on it;
  - the second leg cannot be built in place, because its hip slides on from where the first
    leg's hip already is. It is built beside the model, then set down next to the first;
  - the arms come up from below and clip onto the shoulder bar.
- 45 landings: the 42 pieces, and the two feet and the second leg being joined.
