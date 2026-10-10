"""Xenomorph: a Quick Bricks model. yodakya's design (Rebrickable MOC-34927), imported from the
designer's Studio file and then posed so that every joint really closes and it stands.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the front faces -Z. The table is y = 0, the
figure's middle is x = 0 and its hip bar is over z = 0. Colours are palette roles from
model.toml.

It is an articulated figure, so it is built as sub-assemblies, each flat and square in its own
frame, and then hung on its joint at an angle. Every angle is a pitch: a turn about the
side-to-side axis (X), + nose down. NOTES.md has the joints and what changed from the file."""
import math

import numpy as np

from brickkit.ldraw.matrix import rot

# The pose --------------------------------------------------------------------------------
# The file's pose does not stand: its middle is behind its feet and its tail is in the air. So
# the whole figure is tipped back, as it tips by itself, until the barb at the end of the tail
# is on the table: two feet and the barb. LEAN and HIPS were found together so that the barb's
# point comes down level with the soles (LEAN 7.5 to 8.2 also keeps the video planner's ways
# onto the tail's hinges clear; HIPS then sets the height: 0.1 more LEAN wants 1.1 less HIPS).
LEG = math.degrees(math.atan(0.6))   # 30.96: the thigh leans back just so far that the slope of
#                                      the heel and the toe lie flat on the table (a cheese
#                                      slope rises 12 in 20); 38.1 in the file
LEAN = 7.75         # how far the body is tipped back from the file's pose
TAIL = -LEAN        # the tail's own frame: in it the level links are level, as in the file
TORSO = TAIL + 22.5   # the torso leans forward; the tail's first link is one click off its line
HIPS = 4.5          # the hip piece's stem leans forward (14.4 less the lean in the file)
HEAD = TORSO - 7.0    # the head, nose down: 7 less than the torso, as in the file
ARMS = TAIL           # the arms reach straight forward in the file's pose
LINKS = (-45.0, 0.0, 45.0, 0.0)   # the tail's four links, each from the level: down, level, up, level
TIP = -45.0           # the end link and the barb (36 in the file: between two clicks)

HIP_X = 16.0        # each leg's clip is at the end of the hip bar
HIP_Y = -(48 * math.cos(math.radians(LEG)) + 50 * math.sin(math.radians(LEG)))   # hip bar height
WAIST = 16.0        # the waist clip sits at the top end of the hip piece's stem (14 in the file)
SPINE = 22.0        # a tail spine's clip above its link: its bar ends flush underneath
CREST = 16.0        # the crest's T-bar above its link, so the spines' jaws clear it (14.5 in the file)
TUBES = ((-8, -48.0), (8, -48.0), (-16, -20.0), (16, -20.0))   # the back's four tubes: where on
#                     the cross bar, and how far each droops from the line of the back (the outer
#                     two 10 more than in the file: the saddle in the right one's end clip then
#                     clears the back of the head by 4 LDU and more)


def axes(x, y, z):
    """A rotation given by where a part's own X, Y and Z axes point."""
    return np.column_stack((x, y, z)).astype(float)


def hang(pivot, R, point):
    """Where a part or sub-assembly turned by R goes so that its own `point` is on `pivot`."""
    return tuple(np.asarray(pivot, float) - R @ np.asarray(point, float))


def up(deg):
    """The unit vector that -Y becomes under a pitch."""
    return rot(x=deg) @ np.array([0.0, -1.0, 0.0])


def back(deg):
    """The unit vector that +Z becomes under a pitch."""
    return rot(x=deg) @ np.array([0.0, 0.0, 1.0])


EX, EY, EZ = np.eye(3)


