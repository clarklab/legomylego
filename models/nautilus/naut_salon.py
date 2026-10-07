"""Captain Nemo's salon (Walt Disney's 20,000 Leagues Under the Sea, 1954) at minifigure
scale: a drop-in interior module for the salon bay, the big round salon window its focal point.

`build_salon(model, parent)` builds one sub-assembly, "nemo_salon", in the hull frame (naut_shape:
LDU, -Y up, bow toward -X, port toward -Z, side keels on y = 0) and places it in `parent`. It is
one piece by itself: a raft of plates (top at RAFT = SALON_FLOOR - 8 = 56) pressed down onto the
salon floor's studs (top at SALON_FLOOR = 64) across the bay, x -280..180 at |z| <= 120 (only
|z| <= 100 aft of x = 80, where the hull narrows), and everything else built on the raft:

* **Nemo's pipe organ** against the after bulkhead, its red velvet bench in front: a dais, a
  console with grille-brick cheeks, two manuals of printed keys, candles, sheet music on a desk,
  two tall brass pipes either side of it and eight more along the case in an arch (Pearl Gold
  bars in open-stud round plates, their mouths lined up).
* **The library** on the forward bulkhead: a bookcase ten studs wide built flat and stood up on
  side studs, books of many colours and sizes on two shelves, a gilt-framed portrait (a grey-
  bearded gentleman in black) in the middle.
* **A bookcase** against the starboard wall: a shelf of books under a gilt-framed sailing ship.
* **A round table** on a blue rug (a nautical chart, brass goblets, a candle), two red velvet
  chairs.
* **A red velvet camelback settee** with scrolled arms facing the port window, on a red rug
  (black border, brass corners and medallion, gold fringes).
* **A chart table** (compass, chronometer, candle), **a brass telescope** on a turned stand
  aimed at the window, **an aquarium** (two koi in deep blue water behind clear blue tiles),
  **a cabinet of curiosities** (specimen bottles, gems on brass mounts, brass goblets) and four
  **standard lamps** (brass, Trans-Yellow shades) that glow in lit renders with the candles.
* **Floorboards** in two browns over every stud left bare, except the crew's standing spots.

`crew_spots()` gives where the Nautilus crew (models/nautilus_crew) go: two standing spots at
the port window, one by the organ, Nemo's seat at the organ, the settee's two seats and the two
chairs (seated: legs at 90 degrees; a seated figure is held by its thighs' holes, 16.8 LDU in
front of its `at`, on the seat's front row of studs).

What it needs from the hull: studs under the raft; the room's envelope (the hull's inner faces
as naut_relief drew them on 2026-10-01: 7 studs either side at the floor, narrowing to 3.8 at
the deck) with 24 LDU to spare above every part, so the salon can be pushed down onto the floor
after the walls and the deck are on; the windows' insides clear (nothing over the raft's tiles
at x -130..10 along the port wall, z <= -80, and x -130..0 along the starboard wall)."""
from __future__ import annotations

import random

import numpy as np

import naut_shape as shp
from brickkit.ldraw.matrix import rot

S = 20
RAFT = int(shp.SALON_FLOOR) - 8                 # 56: the raft's top, the salon's floor
BAY = tuple(int(v) for v in shp.SALON_BAY)      # (-280, 180)
WIN_X = int(shp.SALON_C[0])                     # -60: the windows' centre line
# the furniture is laid out for this bay: fail loudly if the hull's frame moves under it
assert BAY == (-280, 180) and WIN_X == -60 and RAFT == 56, (BAY, WIN_X, RAFT)

# colours: real LEGO colour names, the same in every hull colourway
WOOD = "Reddish Brown"
DARK = "Dark Brown"
VELVET = "Dark Red"
BRASS = "Pearl Gold"
GLASS = "Trans-Light Blue"
SHADE = "Trans-Yellow"
BOOKS = ["Dark Red", "Dark Blue", "Dark Green", "Dark Tan", "Tan", "Black", "Reddish Brown",
         "Sand Green", "Medium Nougat", "Dark Orange", "Sand Blue", "Dark Red", "Dark Blue"]
SPINES = ["Dark Red", "Black", "Reddish Brown", "Dark Blue"]     # grille tiles: banded spines

PLATE = {(1, 1): "3024", (1, 2): "3023", (1, 3): "3623", (1, 4): "3710", (1, 6): "3666",
         (1, 8): "3460", (1, 10): "4477", (1, 12): "60479", (2, 2): "3022", (2, 3): "3021",
         (2, 4): "3020", (2, 6): "3795", (2, 8): "3034", (2, 10): "3832", (2, 12): "2445",
         (4, 4): "3031", (4, 6): "3032", (4, 8): "3035", (4, 10): "3030", (4, 12): "3029",
         (6, 6): "3958", (6, 8): "3036", (6, 10): "3033", (6, 12): "3028"}
