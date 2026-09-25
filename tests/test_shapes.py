from brickkit.shapes.rings import exposed, pack_cells, ring_cells, shell_layers


def test_ring_is_symmetric_and_thin():
    cells = ring_cells(6, 5)
    assert cells and all((-i - 1, k) in cells and (i, -k - 1) in cells for i, k in cells)
    assert all(5 <= ((i + .5) ** 2 + (k + .5) ** 2) ** .5 < 6 for i, k in cells)


def test_pack_covers_every_cell_once():
    cells = ring_cells(8, 6)
    runs = pack_cells(cells, lengths=(2, 1), offset=0)
    covered = []
    for i, k, n, axis in runs:
        covered += [(i + d, k) if axis == "x" else (i, k + d) for d in range(n)]
    assert sorted(covered) == sorted(cells)


def test_exposed_cells_face_outward():
    lower, upper = ring_cells(8, 6), ring_cells(7, 5)
    ex = exposed(lower, upper)
    assert ex and all(c in lower and c not in upper for c, _ in ex)


def test_shell_layers_overlap():
    layers = shell_layers(lambda h: 8 - h / 3, [0, 1, 2, 3, 4, 5, 6])
    for (y0, ro0, ri0), (y1, ro1, ri1) in zip(layers, layers[1:]):
        assert ri0 <= ro1 - 1
