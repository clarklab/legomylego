# Mini T. rex — corrected agent build, revision 3

This replaces the first dinosaur reconstruction. Follow `design.py` and `agent_steps.json`; do not reuse the old tall head, doubled teeth, forward/up-curving horns, outward-splayed arms, ordinary unpinned legs, or forward-tapered belly.

## Reference-critical corrections

- Head height reduced from 80 to 56 LDU (32 to 22.4 mm). The eye row is one plate high instead of one brick high. Keep the long, low red snout and small black recessed eyes.
- Exactly **two white 6141 round plates total for teeth**, one per tooth. No vertical stacks. The white 85861 parts elsewhere are leg claw sockets, not extra teeth.
- Claws 53451 are rolled 180 degrees from the earlier placement so their curves point down. Preserve their matrices; do not rotate them to the former upward-hooked pose.
- Orange 3665b inverted slopes form the belly: broad at the top/front, tapering down and backward toward the hips. Do not substitute ordinary 3040 slopes here. The 3040 slopes belong only to the rear tail.
- Separate legs use **2458 bricks with integral Technic pins** inserted into the **3700 hip holes**. These are real pin connections, not surface-contact placeholders. The pins are molded into the leg bricks, not additional loose pin parts.
- Small red arms hang forward at the outer shoulders. Use open-ended handle 2540 and clip centers at X = −16/+16 LDU (32 LDU apart, widened from 20). Keep Y = −84, Z = −20 and the existing arm orientation. Closed-ended handle 48336 cannot support these outer clip positions.

This remains a reconstruction from one view, not a recovered original parts list. The precise hidden ankle assembly and integral-pin choice are inferred. The hidden pin bricks are Tan, covered by Dark Tan leg plates. The feet are three studs long for support. Preserve the visible reference proportions when revising; a validation pass alone does not establish visual accuracy.

## Files

- `design.py`: executable source, **42 pieces** and **26 assembly steps**, including separate feet and pinned legs.
- `agent_steps.json`: every exact part/color, position, rotation, nested assembly attachment and instruction.
- `out/dinosaur.mpd`: LDraw model.
- `out/parts.csv`: purchase inventory with canonical IDs.
- `out/review/three_quarter.png` and `out/review/side.png`: current CPU geometry previews.
- `out/report.json` / `out/report.html`: current validation.

Saved dimensions: **32.0 × 68.0 × 56.0 mm** (width × height × depth).

## Agent construction rules

LDraw coordinates: −Y is up, −Z is forward. One stud is 20 LDU, one plate 8 LDU, one brick 24 LDU, and one LDU 0.4 mm. Use exact part origins and matrices in the JSON. Do not derive placements from bounding-box centers.

Build each foot separately, then attach it beneath its ankle. Assemble each leg with its matching hip half before joining the two halves with the orange tail/base plate. This order leaves room to insert the inward-facing pins and avoids trapping foot plates between already placed parts. The two feet sit on the same flat surface.

Use modern inverted slope `3665b.dat`. The generic LDraw `3665` alias resolves to an older mold that the catalog does not list in Orange. Tooth/eye `4073` resolves to canonical `6141`; buy using `out/parts.csv`. Do not change catalog mappings or disable checks to accommodate a substitute.

The mouth is fixed, with a small gap above the single white tooth plates. This revision does not specify an animated gait, jaw mechanism or a tested range of hip articulation. No physical prototype has been built.

## Build sequence

1. **left_leg: Pin-bearing leg on its side, with dark-tan face over the two front studs**
   Parts: 1 × 2458 (Tan); 1 × 3023b (Dark Tan).

2. **left_leg: White hollow round socket on the lower stud, with the claw curving downward**
   Parts: 1 × 85861 (White); 1 × 53451 (White).

3. **left_leg: Attach the orange ankle behind the lower leg socket**
   Parts: 1 × 87087 (Orange).

4. **left_foot: Dark-tan foot sole**
   Parts: 1 × 3623 (Dark Tan).

5. **left_foot: Orange ankle pad at the rear and smooth orange toe at the front**
   Parts: 1 × 3024 (Orange); 1 × 3070b (Orange).

6. **left_leg: Press the completed foot onto the ankle from underneath**
   Attach the completed `left_foot` assembly using the JSON transform.

7. **left_leg: Slide the orange Technic hip onto the inward-facing integral leg pin**
   Parts: 1 × 3700 (Orange).

8. **dinosaur: Set the left completed leg upright on the table**
   Attach the completed `left_leg` assembly using the JSON transform.

9. **right_leg: Pin-bearing leg on its side, with dark-tan face over the two front studs**
   Parts: 1 × 2458 (Tan); 1 × 3023b (Dark Tan).

10. **right_leg: White hollow round socket on the lower stud, with the claw curving downward**
   Parts: 1 × 85861 (White); 1 × 53451 (White).

11. **right_leg: Attach the orange ankle behind the lower leg socket**
   Parts: 1 × 87087 (Orange).

12. **right_foot: Dark-tan foot sole**
   Parts: 1 × 3623 (Dark Tan).

13. **right_foot: Orange ankle pad at the rear and smooth orange toe at the front**
   Parts: 1 × 3024 (Orange); 1 × 3070b (Orange).