TILE = {(1, 1): "3070b", (1, 2): "3069b", (1, 3): "63864", (1, 4): "2431", (1, 6): "6636",
        (1, 8): "4162", (2, 2): "3068b", (2, 4): "87079"}
BRICK = {(1, 1): "3005", (1, 2): "3004", (1, 3): "3622", (1, 4): "3010", (1, 6): "3009",
         (1, 8): "3008", (2, 2): "3003", (2, 3): "3002", (2, 4): "3001"}
SIDE_STUD = {1: "87087", 2: "11211", 4: "30414"}    # bricks with studs on their -Z side

# which way a piece's front (its own -Z) faces in the hull frame, and that direction
FACE = {"-z": None, "+z": rot(y=180), "-x": rot(y=90), "+x": rot(y=-90)}
DIR = {"-z": (0, -1), "+z": (0, 1), "-x": (-1, 0), "+x": (1, 0)}


def orient(ex, ey, ez) -> np.ndarray:
    """Rotation whose columns are where the part's local X, Y and Z axes point."""
    return np.column_stack([ex, ey, ez]).astype(float)


def runs(n: int, sizes=(8, 6, 4, 3, 2, 1)) -> list[int]:
    out = []
    while n:
        k = next(s for s in sizes if s <= n)
        out.append(k)
        n -= k
    return out


# ------------------------------------------------------------------ panels built flat
class Panel:
    """A panel built flat on its base plate (studs up, the plate's top at y = 0), W columns
    by H rows: column c is centred at x = 20 c + 10 - 10 W, row r at z = -(20 r + 10) (row 0
    is the bottom row once it stands up). Pieces lie on it at y = -8, and -16 on those."""

    def __init__(self, sub, W: int, H: int):
        self.sub, self.W, self.H = sub, W, H

    def x(self, c: float) -> float:
        return S * c + 10 - 10 * self.W

    def z(self, r: float) -> float:
        return -(S * r + 10)

    def at(self, c, r, w=1, h=1, y=-8):
        return ((self.x(c) + self.x(c + w - 1)) / 2, y, (self.z(r) + self.z(r + h - 1)) / 2)

    def put(self, table, color, c, r, w=1, h=1, y=-8, **kw):
        """A part from `table` over columns c..c+w-1 and rows r..r+h-1."""
        part = table[(min(w, h), max(w, h))]
        R = None if w >= h else rot(y=90)
        return self.sub.place(part, color, self.at(c, r, w, h, y), R, **kw)

    def part(self, part, color, c, r, w=1, h=1, y=-8, R=None, **kw):
        return self.sub.place(part, color, self.at(c, r, w, h, y), R, **kw)

    def tiles(self, color, c, r, n, y=-8):
        """A row of tiles over columns c..c+n-1."""
        for k in runs(n):
            self.put(TILE, color, c, r, k, 1, y=y)
            c += k

    def board(self, color, c, r, w=1, h=1):
        """A board standing out 16 LDU: a plate and tiles on it."""
        self.put(PLATE, color, c, r, w, h)
        if w >= h:
            self.tiles(color, c, r, w, y=-16)
        else:
            for k in runs(h):
                self.put(TILE, color, c, r, 1, k, y=-16)
                r += k

    def base(self, color):
        self.sub.place(PLATE[(min(self.W, self.H), max(self.W, self.H))], color,
                       (0, 0, -10 * self.H), None if self.W >= self.H else rot(y=90))

    def books(self, rng, c0, c1, r):
        """Books standing two rows tall in columns c0..c1 (rows r, r + 1): tall books (1 x 2
        tiles), fat ones standing out (a 1 x 2 plate and tile), banded spines (grille tiles)
        and pairs of short ones (1 x 1 tiles)."""
        for c in range(c0, c1 + 1):
            k = rng.random()
            if k < 0.32:
                self.put(TILE, rng.choice(BOOKS), c, r, 1, 2)
            elif k < 0.52:                      # a fat book standing out from the rest
                col = rng.choice(BOOKS)
                self.put(PLATE, col, c, r, 1, 2)
                self.put(TILE, col, c, r, 1, 2, y=-16)
            elif k < 0.72:
                self.part("2412b", rng.choice(SPINES), c, r, 1, 2, R=rot(y=90))
            else:
                a, b = rng.sample(BOOKS, 2)
                self.put(TILE, a, c, r)
                self.put(TILE, b, c, r + 1)

    def frame_side(self, c, r):
        """A side of a gilt frame: a Pearl Gold plate and tile, two rows tall."""
        self.put(PLATE, BRASS, c, r, 1, 2)
        self.put(TILE, BRASS, c, r, 1, 2, y=-16)


