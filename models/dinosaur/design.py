"""Reference revision: low head, one layer of teeth, pin-bearing legs and rear-tapered belly.
LDraw -Y up, -Z front. Agent guide and JSON are generated from this model.
"""
import numpy as np
from brickkit.ldraw.matrix import rot

LEG_R = np.column_stack(((0,1,0), (0,0,1), (1,0,0)))
LEG_L = np.column_stack(((0,-1,0), (0,0,1), (-1,0,0)))


def build(model):
    m = model.main
    for x, R, label in ((-30, LEG_L, "left"), (30, LEG_R, "right")):
        leg = model.submodel(label + "_leg", label.title() + " pinned leg")
        leg.step("Pin-bearing leg on its side, with dark-tan face over the two front studs")
        leg.place("2458", "pin_leg", (x,-36,0), R, tag="pinned_legs")
        leg.place("3023", "leg", (x,-36,-8), R, tag="leg_faces")
        leg.step("White hollow round socket on the lower stud, with the claw curving downward")
        leg.place("85861", "tooth", (x,-26,-16), rot(x=90), tag="claw_sockets")
        leg.place("53451", "tooth", (x,-26,-20), rot(x=180), tag="claws")
        leg.step("Attach the orange ankle behind the lower leg socket")
        leg.place("87087", "body", (x,-36,34), tag="ankles")
        foot = model.submodel(label + "_foot", label.title() + " foot")
        foot.step("Dark-tan foot sole")
        foot.place("3623", "leg", (x,-4,14), rot(y=90), tag="feet")
        foot.step("Orange ankle pad at the rear and smooth orange toe at the front")
        foot.place("3024", "body", (x,-12,34), tag="feet")
        foot.place("3070b", "body", (x,-12,-6), tag="toes")
        leg.step("Press the completed foot onto the ankle from underneath")
        leg.use(foot, tag="foot", insert=(0,1,0))
        leg.step("Slide the orange Technic hip onto the inward-facing integral leg pin")
        leg.place("3700", "body", (x / 3,-46,10), rot(y=90), tag="hip_sockets")
        m.step("Set the " + label + " completed leg upright on the table")
        m.use(leg, tag=label + "_leg")
    m.step("Lock the two hip halves together with an orange plate extending into the tail")
    m.place("3020", "body", (0,-54,30), rot(y=90), tag="tail_base")
    m.step("The inverted orange belly widens toward the chest; red tail slopes taper backward")
    for x in (-10,10):
        m.place("3665b", "body", (x,-78,20), tag="belly")
    for x in (-10,10):
        m.place("3040b", "red", (x,-78,40), rot(y=180), tag="tail")
    m.step("A red shoulder handle with free outer ends, and a red rear plate")
    m.place("2540", "red", (0,-86,0), tag="shoulders")
    m.place("3023", "red", (0,-86,20), tag="shoulders")
    m.step("Clip the arms onto the outer shoulder-bar ends, hands curving forward")
    for x in (-16,16):
        m.place("30377", "red", (x,-84,-20), tag="arms")
    m.step("Orange neck above the front row of the body")
    m.place("3004", "body", (0,-110,0), tag="neck")
    m.step("The flat red lower jaw extends forward from the neck")
    m.place("3020", "red", (0,-118,-30), rot(y=90), tag="lower_jaw")
    m.step("Only one white round plate per tooth; two orange plates form the rear mouth support")
    for x in (-10,10):
        m.place("4073", "tooth", (x,-126,-60), tag="teeth")
    for y in (-126,-134):
        m.place("3023", "body", (0,y,0), tag="mouth_back")
    m.step("A thin red upper jaw spans the mouth")
    m.place("3020", "red", (0,-142,-30), rot(y=90), tag="upper_jaw")
    m.step("A one-plate-high skull row: red snout, black eyes, orange rear")
    m.place("3022", "red", (0,-150,-50), tag="snout")
    for x in (-10,10):
        m.place("4073", "eye", (x,-150,-20), tag="eyes")
    m.place("3023", "body", (0,-150,0), tag="skull")
    m.step("Support the curved forehead; finish with a low red crown")
    m.place("3023", "red", (0,-158,-40), tag="forehead_support")
    m.place("15068", "red", (0,-150,-50), tag="forehead")
    m.place("3022", "red", (0,-158,-10), tag="crown")
    m.place("3068b", "red", (0,-166,-10), tag="crown")
