"""Nautilus (Walt Disney's 20,000 Leagues Under the Sea, 1954, Harper Goff's design) on a stand
that looks like the sea. Bow toward -X, port side toward the front (-Z); see naut_shape.py."""
import math

import naut_details as det
import naut_frame as frame
import naut_relief as rel
import naut_shape as shp
import naut_stand as stand
from brickkit.ldraw.matrix import rot
from naut_kit import S, about, exposed_studs, free_sockets, tile_studs, use_M

FIN_BOTTOM = 112         # the keel fins' undersides (hull frame): they sit on the posts
Y_HULL = stand.post_top() - FIN_BOTTOM   # the side keels' height above the table (LDU, -Y up)
LEAD = 1000.0            # each lamp's share of the 8870's lead (LDU; 40 cm of its 50)


def build(model):
    main = model.main
    hs = model.submodel("hull", "Hull")
    up, lo = rel.Relief("up"), rel.Relief("lo")
    # the side keels first: everything else builds on them
    hs.use(frame.build_frame(model))
    rel.core_batch(up, lo).emit(hs, phases=rel.CORE_PHASES, captions=rel.CORE_CAPTIONS,
                                per_step=10, reach=200, hanging=rel.CORE_HANGING)
    # the hull's sides, each built flat and pushed on sideways
    for r in (up, lo):
        for side in (-1, 1):
            hs.step("A hull side, built flat, pushed onto the core's side studs"
                    if (r, side) == (up, -1) else "")
            use_M(hs, rel.build_relief(model, r, side), rel.relief_frame(side),
                  insert=(0, 0, side))
    frame.deck_batch().emit(hs, phases=[["deck"]], captions={"deck": "The deck strip"},
                            per_step=10, reach=200)
    hs.step("The ram")
    hs.use(det.ram(model), insert=(1, 0, 0))
    hs.step("The wheelhouse")
    hs.use(det.wheelhouse(model), insert=(0, -1, 0))
    hs.step()
    hs.use(det.crest_foot(model), insert=(0, -1, 0))
    hs.step("The crest arch")
    use_M(hs, det.crest_arch(model), det.CREST_FRAME, insert=(0, 0, -1))
    det.searchlights(hs)
    for side in (-1, 1):                 # the salon windows, and the lights round them
        win, lights = det.salon_window(model, side)
        hs.step("The salon window: feed the lamp's lead in and down the core first"
                if side < 0 else "")
        hs.use(win, tag="salon_port" if side < 0 else "salon_stbd", insert=(0, 0, side))
        lights.emit(hs, phases=[["bases"], ["lights"]],
                    captions={"bases": "Eight small yellow lights round the window"},
                    per_step=8, reach=200)
    hs.step("The dorsal fin")
    hs.use(det.dorsal_fin(model), insert=(0, -1, 0))
    hs.step()
    hs.use(det.hatch(model), insert=(0, -1, 0))
    hs.step()
    hs.use(det.skiff(model), insert=(0, -1, 0))
    # the tail: the lower lobe, the propeller, its guard and the rudder, then the upper lobe
    det.tail_lower().emit(hs, phases=[["fin_lo"], ["floor"]], captions={
        "fin_lo": "The tail's lower lobe, pushed up under the stock",
        "floor": "Tiles on the lower lobe, under the propeller and rudder"}, per_step=8,
        reach=200, hanging=("fin_lo",))
    hs.step("The propeller")
    hs.use(det.propeller(model), insert=(1, 0, 0))
    hs.step("The propeller's guard")
    hs.use(det.guard(model), insert=(0, -1, 0))
    hs.step("The rudder, clipped on the guard's post")
    hs.use(det.rudder(model), tag="rudder", insert=(1, 0, 0))
    det.tail_upper().emit(hs, phases=[["fin_up"]], captions={
        "fin_up": "The tail's upper lobe"}, per_step=8, reach=200)
    for which in ("fwd", "rear"):
        hs.step("The keel fins" if which == "fwd" else "")
        hs.use(det.keel_fin(model, which), insert=(0, 1, 0))
    det.saw_teeth(hs, rel.KEEL_SLOPES, shp.FL_B + 8)
    # teeth along the side keels' forward third, in free anti-studs under their edge (the
    # outermost on each side at every other column)
    flat = [(p, M) for p, _, M in hs.flatten_local()]
    socks = free_sockets(flat, keep=lambda x, y, z: abs(y) < 0.5 and -460 < x < -180,
                         room=((-18.5, 0.5, -10.5), (10.5, 24.0, 10.5)))
    outer = {}
    for x, y, z in socks:
        key = (x, z > 0)
        if key not in outer or abs(z) > abs(outer[key][2]):
            outer[key] = (x, y, z)
    det.keel_teeth(hs, [st for (x, _), st in sorted(outer.items()) if int(x // S) % 2 == 0])
    # tiles over every stud left bare: the side keels, the deck, the core's tops and the tail
    flat = [(p, M) for p, _, M in hs.flatten_local()]
    # (not the side keels' studs inside the salon windows' bosses, where the leads go in)
    bare = [st for st in exposed_studs(flat)
            if not (shp.SALON_X[0] <= st[0] < shp.SALON_X[1] and abs(st[2]) < 60
                    and abs(st[1] - shp.FL_A) < 0.5)]
    tile_studs(hs, bare)
    main.step("The display stand")
    main.use(stand.stand(model), tag="stand")
    main.step("Set the Nautilus on its posts (plug the lights' leads in first)")
    main.use(hs, (0, Y_HULL, 0), tag="sub", insert=(0, 1, 0))
    _mechanism(model)
    _electrics(model)


# ------------------------------------------------------------------ mechanism and video
PROP_AXIS = (0.0, Y_HULL + det.PROP_Y, 0.0)          # the propeller's shaft (world)
RUDDER_AXIS = (det.GUARD_X, 0.0, 0.0)                # the guard post the rudder swings on
RUDDER_SWING = 22.0                                  # degrees each way


def pose(t: float) -> dict:
    """t 0..1: the propeller turns once and the rudder swings hard over."""
    return {"prop": about(PROP_AXIS, rot(x=360.0 * t)),
            "rudder": about(RUDDER_AXIS, rot(y=RUDDER_SWING * t))}


def performance(u: float) -> dict:
    """The video's loop (u 0..1): three turns of the propeller, the rudder easing to and fro."""
    return {"prop": about(PROP_AXIS, rot(x=360.0 * 3 * u)),
            "rudder": about(RUDDER_AXIS, rot(y=RUDDER_SWING * math.sin(2 * math.pi * u)))}


def _mechanism(model):
    model.moving_group("prop", "prop")
    model.moving_group("rudder", "rudder")
    model.pose = pose
    model.meta["mechanism_name"] = "Propeller and rudder"
    model.meta["mechanism_labels"] = ["At rest", "Propeller turned, rudder hard over"]
    model.meta["performance"] = performance
    model.meta["performance_info"] = {"hide_tags": ["stand"], "ground_y": Y_HULL + FIN_BOTTOM,
                                      "pivot": [0.0, 0.0], "cycle_s": 4.0,
                                      "forward": [-1.0, 0.0, 0.0], "rev_tag": "prop"}


# ------------------------------------------------------------------ electrics
def _electrics(model):
    """One Power Functions light unit (8870): a lamp behind each salon window. Each lead goes
    in along the side keels' level to the core, down the shaft in it, out under the hull beside
    the forward keel fin's tail, down beside the front post, through the hole in the sea and
    to the battery box's plug."""
    cx, cy = shp.SALON_C
    xs = (shp.SHAFT_X[0] + shp.SHAFT_X[1]) / 2
    face = 20 + 8 * shp.SALON_FACE
    for side, name in ((-1, "salon_port"), (1, "salon_stbd")):
        model.light(name, f"{name}/led", color="#FFC46A", power=1.2, offset=(0, 0, -26))
        z_in = side * 10
        route = [(cx, Y_HULL + 4, side * (face - 10)),            # out of the lamp, inward
                 (xs, Y_HULL + 4, z_in),                          # to the core
                 (xs, Y_HULL + rel.MID_BOT, z_in),                # down the shaft
                 (xs, stand.SEA_TOP, z_in),                       # beside the post
                 (xs, stand.WALL_TOP + 8, z_in),                  # into the base
                 (stand.BOX_X - 60, -44, stand.BOX_Z + 10)]       # to the box's plug
        model.cable(f"{name}_lead", f"{name}/led", "battery", LEAD, route)
    model.glow("lights", 2.5)
    model.glow("glass", 1.2)
    model.extra("62501c01", "led", 1, "Power Functions LED light unit 8870: its two lamps "
                "go behind the salon windows (placed as the lamp heads)")
    model.press_fit("battery", "the battery box stands on the table in the floor's opening, "
                    "boxed in by the floor and the walls", reach=2.0)

