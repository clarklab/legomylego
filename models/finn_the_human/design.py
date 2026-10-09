"""Finn the Human (Adventure Time): a lanky, posable figure. Our own design, worked out from
three pictures (NOTES.md): there are no plans, so the steps here are the build order we chose.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The table is y = 0 and +X
is Finn's left (your right as you face him). Heights below are given as h, LDU above the
table: a part's y is -h. Colours are palette roles from model.toml.

He is built in sections, each in its own frame, and hung on its joint:

  leg       origin: the middle of the hole in its top brick. Swings on a Technic pin (hip)
  arm       origin: the middle of the hole in its sleeve. Swings on a Technic pin (shoulder);
            the forearm hangs on a clip (elbow) and turns on the upper arm's stud
  head      origin: the middle of its underside. Turns on a 2 x 2 turntable (neck)
  backpack  built flat, studs up, then pressed onto four studs on his back
  sword     built flat; its bar goes in the clip of his right hand

A plate's, brick's or tile's origin is its top; a slope's (54200, 85984, 15068, 88930) is its
bottom, and those slopes fall towards their own -Z."""
import numpy as np

from brickkit.ldraw.matrix import rot

PLATE, BRICK = 8, 24

# ---- the pose (every joint is a real one: change these numbers and he still goes together) ----
HIP_SWING = {1: 0.0, -1: 0.0}     # each leg, degrees forward (+) or back (-) on its hip pin
ARM_SWING = {1: 0.0, -1: 0.0}     # each arm, degrees forward on its shoulder pin
ELBOW = {1: 140.0, -1: 90.0}      # degrees each elbow is bent (0 hangs straight)
ELBOW_TURN = {1: -90.0, -1: 90.0}  # the forearm turned on the upper arm's stud: 0 bends forward,
#                                    -90 (left) / 90 (right) bends out to his side
HEAD_TURN = 0.0                   # degrees the head is turned on its turntable
SWORD = True                      # the golden sword in his right hand

# ---- sizes ----
LEG_BRICKS = 7                    # round bricks of bare leg between the sock and the shorts
LEG_TOP = 40 + BRICK * LEG_BRICKS     # h of the top of the bare leg (shoe 16, sock 24)
HIP = LEG_TOP + 22                # h of the hip pins
PELVIS = HIP + 10                 # h of the top of the hips' Technic bricks
SHIRT = PELVIS + 16               # h of the bottom of the shirt (a spacer and the waistband)
SHOULDER = SHIRT + 62             # h of the shoulder pins (three bricks of shirt)
NECK = SHIRT + 88                 # h of the turntable's top: the head's underside
LEG_X, LEG_Z = 30, 10             # where each leg stands
ARM_X = 50                        # each arm hangs here, against the side of the shirt


def orient(ex, ey) -> np.ndarray:
    """3x3 rotation whose columns are where the part's local X, Y and Z axes point."""
    ex, ey = np.asarray(ex, float), np.asarray(ey, float)
    return np.column_stack([ex, ey, np.cross(ex, ey)])


FRONT = orient((1, 0, 0), (0, 0, 1))      # studs towards you (-Z); the part's own +Z points up
BACK = orient((-1, 0, 0), (0, 0, -1))     # studs away from you (+Z); the part's own +Z points up
ACROSS = rot(y=90)                        # a Technic brick's hole (its own Z) along X
CLIP_DOWN = rot(y=90)                     # a 3484 gripping a bar that runs along X, its own bar down
HAND = rot(y=90)                          # the hand plate in the forearm: studs up, its long side
#                                           front to back, its clip to Finn's right (-X)
HAND_AT = np.array([0.0, 62.0, -10.0])    # where it goes, and where its clip then is
HAND_CLIP = HAND_AT + HAND @ np.array([0.0, 2.0, -20.0])
ELBOW_AT = np.array([0.0, 64.0, 0.0])     # the upper arm's handle is 20 from here, to the front