def panel_R(face) -> np.ndarray:
    """Rotation standing a flat-built panel up, its studs toward `face` (a unit vector in the
    parent's frame), its rows going up."""
    f = np.asarray(face, float)
    down = np.array([0.0, 1.0, 0.0])
    return orient(np.cross(-f, down), -f, down)


STAND = panel_R((0, 0, -1))      # a panel facing the parent's -Z


def frame_row(P, r, c0, c1, gilt=(None, None)):
    """A board along row r over columns c0..c1 (a Dark Brown plate under it), Dark Brown tiles
    on it but a gilt frame's edge over columns gilt[0]..gilt[1] (round tiles at its corners)."""
    P.put(PLATE, DARK, c0, r, c1 - c0 + 1, 1)
    g0, g1 = gilt
    if g0 is None:
        P.tiles(DARK, c0, r, c1 - c0 + 1, y=-16)
        return
    if g0 > c0:
        P.tiles(DARK, c0, r, g0 - c0, y=-16)
    P.part("98138", BRASS, g0, r, y=-16)
    P.tiles(BRASS, g0 + 1, r, g1 - g0 - 1, y=-16)
    P.part("98138", BRASS, g1, r, y=-16)
    if g1 < c1:
        P.tiles(DARK, g1 + 1, r, c1 - g1, y=-16)


# ------------------------------------------------------------------ the library wall
def library(model):
    """The forward bulkhead's library, ten studs wide, 7 rows (152 LDU) tall: a wall of bricks
    one stud deep with side studs in its bottom and top courses; pushed onto them, a bookcase
    built flat (a plinth, eight books, a shelf with the portrait's frame in it, books either
    side of a gilt-framed portrait) and its cornice. Local frame: front -Z, x -100..100, the
    bricks at z 0..20, the raft's top at y = 0."""
    lib = model.submodel("salon_library", "Salon: the library")
    for n, row in enumerate([[4, 4, 2], [6, 4], [4, 6], [6, 4], [4, 6], [4, 4]]):
        lib.step("The library's back wall: side studs in the bottom and top courses"
                 if n == 0 else "")
        x = -100 if n < 5 else -80          # the top course: 8 studs (the hull narrows there)
        for w in row:
            lib.place(SIDE_STUD[w] if n in (0, 5) else BRICK[(1, w)], WOOD,
                      (x + 10 * w, -24 * (n + 1), 10))
            x += S * w

    pan = model.submodel("salon_library_case", "Salon: the library's bookcase, built flat")
    P = Panel(pan, 10, 6)
    rng = random.Random(1870)
    pan.step("A 6 x 10 plate: the bookcase's back")
    P.base(WOOD)
    pan.step("The plinth and the sides")
    P.tiles(DARK, 0, 0, 10)
    for c in (0, 9):
        P.board(DARK, c, 1, 1, 2)
        P.board(DARK, c, 4, 1, 2)
    pan.step("The middle shelf, with the foot of the portrait's frame")
    frame_row(P, 3, 0, 9, gilt=(3, 6))
    pan.step("Books on the lower shelf")
    P.books(rng, 1, 4, 1)
    pan.step("More books")
    P.books(rng, 5, 8, 1)
    pan.step("The portrait in its gilt frame")
    P.frame_side(3, 4)
    P.frame_side(6, 4)
    P.part("3068bp75", WOOD, 4, 4, 2, 2, R=rot(y=180))       # upright once stood up
    pan.step("Books either side of it")
    P.books(rng, 1, 2, 4)
    P.books(rng, 7, 8, 4)

    top = model.submodel("salon_library_top", "Salon: the library's cornice, built flat")
    T = Panel(top, 10, 1)
    top.step("The cornice, with the top of the portrait's frame")
    T.base(WOOD)
    frame_row(T, 0, 0, 9, gilt=(3, 6))

    lib.step("Push the bookcase onto the bottom course's side studs")
    lib.use(pan, (0, -4, -8), STAND, insert=(0, 0, -1))
    lib.step("The cornice onto the top course's side studs")
    lib.use(top, (0, -124, -8), STAND, insert=(0, 0, -1))
    return lib


