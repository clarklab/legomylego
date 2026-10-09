"""Freddy Fazbear: a small brown bear robot with a top hat, a bow tie and a microphone, 42 pieces.

Built from the 32 numbered pages of MOC-265184's plans (inbox/freddy_fazbear/, local only): one
step here per page. NOTES.md has the page-by-page parts list and what had to be worked out,
including the three steps that are in a different order from the pages (6, 10, 11: the pages
close the hip's gap before the parts that go in it) and the parts that differ from the pages
(the handle plates for the clip plates, the Tan belly tile, the Black neck plate).

Frame: LDU, -Y up, the front faces -Z; +X is the bear's left (the way the plans' camera sees
its side). The feet's tops are y = 0; the legs stand on the back stud (z = +10) of each foot.

Most of the body is built sideways (SNOT): plates whose studs face front. Their positions are
written as layers in z (front is negative) and rows in y (20 apart):

  hip     2 x 3 plate (z 16..24) | gap (z 8..16: two handle plates, a rounded 1 x 2 plate) |
          2 x 2 plate (z 0..8) | belly tile (z -8..0)
  head    handle plate A (z 0..8) on 2 x 2 plate B (z 8..16); 1 x 2 plates C and D, then the
          muzzle and the nose in front; the inverted slope and a 1 x 2 plate behind

A plate's, brick's or tile's origin is its top (the face its studs rise from); a cheese slope's
(54200) is its bottom. For a part with its studs facing front that origin is the FRONT face."""
import math

import numpy as np

from brickkit.ldraw.matrix import rot

PLATE = 8
LEGS = (-10, 10)                  # x of the right (-x) and left (+x) leg
LEG_Z = 10                        # the back stud of each foot
ARM_X = 33                        # where an arm clips on the shoulder bar (|x|)
ARM_RELAXED = 40                  # degrees the left forearm is swung down from straight forward
ARM_MIC = 15                      # the right arm, raised to hold the microphone


def orient(ex, ey, ez=None) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    ez = np.cross(ex, ey) if ez is None else np.asarray(ez, float)
    return np.column_stack([ex, ey, ez])


# Studs facing front (local -Y -> world -Z). The first has local -Z pointing DOWN (a clip or a
# handle at the bottom edge), the second has local -Z pointing UP (clips at the top edge).
FRONT = orient((1, 0, 0), (0, 0, 1))
FRONT_UP = orient((-1, 0, 0), (0, 0, 1))
# a plate standing 3 high, studs front (the 2 x 3 hip plate: its long side vertical)
FRONT_TALL = orient((0, -1, 0), (0, 0, 1))
# cheese slopes on a front stud, the slope falling towards the middle of the bow tie
SLOPE_L = orient((0, -1, 0), (0, 0, 1))        # the left (-x) wing: high at -x, low towards +x
SLOPE_R = orient((0, 1, 0), (0, 0, 1))
# a bar-holder or an arm hanging from a lateral bar: local x -> front, y -> down, z -> +x
HANG = rot(y=90)


def arm_pose(theta):
    """A 98313 mechanical arm hung by its clip from a lateral bar at the shoulder (the arm's
    origin is the clip, on the bar's axis at x = 0 here; the caller adds the x), swung `theta`
    degrees from pointing straight forward down towards the ground. Returns the arm's rotation,
    the hand's (offset, rotation) and the microphone's, the hand pushed 9 LDU into the rod hole
    at the forearm's end, its clip's axis as near to vertical as the forearm allows."""
    t = math.radians(theta)
    s_, c_ = math.sin(t), math.cos(t)
    ex, ey = np.array((0, s_, -c_)), np.array((0, c_, s_))      # the arm's x (forearm) and y
    R_arm = orient(ex, ey)
    hole = 38 * ex + 17.5 * ey                                  # the rod hole at the forearm's end
    hand_pos = hole + 21 * ex                                   # its bar 9 deep, 12 outside
    R_hand = orient((1, 0, 0), -ex, (0, -c_, -s_))              # bar along the forearm, clip up
    ey_mic = np.array((0, c_, s_))                              # the handle, dome to bottom
    R_mic = orient((1, 0, 0), ey_mic)
    mic_pos = hand_pos - 6.5 * ey_mic                           # the clip on the handle
    # the offsets are relative to the clip on the bar (y = ROW1, z = 10 in the model's frame)
    base = np.array((0, ROW1, 10))
    return R_arm, (base + hand_pos, R_hand), (base + mic_pos, R_mic)


