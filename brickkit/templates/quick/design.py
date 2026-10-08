"""{{name}}: a Quick Bricks model. One step here per page of the plans in reference/ (NOTES.md
has the page-by-page parts list).

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The lowest plate's top is
y = 0. A plate's, brick's or tile's origin is its top; `brickkit inspect PART` shows any other
part's box and where its studs are. Colours are palette roles from model.toml."""
from brickkit.ldraw.matrix import rot  # noqa: F401

PLATE, BRICK = 8, 24


def build(model):
    m = model.main

    m.step("The base")                       # the caption: what the page shows going on
    m.place("3020", "body", (0, 0, 0))       # part, palette role, position, rot(y=90), tag="eyes"