def bookcase(model):
    """A bookcase four studs wide for the starboard wall: a shelf of books under a sailing ship
    in a gilt frame. A column of bricks (side studs in its bottom course) and a panel built flat
    pushed onto them, six rows tall (the hull leans in over it). Local frame: front -Z,
    x -40..40, the bricks at z 0..20."""
    bc = model.submodel("salon_bookcase", "Salon: the bookcase with the ship painting")
    for n in range(5):
        bc.step("The bookcase's back: a column of 1 x 4 bricks" if n == 0 else "")
        bc.place(SIDE_STUD[4] if n == 0 else BRICK[(1, 4)], WOOD, (0, -24 * (n + 1), 10))
    pan = model.submodel("salon_bookcase_case", "Salon: the bookcase, built flat")
    P = Panel(pan, 4, 6)
    rng = random.Random(20000)
    pan.step("A 4 x 6 plate")
    P.base(WOOD)
    pan.step("The plinth and a shelf of books")
    P.tiles(DARK, 0, 0, 4)
    for c in range(4):
        if rng.random() < 0.4:
            P.part("98138", rng.choice(BOOKS), c, 1)
        else:
            P.put(TILE, rng.choice(BOOKS), c, 1)
    pan.step("A gilt frame")
    frame_row(P, 2, 0, 3, gilt=(0, 3))
    pan.step("The sailing ship in it")
    P.frame_side(0, 3)
    P.frame_side(3, 3)
    P.part("3068bp71", "Dark Tan", 1, 3, 2, 2, R=rot(y=90))   # upright once stood up
    frame_row(P, 5, 0, 3, gilt=(0, 3))
    bc.step("Push the bookcase onto the side studs")
    bc.use(pan, (0, -4, -8), STAND, insert=(0, 0, -1))
    return bc


# ------------------------------------------------------------------ the organ
# the back rank of pipes, left to right in the organ's frame: (bar, its length, round plates
# under its foot, the foot's base); the middle two stand on the music desk's brick
PIPES = [("87994", 60, 0, -80), ("30374", 80, 0, -80), ("30374", 80, 1, -80),
         ("87994", 60, 1, -104), ("87994", 60, 1, -104), ("30374", 80, 1, -80),
         ("30374", 80, 0, -80), ("87994", 60, 0, -80)]
BENCH = (-10, -24)       # the organ bench's stud row (z) and seat top (y), the organ's frame
MOUTHS = -130            # the pipes' mouths: round plates slid onto the bars, lined up


def organ(model):
    """Nemo's pipe organ, eight studs wide, with its bench. Local frame: front -Z (toward the
    organist), x -80..80; the dais z -20..60 (the bench on its front row, the console z 0..40,
    the case z 40..60), the raft's top at y = 0. The tallest pipes reach y = -178 (the deck's
    underside is at -208 in this frame, and the hull leans in over the sides)."""
    org = model.submodel("salon_organ", "Salon: Nemo's pipe organ")
    org.step("The organ's dais")
    org.place("3035", WOOD, (0, -8, 20))
    org.step("The bench: red velvet on turned legs")
    for x in (-30, 30):
        org.place("6141", WOOD, (x, -16, -10))
    org.place("3710", VELVET, (0, -24, -10))
    for x in (-30, 30):
        org.place("98138", BRASS, (x, -32, -10))
    org.step("The console's cheeks and the case")
    for x in (-70, 70):
        org.place("2877", WOOD, (x, -32, 20), rot(y=90))
        org.place("3023", DARK, (x, -40, 20), rot(y=90))
    for n in range(3):
        org.place("3008", WOOD, (0, -32 - 24 * n, 50))
    org.place("11211", WOOD, (0, -104, 50))
    org.step("The keyboard shelf and the lower manual")
    org.place("3034", WOOD, (0, -48, 20))
    for x in (-40, 0, 40):
        org.place("3069bp0j", "White", (x, -56, 10))
    org.step("The upper manual")
    org.place("3666", "Black", (0, -56, 30))
    for x in (-40, 0, 40):
        org.place("3069bp0j", "White", (x, -64, 30))
    org.step("Candles at the corners, the music on its desk", view="above")
    for x in (-70, 70):
        org.place("6141", BRASS, (x, -56, 10), tag="salon_candle")
        org.place("3062b", "White", (x, -80, 10), tag="salon_candle")
        org.place("37775", "Trans-Orange", (x, -80, 10), tag="salon_candle")
    org.place("3022", "Black", (0, -104, 32), STAND)
    org.place("3068bp0s", "White", (0, -104, 24), STAND)
    org.step("The tall pipes either side of the music")
    for x in (-70, 70):
        org.place("85861", BRASS, (x, -56, 30))
        org.place("63965", BRASS, (x, -72, 30))
    for k, (bar, length, lift, y) in enumerate(PIPES):
        if k % 4 == 0:
            org.step("The pipes along the case" if k == 0 else "", view="above")
        x = -70 + 20 * k
        for _ in range(lift):
            org.place("6141", BRASS, (x, y - 8, 50))
            y -= 8
        org.place("85861", BRASS, (x, y - 8, 50))
        org.place(bar, BRASS, (x, y - 6 - length, 50))
    org.step("The pipes' mouths, lined up")
    for k in range(len(PIPES)):
        org.place("85861", BRASS, (-70 + 20 * k, MOUTHS, 50))
    return org


