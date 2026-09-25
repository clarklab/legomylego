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
