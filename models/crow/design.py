"""Crow: a Quick Bricks model, imported from MOC-165060_Qrys.And.Reading_crow.io (brickkit import).

Designed by Qrys.And.Reading (Rebrickable MOC-165060). Every part is where its designer put
it. Frame: LDU (stud 20, plate 8, brick 24), -Y up; the model's lowest point is on y = 0.
Colours are palette roles from model.toml.

The crow looks along -X (to the left as you face the model) and its tail points along +X.
The body leans back 5 degrees on its feet, and the tail and the wings sit on clips at angles
of their own, so most rotations are written out as R(...) matrices. "Near side" in the
captions is the side facing you (-Z), "far side" the other (+Z)."""
import numpy as np

from brickkit.ldraw.matrix import rot


def R(*m):
    """A part that is not on a quarter turn (a wing on its clip): its rotation, row by row."""
    return np.array(m, float).reshape(3, 3)


def build(model):
    # The beak and the brow go on as one. The jumper plate under the beak has nothing to
    # click onto (it lies on the chest), so the three are stacked in the hand first and
    # pressed onto the head together. They are the designer's step 7, in the same places.
    brow = model.submodel('brow', 'The beak and the brow')
    brow.step('Press the pointed plate onto the jumper plate, its point to the front')
    brow.place('15573', 'feather', (0, 0, 0), rot(y=90))
    brow.place('49668', 'feather', (0, -8, 0), rot(y=90), tag='beak')
    brow.step('Cap it with the tall curved brick: its curved end on the pointed plate, its stud end sticking out behind')
    brow.place('6091', 'feather', (20, -40, 0), rot(y=90))

    m = model.main

    m.step('The belly: a grey 2 x 3 plate, and the plate with two clips on its back end, clips pointing back')
    m.place('3021', 'grey', (-20, -39.901, 0), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1))
    m.place('60470b', 'feather', (0.621, -46.127, 0), R(0, -0.08716, -0.99619, 0, 0.9962, -0.08716, 1, 0, 0))

    m.step('Two small clip plates on the middle studs, one clip out to each side')
    m.place('4085c', 'feather', (-19.303, -47.871, -10), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1))
    m.place('4085c', 'feather', (-19.303, -47.871, 10), R(-0.99619, -0.08716, 0, -0.08716, 0.9962, 0, 0, 0, -1))

    m.step('A black 1 x 2 plate across the front studs, and a grey 2 x 2 plate on top of the clip plates')
    m.place('3023', 'feather', (-39.227, -49.614, 0), R(0, -0.08716, -0.99619, 0, 0.9962, -0.08716, 1, 0, 0))
    m.place('3022', 'grey', (-8.644, -54.969, 0), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1))

    m.step('The chest: the bracket on the front plate, its side hanging down in front, and the 1 x 2 slope '
           'on its two side studs, thin edge down')
    m.place('99781', 'feather', (-38.529, -57.583, 0), R(0, -0.08716, 0.99619, 0, 0.9962, 0.08716, -1, 0, 0),
            insert=(0.087, -0.996, 0))
    m.place('85984', 'feather', (-53.348, -48.842, 0), R(0, 0.99619, 0.08716, 0, 0.08716, -0.9962, -1, 0, 0))

    m.step('The back: the 2 x 2 curved brick on the grey plate, curving down to the tail, and a jumper plate on the bracket')
    m.place('47457', 'feather', (-17.211, -71.779, 0), R(0, -0.08716, -0.99619, 0, 0.9962, -0.08716, 1, 0, 0))
    m.place('15573', 'feather', (-37.832, -65.553, 0), R(0, -0.08716, 0.99619, 0, 0.9962, 0.08716, -1, 0, 0))

    m.step("The neck: the grey jumper plate on the curved brick's two studs, and a 1 x 1 plate on its stud")
    m.place('15573', 'grey', (-16.514, -79.749, 0), R(0, -0.08716, 0.99619, 0, 0.9962, 0.08716, -1, 0, 0))
    m.place('3024', 'feather', (-15.816, -87.718, 0), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1))

    m.step('The head: the brick with a stud on two sides, on the front jumper plate, its studs out to the sides')
    m.place('47905', 'feather', (-35.74, -89.462, 0), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1))

    m.step('Build the beak and the brow, and press them down onto the head: the stud end of the curved brick '
           "on the head brick's stud, the beak out in front, its jumper plate resting on the chest")
    m.use(brow, (-57.756, -67.296, 0), R(0.99619, -0.08716, 0, 0.08716, 0.9962, 0, 0, 0, 1), tag='brow')

    m.step("The back of the head: a curved slope, its thick end on the brow's stud and its thin end on the neck")
    m.place('11477', 'feather', (-25.778, -88.59, 0), R(0, -0.08716, -0.99619, 0, 0.9962, -0.08716, 1, 0, 0))

    m.step("The eyes: a jumper plate flat against each side of the head, on the brick's side stud, and a printed eye on each")
    m.place('15573', 'feather', (-46.574, -80.371, 18), R(0.99619, 0, -0.08715, 0.08715, 0, 0.99619, 0, -1, 0))
    m.place('98138p8f', 'eye', (-46.574, -80.371, 26), R(-0.90631, 0, 0.42262, -0.42262, 0, -0.90631, 0, -1, -0),
            tag='eye')
    m.place('15573', 'feather', (-46.574, -80.371, -18), R(0.99619, 0, 0.08716, 0.08716, 0, -0.9962, 0, 1, 0))
    m.place('98138p8f', 'eye', (-46.574, -80.371, -26), R(0.99619, 0, 0.08716, 0.08716, 0, -0.99619, 0, 1, 0),
            tag='eye')

    m.step('The tail: push the two handle plates into the clips at the back, the near one a little higher. '
           'On each, a grey quarter-round tile on the stud next to the body, and a curved slope with its thick '
           'end on the end stud, its thin end reaching past the end of the plate')
    m.place('60478', 'feather', (47.877, -54.532, -10), R(-0.93969, 0.34202, 0, 0.34202, 0.93969, 0, 0, 0, -1),
            tag='tail')
    m.place('60478', 'feather', (49.568, -49.571, 10), R(-0.98481, 0.17365, 0, 0.17365, 0.98481, 0, 0, 0, -1),
            tag='tail')
    m.place('25269', 'grey', (35.744, -58.629, -10), R(-0.93969, 0.34202, 0, 0.34202, 0.93969, 0, 0, 0, -1),
            tag='tail')
    m.place('25269', 'grey', (38.33, -55.713, 10), R(0, 0.17365, 0.98481, 0, 0.98481, -0.17365, -1, 0, 0),
            tag='tail')
    m.place('11477', 'feather', (69.407, -53.855, -10), R(0, 0.34202, -0.93969, 0, 0.93969, 0.34202, 1, 0, 0),
            tag='tail')
    m.place('11477', 'feather', (70.653, -45.166, 10), R(0, 0.17365, -0.98481, 0, 0.98481, 0.17365, 1, 0, 0),
            tag='tail')

    m.step('The wings: push a round handle plate into the clip on each side, its stud facing out, '
           'and press a curved slope on it by its thick end, the thin end pointing back')
    m.place('26047', 'feather', (-1.61, -42.307, 38.72), R(0.08716, 0.34072, 0.93612, -0.9962, 0.02981, 0.0819, 0, -0.93969, 0.34202),
            insert=(0, 0, 1), tag='wing')
    m.place('11477', 'feather', (10.476, -41.25, 34.622), R(-0.08716, 0.34072, -0.93612, 0.9962, 0.02981, -0.0819, 0, -0.93969, -0.34202),
            tag='wing')
    m.place('26047', 'feather', (-0.922, -42.247, -37.108), R(-0.08716, 0.25783, 0.96225, 0.9962, 0.02256, 0.08419, 0, 0.96593, -0.25882),
            insert=(0, 0, -1), tag='wing')
    m.place('11477', 'feather', (10.763, -41.225, -31.969), R(0.08716, 0.25783, -0.96225, -0.9962, 0.02256, -0.08419, 0, 0.96593, 0.25882),
            tag='wing')

    m.step('The legs and feet: press the grey plate with a handle up under the belly, handle down, '
           'and clip the two yellow feet onto the handle, side by side')
    m.place('30166', 'shield', (-22.266, -14, 0), R(0, -0.99619, -0.08716, 0, -0.08716, 0.9962, -1, 0, 0),
            tag='legs')
    m.place('92280', 'feet', (-32.266, -8, -10), tag='feet')
    m.place('92280', 'feet', (-32.266, -8, 10), tag='feet')