# ------------------------------------------------------------------ smaller furniture
def table(model):
    """The round table: a Dark Brown 4 x 4 round plate on a turned pedestal, a nautical chart,
    brass goblets and a candle. Local frame: centred, the raft's top at y = 0."""
    t = model.submodel("salon_table", "Salon: the round table")
    t.step("The pedestal and the top")
    t.place("4032a", DARK, (0, -8, 0))
    t.place("3941", WOOD, (0, -32, 0))
    t.place("60474", DARK, (0, -40, 0))
    t.step("A nautical chart, brass goblets and a candle", view="above")
    t.place("3068bp32", "Tan", (0, -48, 0))
    t.place("2343", BRASS, (-30, -80, 10))
    t.place("2343", BRASS, (30, -80, -10))
    t.place("6141", BRASS, (10, -48, 30), tag="salon_candle")
    t.place("3062b", "White", (10, -72, 30), tag="salon_candle")
    t.place("37775", "Trans-Orange", (10, -72, 30), tag="salon_candle")
    return t


def chair(model):
    sub = model.submodel("salon_chair", "Salon: a red velvet chair")
    sub.step("A chair")
    sub.place("4079", VELVET, (0, -8, 0))
    return sub


def settee(model):
    """A red velvet camelback settee six studs wide and three deep: two seats (the front row's
    studs for the crew's thighs, a smooth row under their hips), a back rising to a hump in the
    middle, scrolled arms with brass caps. Local frame: front -Z, x -60..60, z -30..30."""
    s = model.submodel("salon_settee", "Salon: the settee")
    s.step("The frame: two plates joined by the arms")
    s.place("3795", WOOD, (0, -8, -10))
    s.place("3666", WOOD, (0, -8, 20))
    for x in (-50, 50):
        s.place("20310", WOOD, (x, -32, -20))
        s.place("3004", WOOD, (x, -32, 10), rot(y=90))
    s.step("Cushions and the back")
    s.place("3710", VELVET, (0, -16, -20))
    s.place("2431", VELVET, (0, -16, 0))
    s.place("3010", VELVET, (0, -32, 20))
    s.place("11477", VELVET, (-20, -32, 20), rot(y=90))
    s.place("11477", VELVET, (20, -32, 20), rot(y=-90))
    s.step("Brass caps on the scrolls, velvet on the arms")
    for x in (-50, 50):
        s.place("98138", BRASS, (x, -40, -20))
        s.place("98138", BRASS, (x, -40, -40))
        s.place("3069b", VELVET, (x, -40, 10), rot(y=90))
    return s


def lamp(model, name, bar="30374", length=80):
    """A standard lamp: a turned foot, a brass column (a bar between two open-stud round plates),
    a Trans-Yellow shade with a brass cap."""
    s = model.submodel(name, "Salon: a standard lamp")
    s.step("A standard lamp")
    s.place("3062b", WOOD, (0, -24, 0))
    s.place("85861", BRASS, (0, -32, 0))
    top = -34 - length
    s.place(bar, BRASS, (0, top, 0))
    s.place("85861", BRASS, (0, top + 2, 0))
    s.place("3062b", SHADE, (0, top - 22, 0), tag="salon_lamp")
    s.place("98138", BRASS, (0, top - 30, 0))
    return s


def chart_table(model):
    """A narrow chart table along the port wall, three studs long on turned legs: a compass,
    a chronometer and a candle. Local frame: front -Z, x -30..30, z -10..10."""
    s = model.submodel("salon_chart_table", "Salon: the chart table")
    s.step("Turned legs and the top")
    for x in (-20, 20):
        s.place("3062b", WOOD, (x, -24, 0))
        s.place("3062b", WOOD, (x, -48, 0))
    s.place("3623", WOOD, (0, -56, 0))
    s.step("A compass, a chronometer and a candle", view="above")
    s.place("98138pc2", BRASS, (-20, -64, 0))
    s.place("98138p2r", BRASS, (0, -64, 0))
    s.place("6141", BRASS, (20, -64, 0), tag="salon_candle")
    s.place("3062b", "White", (20, -88, 0), tag="salon_candle")
    s.place("37775", "Trans-Orange", (20, -88, 0), tag="salon_candle")
    return s


def telescope(model, aim_deg=45):
    """A brass telescope on a turned stand, aimed `aim_deg` degrees from its front (-Z) toward
    +X: the top brick's side stud turns on the round brick under it."""
    s = model.submodel("salon_telescope", "Salon: the telescope")
    s.step("The stand")
    s.place("3062b", WOOD, (0, -24, 0))
    s.place("3062b", WOOD, (0, -48, 0))
    a = np.radians(aim_deg)
    d = np.array([np.sin(a), 0.0, -np.cos(a)])           # where it looks
    s.place("87087", WOOD, (0, -72, 0), rot(y=-aim_deg))
    s.step("The telescope")
    Y = -d
    X = np.cross(Y, [0.0, 1.0, 0.0])
    X /= np.linalg.norm(X)
    stud = np.array([0.0, -62.0, 0.0]) + 10 * d          # the side stud's base
    s.place("64644", BRASS, tuple(stud + 40 * d), orient(X, Y, np.cross(X, Y)))
    return s


