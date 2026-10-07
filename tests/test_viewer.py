import json

import trimesh

from brickkit import paths
from brickkit.project import Project
from brickkit.viewer_export import export_model


def test_viewer_export(engine, tmp_path):
    proj = Project("_sample", paths.MODELS_DIR)
    model = proj.build(engine.catalog)
    dst = export_model(engine, proj, model, site_dir=tmp_path)
    d = json.loads((dst / "model.json").read_text())
    assert d["slug"] == "_sample" and d["parts"] == len(model.flatten())
    assert d["pieces"] >= 1 and 0 < d["price"]["low"] < d["price"]["high"]
    assert {"mechanism", "lights"} <= set(d["features"])
    assert all("details" in c for c in d["checks"])
    glb = trimesh.load(dst / "model.glb", force="scene")
    nodes = set(glb.graph.nodes_geometry)
    assert nodes == {f"p{p.index}" for p in model.flatten()} | {
        n for n in nodes if "c" in n[1:]}                 # no template nodes at the origin
    index = json.loads((tmp_path / "models.json").read_text())
    assert index["models"] == []                          # "_" models stay off the index


def test_viewer_export_companions(engine, tmp_path):
    """A model's [[companions]] (smaller builds shown on its page) are summarised in its
    model.json, with their files copied under companions/<slug>/."""
    import shutil
    models = tmp_path / "models"
    for name in ("_host", "_mini"):
        shutil.copytree(paths.MODELS_DIR / "_sample", models / name,
                        ignore=shutil.ignore_patterns("out", "__pycache__"))
    (models / "_mini" / "out").mkdir()
    (models / "_mini" / "out" / "pick_a_brick.csv").write_text("elementId,quantity\n300101,1\n")
    toml = models / "_host" / "model.toml"
    toml.write_text(toml.read_text() + '\n[[companions]]\nslug = "_mini"\nanchor = "mini"\n'
                    'heading = "The mini"\nprice = { pick_a_brick = 1.5, checked = "2026-10-03" }\n')
    proj = Project("_host", models)
    dst = export_model(engine, proj, proj.build(engine.catalog), site_dir=tmp_path / "site")
    c = json.loads((dst / "model.json").read_text())["companions"][0]
    assert c["slug"] == "_mini" and c["anchor"] == "mini" and c["heading"] == "The mini"
    assert c["pieces"] >= 1 and c["steps"] >= 1 and len(c["dims_mm"]) == 3
    assert c["price"]["pick_a_brick"] == 1.5
    assert c["files"] == {"pick_a_brick_csv": "companions/_mini/pick_a_brick.csv"}
    assert (dst / c["files"]["pick_a_brick_csv"]).exists()
