"""Original small Bulbasaur from the owner's character references, not a copied LEGO build.
LDU: -Y is up, -Z faces front, one stud=20, one plate=8. The paws rest on y=0.
The four-stud-wide head shares the body's grid; the bulb is deliberately oversized.
"""
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)


def build(model):
    m = model.main
    # (a paw is built first and made four times, and the four go on with the belly that ties them:
    # no step leaves pieces standing loose beside each other)
    paw = model.submodel("paw", "Paw")
    paw.step("A paw: a teal 1 x 2 brick on a white 1 x 2 plate. Make four")
    paw.place("3023", "white", (0, -8, 0), rot(y=90), tag="paws")
    paw.place("3004", "body", (0, -32, 0), rot(y=90), tag="legs")
    m.step("Stand the four paws in a rectangle, their long sides running front to back, and "
           "press the broad teal belly down onto all four")
    for x in (-30, 30):
        for z in (-30, 50):
            m.use(paw, (x, 0, z), tag="paw")
    m.place("3032", "body", (0, -40, 10), rot(y=90), tag="belly")
    m.step("The front and back of the low body")
    for z in (-30, 50):
        m.place("3001", "body", (0, -64, z), tag="body")
    for z, text in ((0, "Fill the middle: a 1 x 2 brick with a 1 x 1 brick each side"),
                    (20, "Behind them the same again, with a stud on the side of each 1 x 1 brick, "
                         "facing out: for the two leafy-green spots")):
        m.step(text)
        m.place("3004", "body", (0, -64, z), tag="body")
        for side in (-1, 1):
            m.place("87087" if z == 20 else "3005", "body", (30*side, -64, z),
                    rot(y=-90*side) if z == 20 else None, tag="body")
    m.step("A green spot on each flank")
    for side in (-1, 1):
        m.place("98138", "spot", (48*side, -54, 20), rot(y=-90*side) @ FRONT, tag="spots")
    m.step("The lower head: a 1 x 4 brick and the two front corners")
    m.place("3010", "body", (0, -88, -20), tag="head")
    for x in (-30, 30):
        m.place("3005", "body", (x, -88, -40), tag="head")
    m.step("Between the corners, two bricks with a stud facing forward: for the grin")
    for x in (-10, 10):
        m.place("87087", "body", (x, -88, -40), tag="mouth_mount")
    m.step("The upper head, with an outward stud at each cheek")
    for x in (-30, 30):
        m.place("87087", "body", (x, -112, -40), tag="eyes_mount")
    m.place("3004", "body", (0, -112, -40), tag="head")
    m.place("3010", "body", (0, -112, -20), tag="head")
    m.step("A plate across the head")
    m.place("3020", "body", (0, -120, -30), tag="head")
    m.step("Two pointed ears and a green forehead marking")
    for side in (-1, 1):
        m.place("54200", "body", (30*side, -120, -20), rot(y=-90*side), tag="ears")
    m.place("85984", "spot", (0, -120, -40), tag="spots")
    m.step("Smooth the top of the head: a tile on each front corner and one between the ears")
    for side in (-1, 1):
        m.place("3070b", "body", (30*side, -128, -40), tag="head")
    m.place("3069b", "body", (0, -128, -20), tag="head")
    m.step("Big white eyes, each with a red round pupil")
    for x in (-20, 20):
        m.place("18674", "white", (x, -112, -58), FRONT, tag="eyes")
        m.place("98138", "eye", (x, -112, -66), FRONT, tag="eyes")
    m.step("A small curved black grin")
    m.place("1748", "mouth", (0, -78, -58), FRONT, tag="mouth")
    m.step("A round green base for the bulb")
    m.place("60474", "bulb", (0, -72, 30), tag="bulb")
    m.step("A round green brick gives the bulb its oversized belly")
    m.place("87081", "bulb", (0, -96, 30), tag="bulb")
    m.step("Four curved corners round the top of the bulb")
    for x, z, angle in ((-10,20,0),(10,20,-90),(10,40,180),(-10,40,90)):
        m.place("67810", "bulb", (x,-128,z), rot(y=angle), tag="bulb")
    m.step("A central jumper holds the fresh green leaves")
    m.place("87580", "bulb", (0, -128, 30), tag="bulb")
    m.step("Three bright green leaves unfurl from the bulb")
    m.place("6255", "leaf", (0, -144, 30), tag="leaves")
