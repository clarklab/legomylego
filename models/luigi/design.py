"""Luigi: JellsaTheBobJeffCreator's brick-built Mario (Rebrickable MOC-249307) with the red
swapped for green. The bricks are the same as models/mario (brickkit/designs/mario.py): this
model's palette (model.toml) makes the cap, the shirt and the stand green. The colour swap is
ours, not the designer's."""
from brickkit.designs.mario import build_plumber


def build(model):
    build_plumber(model)