def build_leg(model, side):
    """A leg, standing. `side` +1 is his left (+X). Origin: the middle of the hole in the
    Technic brick at its top (the hip pin's line, along X)."""
    name = "left" if side > 0 else "right"
    leg = model.submodel(name + "_leg", name.title() + " leg")
    top = 22                                              # y of the top of the bare leg
    sole = top + BRICK * (LEG_BRICKS + 1) + PLATE         # y of the sole's top
    ankle = sole - PLATE                                  # y of the top of the shoe's jumper plate
    leg.step("The shoe: a 2 x 4 plate. On it, behind the toe's two studs: a 1 x 2 plate, a 1 x 2 "
             "plate with one stud, and a slope for the heel")
    leg.place("3020", "shoe", (0, sole, -10), rot(y=90), tag="shoe")
    leg.place("3023", "shoe", (0, sole - PLATE, -20), tag="shoe")
    leg.place("15573", "shoe", (0, ankle, 0), tag="shoe")
    leg.place("85984", "shoe", (0, sole, 20), rot(y=180), tag="shoe")
    leg.step("The toe: a curved slope, its high end on the 1 x 2 plate")
    leg.place("15068", "shoe", (0, sole, -30), tag="shoe")
    leg.step("The sock: a white round brick on the single stud")
    leg.place("3062b", "sock", (0, top + BRICK * LEG_BRICKS, 0), tag="sock")
    leg.step(f"The leg: {LEG_BRICKS} round bricks. Push two long bars down through them, one "
             "after the other, into the hole in the shoe's stud: they stiffen the leg")
    for k in reversed(range(LEG_BRICKS)):
        leg.place("3062b", "skin", (0, top + BRICK * k, 0), tag="leg")
    leg.place("30374", "spine", (0, ankle - 80, 0), tag="spine", insert=(0, -1, 0))
    leg.place("30374", "spine", (0, ankle - 160, 0), tag="spine", insert=(0, -1, 0))
    leg.step("The leg of his shorts: a 1 x 2 plate pointing forward, a small slope on its front "
             "stud and a Technic brick on its back stud, the hole across")
    leg.place("3023", "shorts", (0, 14, -10), rot(y=90), tag="shorts_leg")
    leg.place("54200", "shorts", (0, 14, -20), tag="shorts_leg")
    leg.place("6541", "shorts", (0, -10, 0), ACROSS, tag="hip")
    return leg


def build_forearm(model, name, hand):
    """A forearm, hanging. Origin: the middle of its clip (the elbow's line, along X). `hand`:
    with a plate that has a clip on its side under its end (the sword hand): with the elbow
    bent out to his right, the plate is in front and the clip behind it."""
    arm = model.submodel(name, "Forearm")
    arm.step("A forearm: push the bar of a clip into the top of a round brick, and add a "
             "second round brick under it")
    arm.place("3484", "skin", (0, 0, 0), CLIP_DOWN, tag="elbow_clip")
    arm.place("3062b", "skin", (0, 14, 0), tag="forearm")
    arm.place("3062b", "skin", (0, 38, 0), tag="forearm")
    if hand:
        arm.step("The hand: a plate with a clip on its side. Press one of its studs up into "
                 "the forearm, the other stud to the front, the clip to the right")
        arm.place("11476", "skin", tuple(HAND_AT), HAND, tag="hand", insert=(0, 1, 0))
    return arm


def build_arm(model, side, forearm):
    """An arm, hanging. Origin: the middle of the hole in its sleeve (the shoulder pin's line,
    along X). `side` +1 is his left."""
    name = "left" if side > 0 else "right"
    arm = model.submodel(name + "_arm", name.title() + " arm")
    turn, bend = ELBOW_TURN[side], ELBOW[side]
    arm.step("The sleeve: a blue Technic brick, its hole across, with a tile on top. Under it "
             "two round bricks, and a round plate with a handle: the upper arm")
    arm.place("6541", "shirt", (0, -10, 0), ACROSS, tag="sleeve")
    arm.place("3070b", "shirt", (0, -18, 0), tag="sleeve")
    arm.place("3062b", "skin", (0, 14, 0), tag="upper_arm", insert=(0, 1, 0))
    arm.place("3062b", "skin", (0, 38, 0), tag="upper_arm", insert=(0, 1, 0))
    arm.place("26047", "skin", (0, 62, 0), rot(y=turn), tag="elbow", insert=(0, 1, 0))
    handle = ELBOW_AT + rot(y=turn) @ np.array([0.0, 0.0, -20.0])
    arm.step("Clip the forearm onto the handle: the elbow")
    arm.use(forearm, tuple(handle), rot(x=-bend, y=turn), tag="forearm")
    return arm


