"""The inner body: a Dark Red membrane platform on three posts (it also hides the mechanism),
and three nuclei - hollow, bumpy Trans-Red balls, each lit from inside by a Power Functions LED
on a Dark Red post. Two nuclei sit low at the front, one higher at the back.

Heights: posts from the base disc (y 56) up to the platform (plates -40..-24)."""
import math

from brickkit.ldraw.matrix import rot
from brickkit.shapes.rings import ring_cells
from brickkit.shapes.shell import Layer, ShellVocab, build_shell, pack_cells, plan_layers, woven_disc, _place_run

PLATFORM_R = 8.0
PLATFORM_TOP = -24
POSTS = [(-100, -100), (100, -100), (-100, 100)]
BALL_R = 60.0                     # LDU (3 studs)
FRONT = [(-120, -20), (-20, -120)]
BACK = (40, 40)
BACK_RISER = 56                   # 2 bricks + a 4x4 round plate

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
    sub.step("Three posts for the inner body")
    for x, z in POSTS:
        for y in (32, 8):
            sub.place("3003", "frame_dark", (x, y, z))
        for y in (0, -8):
            sub.place("3022", "frame_dark", (x, y, z))


def platform(sub) -> set:
    cells = ring_cells(PLATFORM_R)
    res = woven_disc(sub, cells, "nucleus_core", surface_y=PLATFORM_TOP + 16,
                     caption="Inner membrane: two crossed layers",
                     plate={6: "3666", 4: "3710", 2: "3023b", 1: "3024"})
    return res["cells"]


def _led_post(model, sub, cx, cz, base_y, name, tag):
    """Dark Red post on the ball's axis: a 2x2 brick and a Technic brick 1x2 whose hole holds
    the LED. The LED goes in from the far side so the lamp sits on the axis, near the centre."""
    sub.step(f"{name}: light post")
    sub.place("3023b", "nucleus_core", (cx, base_y - 8, cz + 10))
    sub.place("3700", "nucleus_core", (cx, base_y - 32, cz + 10))
    sub.place("62498c01", "led", (cx, base_y - 22, cz), rot(y=180), tag=tag, insert=(0, 0, -1))
    model.light(name, tag, color="#FF2A12", power=1.2)


def ball(model, sub, cx, cz, base_y, base_cells, name, tag):
    _led_post(model, sub, cx, cz, base_y, name, f"led_{tag}")
    layers = ball_layers()
    rel_base = {(i - cx // 20, k - cz // 20) for i, k in base_cells}
    stats = build_shell(sub, layers, "nucleus", y_base=base_y, vocab=VOCAB,
                        base_cells=rel_base, origin=(cx, cz), tag=tag, quadrant_steps=False,
                        caption=f"{name}: layer {{n}}")
    y = stats["top_y"]
    cap_cells = ring_cells(layers[-1].r_out)
    cap = woven_disc(sub, cap_cells, "nucleus", surface_y=y, caption=f"{name}: close the top",
                     origin=(cx, cz), tag=tag)
    sub.step(f"{name}: round tiles")
    for i, k in sorted(cap["cells"]):
        sub.place("98138", "nucleus", ((i + .5) * 20 + cx, cap["top_y"] - 8, (k + .5) * 20 + cz),
                  tag=tag)
    model.glow(tag, 1.5)


def nuclei(model, sub):
    posts(sub)
    pcells = platform(sub)
    for n, (cx, cz) in enumerate(FRONT):
        ball(model, sub, cx, cz, PLATFORM_TOP, pcells, f"Front nucleus {n + 1}", f"nucleus_{n}")
    sub.step("Riser for the back nucleus")
    bx, bz = BACK
    sub.place("3003", "nucleus_core", (bx, PLATFORM_TOP - 24, bz))
    sub.place("3003", "nucleus_core", (bx, PLATFORM_TOP - 48, bz))
    sub.place("3031", "nucleus_core", (bx, PLATFORM_TOP - 56, bz))
    riser = {(i, k) for i in range(bx // 20 - 2, bx // 20 + 2) for k in range(bz // 20 - 2, bz // 20 + 2)
             if math.hypot(i + .5 - bx / 20, k + .5 - bz / 20) < 2.0}
    ball(model, sub, bx, bz, PLATFORM_TOP - BACK_RISER, riser, "Back nucleus", "nucleus_2")