def build_leg(model, side):
    """A leg, lying flat: the thigh plate studs up, hip end at -X. `side` +1 is the figure's
    right (it ends up at +X), -1 its left: mirror images. The hip clip's middle is at
    (-20, -4, 20 * side)."""
    name = "right" if side > 0 else "left"
    leg = model.submodel(name + "_leg", name.title() + " leg")
    flip = None if side > 0 else rot(y=180)
    leg.step("The thigh: a 1 x 3 plate. On its middle stud a 1 x 1 plate; on one end stud a "
             "plate with a ring, ring out to the side: the ankle")
    leg.place("3623", "black", (0, 0, 0), tag="thigh")
    leg.place("3024", "black", (0, -8, 0), tag="thigh")
    leg.place("4081b", "black", (20, -8, 0), flip, tag="ankle")
    leg.step("On the other end stud a plate with an upright clip, clip out to the other side: "
             "the hip")
    leg.place("60897", "black", (-20, -8, 0), rot(y=180) if side > 0 else None, tag="hip_clip")
    leg.step("The foot: a 1 x 2 plate, standing on edge. Push one of its end holes onto the rim "
             "of the ring that faces the hip, so that it points away from the thigh")
    foot = axes(EZ, EX, EY) if side > 0 else axes(-EZ, EX, -EY)
    leg.place("3023", "black", (8, -6, -30 * side), foot, tag="foot")
    leg.step("The heel: a cheese slope on the ring's other rim, its thin edge towards the toe")
    heel = axes(EY, -EX, EZ) if side > 0 else axes(-EY, -EX, -EZ)
    leg.place("54200", "black", (24, -6, -20 * side), heel, tag="heel")
    return leg


