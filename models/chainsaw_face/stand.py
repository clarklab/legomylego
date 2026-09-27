"""The display stand: a black base 16 x 14 studs with dark wooden floorboards, a raised black
nameplate at the front (left blank for a sticker), exposed studs where the shoes go and a
support post behind the figure that pins into the back of the hips.

World frame: the base's underside at y = 0, its plate deck's studs at y = -48, the
floorboards' top at y = -56. Cell (i, k) = x in [20 i, 20 i + 20], z in [20 k, 20 k + 20]."""
from __future__ import annotations

from kit import BR, PL, S, Seg, box_cells, rot

I0, I1, K0, K1 = -8, 7, -7, 6          # base cells
DECK = -48                             # top of the plate deck (studs)
FLOOR = -56                            # top of the floorboards
PLAQUE = (-4, 3, -7, -6)               # nameplate cells (i0, i1, k0, k1)
POST = (-1, 0, 3, 4)                   # support post cells


def foot_cells(xf: float, zf: float) -> set:
    """Cells under a shoe (4 x 7 studs, ankle at (xf, zf), heel 2 studs behind it)."""
    i0, k0 = round((xf - 40) / S), round((zf - 100) / S)
    return {(i, k) for i in range(i0, i0 + 4) for k in range(k0, k0 + 7)}


def plank_rows(cells: set, phase: int = 0):
    """Floorboards: 1 x N tiles along x, rows alternating two browns, joints staggered."""
    out = []
    lengths = (8, 6, 4, 3, 2, 1)
    for n, k in enumerate(sorted({c[1] for c in cells})):
        xs = sorted(i for i, kk in cells if kk == k)
        segs, cur = [], [xs[0]]
        for x in xs[1:]:
            if x == cur[-1] + 1:
                cur.append(x)
            else:
                segs.append(cur)
                cur = [x]
        segs.append(cur)
        role = "floor" if (k + phase) % 2 == 0 else "floor2"
        first = (3, 6, 4, 2)[(k + phase) % 4]
        for seg in segs:
            pos, left = seg[0], len(seg)
            run = []
            if left > first + 1:
                run.append(first)
                left -= first
            while left:
                L = next(L for L in lengths if L <= left and (left - L != 1 or L == 1))
                run.append(L)
                left -= L
            for L in run:
                out.append((role, (pos, pos + L - 1, k, k)))
                pos += L
    return out


def build_stand(model, feet: list[tuple[float, float]], post_top: float):
    """`feet`: ankle (x, z) of each shoe. `post_top`: y of the top of the post's last brick
    (its Technic brick's top, which carries the pins into the hips)."""
    sub = model.submodel("stand", "Display stand")
    st = Seg(sub)
    all_cells = box_cells(I0, I1, K0, K1, "base")

    st.step("The base: two layers of black plates, crosswise", view="above")
    st.course("plate", all_cells, -PL, prefer="x", max_len=16, bond=False)
    st.step()
    st.course("plate", all_cells, -2 * PL, prefer="z", max_len=16)

    st.step("A frame of bricks with ribs under the shoes and the post")
    frame = {c: "base" for c in all_cells
             if c[0] in (I0, I1) or c[1] in (K0, K1) or c[1] in (-3, 0, 3)
             or c[0] in (-5, -1, 0, 4)}
    st.course("brick", frame, -2 * PL - BR, prefer="x")

    st.step("The deck: plates over the frame")
    st.course("plate", all_cells, DECK, prefer="z", max_len=16)

    shoe = set()
    for xf, zf in feet:
        shoe |= foot_cells(xf, zf)
    post = {(i, k) for i in range(POST[0], POST[1] + 1) for k in range(POST[2], POST[3] + 1)}
    plaque = {(i, k) for i in range(PLAQUE[0], PLAQUE[1] + 1)
              for k in range(PLAQUE[2], PLAQUE[3] + 1)}
    border = {c for c in all_cells if c[0] in (I0, I1) or c[1] == K1 or c[1] <= K0 + 1}
    floor = set(all_cells) - border - shoe - post

    st.step("The support post: black bricks behind where the figure stands")
    # two Technic levels at the top (holes 24 apart) take the pins into the hips
    tech_low = post_top + BR
    y = DECK
    n = 0
    while y - BR >= tech_low + BR:
        if n % 2 == 0:
            st.put("3003", "base", (0, y - BR, 80))
        else:
            st.put("3004", "base", (-10, y - BR, 80), rot(y=90))
            st.put("3004", "base", (10, y - BR, 80), rot(y=90))
        y -= BR
        n += 1
        if n % 5 == 0:
            st.step()
    while y - (tech_low + BR) >= PL - 1e-6:
        st.put("3022", "base", (0, y - PL, 80))
        y -= PL
    assert abs(y - (tech_low + BR)) < 1e-6, (y, post_top)
    st.step("Technic bricks at the top: the pins into the hips go through their holes")
    for yt in (tech_low, post_top):
        st.put("3700", "base", (0, yt, 70))
        st.put("3700", "base", (0, yt, 90))
    st.step("Floorboards")
    for role, r in plank_rows(floor):
        st.rect("tile", role, r, FLOOR)
    st.step("A black border, and the nameplate raised on a plate: leave it blank for a "
            "sticker")
    for role, r in plank_rows(border - plaque, phase=0):
        st.rect("tile", "base", r, FLOOR)
    st.rect("plate", "plaque", PLAQUE, FLOOR)                 # 2 x 8 plate
    st.rect("tile", "plaque", (PLAQUE[0], PLAQUE[0] + 3, PLAQUE[2], PLAQUE[3]), FLOOR - PL)
    st.rect("tile", "plaque", (PLAQUE[0] + 4, PLAQUE[1], PLAQUE[2], PLAQUE[3]), FLOOR - PL)
    return sub