def aquarium(model):
    """An aquarium four studs wide: a cabinet with grille doors under a box of deep blue water,
    its glass front a wall of clear blue tiles on side studs with two koi swimming in it, a clear
    blue lid. Local frame: front -Z, x -40..40, z -20..20."""
    s = model.submodel("salon_aquarium", "Salon: the aquarium")
    s.step("The cabinet")
    for x in (-20, 20):
        s.place("2877", WOOD, (x, -24, -10))
    s.place("3010", WOOD, (0, -24, 10))
    s.place("3020", "Black", (0, -32, 0))
    s.step("The water: bricks with studs on their front")
    for y in (-56, -80):
        for x in (-20, 20):
            s.place("11211", "Dark Blue", (x, y, -10))
        s.place("3010", "Dark Blue", (0, y, 10))
    s.step("The glass: clear blue tiles, two koi swimming in it")
    for (x, y), part in (((-20, -46), "3069bp0p"), ((20, -46), "3069b"),
                         ((-20, -70), "3069b"), ((20, -70), "3069bp0q")):
        s.place(part, GLASS, (x, y, -28), STAND)
    s.step("The lid")
    s.place("3020", WOOD, (0, -88, 0))
    for z in (-10, 10):
        s.place("2431", GLASS, (0, -96, z))
    return s


def curiosities(model):
    """A cabinet of curiosities three studs wide: specimen bottles, gems on brass mounts and a
    brass goblet. Local frame: front -Z, x -30..30, z -20..20."""
    s = model.submodel("salon_curiosities", "Salon: the cabinet of curiosities")
    s.step("The cabinet")
    s.place("3002", WOOD, (0, -24, 0))
    s.place("3021", "Black", (0, -32, 0))
    s.step("Specimens", view="above")
    for x in (-20, 20):
        s.place("95228", "Trans-Clear", (x, -80, 10))
    for z, c in ((10, GLASS), (-10, "Trans-Clear")):
        s.place("85861", BRASS, (0, -40, z))
        s.place("30153", c, (0, -44, z))
    s.place("2343", BRASS, (-20, -72, -10))
    s.place("2343", BRASS, (20, -72, -10))
    return s


# ------------------------------------------------------------------ the salon
ORGAN_AT = (120, 0)          # the organ's frame origin (x, z), facing the bow: dais x 100..180
SETTEE_AT = (-60, 50)        # facing the port window: x -120..0, z 20..80
TABLE_AT = (-180, 0)
CHAIRS = {"port": (0, -60, "+z"), "aft": (60, 0, "-x")}      # offsets from the table, facing
LAMPS = [((170, -90), "30374", 80), ((170, 90), "30374", 80),
         ((-270, -110), "87994", 60), ((-270, 110), "87994", 60)]


def crew_spots():
    """Where the Nautilus crew go (hull frame): {name: dict(at, rot, face, pose)} for
    model.minifig(name, at, rot, pose=pose, ...). Standing spots are bare raft studs (feet at
    y = RAFT); seated spots put the figure's thigh holes on the seat's front row of studs."""
    sit = dict(leg_r=90, leg_l=90)
    spots = {
        "window_fore": ((WIN_X - 40, RAFT, -70), "-z", {}),
        "window_aft": ((WIN_X + 40, RAFT, -70), "-z", {}),
        "by_the_organ": ((50, RAFT, -40), "+x", {}),
    }
    # seated: `at` is 16.8 LDU behind the seat's stud row, 19.2 below the seat's top
    ox, oz = ORGAN_AT
    spots["organ_bench"] = ((ox + BENCH[0] - 16.8, RAFT + BENCH[1] + 19.2, oz), "+x",
                            dict(sit, arm_r=75, arm_l=75))
    sx, sz = SETTEE_AT
    for n, dx in enumerate((-20, 20)):
        spots[f"settee_{n + 1}"] = ((sx + dx, RAFT - 16 + 19.2, sz - 20 + 16.8), "-z", sit)
    tx, tz = TABLE_AT
    for name, (cx, cz, f) in CHAIRS.items():
        fx, fz = DIR[f]
        spots[f"chair_{name}"] = ((tx + cx - 6.8 * fx, RAFT - 8 + 19.2, tz + cz - 6.8 * fz), f,
                                  dict(sit, arm_r=30, arm_l=30))
    return {k: dict(at=at, rot=FACE[f], face=f, pose=p) for k, (at, f, p) in spots.items()}