def build_sword(model):
    """The sword, lying flat, blade towards +X, its flat side up. Origin: the middle of the
    stretch of its bar that the hand's clip holds."""
    sword = model.submodel("sword", "Sword")
    ox, oy = 91, -2                   # the tile's middle is 91 along the blade from the origin
    #                                   (the bar is only bar-thick for its last 14: the clip holds
    #                                   it there, with 2 to spare before the jewel's stud)
    sword.step("The sword: a long yellow tile. Under one end a round plate with a bar, the bar "
               "pointing away from the blade; next to it a 1 x 3 plate across: the guard")
    sword.place("32828", "hilt", (ox - 70, oy, 0), rot(y=180), tag="sword")
    sword.place("3623", "blade", (ox - 50, oy, 0), rot(y=90), tag="sword")
    sword.place("4162", "blade", (ox, oy - 8, 0), tag="sword")
    sword.step("A red round plate, the hole in its stud pushed onto the end of the bar: the "
               "jewel")
    sword.place("85861", "jewel", (-10, oy + 2, 0), orient((0, 1, 0), (-1, 0, 0)),
                tag="sword", insert=(-1, 0, 0))
    return sword


def build_head(model):
    """The head. Origin: the middle of its underside (hh below is height above that). It is a
    hollow white box, 6 x 4 studs; the face is built sideways on a 4 x 4 plate, studs forward,
    set 4 LDU back into the hat."""
    head = model.submodel("head", "Head")

    def hh(v):
        return -v

    FACE, RAISED = -36, -44          # z of the fronts of the face's tiles, and of what stands on them
    head.step("The bottom of the hat: the turntable's top, and a 4 x 6 plate pressed onto its "
              "four studs, its middle over them. On the plate a 1 x 6 tile along the front (the "
              "face stands on this), a 2 x 6 plate and a 1 x 6 plate")
    head.place("3679", "turntable", (0, 0, 0), tag="neck")
    head.place("3032", "hat", (0, hh(8), 0), tag="hat")
    head.place("6636", "hat", (0, hh(16), -30), tag="chin")
    head.place("3795", "hat", (0, hh(16), 0), tag="hat")
    head.place("3666", "hat", (0, hh(16), 30), tag="hat")
    head.step("Behind where the face will go: two 1 x 4 plates and a brick with four studs on "
              "its side, studs forward")
    head.place("3710", "hat", (0, hh(24), -10), tag="hat")
    head.place("3710", "hat", (0, hh(32), -10), tag="hat")
    head.place("30414", "hat", (0, hh(56), -10), tag="hat")
    head.step("The face: a 4 x 4 plate standing on its edge, on the four studs. A white tile "
              "along its top row and a skin one under it: the forehead")
    head.place("3031", "hat", (0, hh(56), -28), FRONT, tag="face_plate")
    head.place("2431", "hat", (0, hh(86), FACE), FRONT, tag="brow")
    head.place("2431", "skin", (0, hh(66), FACE), FRONT, tag="face")
    head.step("The eyes, wide apart: a 1 x 1 plate at each end of the row with a round black "
              "tile on it, and a 1 x 2 tile between them")
    for x in (-30, 30):
        head.place("3024", "skin", (x, hh(46), FACE), FRONT, tag="face")
        head.place("98138", "eye", (x, hh(46), RAISED), FRONT, tag="eyes")
    head.place("3069b", "skin", (0, hh(46), FACE), FRONT, tag="face")
    head.step("The mouth: a 1 x 2 plate between two tiles, and the half circle on it, flat edge "
              "up")
    for x in (-30, 30):
        head.place("3070b", "skin", (x, hh(26), FACE), FRONT, tag="face")
    head.place("3023", "skin", (0, hh(26), FACE), FRONT, tag="face")
    head.place("1748", "mouth", (0, hh(26), RAISED), FRONT, tag="mouth")
    head.step("The sides and the back of the hat: a tall 1 x 4 brick each side, a tall panel "
              "behind with its wall to the back, and a 1 x 4 plate on each")
    head.place("49311", "hat", (50, hh(88), 0), rot(y=90), tag="hat")
    head.place("49311", "hat", (-50, hh(88), 0), rot(y=90), tag="hat")
    head.place("60581", "hat", (0, hh(88), 30), tag="hat")
    head.place("3710", "hat", (50, hh(96), 0), rot(y=90), tag="hat")
    head.place("3710", "hat", (-50, hh(96), 0), rot(y=90), tag="hat")
    head.place("3710", "hat", (0, hh(96), 30), tag="hat")
    head.step("The top: a 4 x 6 plate, and a 2 x 6 plate across its middle")
    head.place("3032", "hat", (0, hh(104), 0), tag="hat")
    head.place("3795", "hat", (0, hh(112), 0), tag="hat")
    head.step("Round it off: a curved slope in the middle of the front and of the back, and "
              "a 1 x 2 slope each side of them")
    head.place("15068", "hat", (0, hh(104), -20), tag="hat")
    head.place("15068", "hat", (0, hh(104), 20), rot(y=180), tag="hat")
    for x in (-40, 40):
        head.place("85984", "hat", (x, hh(104), -30), tag="hat")
        head.place("85984", "hat", (x, hh(104), 30), rot(y=180), tag="hat")
    head.step("The ears: a 2 x 2 dome on each end of the 2 x 6 plate, standing a plate deep in "
              "the top of the hat")
    for x in (-40, 40):
        head.place("30367c", "hat", (x, hh(136), 0), tag="ear")
    return head


