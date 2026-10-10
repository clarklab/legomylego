"""Mario, and Luigi from the same bricks: JellsaTheBobJeffCreator's design (Rebrickable
MOC-249307), taken in from the designer's Studio file with every part where they put it. We
turned it to face the front, named the colours by what they are, and grouped the designer's 29
small steps into 14.

Two models build it (models/mario, models/luigi): the bricks are the same, and each model's
palette says what colour the cap, the shirt and the stand are.

Frame: LDU (stud 20, plate 8, brick 24), -Y up, the face looks to -Z; the table is y = 0.
Palette roles: shirt (the cap, the shirt, the arms), stand, stand_top, overalls, skin, hair
(and the moustache and shoes), glove, button, eye."""
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)                 # a round tile on a stud that faces the front
SIDES = (1, -1)                   # his left (our right, x > 0), then his right

STAND = 32                        # the stand: a layer of plates and a layer of bricks
SHOES = STAND + 8                 # ... and a plate on its back three rows: the shoes start here
LEGS = SHOES + 16                 # the top of the shoes: the overalls' legs start here
WAIST = LEGS + 3 * 24             # the top of the legs
SHOULDER = WAIST + 2 * 24         # the top of the arms and the chest
NECK = SHOULDER + 8 + 24          # the top of the brick across the shoulders: the head starts
FACE = NECK + 3 * 8               # the top of the three plates of chin
BROW = FACE + 24                  # the top of the row the eyes are in
CAP = BROW + 24 + 8               # the top of the hair: the cap starts here


def y(h) -> float:
    """Height above the table -> the frame's y."""
    return -float(h)


def build_arm(model):
    """An arm, hanging from the plate at its top: a glove and two bricks of sleeve."""
    arm = model.submodel("arm", "Arm")
    arm.step("An arm: a white 2 x 2 brick for the glove, two more for the sleeve, and a 2 x 4 "
             "plate on top that sticks out to one side. Make two")
    arm.place("3003", "glove", (0, y(24), 0), tag="gloves")
    for h in (48, 72):
        arm.place("3003", "shirt", (0, y(h), 0), tag="arms")
    arm.place("3020", "shirt", (-20, y(80), 0), tag="arms")
    return arm


