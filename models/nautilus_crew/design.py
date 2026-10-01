"""Nautilus Crew: Captain Nemo, Ned Land, Professor Aronnax and Conseil from Jules Verne's
20,000 Leagues Under the Sea (dressed loosely after Walt Disney's 1954 film) as minifigures on
a 16 x 8 slice of the Nautilus's deck, in front of a salon window.

The base (LDU, -Y up, front -Z): a black 8 x 16 plate under reddish brown deck plates, their
top at y = 0. Columns i = 0..15 (stud centres x = -150 + 20 i), rows j = 0..7 (z = -70 + 20 j,
row 0 at the front). The figures stand on the studs of row 2; the bulkhead with the salon
window fills columns 5-10 of rows 6-7. See NOTES.md for the part choices."""
from brickkit.ldraw.matrix import rot
from brickkit.model.minifig import grip_up

# The crew, left to right as seen from the front. Every head, torso and legs number is what
# LEGO sells (Rebrickable numbers; colour = the head's, the torso's, the hips'); see NOTES.md.
CREW = [
    dict(name="conseil", title="Conseil", x=-120,
         head=("3626cpr2224", "Yellow"),          # scared / lopsided smile
         torso=("973c27h01pr4203", "Black"),      # waistcoat, shirt sleeves, blue tie
         legs=("970c12", "Dark Bluish Gray"),
         hat=("95674", "Black"),                  # bowler hat
         accessory=dict(part="95228", color="Trans-Clear", hand="right"),   # specimen bottle
         pose=dict(arm_r=48, arm_l=0, head=25)),
    dict(name="aronnax", title="Professor Aronnax", x=-60, z=-10,
         head=("3626cpr2522", "Yellow"),          # grey beard, moustache and eyebrows
         torso=("973c14h01pr6850", "Light Bluish Gray"),   # three-piece suit, vest and tie
         legs=("970c14", "Light Bluish Gray"),
         hair=("21268", "Light Bluish Gray"),     # grey, swept back, sideburns
         accessory=dict(part="10830p01", color="Black", hand="right", spin=-60),  # magnifier
         pose=dict(arm_r=12, arm_l=8, head=-10)),     # holds it at his chest: his face shows
    dict(name="captain_nemo", title="Captain Nemo", x=0,
         head=("3626bpr0251", "Yellow"),          # grey beard, moustache, stern eyebrows
         torso=("973c03h01pr0049", "Black"),      # double-breasted captain's coat, gold anchor
         legs=("970c03", "Black"),
         hair=("92081", "Dark Bluish Gray"),      # combed back, greying
         accessory=dict(part="64644", color="Pearl Gold", hand="right"),    # brass spyglass
         pose=dict(arm_r=45, arm_l=0, head=-8)),
    dict(name="diver", title="Nautilus diver", x=60, z=-10,
         head=("3626cpr0933", "Yellow"),          # stubble goatee (inside the helmet's glass)
         torso=("973c23h12pr2119", "Medium Nougat"),  # diving suit, crossed belts, weight belt
         legs=("970c23pr0378", "Dark Bluish Gray"),   # medium nougat legs, kneepads
         hat=("10165c01", "Pearl Gold"),          # the brass deep-sea diving helmet
         accessory=dict(part="30088", color="Black", hand="left", bar=1, spin=180),  # speargun,
         pose=dict(arm_l=-20, arm_r=10, head=-20)),   # by its grip, upright at his side
    dict(name="ned_land", title="Ned Land", x=120,
         head=("3626cpr0754", "Yellow"),          # stubble, crooked grin, scar
         torso=("973c01h01pr9741", "White"),      # striped tank top with belt, bare arms
         legs=("970c05", "Dark Blue"),
         hair=("62810", "Reddish Brown"),         # short tousled hair with side parting
         accessory=dict(part="18041", color="Flat Silver", hand="left"),    # the harpoon
         pose=dict(arm_l=grip_up(), arm_r=10, head=-12)),
]
FIG_ROW = -30          # z of the studs the figures stand on (row 2); some stand a row back
                       # (z = -10, row 3) so neighbours' hands and what they hold don't meet


def X(i: float) -> float:
    return -150 + 20 * i


def Z(j: float) -> float:
    return -70 + 20 * j


def build(model):
    main = model.main
    R90 = rot(y=90)

    # --- the base -----------------------------------------------------------------------
    main.step("The bottom plate")
    main.place("92438", "base", (0, 8, 0))
    main.step("Three deck plates bridge it")
    main.place("3036", "deck", (-100, 0, 0), R90)        # 6 x 8
    main.place("3035", "deck", (0, 0, 0), R90)           # 4 x 8
    main.place("3036", "deck", (100, 0, 0), R90)
    main.step("The gold edge and the nameplate")
    for i in (0, 2, 4, 10, 12, 14):
        main.place("3069b", "trim", (X(i + 0.5), -8, Z(0)))
    main.place("87079", "nameplate", (0, -8, -60))        # 2 x 4, columns 6-9, rows 0-1
    main.step("The walkway")
    main.place("6636", "walk", (X(2.5), -8, Z(1)))
    main.place("6636", "walk", (X(12.5), -8, Z(1)))
    deck_tiles(main)

    main.step("The hatch", view="above")
    main.place("60474", "walk", (-120, -8, 40))           # round 4 x 4, columns 0-3, rows 4-7
    main.place("14769", "trim", (-120, -16, 40))          # its gold hand wheel
    main.step("The mooring bollard")
    main.place("3941", "deck", (120, -24, 40))            # columns 13-14, rows 5-6
    main.place("14769", "trim", (120, -32, 40))

    bulkhead(model, main)

    # --- the crew -----------------------------------------------------------------------
    for fig in CREW:
        main.step(f"{fig['title']} takes his place", view="above")
        kw = {k: v for k, v in fig.items() if k not in ("name", "title", "x", "z")}
        model.minifig(fig["name"], (fig["x"], 0, fig.get("z", FIG_ROW)), title=fig["title"],
                      **kw)


