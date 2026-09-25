import numpy as np

from brickkit.ldraw.matrix import apply, format_type1, is_mirror, parse_type1, rot, transform


def test_rot_y_90_maps_x_to_minus_z():
    assert np.allclose(rot(y=90) @ [1, 0, 0], [0, 0, -1])


def test_parse_format_roundtrip():
    color, M, name = parse_type1("1 4 10 -24 0 0 0 1 0 1 0 -1 0 0 3001.dat".split())
    assert color == 4 and name == "3001.dat"
    assert np.allclose(M[:3, 3], [10, -24, 0])
    assert np.allclose(parse_type1(format_type1(color, M, name).split())[1], M)


def test_apply_and_mirror():
    M = transform((1, 2, 3), rot(z=90))
    assert np.allclose(apply(M, [[1, 0, 0]]), [[1, 3, 3]])
    assert not is_mirror(M)
    assert is_mirror(np.diag([-1.0, 1, 1, 1]))
