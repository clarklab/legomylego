"""Charmander: a small Quick Bricks model, 14 pieces, about 4 cm long and 3 cm tall: an orange
body on two round feet, a tan belly, little cheese-slope arms, a head with a curved dome and a
black eye band, and a tail that ends in a trans-orange flame.

The design is SwordBricks' (RSierra), Rebrickable MOC-220190, taken in from its BrickLink Studio
file by `brickkit import`: every part is where its designer put it. NOTES.md says what was
changed (the cone's mould, and the order of the last two head pieces) and what else is in the
Studio file.

Frame: LDU (stud 20, plate 8, brick 24), -Y up; the model's lowest point is on y = 0.
Charmander faces -X: the tail and its flame go out towards +X. The feet are on x = -18, one
stud wide, side by side across z. Colours are palette roles from model.toml."""
from brickkit.ldraw.matrix import rot


def build(model):
    # the designer faced it along -X, not the engine's -Z: turn the stills and the video round
    # so "front" is Charmander's face
    model.meta["azimuth_offset"] = -90

    m = model.main

    m.step("The feet: two round 1 x 1 plates, side by side")
    m.place('6141', 'body', (-18, -8, -10))
    m.place('6141', 'body', (-18, -8, 10))

    m.step("The legs: a 1 x 2 plate across both feet, then a jumper plate on top of it")
    m.place('3023b', 'body', (-18, -16, 0), rot(y=-90))
    m.place('15573', 'body', (-18, -24, 0), rot(y=-90))

    m.step("The body: a black brick with studs on all four sides, on the jumper's middle stud")
    m.place('4733', 'core', (-18, -48, 0))

    m.step("The belly and the back: a tan tile on the front stud, an orange plate standing "
           "on the back stud")
    m.place('3069b', 'belly', (-36, -28, 0), rot(z=-90), tag="belly")
    m.place('3023b', 'body', (0, -28, 0), rot(z=90))

    m.step("The arms: an orange cheese slope on each side stud")
    m.place('54200', 'body', (-18, -38, -10), rot(x=90, z=180))
    m.place('54200', 'body', (-18, -38, 10), rot(x=-90))

    m.step("The tail: a cone on the back plate, pointing out behind, and the flame on its tip")
    m.place('59900', 'body', (24, -18, 0), rot(y=90, z=90), tag="tail")
    m.place('64647', 'flame', (22.74, -18, 0), rot(y=-90, z=90), tag="flame")

    m.step("The head: a 1 x 2 plate on the body's top stud, reaching forward, and a black "
           "plate on its back stud for the eye band")
    m.place('3023b', 'body', (-28, -56, 0))
    m.place('3024', 'eyes', (-18, -64, 0), tag="face")

    m.step("The dome: a curved slope over both, its low end out front, its high end over the "
           "black plate")
    m.place('11477', 'body', (-28, -56, 0), rot(y=90), tag="face")