def deck_tiles(main):
    """Reddish brown 2 x 2 plating on rows 3-7 wherever nothing else stands, with 1 x 2 and
    1 x 1 tiles to fill; row 2 stays studs (the figures stand on it: a row of rivets)."""
    used = set()
    used |= {(i, j) for i in range(0, 4) for j in range(4, 8)}      # hatch
    used |= {(i, j) for i in range(13, 15) for j in range(5, 7)}    # bollard
    used |= {(i, j) for i in range(5, 11) for j in range(6, 8)}     # bulkhead
    for fig in CREW:                                                # the back row's feet
        if fig.get("z", FIG_ROW) == Z(3):
            i = round((fig["x"] - 10 + 150) / 20)
            used |= {(i, 3), (i + 1, 3)}
    main.step("The deck plating")
    for j in (3, 5):                 # 2 x 2 tiles in pairs of rows
        for i in range(0, 16, 2):
            cells = {(i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)}
            if not cells & used:
                main.place("3068b", "deck", (X(i + 0.5), -8, Z(j + 0.5)))
                used |= cells
    for j in range(3, 8):            # what's left: 1 x 2 tiles along the rows, then 1 x 1
        i = 0
        while i < 16:
            if (i, j) in used:
                i += 1
                continue
            if i + 1 < 16 and (i + 1, j) not in used:
                main.place("3069b", "deck", (X(i + 0.5), -8, Z(j)))
                used |= {(i, j), (i + 1, j)}
                i += 2
            else:
                main.place("3070b", "deck", (X(i), -8, Z(j)))
                used.add((i, j))
                i += 1


def bulkhead(model, main):
    """A 6 x 2 bulkhead on columns 5-10, rows 6-7, with three rows of side studs (bricks
    1 x 4 with studs on the side, 40 LDU apart: a brick and two plates) facing the front for
    the salon window, built flat on a 6 x 6 plate and pressed on."""
    zf, zb, zc = Z(6), Z(7), (Z(6) + Z(7)) / 2       # front row, back row, middle
    y = 0
    main.step("The bulkhead", view="above")
    for k in range(3):               # three plain courses, bonded across both rows
        y -= 24
        if k == 1:
            main.place("3001", "deck", (-20, y, zc))
            main.place("3003", "deck", (40, y, zc))
        else:
            main.place("3009", "deck", (0, y, zf))
            main.place("3009", "deck", (0, y, zb))
    for k in range(3):               # the side-stud courses and the plates between them
        if k:
            main.step()
            y -= 8
            main.place("3795", "deck", (0, y, zc))
            y -= 8
            main.place("3795", "deck", (0, y, zc))
        else:
            main.step("Studs on the side face the front")
        y -= 24
        main.place("3005", "deck", (-50, y, zf))
        main.place("30414", "deck", (0, y, zf))
        main.place("3005", "deck", (50, y, zf))
        main.place("3009", "deck", (0, y, zb))
    main.step("The bulkhead's rounded top")
    y -= 24
    main.place("3001", "deck", (-20, y, zc))
    main.place("3003", "deck", (40, y, zc))
    for x in (-40, 0, 40):           # (a curved brick's origin is at its bottom)
        main.place("15068", "deck", (x, y, zc))

    # the salon window, built flat (studs up) on a 6 x 6 plate, then turned to face the front
    win = model.submodel("salon_window", "Salon window")
    win.step("A gold round frame on the bulkhead plate")
    win.place("3958", "deck")
    win.place("60474", "trim", (0, -8, 0))
    win.step("The glass")
    win.place("87580", "glass", (0, -16, 0))
    win.place("4740", "glass", (0, -24, 0))
    win.step("Eight yellow lights round the window")
    for dx, dz in ((-30, -10), (-30, 10), (30, -10), (30, 10),
                   (-10, -30), (10, -30), (-10, 30), (10, 30)):
        win.place("98138", "lights", (dx, -16, dz))
    win.step("Plating round the frame (its corner studs stay: rivets)")
    for z in (-50, 50):
        win.place("6636", "deck", (0, -8, z))                     # 1 x 6
    for x in (-50, 50):
        win.place("2431", "deck", (x, -8, 0), rot(y=90))         # 1 x 4
    main.step("Press the window onto the side studs")
    # turned so its studs face the front: local -Y -> world -Z; the plate's underside on the
    # bulkhead face (z = 40); centred on the middle row of side studs (y = -126) minus 10, so
    # its rows line up with all three
    main.use(win, (0, -136, zf - 10 - 8), rot(x=90), tag="window")
