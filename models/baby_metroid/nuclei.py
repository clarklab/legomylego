"""The inner body: a Dark Red membrane platform on three posts (it also hides the mechanism),
and three nuclei - hollow, bumpy Trans-Red balls, each lit from below by a Power Functions LED
pushed up into the pin hole of a round 4x4 plate. Two nuclei sit low at the front, one higher at
the back on a hollow chimney.

Wiring: the two 8870 light leads are laid before the membrane. Their plugs go down through the
opening in the base disc (core.LEAD_HOLE) and hang down to the stand; the lamps come up through
2x2 openings in the membrane (the back one up the chimney). Under the membrane the leads run in
the 16 LDU gap above the hub (y -8..8), clear of every moving part.

Heights: posts from the base disc (y 56) up to the platform (plates -24..-8)."""
import math

from brickkit.ldraw.matrix import rot
from brickkit.shapes.rings import ring_cells
from brickkit.shapes.shell import Layer, ShellVocab, _place_run, build_shell, plan_layers, woven_disc

PLATFORM_R = 8.0
PLATFORM_TOP = -24
POSTS = [(-100, -100), (100, -100), (-100, 100)]
BALL_R = 68.0                     # LDU (3.4 studs)
FRONT = [(-120, -20), (-20, -120)]
BACK = (40, 40)

VOCAB = ShellVocab(brick={2: "3065", 1: "3062b"}, plate={2: "3023b", 1: "6141"},
                   slope1="54200", slope2="11477", tile1="98138", slope45="3040b")


def ball_layers() -> list[Layer]:
    """A hollow sphere of radius BALL_R, from where it is 1.8 studs wide at the bottom up to
    the same at the top; the centre (2x2) stays open for the LED post."""
    h0 = BALL_R - math.sqrt(BALL_R ** 2 - 36 ** 2)          # radius 1.8 studs
    top = 2 * BALL_R - 2 * h0

    def profile(h):
        z = h + h0 - BALL_R
        return math.sqrt(max(0.0, BALL_R ** 2 - z * z)) / 20

    layers = plan_layers(profile, top, max_step=0.5, closed_top=False)
    return [Layer(L.kind, L.r_out, max(L.r_in, 1.25)) for L in layers]


def posts(sub):
    sub.step("Three posts for the inner body. Then lay the two light leads: push each plug "
             "down through the opening in the base, next to the back-left post")
    for x, z in POSTS:
        for y in (32, 8):
            sub.place("3003", "frame_dark", (x, y, z))
        for y in (0, -8):
            sub.place("3022", "frame_dark", (x, y, z))


def platform(sub, openings=frozenset()) -> set:
    cells = ring_cells(PLATFORM_R) - set(openings)
    res = woven_disc(sub, cells, "nucleus_core", surface_y=PLATFORM_TOP + 16,
                     caption="Inner membrane: two crossed layers, around the light leads",
                     plate={6: "3666", 4: "3710", 2: "3023b", 1: "3024"})
    return res["cells"]


CENTRE_2X2 = {(-1, -1), (-1, 0), (0, -1), (0, 0)}
ROUND4 = {(i, k) for i in range(-2, 2) for k in range(-2, 2) if math.hypot(i + .5, k + .5) < 2.0}
LED_ROT = rot(x=-90)              # lamp up (part -Z -> world -Y), lead out underneath