class Floor:
    """The raft's cells (column i: x in [20 i, 20 i + 20], row k: z in [20 k, 20 k + 20]) and
    which are taken: furniture standing on them, a panel just over them, a crew spot."""

    def __init__(self):
        self.cells = set()
        for i in range(BAY[0] // S, BAY[1] // S):
            hw = 120 if S * i < 80 else 100
            self.cells |= {(i, k) for k in range(-hw // S, hw // S)}
        self.taken = set()

    def take(self, x0, x1, z0, z1):
        self.taken |= {(i, k) for i in range(int(min(x0, x1) // S), int(-(-max(x0, x1) // S)))
                       for k in range(int(min(z0, z1) // S), int(-(-max(z0, z1) // S)))}

    def free(self):
        return self.cells - self.taken


def build_salon(model, parent, pos=(0, 0, 0), insert=(0, -1, 0)):
    """Build Captain Nemo's salon as one sub-assembly ("nemo_salon", hull frame) and place it in
    `parent` at `pos` (default the hull frame's origin), pushed down from above. Returns it."""
    salon = model.submodel("nemo_salon", "Captain Nemo's salon")
    floor = Floor()

    salon.step("The salon's floor: plates over the hull's floor studs")
    for xc in (-220, -100, 20):
        salon.place("3028", WOOD, (xc, RAFT, 0), rot(y=90))
    salon.place("3030", WOOD, (120, RAFT, 0), rot(y=90))
    salon.place("4477", WOOD, (170, RAFT, 0), rot(y=90))

    pieces = []        # (caption, sub, x, z, face); their footprints are taken from the floor

    def add(caption, sub, x, z, face, rect):
        floor.take(*rect)
        pieces.append((caption, sub, x, z, face))

    add("The library", library(model), -260, 0, "+x", (-280, -240, -100, 100))
    add("The bookcase", bookcase(model), -180, 100, "-z", (-220, -140, 80, 120))
    ox, oz = ORGAN_AT
    add("Nemo's organ", organ(model), ox, oz, "-x", (100, 180, -80, 80))
    lamps = {}
    for (x, z), bar, length in LAMPS:
        if bar not in lamps:
            lamps[bar] = lamp(model, f"salon_lamp_{length}", bar, length)
        add("A standard lamp", lamps[bar], x, z, "-z", (x - 10, x + 10, z - 10, z + 10))
    tx, tz = TABLE_AT
    add("The round table", table(model), tx, tz, "-z", (tx - 20, tx + 20, tz - 20, tz + 20))
    ch = chair(model)
    for name, (cx, cz, f) in CHAIRS.items():
        x, z = tx + cx, tz + cz
        add("A chair", ch, x, z, f, (x - 20, x + 20, z - 20, z + 20))
    sx, sz = SETTEE_AT
    add("The settee", settee(model), sx, sz, "-z", (sx - 60, sx + 60, sz - 30, sz + 30))
    add("The chart table", chart_table(model), -210, -110, "+z", (-240, -180, -120, -100))
    add("The telescope, aimed at the window", telescope(model), -150, -90, "-z",
        (-160, -140, -100, -80))
    add("The aquarium", aquarium(model), 40, 100, "-z", (0, 80, 80, 120))
    add("The cabinet of curiosities", curiosities(model), 50, -100, "+z", (20, 80, -120, -80))
    for spot in crew_spots().values():              # standing spots stay bare studs
        if spot["pose"].get("leg_r"):
            continue
        x, _, z = spot["at"]
        w, d = (2, 1) if spot["face"] in ("-z", "+z") else (1, 2)
        floor.take(x - 10 * w, x + 10 * w, z - 10 * d, z + 10 * d)

    rug(salon, floor)
    rug(salon, floor, RUG2, field="Dark Blue", border="Dark Tan", fringe=False, medallion=False,
        name="The blue rug")
    boards(salon, floor)
    for caption, sub, x, z, face in pieces:
        salon.step(caption)
        salon.use(sub, (x, RAFT, z), FACE[face], insert=(0, -1, 0))

    model.glow("salon_lamp", strength=2.5)
    model.glow("salon_candle", strength=2.0)
    parent.use(salon, pos, tag="salon_interior", insert=insert)
    _light_walls(parent)
    return salon


def _light_walls(parent):
    """Low walls of bricks on the side keels inside the salon's side panels, either side of the
    windows' bosses (between the hinges' bar stacks): the lamps' light can't reach the joint
    between the side keels and the upper panels' lower edges."""
    import naut_panels as pn
    from naut_kit import AV, BRICK, rect_part
    hinges = set(pn.frame_stations("a"))
    w = pn.FACETS["a"].P[0] - 20                   # inside the panels' hinge line (|z| 170)
    lengths = [n for n in (6, 4, 3, 2, 1) if (1, n) in AV.sizes(BRICK, "hull")]
    first = True
    for side in (-1, 1):
        cols = [i for i in range(int(shp.SALON_BAY[0] // S), int(shp.SALON_BAY[1] // S))
                if not shp.BOSS_X[0] <= S * i + S / 2 < shp.BOSS_X[1]
                and not any(abs(S * i + S / 2 - h) < 15 for h in hinges)]
        runs = []
        for i in cols:
            if runs and runs[-1][-1] == i - 1:
                runs[-1].append(i)
            else:
                runs.append([i])
        for run in runs:
            i0, left = run[0], len(run)
            while left:
                n = next(n for n in lengths if n <= left)
                part, R = rect_part(BRICK, n, 1)
                if first:
                    parent.step("Low walls on the side keels round the salon: they keep its light in")
                    first = False
                parent.place(part, "hull", (S * i0 + S * n / 2, shp.FL_A - 24, side * w), R)
                i0, left = i0 + n, left - n


RUG = (-140, 20, -60, 60)        # x0, x1, z0, z1: in front of the window, under the settee
RUG2 = (-240, -140, -60, 60)     # under the round table


def rug(salon, floor, rect=RUG, field=VELVET, border="Black", fringe=True, medallion=True,
        name="The rug"):
    """A rug: gold fringes at its ends, a border with brass corners, the field and a brass
    medallion; under the furniture standing on it, the raft's studs."""
    x0, x1, z0, z1 = rect
    i0, i1, k0, k1 = x0 // S, x1 // S - 1, z0 // S, z1 // S - 1
    cells = {(i, k) for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)} & floor.free()
    done = set()
    if fringe:
        salon.step(f"{name}: gold fringes", view="above")
        for i in (i0, i1):                   # fringes: grille tiles across the ends
            for k in range(k0, k1 + 1, 2):
                if {(i, k), (i, k + 1)} <= cells:
                    salon.place("2412b", BRASS, (S * i + 10, RAFT - 8, S * k + 20), rot(y=90))
                    done |= {(i, k), (i, k + 1)}
    salon.step(f"{name}'s border, brass at its corners", view="above")
    b0, b1 = (i0 + 1, i1 - 1) if fringe else (i0, i1)
    for (i, k) in sorted(cells - done):
        if i in (b0, b1) or k in (k0, k1):
            corner = i in (b0, b1) and k in (k0, k1)
            salon.place("98138" if corner else "3070b", BRASS if corner else border,
                        (S * i + 10, RAFT - 8, S * k + 10))
            done.add((i, k))
    rest = cells - done
    salon.step(f"{name}'s field", view="above")
    if medallion:
        mi = (x0 + x1) // 2 // S
        mk = k0 + 2                           # in the middle of the part left in view
        med = {(mi - 1, mk - 1), (mi, mk - 1), (mi - 1, mk), (mi, mk)}
        if med <= rest:
            salon.place("14769", BRASS, (S * mi, RAFT - 8, S * mk))
            rest -= med
    fill(salon, rest, field)
    floor.taken |= cells


def boards(salon, floor):
    """Floorboards on every free raft stud: rows of 1 x N tiles along the room, the rows in two
    browns, their joints staggered."""
    cells = floor.free()
    for row_no, k in enumerate(sorted({k for _, k in cells})):
        if row_no % 2 == 0:
            salon.step("Floorboards in two browns" if row_no == 0 else "", view="above")
        row = sorted(i for i, kk in cells if kk == k)
        color = WOOD if k % 2 == 0 else DARK
        spans, start = [], None
        for m, i in enumerate(row):
            start = i if start is None else start
            if m + 1 == len(row) or row[m + 1] != i + 1:
                spans.append((start, i))
                start = None
        for a, b in spans:
            i, first = a, True
            while i <= b:
                lens = (6, 4, 3, 2, 1) if color == WOOD else (4, 3, 2, 1)
                if first and k % 3 == 1:             # stagger the joints
                    lens = (3, 2, 1)
                n = next(n for n in lens if n <= b - i + 1)
                salon.place(TILE[(1, n)], color, (S * i + 10 * n, RAFT - 8, S * k + 10))
                i += n
                first = False


def fill(salon, cells, color):
    """Tile cells with 2 x 4, 2 x 2, 1 x 4, 1 x 2 and 1 x 1 tiles."""
    cells = set(cells)
    for i, k in sorted(cells):
        if (i, k) not in cells:
            continue
        for w, d in ((4, 2), (2, 4), (2, 2), (4, 1), (1, 4), (2, 1), (1, 2), (1, 1)):
            cc = {(i + a, k + b) for a in range(w) for b in range(d)}
            if cc <= cells:
                salon.place(TILE[(min(w, d), max(w, d))], color,
                            (S * i + 10 * w, RAFT - 8, S * k + 10 * d),
                            None if w >= d else rot(y=90))
                cells -= cc
                break
