"""Original small Charmander inspired by the three saved character references.

LDraw units; -Y is up and the face is -Z. A broad four-stud stance carries the
oversized head. A genuine curved animal tail holds a real LEGO flame.
"""
import numpy as np
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)


def build(model):
    m = model.main
    m.step("Put the two orange feet side by side and join them with the orange hips")
    for side in (-1, 1):
        m.place("3021", "body", (side * 20, 0, -10), rot(y=90), tag=f"foot_{side}")
    m.place("3001", "body", (0, -24, 0), tag="hips")
    m.step("Give each foot three little white claws")
    for side in (-1, 1):
        m.place("2412b", "claws", (side * 20, -8, -30), tag="claws")
    m.step("Build the waist and the hollow rear stud for the tail")
    m.place("3004", "body", (0, -48, -10), tag="waist_front")
    m.place("3005", "body", (-10, -48, 10), tag="waist_back")
    m.place("87087", "body", (10, -48, 10), rot(y=180), tag="tail_mount")
    for side in (-1, 1):
        m.place("37352", "body", (side * 30, -48, 0), rot(y=-90 * side), tag="haunches")
    m.step("Add chest studs in front and shoulder studs at the sides")
    m.place("11211", "body", (0, -72, -10), tag="belly_mount")
    for side in (-1, 1):
        m.place("87087", "body", (side * 10, -72, 10), rot(y=-90 * side), tag=f"arm_mount_{side}")
    m.step("Round off the tan belly")
    m.place("15068", "belly", (0, -52, -20), FRONT @ rot(y=180), tag="belly")
    m.step("Two short arms reach toward a new friend")
    for side in (-1, 1):
        m.place("11477", "body", (side * 20, -62, 0), rot(z=90 * side) @ rot(y=180), tag=f"arm_{side}")
    # (the tail before the head: the eyes are then the last close-up of the video, and it ends on
    # the face; with the flame last it ended behind it)
    m.step("Curl the tail up and out to the side")
    tail_rotation = rot(z=40)
    tail_base = np.array((10., -38., 24.))
    m.place("40379", "body", tail_base, tail_rotation, tag="curved_tail")
    m.step("Build a translucent two-plate collar at the tail tip")
    tip = tail_base + tail_rotation @ np.array((0., -58.5, 69.))
    collar_rotation = tail_rotation @ rot(x=-16)
    upward = collar_rotation @ np.array((0., -1., 0.))
    collar = tip + upward * 4
    m.place("85861", "flame", collar, collar_rotation, tag="tail_collar_lower")
    m.place("85861", "flame", collar + upward * 8, collar_rotation, tag="tail_collar_upper")
    m.step("Light the tail with a translucent orange flame")
    m.place("6126b", "flame", collar + upward * 16, collar_rotation @ rot(x=90), tag="tail_flame")
    m.step("Make a short neck and a broad base for the head")
    m.place("3022", "body", (0, -80, 0), tag="neck")
    m.place("3020", "body", (0, -88, -20), tag="jaw_base")
    m.place("3710", "body", (0, -88, 10), tag="head_back_base")
    m.step("Build the lower jaw and two orange cheeks")
    m.place("3001", "body", (0, -112, 0), tag="jaw_back")
    m.place("11211", "body", (0, -112, -30), tag="mouth_mount")
    for side in (-1, 1):
        m.place("3005", "body", (side * 30, -112, -30), tag="cheeks")
    m.step("A tiny dark mouth below the eyes")
    m.place("3069b", "mouth", (0, -102, -48), FRONT, tag="mouth")
    m.step("Build the forehead with the eye studs facing forward")
    m.place("3001", "body", (0, -136, 0), tag="head_back")
    m.place("3004", "body", (0, -136, -30), tag="forehead")
    for side in (-1, 1):
        m.place("87087", "body", (side * 30, -136, -30), tag=f"eye_mount_{side}")
    m.step("Two bright eyes with their highlights at the top")
    for side in (-1, 1):
        m.place("98138p2j", "eyes", (side * 30, -126, -48), FRONT @ rot(y=45), tag="eyes")
    m.step("Round off the orange head")
    for side in (-1, 1):
        m.place("15068", "body", (side * 20, -136, -20), tag="crown")
    m.place("2431", "body", (0, -144, 10), tag="crown_back")