def _cells_at(rel, cx, cz):
    return {(i + int(cx // 20), k + int(cz // 20)) for i, k in rel}


def lamp_submodel(model):
    """Round 4x4 plate with a light pushed up into its centre pin hole from below, lead hanging
    down. Built in the hand, then set down over an opening with the lead through it."""
    lamp = model.submodel("lamp_plate", "Lamp plate")
    lamp.place("60474", "nucleus_core", (0, 0, 0))
    lamp.step("Push the light up into the centre hole from below")
    lamp.place("62498c01", "led", (0, 10, 0), LED_ROT, tag="led", insert=(0, 1, 0))
    return lamp


def lamp_plate(model, sub, lamp, cx, cz, y_top, name, tag):
    sub.step(f"{name}: lamp plate, lead down through the opening")
    sub.use(lamp, (cx, y_top, cz), None, tag=f"lamp_{tag}", insert=(0, -1, 0))
    model.light(name, f"lamp_{tag}/led", color="#FF2A12", power=0.2,
                offset=(0, 0, -(BALL_R + 4)))            # render light at the ball's middle


def ball(model, sub, cx, cz, base_y, name, tag):
    """base_y: top of the round plate the ball sits on."""
    layers = ball_layers()
    stats = build_shell(sub, layers, "nucleus", y_base=base_y, vocab=VOCAB,
                        base_cells=ROUND4, origin=(cx, cz), tag=tag, quadrant_steps=False,
                        caption=f"{name}: layer {{n}}")
    y = stats["top_y"]
    cap_cells = ring_cells(layers[-1].r_out)
    cap = woven_disc(sub, cap_cells, "nucleus", surface_y=y, caption=f"{name}: close the top",
                     origin=(cx, cz), tag=tag)
    sub.step(f"{name}: round tiles")
    for i, k in sorted(cap["cells"]):
        sub.place("98138", "nucleus", ((i + .5) * 20 + cx, cap["top_y"] - 8, (k + .5) * 20 + cz),
                  tag=tag)
    model.glow(tag, 4.0)


def chimney(sub, cx, cz, y_base):
    """Two courses of bricks around an open 2x2 centre: the back lamp's lead runs down inside."""
    i0, k0 = int(cx // 20) - 2, int(cz // 20) - 2
    sub.step("Back nucleus: a hollow chimney for the light lead")
    courses = [[("3010", i0, k0, 4, "x"), ("3010", i0, k0 + 3, 4, "x"),
                ("3004", i0, k0 + 1, 2, "z"), ("3004", i0 + 3, k0 + 1, 2, "z")],
               [("3010", i0, k0, 4, "z"), ("3010", i0 + 3, k0, 4, "z"),
                ("3004", i0 + 1, k0, 2, "x"), ("3004", i0 + 1, k0 + 3, 2, "x")]]
    for n, course in enumerate(courses):
        for part, i, k, length, axis in course:
            _place_run(sub, part, "nucleus_core", i, k, length, axis, y_base - 24 * (n + 1), "")
    return y_base - 48


def nuclei(model, sub):
    posts(sub)
    openings = set()
    for cx, cz in FRONT + [BACK]:
        openings |= _cells_at(CENTRE_2X2, cx, cz)
    platform(sub, openings)
    lamp = lamp_submodel(model)
    for n, (cx, cz) in enumerate(FRONT):
        name, tag = f"Front nucleus {n + 1}", f"nucleus_{n}"
        lamp_plate(model, sub, lamp, cx, cz, PLATFORM_TOP - 8, name, tag)
        ball(model, sub, cx, cz, PLATFORM_TOP - 8, name, tag)
    bx, bz = BACK
    y = chimney(sub, bx, bz, PLATFORM_TOP)
    lamp_plate(model, sub, lamp, bx, bz, y - 8, "Back nucleus", "nucleus_2")
    ball(model, sub, bx, bz, y - 8, "Back nucleus", "nucleus_2")
    leads(model)


LEAD_LEN = 1000.0   # LDU (40 cm) per lamp: the 8870's lead is listed at 50 cm; 10 cm kept in
                    # reserve for where the lead splits to its two lamps
UNDER = 0.0         # the leads run under the membrane at this height
DROP = (-90.0, 60.0)   # centre of core.LEAD_HOLE


def leads(model):
    """Electrics check: each lamp's lead, from the lamp to the battery box in the stand. The two
    8870 light units (lead, junction and plug) go on the parts lists; their lamp heads are the
    placed 62498c01 parts."""
    model.extra("62501c01", "led", 2, "Power Functions light unit 8870: 2 lamps on one lead")
    dx, dz = DROP
    tail = [(dx, 64.0, dz), (dx, 250.0, dz), (-50.0, 300.0, dz)]   # through the base, down to
    for n, (cx, cz) in enumerate(FRONT + [BACK]):                    # the hatch in the stand
        route = [(cx, UNDER, cz), (dx, UNDER, dz)] + tail
        model.cable(f"Light lead to nucleus {n + 1}", f"lamp_nucleus_{n}/led", "battery", LEAD_LEN,
                    route)