14. **right_leg: Press the completed foot onto the ankle from underneath**
   Attach the completed `right_foot` assembly using the JSON transform.

15. **right_leg: Slide the orange Technic hip onto the inward-facing integral leg pin**
   Parts: 1 × 3700 (Orange).

16. **dinosaur: Set the right completed leg upright on the table**
   Attach the completed `right_leg` assembly using the JSON transform.

17. **dinosaur: Lock the two hip halves together with an orange plate extending into the tail**
   Parts: 1 × 3020 (Orange).

18. **dinosaur: The inverted orange belly widens toward the chest; red tail slopes taper backward**
   Parts: 2 × 3665b (Orange); 2 × 3040b (Red).

19. **dinosaur: A red shoulder handle with free outer ends, and a red rear plate**
   Parts: 1 × 2540 (Red); 1 × 3023b (Red).

20. **dinosaur: Clip the arms onto the outer shoulder-bar ends, hands curving forward**
   Parts: 2 × 30377 (Red).

21. **dinosaur: Orange neck above the front row of the body**
   Parts: 1 × 3004 (Orange).

22. **dinosaur: The flat red lower jaw extends forward from the neck**
   Parts: 1 × 3020 (Red).

23. **dinosaur: Only one white round plate per tooth; two orange plates form the rear mouth support**
   Parts: 2 × 6141 (White); 2 × 3023b (Orange).

24. **dinosaur: A thin red upper jaw spans the mouth**
   Parts: 1 × 3020 (Red).

25. **dinosaur: A one-plate-high skull row: red snout, black eyes, orange rear**
   Parts: 1 × 3022 (Red); 2 × 6141 (Black); 1 × 3023b (Orange).

26. **dinosaur: Support the curved forehead; finish with a low red crown**
   Parts: 1 × 3023b (Red); 1 × 15068 (Red); 1 × 3022 (Red); 1 × 3068b (Red).

## Parts inventory

| Qty | Part | Color | Description |
|---:|---|---|---|
| 2 | 6141 | Black | Plate Round 1 x 1 with Solid Stud |
| 2 | 3023b | Dark Tan | Plate 1 x 2 |
| 2 | 3623 | Dark Tan | Plate 1 x 3 |
| 1 | 3004 | Orange | Brick 1 x 2 |
| 1 | 3020 | Orange | Plate 2 x 4 |
| 3 | 3023b | Orange | Plate 1 x 2 |
| 2 | 3024 | Orange | Plate 1 x 1 |
| 2 | 3070b | Orange | Tile 1 x 1 with Groove |
| 2 | 3665b | Orange | Brick Sloped Inverted 45° 2 x 1 |
| 2 | 3700 | Orange | Technic Brick 1 x 2 [1 Pin Hole] |
| 2 | 87087 | Orange | Brick Special 1 x 1 with Stud on 1 Side |
| 1 | 15068 | Red | Brick Curved 2 x 2 x 2/3 |
| 1 | 2540 | Red | Plate Special 1 x 2 Side Handle [Free Ends] |
| 2 | 3020 | Red | Plate 2 x 4 |
| 2 | 3022 | Red | Plate 2 x 2 |
| 2 | 3023b | Red | Plate 1 x 2 |
| 2 | 30377 | Red | Arm Mechanical with 2 Clips [Battle Droid] |
| 2 | 3040b | Red | Brick Sloped 45° 2 x 1 with Bottom Pin |
| 1 | 3068b | Red | Tile 2 x 2 with Groove |
| 2 | 2458 | Tan | Brick Special 1 x 2 with Pin |
| 2 | 53451 | White | Animal Body Part, Barb / Claw / Tooth / Talon / Horn, Small |
| 2 | 6141 | White | Plate Round 1 x 1 with Solid Stud |
| 2 | 85861 | White | Plate Round 1 x 1 with Open Stud |

## Validation

- real_elements: PASS — 23 part/colour combinations: 0 not real, 0 rare
- connections: PASS — 70 connections (60 stud, 4 bar, 4 pin, 2 clip); 1 separate piece(s)
- collisions: PASS — 0 overlapping pair(s) among 42 parts
- buildability: PASS — 40 insertions tried across 5 submodel(s); 0 problem(s)
- stability: PASS — about 22 g; centre of mass inside the base (54% margin); tips at 11.1 deg
- mechanism: PASS — no moving parts defined
- electrics: PASS — no electrics in this model
- technique: PASS — 0 note(s)

“1 separate piece(s)” in the connection report means one connected component: the complete model. No captive declarations, collision exemptions or weakened stability thresholds are used.

Regenerate after any edit, from the repository root:

```sh
.venv/bin/python -m brickkit all dinosaur
PYTHONPATH=. .venv/bin/python models/dinosaur/export_agent.py
PYTHONPATH=. .venv/bin/python models/dinosaur/review_render.py
```

For a Blender beauty render once the shared renderer is available:

```sh
.venv/bin/python -m brickkit render dinosaur --views three_quarter,side --size 850 --samples 32
```

Keep the shared Blender lock. Preserve `collection = "quick_bricks"`. This handoff is text and structured data; do not generate a PDF.
