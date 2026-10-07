"""LEGO 11039 birthday cake, PDF 6555451 pages 6-11, all 20 pieces.

-X left, -Z front, -Y up. The 2x4 base is centered at y=0.
The official candle callout is built separately before source step 11.
"""
from brickkit.ldraw.matrix import rot


def build(model):
    m = model.main
    m.step("1. Brown 2 x 4 base (LEGO page 6)")
    m.place("3020", "cake", tag="base")
    m.step("2. Brown 2 x 2 centre (page 7)")
    m.place("3003", "cake", (0, -24, 0))
    m.step("3. Two inverted slopes widen the cake (page 7)")
    m.place("76959", "cake", (-30, -24, 0), rot(y=90))
    m.place("76959", "cake", (30, -24, 0), rot(y=-90))
    m.step("4. White 1 x 4 at the back (page 8)")
    m.place("3010", "frosting", (0, -48, 10))
    m.step("5. Curved frosting at both ends (page 8)")
    m.place("37352", "frosting", (-50, -48, 0), rot(y=90))
    m.place("37352", "frosting", (50, -48, 0), rot(y=-90))
    m.step("6. Two eye bricks and the printed smile (page 9)")
    for x in (-30, 30):
        m.place("87087", "frosting", (x, -48, -10))
    m.place("3004p0g", "frosting", (0, -48, -10), tag="smile")
    m.step("7. Two sleepy printed eyes (page 9)")
    for x in (-30, 30):
        m.place("98138p2l", "frosting", (x, -38, -28), rot(x=90) @ rot(y=180), tag="eyes")
    m.step("8. Two small slopes on the right (page 10)")
    for z in (-10, 10):
        m.place("54200", "frosting", (30, -48, z), rot(y=-90))
    m.step("9. The top frosting and curved cutouts (page 10)")
    m.place("3004", "frosting", (10, -72, 0), rot(y=90))
    for z in (-10, 10):
        m.place("78666", "frosting", (-10, -72, z), rot(y=180))
    m.step("10. Red cherry (page 11)")
    m.place("3262", "cherry", (0, -96, 0), tag="cherry")
    candle = model.submodel("candle", "Candle and flame - page 11 callout")
    candle.step("Push the small flame into the top of the white candle")
    candle.place("37762", "frosting", tag="wax")
    candle.place("37775", "flame", (0, -27, 0), rot(y=90), tag="flame")
    m.step("11. Put the completed candle in the cherry (page 11)")
    m.use(candle, (0, -104, 0), tag="candle")