def build(model):
    m = model.main
    # (seen head on it is a narrow black shape: its best side is three-quarters on, so that is
    # the "front" the stills, the booklet's cover and the end of the video look from)
    model.meta["azimuth_offset"] = 50
    legs = {side: build_leg(model, side) for side in (1, -1)}

    # The hips: a T-bar, its cross bar along X (the hip bar), its stem up. The waist clip's
    # middle is at (0, -WAIST - 20, -16)
    hips = model.submodel("hips", "Hips")
    hips.step("The hips: a T-bar, stem up. Clip the tile with a clip onto the top end of the "
              "stem from the front, its underside facing forward")
    hips.place("4697b", "black", (0, 0, 0), axes(EZ, -EY, EX), tag="hip_bar")
    hips.place("15712", "black", (0, -WAIST, -6), rot(x=-90), tag="waist")
    hips.step("Press a plate with a level clip onto the underside of the tile, clip up: the "
              "waist")
    hips.place("61252", "black", (0, -WAIST, -14), rot(x=-90), tag="waist")

    # An arm: the shoulder clip at the origin, reaching forward (-Z)
    arm = model.submodel("arm", "Arm")
    arm.step("An arm: push a claw's bar into the hole in the end of a robot arm, as far as the "
             "picture shows, the claw's two prongs one above the other. Make two")
    arm.place("98313", "black", (0, 0, 0), rot(y=90), tag="arm")
    arm.place("48729b", "black", (0, 17.5, -51.8), rot(x=90, z=-90), tag="claw", insert=(0, 0, -1))

    # The head, level: the long top plate at the origin. It sits on the stud of the teeth,
    # under its front hole at (0, 8, -20); the neck clip's middle is at (0, 18, 0)
    head = model.submodel("head", "Head")
    head.step("The head: two 1 x 3 plates in a line, the front one on top of the back one's "
              "first stud")
    head.place("3623", "black", (0, 8, 40), rot(y=90), tag="skull")
    head.place("3623", "black", (0, 0, 0), rot(y=90), tag="skull")
    head.step("A cheese slope on the front stud, sloping down to the front: the snout. A 1 x 1 "
              "plate behind it")
    head.place("54200", "black", (0, 0, -20), tag="snout")
    head.place("3024", "black", (0, -8, 0), tag="skull")
    head.step("A 1 x 1 tile on the plate, and the long curved slope behind it, high end forward: "
              "the dome")
    head.place("3070b", "black", (0, -16, 0), tag="dome")
    head.place("50950", "black", (0, -16, 40), rot(y=180), tag="dome")

    # The back: a T-bar, cross bar along X, stem forward (-Z) into the torso's back. Four
    # droid arms trail from the cross bar: the tubes on the creature's back. Square with the
    # torso; the T-bar's middle is the origin, the tail's hinge is at (0, 40, 6)
    spine = model.submodel("back", "Back")
    spine.step("The back: a plate with an upright clip. Press the hinge plate onto its stud, "
               "the hinge finger at the far end from the clip")
    spine.place("60897", "black", (0, 20, -8), rot(x=-90), tag="back_plate")
    spine.place("30383", "black", (0, 30, 0), axes(EY, -EZ, -EX), tag="tail_hinge")
    spine.step("Press the stem of a T-bar into the clip, the end of the stem pointing away "
               "from the hinge plate")
    spine.place("4697b", "black", (0, 0, 0), axes(-EY, -EZ, EX), tag="back_bar")
    spine.step("Clip four droid arms onto the cross bar, two each side of the stem, all "
               "trailing to the back: the inner two hanging low, the outer two a little below "
               "level")
    for x, droop in TUBES:
        spine.place("30377", "black", (x, 0, 0), rot(x=droop + 90) @ rot(y=180), tag="tubes")

    # The crest: a T-bar, cross bar along Z, stem down, four spines standing on it
    crest = model.submodel("crest", "Crest")
    crest.step("The crest: a T-bar, stem down. Clip four claws onto its cross bar, two each "
               "side of the stem, bars straight up")
    crest.place("4697b", "black", (0, 0, 0), tag="crest_bar")
    for z in (-16, -8, 8, 16):
        crest.place("48729b", "black", (0, 0, z), rot(x=180), tag="crest_spines")

    # The sting: the barb in the far end of the short end link, the link's hinge at the origin.
    # In its own frame it lies on its side, as the two pieces lie on a table: the barb's curve
    # points to +X
    sting = model.submodel("sting", "Sting")
    sting.step("The sting: lay the barb on its side and push the short hinge cylinder onto its "
               "bar, as far as it goes. The barb curves across the cylinder's two fingers")
    sting.place("87747", "black", (0, 0, 30), rot(z=-90) @ rot(x=-90), tag="barb")
    sting.place("30553", "black", (0, 0, 10), rot(z=-90), tag="tail_end", insert=(0, 0, -1))
    # A round bar is a tight push fit in a cross-shaped axle hole: held by friction on the
    # hole's four ribs, not by a click. LDCad's snap data has no such joint
    model.press_fit("barb", "its bar is pushed into the end link's axle hole", reach=1.0)

    # The tail, from its hinge at the origin back (+Z): four links, each clicked onto the
    # last, then the sting
    tail = model.submodel("tail", "Tail")
    joint = np.zeros(3)
    centres = []
    words = ("The tail's first link: a hinge cylinder with a hole, its two-finger end forward "
             "and up. Push a claw's bar down through the hole: a spine",
             "Click the second link onto the first, turned up two clicks, and give it a spine",
             "Click on the third link, turned up two clicks again, and give it a spine",
             "Click on the fourth link, turned down two clicks")
    for k, (e, text) in enumerate(zip(LINKS, words)):
        centre = joint + 20 * back(e)
        centres.append(centre)
        tail.step(text)
        tail.place("30554b", "black", tuple(centre), rot(x=e) @ rot(y=180), tag="links")
        if k < 3:
            tail.place("48729b", "black", tuple(centre + SPINE * up(e)), rot(x=e) @ rot(y=90),
                       tag="spines", insert=tuple(up(e)))
        joint = joint + 40 * back(e)
    tail.step("Push the crest's stem into the hole in the fourth link, until the claws' jaws "
              "just clear the link")
    tail.use(crest, tuple(centres[3] + CREST * up(LINKS[3])), rot(x=LINKS[3]), tag="crest",
             insert=tuple(up(LINKS[3])))
    tail.step("Click the sting onto the end of the fourth link, turned down two clicks")
    tail.use(sting, tuple(joint), rot(x=TIP) @ rot(z=90), tag="sting")

    # The figure --------------------------------------------------------------------------
    hip = np.array([0.0, HIP_Y, 0.0])
    turn = {1: rot(x=LEG) @ rot(z=90), -1: rot(x=LEG) @ rot(z=90) @ rot(x=180)}

    m.step("Stand the hips' T-bar up, stem leaning a little forward")
    m.use(hips, tuple(hip), rot(x=HIPS), tag="hips")
    for side, text in ((1, "Slide the right leg's clip onto the end of the hip bar. The leg "
                           "stands on its toe and on the slope of its heel"),
                       (-1, "Slide the left leg onto the other end, to match")):
        m.step(text)
        m.use(legs[side], hang(hip + (HIP_X * side, 0, 0), turn[side], (-20, -4, 20 * side)),
              turn[side], tag="right_leg" if side > 0 else "left_leg", insert=(side, 0, 0))

    waist = hip + rot(x=HIPS) @ np.array([0.0, -WAIST - 20, -16.0])
    Rt = rot(x=TORSO)
    R = Rt @ rot(z=180)
    chest = np.array(hang(waist, R, (0, -32, 0)))       # the torso's own hip bar: the neck
    m.step("The torso: a battle droid's, upside down, its stud to the back. Press the thin "
           "middle of its shoulder bar down into the waist clip")
    m.place("30375", "black", tuple(chest), R, tag="torso")
    m.step("Slide an arm onto each end of the shoulder bar, reaching forward")
    for side in (1, -1):
        m.use(arm, tuple(waist + (15.5 * side, 0, 0)), rot(x=ARMS), tag="arms", insert=(side, 0, 0))
    Rh = rot(x=HEAD)
    crown = np.array(hang(chest, Rh, (0, 18, 0)))       # the head's own origin
    m.step("The neck: clip a plate with a level clip onto the bar at the top of the torso, "
           "from the front, studs up. Press the silver round plate onto it: the teeth")
    m.place("61252", "black", tuple(crown + Rh @ np.array([0.0, 16, -20])), Rh @ rot(y=180),
            tag="neck")
    m.place("6141", "silver", tuple(crown + Rh @ np.array([0.0, 8, -20])), Rh, tag="teeth")
    m.step("Press the head down onto the teeth, by the hole under its front end")
    m.use(head, tuple(crown), Rh, tag="head")
    m.step("Push the stem of the back's T-bar into the stud on the torso's back, tubes "
           "trailing, hinge plate hanging down")
    bar = chest + Rt @ np.array([0.0, 17.5, 27.5])
    m.use(spine, tuple(bar), Rt, tag="back", insert=tuple(back(TORSO)))
    m.step("Click the tail onto the hinge, one click up from the line of the back. The barb "
           "comes down onto the table: the third foot")
    m.use(tail, tuple(bar + Rt @ np.array([0.0, 40.0, 6.0])), rot(x=TAIL), tag="tail")

    # The cat: ours, not the designer's. Nothing on the back has a free stud, but each tube ends
    # in a free clip. The outer right tube's takes the handle of a 1 x 2 plate, held level
    # behind the head: a saddle, and the cat stands on its two studs, looking forward
    x, droop = TUBES[3]
    hand = Rt @ rot(x=droop + 90) @ rot(y=180)          # that tube, as it hangs on the figure
    grip = bar + Rt @ np.array([x, 0.0, 0.0]) + hand @ np.array([0.0, 38.2, -12.0])
    mouth = hand @ rot(x=-30) @ EY                      # its end clip's jaws open up and back
    seat = grip + np.array([0.0, -2.0, 30.0])           # the plate's top: its handle is 2 lower
    m.step("The saddle: press the handle of the 1 x 2 plate into the clip at the end of the "
           "outer right tube, from behind, studs up and level. Stand the cat on its two studs, "
           "looking forward over the shoulder")
    m.place("60478", "black", tuple(seat), axes(-EZ, EY, EX), tag="saddle", insert=tuple(mouth))
    m.place("13786p07", "cat", tuple(seat + np.array([0.0, 0.0, -10.0])), tag="cat")
