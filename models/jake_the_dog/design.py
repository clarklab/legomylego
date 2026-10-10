"""Jake, built to sit beside Finn: one rounded body, disc eyes and noodle limbs.
LDraw coordinates: -Y is up, front is -Z. Table y=0; one stud=20 LDU.
Our own construction from the owner's character references; no borrowed LEGO design.
"""
import numpy as np
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)
ACROSS = rot(y=90)
HIP = 86
BODY_FLOOR = 120
SHOULDER = 206
ARM_BEND = {-1: 100, 1: 130}
ARM_TURN = {-1: 90, 1: -90}


def build_leg(model, side):
    name = 'left' if side > 0 else 'right'
    leg = model.submodel(name + '_leg', name.title() + ' leg')
    # Origin is the hip pin; local table is y=86.
    leg.step('A yellow foot: the sole, a plate for the toe and a jumper for the ankle')
    leg.place('3020', 'body', (0, 78, -20), rot(y=90), tag='foot')
    leg.place('3023', 'body', (0, 70, -30), tag='foot')
    leg.place('87580', 'body', (0, 70, 0), tag='ankle')
    leg.step('Round the toe, then stack two round bricks for the short leg')
    leg.place('15068', 'body', (0, 78, -40), tag='toe')
    leg.place('3062b', 'body', (0, 46, 0), tag='leg')
    leg.place('3062b', 'body', (0, 22, 0), tag='leg')
    leg.step('The hip: a plate with a Technic brick above the leg and a slope in front')
    leg.place('3023', 'body', (0, 14, -10), rot(y=90), tag='hip')
    leg.place('6541', 'body', (0, -10, 0), ACROSS, tag='hip')
    leg.place('54200', 'body', (0, 14, -20), tag='hip')
    return leg


def build_arm(model, side):
    name = 'left' if side > 0 else 'right'
    forearm = model.submodel(name + '_forearm', name.title() + ' forearm')
    forearm.step('Push the elbow clip into two yellow round bricks')
    forearm.place('3484', 'body', (0, 0, 0), rot(y=90), tag='elbow_clip')
    forearm.place('3062b', 'body', (0, 14, 0), tag='forearm')
    forearm.place('3062b', 'body', (0, 38, 0), tag='hand')
    arm = model.submodel(name + '_arm', name.title() + ' arm')
    arm.step('The shoulder: a yellow Technic brick and tile, with two round bricks below')
    arm.place('6541', 'body', (0, -10, 0), ACROSS, tag='shoulder')
    arm.place('3070b', 'body', (0, -18, 0), tag='shoulder')
    arm.place('3062b', 'body', (0, 14, 0), tag='upper_arm', insert=(0, 1, 0))
    arm.place('3062b', 'body', (0, 38, 0), tag='upper_arm', insert=(0, 1, 0))
    turn = ARM_TURN[side]
    arm.place('26047', 'body', (0, 62, 0), rot(y=turn), tag='elbow', insert=(0, 1, 0))
    arm.step('Clip on the forearm and bend it up')
    handle = np.array([0, 64, 0]) + rot(y=turn) @ np.array([0, 0, -20])
    arm.use(forearm, tuple(handle), rot(x=-ARM_BEND[side], y=turn), tag='forearm')
    return arm


def rounded_floor(m, height):
    m.place('3795', 'body', (0, -height, 0), rot(y=90), tag='body')
    for x, z, a in ((30,30,0),(30,-30,90),(-30,-30,180),(-30,30,270)):
        # Each corner's inner stud is at x=+/-30,z=+/-10.
        m.place('30357', 'body', (x, -height, z/3), rot(y=a), tag='body')


