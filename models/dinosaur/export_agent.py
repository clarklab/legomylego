"""Generate the agent handoff, including nested foot and pinned-leg assemblies."""
import csv
import hashlib
import json
from collections import Counter
from brickkit.engine import Engine
from brickkit.project import Project
from brickkit.model.builder import Use
from brickkit.render.scene import bounds

e = Engine()
p = Project("dinosaur")
m = p.build(e.catalog)
placed = m.flatten()
lo, hi = bounds(e, placed)
dims = {axis: round((hi[i]-lo[i])*.4,2) for i,axis in enumerate(("width","height","depth"))}
steps=[]
for ordinal,(owner,local_step) in enumerate(m.instruction_order(),1):
    sub=m.submodels[owner]
    parts=[q for q in placed if q.owner==owner and q.local_step==local_step]
    uses=[{"submodel":it.sub.name,"transform":it.M.tolist(),"insertion_hint":it.insert}
          for it in sub.items if isinstance(it,Use) and it.step==local_step]
    steps.append({"step":ordinal,"assembly":owner,"local_step":local_step+1,
                  "instruction":sub.captions[local_step],"attach_assemblies":uses,
                  "parts":[{"instance":q.index,"part":q.part,"color":q.color.name,
                             "ldraw_color":q.color.ldraw,"position_ldu":q.M[:3,3].tolist(),
                             "rotation_matrix":q.M[:3,:3].round(9).tolist(),"tags":list(q.tags)}
                            for q in parts]})
report=json.loads((p.out/'report.json').read_text())
data={"schema":"brickkit.agent-build.v2","model":m.name,"revision":3,
      "source_sha256":hashlib.sha256((p.dir/'design.py').read_bytes()).hexdigest(),
      "part_count":len(placed),"dimensions_mm":dims,
      "coordinate_system":"LDraw: -Y up, -Z front; 20 LDU/stud, 8 LDU/plate, 24 LDU/brick; 0.4 mm/LDU",
      "transform":"world_point = rotation_matrix @ local_point + position_ldu",
      "assembly_note":"Build child assemblies in the listed order, then attach them at attach_assemblies steps. Part positions are final world coordinates; all assembly transforms in this revision are identity.",
      "steps":steps}
assert sum(len(s['parts']) for s in steps)==len(placed)
assert len({q['instance'] for s in steps for q in s['parts']})==len(placed)
(p.dir/'agent_steps.json').write_text(json.dumps(data,indent=2)+'\n')
text=f'''# Mini T. rex — corrected agent build, revision 3

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

- `design.py`: executable source, **{len(placed)} pieces** and **{len(steps)} assembly steps**, including separate feet and pinned legs.
- `agent_steps.json`: every exact part/color, position, rotation, nested assembly attachment and instruction.
- `out/dinosaur.mpd`: LDraw model.
- `out/parts.csv`: purchase inventory with canonical IDs.
- `out/review/three_quarter.png` and `out/review/side.png`: current CPU geometry previews.
- `out/report.json` / `out/report.html`: current validation.

Saved dimensions: **{dims['width']} × {dims['height']} × {dims['depth']} mm** (width × height × depth).

## Agent construction rules

LDraw coordinates: −Y is up, −Z is forward. One stud is 20 LDU, one plate 8 LDU, one brick 24 LDU, and one LDU 0.4 mm. Use exact part origins and matrices in the JSON. Do not derive placements from bounding-box centers.

Build each foot separately, then attach it beneath its ankle. Assemble each leg with its matching hip half before joining the two halves with the orange tail/base plate. This order leaves room to insert the inward-facing pins and avoids trapping foot plates between already placed parts. The two feet sit on the same flat surface.

Use modern inverted slope `3665b.dat`. The generic LDraw `3665` alias resolves to an older mold that the catalog does not list in Orange. Tooth/eye `4073` resolves to canonical `6141`; buy using `out/parts.csv`. Do not change catalog mappings or disable checks to accommodate a substitute.

The mouth is fixed, with a small gap above the single white tooth plates. This revision does not specify an animated gait, jaw mechanism or a tested range of hip articulation. No physical prototype has been built.

## Build sequence

'''
for s in steps:
    text+=f"{s['step']}. **{s['assembly']}: {s['instruction']}**\n"
    counts=Counter((q['part'].removesuffix('.dat'),q['color']) for q in s['parts'])
    if counts:
        text+='   Parts: '+'; '.join(f'{n} × {part} ({color})' for (part,color),n in counts.items())+'.\n'
    for use in s['attach_assemblies']:
        text+=f"   Attach the completed `{use['submodel']}` assembly using the JSON transform.\n"
    text+='\n'
text+='## Parts inventory\n\n| Qty | Part | Color | Description |\n|---:|---|---|---|\n'
for r in csv.DictReader((p.out/'parts.csv').open()):
    text+=f"| {r['qty']} | {r['part']} | {r['colour']} | {r['name']} |\n"
text+='\n## Validation\n\n'
for check in report['checks']:
    text+=f"- {check['name']}: {check['status'].upper()} — {check['summary']}\n"
text+='''
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
'''
(p.dir/'AGENT_BUILD.md').write_text(text)
print(json.dumps({"pieces":len(placed),"steps":len(steps),"dimensions_mm":dims,"status":report['status']}))
