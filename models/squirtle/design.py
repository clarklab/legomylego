"""Our own pocket Squirtle: a dish shell and an oversized curled plumbing tail.
LDraw: -Y up, -Z front; 20 LDU per stud, 8 per plate. Table is y=0.
"""
import numpy as np
from brickkit.ldraw.matrix import rot

FRONT = rot(x=90)
BACK = rot(x=-90)


def foot(model, side):
    leg = model.submodel('left_foot' if side < 0 else 'right_foot')
    leg.step('A broad blue sole with a raised heel')
    leg.place('3021', 'body', (20*side, -8, 0), rot(y=90), tag='sole')
    leg.place('3022', 'body', (20*side, -16, 10), tag='heel')
    leg.step('Round the front into a flipper toe')
    leg.place('15068', 'body', (20*side, -8, -10), tag='toe')
    return leg


def build(model):
    m = model.main
    # (the right foot first: in the video pieces come in from the left, and the left foot's heel
    # then has nothing to pass over; the other way round the right heel brushed the left toe)
    feet = [foot(model, s) for s in (1,-1)]
    # (the feet first, then the plate that ties them: no step is one piece by itself)
    m.step('Stand the two flipper feet side by side, toes forward, and tie their heels together '
           'with a blue 1 x 2 plate')
    for f in feet:
        m.use(f, tag=f.name)
    m.place('3023', 'body', (0,-24,20), tag='hips')
    m.step('A blue plate behind the right heel starts the outboard tail, and a second hip plate '
           'leaves clearance above the curved toes')
    m.place('3023', 'body', (40,-24,20), tag='tail_root')
    m.place('3022', 'body', (0,-32,10), tag='hips')
    m.step('Two bricks turn studs toward the sides for the little arms')
    for s in (-1,1):
        m.place('11211', 'body', (10*s,-56,10), rot(y=-90*s), tag='shoulders')
    m.step('The chest and back each have two studs for the belly and shell')
    m.place('11211', 'body', (0,-80,0), tag='chest')
    m.place('11211', 'body', (0,-80,20), rot(y=180), tag='back')
    m.place('3022', 'body', (0,-88,10), tag='neck')
    m.step('A round tan belly and two rounded blue flippers')
    m.place('14769', 'belly', (0,-60,-18), FRONT, tag='belly')
    for s in (-1,1):
        side = rot(y=-90*s) @ FRONT @ rot(y=90)
        m.place('37352', 'body', (44*s,-46,0), side, tag='arm')
    m.step('A jumper behind the body centres the shell')
    m.place('87580', 'belly', (0,-60,38), BACK, tag='shell_mount')
    m.step('A tan rim around a brown domed shell, finished with a smooth centre')
    m.place('3960', 'belly', (0,-60,54), BACK, tag='shell_rim')
    m.place('6141', 'belly', (0,-60,62), BACK, tag='shell_spacer')
    m.place('43898', 'shell', (0,-60,70), BACK, tag='shell')
    m.place('98138', 'shell', (0,-60,78), BACK, tag='shell_centre')
    m.step('A wide plate supports the oversized head')
    m.place('3031', 'body', (0,-96,-10), tag='head_base')
    m.step('Two eye-support bricks in front and two bricks behind them')
    for x in (-20,20):
        m.place('11211', 'body', (x,-120,-40), tag='face')
    m.place('3001', 'body', (0,-120,-10), tag='head')
    m.place('3010', 'body', (0,-120,20), tag='head')
    m.step('Tie the head together and raise the centre of the crown')
    m.place('3031', 'body', (0,-128,-10), tag='crown_base')
    m.place('3020', 'body', (0,-136,-10), tag='crown_support')
    m.step('Four curved slopes make a rounded blue crown')
    for x in (-20,20):
        for z,a in ((-30,0),(10,180)):
            m.place('15068', 'body', (x,-128,z), rot(y=a), tag='crown')
    m.step('Two printed eyes and a small blue pad for the smile')
    for x in (-30,30):
        m.place('98138p07', 'eye', (x,-110,-58), FRONT, tag='eye')
    m.place('87580', 'body', (0,-100,-58), FRONT, tag='smile_mount')
    m.step('A little black smile below the eyes')
    m.place('1748', 'mouth', (0,-100,-66), FRONT, tag='smile')
    m.step('The first blue elbow curls up from the heel')
    turn = np.column_stack(((0,-1,0),(0,0,-1),(1,0,0)))
    m.place('25214', 'body', (50,-54,20), turn, tag='tail')
    m.step('An axle joins the next blue bend, turning the tail upward')
    m.place('32062', 'axle', (80,-54,20), tag='tail_axle')
    turn = np.column_stack(((1,0,0),(0,0,1),(0,-1,0)))
    m.place('25214', 'body', (110,-54,20), turn, tag='tail')
    m.step('One more axle and elbow curl the tip back toward the head')
    m.place('32062', 'axle', (110,-84,20), rot(z=90), tag='tail_axle')
    turn = np.column_stack(((0,-1,0),(0,0,1),(-1,0,0)))
    m.place('25214', 'body', (110,-114,20), turn, tag='tail')