def build(model):
    m = model.main
    legs = {s: build_leg(model, s) for s in (-1,1)}
    arms = {s: build_arm(model, s) for s in (-1,1)}
    m.step('The hidden hips: a plate, two Technic bricks and a brick in front')
    m.place('3022', 'body', (0,-72,0), tag='hips')
    for x in (-10,10):
        m.place('6541', 'body', (x,-96,10), ACROSS, tag='hips')
    m.place('3004', 'body', (0,-96,-10), tag='hips')
    m.step('Tie the hips together and push in the two leg pins')
    m.place('3022', 'body', (0,-104,0), tag='hips')
    m.place('3032', 'body', (0,-112,0), tag='belly')
    for s in (-1,1):
        m.place('2780', 'pin', (20*s,-HIP,10), tag='hip_pin', insert=(s,0,0))
    m.step('Five plates make the rounded floor of the belly')
    rounded_floor(m, BODY_FLOOR)
    for layer in range(1,7):
        height = BODY_FLOOR + 24*layer
        m.step(f'Body ring {layer}: rounded corners, a front and back, and two sides')
        for x,z,a in ((50,-30,0),(-50,-30,90),(-50,30,180),(50,30,270)):
            m.place('85080', 'body', (x,-height,z), rot(y=a), tag='body')
        front = '30414' if layer == 5 else '3010'
        m.place(front, 'body', (0,-height,-50), tag='face_mount' if layer==5 else 'body')
        m.place('30414' if layer==2 else '3010', 'body', (0,-height,50), rot(y=180), tag='tail_mount' if layer==2 else 'body')
        for s in (-1,1):
            side_part = '3700' if layer==4 else ('11211' if layer==6 else '3004')
            m.place(side_part, 'body', (70*s,-height,0), rot(y=-90*s), tag='body')
        if layer==4:
            m.step('Push a black shoulder pin into each side')
            for s in (-1,1):
                m.place('2780', 'pin', (80*s,-SHOULDER,0), tag='shoulder_pin', insert=(s,0,0))
    m.step('Tie the walls together with another rounded layer of plates')
    rounded_floor(m, 272)
    m.step('Four dome corners round the top of his head')
    for x,z,a in ((30,-10,0),(-30,-10,90),(-30,10,180),(30,10,270)):
        m.place('88293', 'body', (x,-320,z), rot(y=a), tag='crown')
    m.step('Fill the middle of the crown and smooth its exposed studs')
    m.place('2456', 'body', (0,-296,0), rot(y=90), tag='crown')
    for z,a in ((-30,0),(30,180)):
        m.place('24309', 'body', (0,-320,z), rot(y=a), tag='crown')
    for x in (-30,30):
        for z in (-10,10):
            m.place('98138', 'body', (x,-328,z), tag='crown')
    m.step('Press a six-stud face plate onto the four front studs')
    m.place('3958', 'body', (0,-240,-68), FRONT, tag='face')
    m.step('Smooth the forehead and cheeks with yellow tiles')
    m.place('6636', 'body', (0,-290,-76), FRONT, tag='face')
    for h in (250,270):
        m.place('3069b', 'body', (0,-h,-76), FRONT, tag='face')
    for x in (-50,50):
        m.place('63864', 'body', (x,-210,-76), FRONT @ rot(y=90), tag='face')
    m.step('A small black smile, with a support plate for each round jowl')
    m.place('1748', 'eye', (0,-190,-76), FRONT, tag='mouth')
    for x in (-20,20):
        m.place('3023', 'body', (x,-210,-76), FRONT, tag='muzzle_mount')
    m.step('Two yellow jumpers position the eyes; black round plates lift their rims clear')
    for x in (-40,40):
        m.place('87580', 'body', (x,-260,-76), FRONT, tag='eyes_mount')
        m.place('85861', 'eye', (x,-260,-84), FRONT, tag='eyes_mount')
    m.step('Black dishes outline the two big white eyes')
    for x in (-40,40):
        m.place('43898', 'eye', (x,-260,-92), FRONT, tag='eyes')
        m.place('14769', 'white', (x,-260,-100), FRONT, tag='eyes')
    m.step('Two narrow round bricks support the oval black nose')
    for x in (-10,10):
        m.place('3062b', 'body', (x,-230,-92), FRONT, tag='nose_mount')
    m.place('1126', 'eye', (0,-230,-100), FRONT, tag='nose')
    m.step('Stack a round plate and smooth round tile for each hanging jowl')
    for x in (-20,20):
        m.place('4032', 'body', (x,-200,-84), FRONT, tag='muzzle')
        m.place('14769', 'body', (x,-200,-92), FRONT, tag='muzzle')
    for s in (-1,1):
        m.step('A short rounded ear on the side of the head')
        side = rot(y=-90*s) @ FRONT
        # On the forward of the two side studs; long axis vertical.
        turn = side @ rot(y=90)
        m.place('3023', 'body', (88*s,-244,-10), turn, tag='ear')
        m.place('1126', 'body', (96*s,-244,-10), turn, tag='ear')
    m.step('A small upturned tail: an open stud holding a yellow curved bar')
    m.place('85861', 'body', (10,-158,68), rot(x=-90), tag='tail_mount')
    tail_turn = np.column_stack([(0,0,-1),(-1,0,0),(0,1,0)])
    m.place('33085', 'body', (10,-158,64), tail_turn, tag='tail')
    for s in (-1,1):
        m.step('Push a short leg onto its hidden hip pin')
        m.use(legs[s], (30*s,-HIP,10), tag='left_leg' if s>0 else 'right_leg', insert=(s,0,0))
    for s in (-1,1):
        m.step('Attach the arm and pose the elbow')
        m.use(arms[s], (90*s,-SHOULDER,0), tag='left_arm' if s>0 else 'right_arm', insert=(s,0,0))