# rows (y of a one-stud row's centre) and layers (z of a plate's front face)
ROW3, ROW2, ROW1 = -66, -86, -106              # the hip: 2 x 3 plate rows, bottom to top
HEAD_LOW, HEAD_TOP = -146, -166                # A, C, D, the muzzle | B's top row, the ears
LEG_TOP = -46                                  # the holder's origin (its clip)


def build(model):
    m = model.main

    # ---- the legs: foot, round plate, tile with a pin, holder with a clip
    m.step("The first foot: a 1 x 2 plate")
    m.place("3023", "body", (LEGS[0], 0, 0), rot(y=90), tag="foot")

    m.step("A round plate on its back stud")
    m.place("6141", "body", (LEGS[0], -PLATE, LEG_Z))

    m.step("A round tile with a pin on top")
    m.place("20482", "body", (LEGS[0], -2 * PLATE, LEG_Z))

    m.step("The leg: a holder with a clip over the pin")
    m.place("11090", "body", (LEGS[0], LEG_TOP, LEG_Z), HANG, tag="leg")

    # ---- the hip
    # The pages show a 1 x 1 plate with a horizontal clip here (61252, rare in Reddish Brown);
    # brickkit has no clip-hooks-into-clip snap, so this is the common 1 x 1 plate with a side
    # handle, whose bar the leg's clip grips. It lies in the hip's gap (z 8..16), its underside
    # on a stud of the 2 x 3 plate, its stud facing front into a socket of the 2 x 2 plate, its
    # handle hanging below.
    m.step("A plate with a side handle, studs facing front, its handle in the leg's clip")
    m.place("26047", "body", (LEGS[0], ROW3, 8), FRONT, tag="handle_plate")

    # (the pages put the 2 x 2 plate on here, but a 2 x 3 plate, the handle plates and the
    # rounded plate go together in a gap the 2 x 2 plate then closes: it goes on in step 11)
    m.step("The hip: a 2 x 3 plate standing up, studs facing front, behind the handle plate")
    m.place("3021", "body", (0, ROW2, 16), FRONT_TALL, tag="hip")

    m.step("The second handle plate")
    m.place("26047", "body", (LEGS[1], ROW3, 8), FRONT, tag="handle_plate")

    m.step("The second leg's holder, pushed up onto the handle")
    m.place("11090", "body", (LEGS[1], LEG_TOP, LEG_Z), HANG, tag="leg")

    m.step("The second foot goes on from underneath: a tile with a pin, a round plate, a 1 x 2 plate")
    m.place("20482", "body", (LEGS[1], -2 * PLATE, LEG_Z), insert=(0, 1, 0))
    m.place("6141", "body", (LEGS[1], -PLATE, LEG_Z), insert=(0, 1, 0))
    m.place("3023", "body", (LEGS[1], 0, 0), rot(y=90), tag="foot", insert=(0, 1, 0))

    # ---- the belly and the shoulders
    m.step("A rounded 1 x 2 plate on the 2 x 3 plate's middle studs")
    m.place("35480", "body", (0, ROW2, 8), FRONT, tag="hip_fill")

    m.step("The belly: a 2 x 2 plate over the handle plates and the rounded plate, and a round tile on it")
    m.place("3022", "body", (0, (ROW2 + ROW3) / 2, 0), FRONT, tag="hip")
    m.place("14769", "belly", (0, (ROW2 + ROW3) / 2, -8), FRONT, tag="belly")

    m.step("The shoulders: two round plates with a bar, bars pointing out")
    m.place("32828", "body", (LEGS[0], ROW1, 8), FRONT_UP, tag="shoulder")
    m.place("32828", "body", (LEGS[1], ROW1, 8), FRONT, tag="shoulder")

    # ---- the arms
    m.step("The left arm: a mechanical arm clipped on the bar")
    R, hand, _ = arm_pose(ARM_RELAXED)
    m.place("98313", "body", (ARM_X, ROW1, 10), R, tag="arm_l")

    m.step("Its hand, pushed into the end of the forearm")
    m.place("3484", "body", hand[0] + np.array((ARM_X, 0, 0)), hand[1], tag="hand_l")

    m.step("The right arm")
    R, hand, mic = arm_pose(ARM_MIC)
    m.place("98313", "body", (-ARM_X, ROW1, 10), R, tag="arm_r")

    m.step("Its hand")
    m.place("3484", "body", hand[0] + np.array((-ARM_X, 0, 0)), hand[1], tag="hand_r")

    m.step("The microphone in the right hand")
    m.place("90370p05", "mic", mic[0] + np.array((-ARM_X, 0, 0)), mic[1], tag="mic")

    # ---- the neck and the bow tie
    m.step("The neck: a plate with two clips pointing up, on the shoulders' studs")
    m.place("60470b", "neck", (0, ROW1, 0), FRONT_UP, tag="neck")

    m.step("A black 1 x 2 plate for the bow tie")
    m.place("3023", "tie", (0, ROW1, -8), FRONT, tag="tie")

    m.step("The bow tie: two slopes")
    m.place("54200", "tie", (-10, ROW1, -8), SLOPE_L, tag="tie")
    m.place("54200", "tie", (10, ROW1, -8), SLOPE_R, tag="tie")

    # ---- the head
    m.step("The head: a plate with a handle, its handle in the neck's clips")
    m.place("48336", "body", (0, HEAD_LOW, 0), FRONT, tag="head")

    m.step("A 2 x 2 plate behind it and a 1 x 2 plate in front")
    m.place("3022", "body", (0, (HEAD_TOP + HEAD_LOW) / 2, 8), FRONT, tag="head")
    m.place("3023", "body", (0, HEAD_LOW, -8), FRONT, tag="head")

    # The inverted slope (76959, the shape of 3660) goes behind B, its studs in B's sockets and
    # its slanted face at the back and below. How the page has it is not clear (see NOTES.md).
    m.step("Another 1 x 2 plate in front, and a slope behind the head")
    m.place("3023", "body", (0, HEAD_LOW, -16), FRONT, tag="head")
    m.place("76959", "body", (0, HEAD_TOP, 16), FRONT, tag="head")

    m.step("The muzzle: a 1 x 2 plate with a stud in the middle")
    m.place("15573", "muzzle", (0, HEAD_LOW, -24), FRONT, tag="muzzle")

    m.step("The nose: a round tile")
    m.place("98138", "tie", (0, HEAD_LOW, -32), FRONT, tag="nose")

    m.step("The ears' bars: two round plates with a bar on the head's top studs")
    m.place("32828", "body", (LEGS[0], HEAD_TOP, 0), FRONT_UP, tag="ear_bar")
    m.place("32828", "body", (LEGS[1], HEAD_TOP, 0), FRONT, tag="ear_bar")

    # The bracket: its 1 x 2 leaf on the posts' hollow studs, its 2 x 2 leaf the roof, studs up.
    # The 1 x 2 plate on the page goes where, I could not tell: it is on the back of the slope.
    m.step("The head's top: a bracket, and a plate at the back")
    m.place("44728", "body", (0, HEAD_TOP, -8), FRONT_UP, tag="head")
    m.place("3023", "body", (0, HEAD_TOP, 40), FRONT, tag="head")

    m.step("The eyes: two round tiles on the front studs")
    for x in LEGS:
        m.place("98138p07", "eye", (x, HEAD_TOP, -16), FRONT, tag="eyes")

    # an open-stud round plate: the post's tip (|x| = 40) goes 2 LDU into the hole under it
    m.step("The right ear: a round plate on the bar's end")
    m.place("85861", "body", (-38, HEAD_TOP, 2), orient((0, 0, 1), (1, 0, 0)), tag="ear")

    m.step("The left ear")
    m.place("85861", "body", (38, HEAD_TOP, 2), orient((0, 0, 1), (-1, 0, 0)), tag="ear")

    m.step("The hat's brim: a black round plate on the top studs")
    m.place("4032a", "tie", (0, -188, 12), tag="hat")

    m.step("The top of the hat: a black round brick")
    m.place("3062b", "tie", (-10, -212, 22), tag="hat")
