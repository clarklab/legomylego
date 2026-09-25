from brickkit.project import Project


def test_variants_change_colours_only(engine, tmp_path):
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "model.toml").write_text(
        '[model]\nname = "V"\n[palette]\nbody = "White"\n'
        '[variants.red]\ntitle = "Red one"\nbody = "Red"\n')
    (tmp_path / "v" / "design.py").write_text(
        'def build(model):\n    model.main.place("3001", "body")\n')
    p = Project("v", tmp_path)
    assert list(p.variants()) == ["red"]
    a, b = p.build(engine.catalog), p.build(engine.catalog, variant="red")
    assert a.flatten()[0].color.name == "White" and b.flatten()[0].color.name == "Red"
    assert b.variant == "red" and p.variant_title("red") == "Red one"