def build_backpack(model):
    """The backpack, lying flat, studs up: 8 studs wide, so it shows behind his arms. Lime
    above (a half circle), green below (shallower, with round corners). Its own +Z is up on
    Finn's back; its origin is the middle of the underside of its mounting plate, on the line
    where the two colours meet. The mounting plate is a 2 x 4 wedge, wide edge up: its cut
    corners leave room for the tops of his legs when they swing forward."""
    pack = model.submodel("backpack", "Backpack")
    pack.step("The backpack: a 2 x 4 wedge plate, wide edge away from you, and a 1 x 1 plate "
              "three studs out from each of its near corners (clear of his arms)")
    pack.place("51739", "pack_low", (0, -8, 0), tag="backpack")
    for x in (-70, 70):
        pack.place("3024", "pack_low", (x, -8, -10), tag="backpack")
    pack.step("Green, on the near studs: a 2 x 3 plate in the middle and a round corner plate "
              "each side on the 1 x 1 plates, the round corners towards you and out")
    pack.place("3021", "pack_low", (0, -16, -30), rot(y=90), tag="backpack")
    pack.place("30357", "pack_low", (30, -16, -10), rot(y=90), tag="backpack")
    pack.place("30357", "pack_low", (-30, -16, -10), rot(y=180), tag="backpack")
    pack.step("Lime, on the far studs: a half circle, round side away from you")
    pack.place("22888", "pack_top", (0, -16, 40), rot(y=180), tag="backpack")
    pack.step("A 2 x 4 curved slope on each colour, their high edges meeting in the middle")
    pack.place("88930", "pack_low", (0, -16, -20), tag="backpack")
    pack.place("88930", "pack_top", (0, -16, 20), rot(y=180), tag="backpack")
    return pack