def build_plumber(model):
    m = model.main
    arm = build_arm(model)

    m.step("The stand: two 2 x 4 plates side by side, and two 2 x 4 bricks across them")
    for z in (-20, 20):
        m.place("3020", "stand", (0, y(8), z), tag="stand")
    for s in SIDES:
        m.place("3001", "stand", (20 * s, y(32), 0), rot(y=90), tag="stand")

    m.step("Two 2 x 3 plates on the back three rows of studs, and on each the first plate of "
           "a shoe")
    for s in SIDES:
        m.place("3021", "stand_top", (20 * s, y(STAND + 8), 10), rot(y=90), tag="stand")
    for s in SIDES:
        m.place("3021", "hair", (20 * s, y(SHOES + 8), 10), rot(y=90), tag="shoes")

    m.step("The rest of the shoes: a second plate, and a 1 x 2 tile across each toe")
    for s in SIDES:
        m.place("3021", "hair", (20 * s, y(SHOES + 16), 10), rot(y=90), tag="shoes")
    for s in SIDES:
        m.place("3069b", "hair", (20 * s, y(LEGS + 8), -10), tag="shoes")

    m.step("The legs: three blue 2 x 4 bricks, one on another, behind the toes")
    for k in (1, 2, 3):
        m.place("3001", "overalls", (0, y(LEGS + 24 * k), 20), tag="legs")

    m.step("The bib and the shirt: a blue brick with a stud on its side at each front corner, "
           "studs forward, and a corner brick behind each")
    for s in SIDES:
        m.place("87087", "overalls", (30 * s, y(WAIST + 24), 10), tag="bib")
    m.place("2357", "shirt", (10, y(WAIST + 24), 30), rot(y=90), tag="chest")
    m.place("2357", "shirt", (-10, y(WAIST + 24), 30), rot(y=180), tag="chest")

    m.step("The same again with plain blue 1 x 1 bricks for the straps, then a yellow button "
           "on each stud on the front")
    for s in SIDES:
        m.place("3005", "overalls", (30 * s, y(SHOULDER), 10), tag="bib")
    m.place("2357", "shirt", (10, y(SHOULDER), 30), rot(y=90), tag="chest")
    m.place("2357", "shirt", (-10, y(SHOULDER), 30), rot(y=180), tag="chest")
    for s in SIDES:
        m.place("98138", "button", (30 * s, y(WAIST + 14), -8), FRONT, tag="buttons",
                insert=(0, 0, -1))

    m.step("Hang an arm each side, its plate over the chest, and lock both with a 2 x 4 "
           "brick across the shoulders")
    for s in SIDES:
        m.use(arm, (60 * s, y(WAIST - 24), 20), None if s > 0 else rot(y=180), tag="arms")
    m.place("3001", "shirt", (0, y(NECK), 20), tag="chest")

    m.step("The chin: two 2 x 4 plates front to back, then two across them")
    for s in SIDES:
        m.place("3020", "skin", (20 * s, y(NECK + 8), 20), rot(y=90), tag="face")
    for z in (0, 40):
        m.place("3020", "skin", (0, y(NECK + 16), z), tag="face")

    m.step("One more layer: the bracket in the middle of the front, its studs forward for the "
           "moustache, a corner plate either side of it, and a 2 x 4 plate at the back")
    m.place("99781", "skin", (0, y(FACE), -10), tag="face")
    m.place("2420", "skin", (30, y(FACE), 10), rot(y=180), tag="face")
    m.place("2420", "skin", (-30, y(FACE), 10), rot(y=90), tag="face")
    m.place("3020", "skin", (0, y(FACE), 40), tag="face")

    m.step("The moustache: a curved slope on each of the bracket's studs, thick ends together. "
           "Behind it a 1 x 4 brick, and a 2 x 4 brick at the back")
    m.place("11477", "hair", (20, y(FACE - 10), -24), rot(x=90) @ rot(y=90), tag="moustache",
            insert=(0, 0, -1))
    m.place("11477", "hair", (-20, y(FACE - 10), -24), rot(x=90) @ rot(y=-90), tag="moustache",
            insert=(0, 0, -1))
    m.place("3010", "skin", (0, y(BROW), 10), tag="face")
    m.place("3001", "skin", (0, y(BROW), 40), tag="face")

    m.step("The eyes: a brick with a stud on its side at each end of the front row, studs "
           "forward, a 1 x 2 brick between them, and a black round tile on each stud")
    for s in SIDES:
        m.place("87087", "skin", (30 * s, y(BROW), -10), tag="face")
    m.place("3004", "skin", (0, y(BROW), -10), tag="face")
    for s in SIDES:
        m.place("98138", "eye", (30 * s, y(BROW - 10), -28), FRONT, tag="eyes",
                insert=(0, 0, -1))

    m.step("The forehead and the hair: a tan 2 x 4 brick at the front and a brown one behind "
           "it, then two brown 2 x 4 plates front to back across both")
    m.place("3001", "skin", (0, y(BROW + 24), 0), tag="face")
    m.place("3001", "hair", (0, y(BROW + 24), 40), tag="hair")
    for s in SIDES:
        m.place("3020", "hair", (20 * s, y(CAP), 20), rot(y=90), tag="hair")

    m.step("The cap: two 2 x 4 bricks front to back, sticking out over the face for the peak, "
           "and one across the back")
    for s in SIDES:
        m.place("3001", "shirt", (20 * s, y(CAP + 24), -20), rot(y=90), tag="cap")
    m.place("3001", "shirt", (0, y(CAP + 24), 40), tag="cap")

    m.step("The top of the cap: two 2 x 4 plates front to back, then two across them")
    for s in SIDES:
        m.place("3020", "shirt", (20 * s, y(CAP + 32), 20), rot(y=90), tag="cap")
    for z in (0, 40):
        m.place("3020", "shirt", (0, y(CAP + 40), z), tag="cap")