def build(model):
    m = model.main
    legs = {s: build_leg(model, s) for s in (1, -1)}
    arms = {s: build_arm(model, s, build_forearm(
        model, ("left" if s > 0 else "right") + "_forearm", hand=SWORD and s < 0))
        for s in (1, -1)}
    pack = build_backpack(model)
    head = build_head(model)
    sword = build_sword(model) if SWORD else None

    def y(h):
        return -h

    m.step("The hips: a 2 x 2 plate. On its back studs two Technic bricks, their holes across; "
           "on its front studs a 1 x 2 brick")
    m.place("3022", "shorts", (0, y(PELVIS - BRICK), 0), tag="hips")
    for x in (-10, 10):
        m.place("6541", "shorts", (x, y(PELVIS), 10), ACROSS, tag="hips")
    m.place("3004", "shorts", (0, y(PELVIS), -10), tag="hips")
    m.step("A 2 x 2 plate on top, then the waistband: a 2 x 4 plate. Push a black pin into "
           "each Technic brick from the outside")
    m.place("3022", "shorts", (0, y(PELVIS + 8), 0), tag="shorts")
    m.place("3020", "shorts", (0, y(SHIRT), 0), tag="shorts")
    for s in (1, -1):
        m.place("2780", "pin", (20 * s, y(HIP), LEG_Z), tag="hip_pin", insert=(s, 0, 0))
    m.step("The shirt: a 1 x 4 brick in front, and two bricks with studs on their sides behind "
           "it, studs to the back")
    m.place("3010", "shirt", (0, y(SHIRT + 24), -10), tag="shirt")
    for x in (-20, 20):
        m.place("11211", "shirt", (x, y(SHIRT + 24), 10), rot(y=180), tag="shirt")
    m.step("A 2 x 4 brick")
    m.place("3001", "shirt", (0, y(SHIRT + 48), 0), tag="shirt")
    m.step("The shoulders: a 2 x 2 brick between two Technic bricks, their holes across. Push "
           "a black pin into each from the outside")
    m.place("3003", "shirt", (0, y(SHIRT + 72), 0), tag="shirt")
    for s in (1, -1):
        m.place("3700", "shirt", (30 * s, y(SHIRT + 72), 0), ACROSS, tag="shirt")
        m.place("2780", "pin", (40 * s, y(SHOULDER), 0), tag="shoulder_pin", insert=(s, 0, 0))
    m.step("The neck: a round white plate and the turntable's base")
    m.place("4032a", "hat", (0, y(SHIRT + 80), 0), tag="neck")
    m.place("3680", "hat", (0, y(NECK), 0), tag="neck")
    for s, text in ((1, "Push his left leg onto the pin under the shorts, standing straight"),
                    (-1, "And his right leg")):
        m.step(text)
        m.use(legs[s], (LEG_X * s, y(HIP), LEG_Z), rot(x=-HIP_SWING[s]),
              tag="left_leg" if s > 0 else "right_leg", insert=(s, 0, 0))
    for s, text in ((-1, "Push his right arm onto the pin in his shoulder, its forearm out to "
                         "his side"),
                    (1, "And his left arm, waving")):
        m.step(text)
        m.use(arms[s], (ARM_X * s, y(SHOULDER), 0), rot(x=-ARM_SWING[s]),
              tag="left_arm" if s > 0 else "right_arm", insert=(s, 0, 0))
    m.step("Press the backpack onto the four studs on his back")
    m.use(pack, (0, y(SHIRT + 4), 20), BACK, tag="backpack", insert=(0, 0, 1))
    m.step("Press the head onto the turntable")
    m.use(head, (0, y(NECK), 0), rot(y=HEAD_TURN), tag="head")
    if sword is not None:
        s = -1                                                    # his right hand holds it
        Ra = rot(x=-ARM_SWING[s])
        Rf = rot(x=-ELBOW[s], y=ELBOW_TURN[s])
        handle = ELBOW_AT + rot(y=ELBOW_TURN[s]) @ np.array([0.0, 0.0, -20.0])
        grip = np.array([ARM_X * s, y(SHOULDER), 0.0]) + Ra @ (handle + Rf @ HAND_CLIP)
        # the blade along the hand's long side, its flat side to the front (the hand's +Z)
        m.step("Clip the sword's bar into his right hand from behind, blade up, flat side "
               "forward")
        m.use(sword, tuple(grip), Ra @ Rf @ HAND @ rot(x=-90), tag="sword")
