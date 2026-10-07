"""Audit four standalone primary builds against LEGO PDF 6555451.

The source-step element IDs below were independently transcribed from the numbered
instruction diagrams and the element key on pp. 46–47. They deliberately do not
come from design.py or inventory.json: deleting the same piece from both must fail.
Run: .venv/bin/python tools/audit_lego_11039.py [slug ...] --exports --quick
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brickkit.bom.bom import build_bom
from brickkit.checks import run_checks
from brickkit.checks.base import ORDER
from brickkit.engine import Engine
from brickkit.io.mpd import read_mpd
from brickkit.ldraw.library import normalize
from brickkit.model.builder import Placement
from brickkit.project import Project
from brickkit.video import quick

SOURCE_URL = "https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555451.pdf"
# Each entry is (printed page, {LEGO element ID: quantity added at this step}).
SOURCE = {
    "birthday_cake": [
        (6, {"4211186": 1}), (7, {"4211210": 1}), (7, {"6425510": 2}),
        (8, {"301001": 1}), (8, {"6248827": 2}),
        (9, {"4558952": 2, "6522847": 1}), (9, {"6434345": 2}),
        (10, {"4504369": 2}), (10, {"300401": 1, "6346616": 2}),
        (11, {"6429055": 1}), (11, {"6234807": 1, "6514274": 1}),
    ],
    "watermelon_ice_lolly": [
        (14, {"4165967": 1, "302001": 1}), (14, {"6422918": 1}),
        (15, {"6523861": 2, "6284070": 2}), (15, {"6523861": 1, "6284070": 1}),
        (16, {"6258572": 3}), (16, {"6422918": 1, "6522845": 1}),
        (17, {"6261292": 2}), (17, {"6431716": 2}), (18, {"6422920": 1}),
        (18, {"6261293": 2}), (19, {"4125220": 2}),
    ],
    "avocado": [
        (22, {"4537936": 1}), (23, {"4220632": 1}), (23, {"6030276": 2}),
        (24, {"4537919": 1}), (24, {"6528558": 1}),
        (25, {"4164022": 1, "6030276": 1}), (26, {"4164022": 1, "6030276": 1}),
        (27, {"4220632": 1}), (27, {"4650630": 2}), (28, {"6440768": 1}),
        (29, {"4234716": 1}), (29, {"6073026": 2, "6432104": 1}),
        (30, {"6431715": 2}), (30, {"4650630": 2}), (31, {"6380676": 1}),
    ],
    "taco": [
        (34, {"6344217": 1}), (34, {"300824": 1}), (35, {"6344217": 1}),
        (35, {"4234716": 1, "6223427": 2}), (36, {"4558952": 2, "6258572": 1}),
        (37, {"6312452": 1, "6371437": 1}), (37, {"6252037": 1}),
        (38, {"6182261": 2}), (39, {"6168642": 2}), (39, {"6182261": 2}),
        (40, {"6344217": 2}), (40, {"6092583": 1, "6433502": 2}),
    ],
}


SOURCE_SHA256 = "3d72407e04a6e77ac486f71280385d2190e7f4ac690b843cf77f7802bdb77965"
# Independent transcription of the complete set's element key on printed pp. 46–47.
SET_SOURCE_COUNTS = {
    "6234807": 2, "6431716": 2, "6434345": 2, "6433502": 2, "6168642": 2,
    "6431715": 2, "6432105": 2, "6433501": 2, "6250591": 2, "4558952": 4,
    "4504369": 2, "6510068": 2, "6093053": 2, "6194851": 1, "6248827": 2,
    "6346616": 2, "6522847": 1, "300401": 2, "6058177": 2, "301001": 2,
    "302001": 4, "6284070": 4, "4125220": 2, "6223427": 2, "6324417": 1,
    "6516544": 2, "6429055": 1, "6252037": 2, "6284577": 2, "6092583": 2,
    "300124": 2, "6344217": 4, "300824": 1, "6182261": 6, "6380676": 2,
    "6525777": 2, "6514093": 2, "6312452": 2, "6073026": 2, "6429057": 1,
    "6528558": 2,
    "6030276": 4, "4164022": 4, "6432104": 1, "4220632": 2, "4650630": 4,
    "4234716": 2, "4165967": 2, "4537936": 2, "4537919": 1, "6514274": 2,
    "4529242": 2, "6371437": 2, "6035291": 4, "6425510": 2, "4211210": 2,
    "6440768": 1, "4211186": 2, "6284587": 2, "6322819": 2, "6261292": 4,
    "6523861": 4, "6258572": 4, "6422920": 2, "6422918": 2, "6522845": 1,
    "6261293": 2,
}


def audit_set_inventory(engine, inventory=None, *, source_pdf=None):
    directory = ROOT / "docs" / "references" / "lego_11039"
    if inventory is None:
        inventory = json.loads((directory / "set_inventory.json").read_text())
    pdf = Path(source_pdf) if source_pdf else directory / "6555451.pdf"
    assert sha256(pdf.read_bytes()).hexdigest() == SOURCE_SHA256, "source PDF SHA-256 differs"
    assert inventory["sha256"] == SOURCE_SHA256, "inventory records wrong source PDF hash"
    assert inventory["source_url"] == SOURCE_URL and str(inventory["set_number"]) == "11039"
    assert inventory["inventory_pages"] == [46, 47]
    rows = inventory["elements"]
    assert len(rows) == len({str(row["element_id"]) for row in rows}) == 67, "duplicate or missing set elements"
    available = Counter({str(row["element_id"]): row["quantity"] for row in rows})
    assert available == Counter(SET_SOURCE_COUNTS), "set inventory differs from source element key"
    used = Counter()
    for slug, source in SOURCE.items():
        manifest = json.loads((Project(slug).dir / "reference" / "inventory.json").read_text())
        assert manifest["source_url"] == SOURCE_URL
        assert manifest.get("source_sha256", SOURCE_SHA256) == SOURCE_SHA256
        recorded = Counter()
        for step in manifest["steps"]:
            for part in step["parts"]:
                recorded[str(part["element_id"])] += part["quantity"]
        expected = sum((Counter(elements) for _, elements in source), Counter())
        assert recorded == expected, f"{slug}: allocation differs from independent source steps"
        used.update(recorded)
    assert not (used - available), "primary builds exceed the official set inventory"
    remaining = available - used
    for row in rows:
        eid = str(row["element_id"])
        quantity = row["quantity"]
        assert isinstance(quantity, int) and quantity > 0, f"{eid}: invalid set quantity"
        assert row["used_in_primary_models"] == used[eid], f"{eid}: wrong primary allocation"
        assert row["remaining_for_rebuilds"] == remaining[eid], f"{eid}: wrong rebuild remainder"
        color = engine.catalog.color(row["color"])
        element = engine.catalog.element(row["rebrickable"], color)
        assert element and eid in element.element_ids, f"{eid}: wrong set part/color identity"
    assert sum(available.values()) == inventory["total_pieces"] == 150
    assert sum(used.values()) == inventory["primary_build_pieces"] == 89
    assert sum(remaining.values()) == inventory["remaining_for_rebuilds"] == 61
    assert available == used + remaining, "set inventory is not fully accounted for"
    return {"set_number": "11039", "source_sha256": SOURCE_SHA256,
            "element_entries": len(rows), "total_pieces": 150,
            "primary_build_pieces": 89, "remaining_for_rebuilds": 61}


def main_step_parts(model, step):
    """Expand every occurrence of a subassembly at its parent instruction step."""
    result = Counter()
    for item in model.main.items:
        if item.step != step:
            continue
        parts = [(item.part, item.color, item.M)] if isinstance(item, Placement) else item.sub.flatten_local()
        result.update((part, color.ldraw) for part, color, _ in parts)
    return result


def audit_source(slug, model, catalog, inventory):
    assert inventory["source_url"] == SOURCE_URL, "wrong instruction PDF"
    assert str(inventory["set_number"]) == "11039", "wrong LEGO set"
    source = SOURCE[slug]
    steps = inventory["steps"]
    assert len(steps) == len(source) == model.main.n_steps, "missing numbered instruction step"
    assert [s["number"] for s in steps] == list(range(1, len(source) + 1)), "nonconsecutive steps"
    total = Counter()
    for i, (step, (page, elements)) in enumerate(zip(steps, source)):
        assert step["page"] == page, f"step {i + 1}: wrong source page"
        recorded = Counter()
        expected = Counter()
        for item in step["parts"]:
            qty = item["quantity"]
            assert isinstance(qty, int) and qty > 0, f"step {i + 1}: invalid quantity"
            eid = str(item["element_id"])
            recorded[eid] += qty
            part = catalog.canonical(str(item["ldraw"]))
            color = catalog.color(item["color"])
            element = catalog.element(part, color)
            assert element and eid in element.element_ids, f"step {i + 1}: {eid} is not {part}/{color.name}"
            expected[part, color.ldraw] += qty
        assert recorded == Counter(elements), f"step {i + 1}: ledger differs from source: {recorded} != {elements}"
        actual = main_step_parts(model, i)
        assert actual == expected, f"step {i + 1}: model differs from ledger: {actual} != {expected}"
        total.update(expected)
    assert not model.extras and not model.hardware_items, "unplaced or non-LEGO pieces"
    assert Counter((p.part, p.color.ldraw) for p in model.flatten()) == total, "flattened inventory differs"
    if "physical_piece_count" in inventory:
        assert inventory["physical_piece_count"] == sum(total.values()), "incorrect declared piece count"
    if "official_numbered_step_count" in inventory:
        assert inventory["official_numbered_step_count"] == len(source), "incorrect declared step count"
    order = model.instruction_order()
    assert len(order) == len(set(order)), "duplicate expanded instruction steps"
    for sub in model.submodels.values():
        for step in range(sub.n_steps):
            assert any(item.step == step for item in sub.items), f"empty step: {sub.name}/{step + 1}"
            assert (sub.name, step) in order, f"unused subassembly: {sub.name}/{step + 1}"
    return total


def audit_geometry(engine, model):
    """Traverse actual files as well as meshes; cached meshes can conceal missing children."""
    visited = set()
    def visit(part):
        part = normalize(part)
        if part in visited:
            return
        visited.add(part)
        path = engine.lib.resolve(part)
        assert path is not None, f"missing LDraw dependency: {part}"
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = line.split()
            if len(fields) >= 15 and fields[0] == "1":
                visit(" ".join(fields[14:]))
    for part in {p.part for p in model.flatten()}:
        visit(part)
        mesh = engine.geom.mesh(part)
        assert len(mesh.tris) > 0 and np.isfinite(mesh.tris).all(), f"empty/invalid mesh: {part}"
    return len(visited)


def audit_exports(model, catalog, directory):
    """Check saved CSV, BrickLink XML, and PaB CSV by full identities, not just totals."""
    directory = Path(directory)
    bom = build_bom(model.flatten(), catalog, model.extras)
    expected = Counter({(line.ldraw_part, line.color.ldraw): line.qty for line in bom})
    actual = Counter()
    with (directory / "parts.csv").open() as fh:
        for row in csv.DictReader(fh):
            actual[row["part"], int(row["ldraw_colour"])] += int(row["qty"])
    assert actual == expected, "parts.csv drops or changes pieces"
    assert sum(actual.values()) == len(model.flatten()), "BOM physical count differs"
    expected_xml = Counter()
    expected_pab = Counter()
    for line in bom:
        assert line.bl_part and line.color.bl_id is not None and line.element_id, f"unexportable part: {line}"
        expected_xml[line.bl_type, line.bl_part, str(line.color.bl_id)] += line.qty
        expected_pab[line.element_id] += line.qty
    actual_xml = Counter()
    for item in ET.parse(directory / "bricklink_wanted.xml").getroot().findall("ITEM"):
        actual_xml[item.findtext("ITEMTYPE"), item.findtext("ITEMID"), item.findtext("COLOR")] += int(item.findtext("MINQTY"))
    assert actual_xml == expected_xml, "BrickLink XML drops or changes pieces"
    actual_pab = Counter()
    with (directory / "pick_a_brick.csv").open() as fh:
        for row in csv.DictReader(fh):
            actual_pab[row["elementId"]] += int(row["quantity"])
    assert actual_pab == expected_pab, "Pick a Brick CSV drops or changes pieces"
    mpd = directory / f"{model.slug}.mpd"
    saved = read_mpd(mpd)
    placed = model.flatten()
    assert len(saved) == len(placed), "MPD drops/duplicates physical pieces"
    for (part, color, matrix), original in zip(saved, placed):
        assert part == original.part and color == original.color.ldraw, "MPD changes part identities"
        assert np.allclose(matrix, original.M, atol=1e-5), "MPD changes part placement"
    blocks = {}
    for block in mpd.read_text().split("0 FILE ")[1:]:
        name, body = block.split("\n", 1)
        blocks[name] = body.split("0 NOFILE", 1)[0].splitlines()
    for sub in model.submodels.values():
        assert blocks[f"{sub.name}.ldr"].count("0 STEP") == sub.n_steps, "MPD loses instruction steps"


def audit_quick(engine, model, config):
    placed = model.flatten()
    result = quick.plan(engine, model, quick.quick_config(config, slug=model.slug))
    assert sorted(result["order"]) == list(range(len(placed))), "Quick drops/duplicates parts"
    assert len(result["parts"]) == len(placed), "Quick has missing flight records"
    assert [placed[i].build_order for i in result["order"]] == sorted(p.build_order for p in placed), "Quick reorders source steps"
    for index, flight in enumerate(result["parts"]):
        frames = np.asarray(flight["frames"]).reshape(-1, 4, 4)
        last = quick.pose_at(result, index, result["cut"] - 1)     # (built on the table, then set on its stick)
        assert np.isfinite(frames).all() and np.allclose(last, placed[index].M, atol=1e-3), f"Quick part {index} never reaches its final position"
    assert quick.clashes(engine, placed, result) == [] and result["notes"] == [], "Quick parts pass through each other"
    return len(result["order"])



def audit_viewer(engine, project, model, directory=None):
    """Check saved viewer data and every glTF instance, including printed color channels."""
    import trimesh
    from brickkit.viewer_export import C
    directory = Path(directory) if directory else project.out / "viewer" / "models" / project.slug
    data = json.loads((directory / "model.json").read_text())
    placed = model.flatten()
    order = model.instruction_order()
    assert data["slug"] == project.slug
    assert data["parts"] == data["pieces"] == len(data["nodes"]) == len(placed), "viewer drops pieces"
    assert [(step["index"], step["submodel"], step["local_step"]) for step in data["steps"]] == [
        (index, sub, local) for index, (sub, local) in enumerate(order)], "viewer drops or changes instruction steps"
    for node, part in zip(data["nodes"], placed):
        assert node["part"] + ".dat" == part.part, "viewer changes piece identity"
        assert (node["join"], node["sub"], node["local_step"]) == (
            part.build_order, part.owner, part.local_step), "viewer changes piece build step"
    default = data["variants"][0]
    assert default["colors"] == [part.color.ldraw for part in placed], "viewer changes part colors"
    expected_bom = Counter({(line.ldraw_part, line.color.name): line.qty
                            for line in build_bom(placed, engine.catalog)})
    assert Counter({(row["part"], row["colour"]): row["qty"] for row in default["bom"]}) == expected_bom
    scene = trimesh.load(directory / data["files"]["glb"], force="scene")
    expected_nodes = set()
    for part in placed:
        for code in np.unique(engine.geom.mesh(part.part).colors):
            name = f"p{part.index}" if code == 16 else f"p{part.index}c{code}"
            expected_nodes.add(name)
            matrix, geometry = scene.graph.get(name)
            assert np.allclose(matrix, C @ part.M, atol=1e-6), f"viewer changes transform: {name}"
            mesh = scene.geometry[geometry]
            assert len(mesh.faces) and len(mesh.vertices) and np.isfinite(mesh.vertices).all(), f"viewer lacks geometry: {name}"
    assert set(scene.graph.nodes_geometry) == expected_nodes, "viewer drops/duplicates GLB part/color nodes"
    for references in data["files"].values():
        for filename in references if isinstance(references, list) else [references]:
            assert (directory / filename).is_file(), f"viewer references missing file: {filename}"
    assert {check["name"] for check in data["checks"]} == set(ORDER), "viewer omits check results"
    assert all(check["status"] != "fail" for check in data["checks"]), "viewer contains failed checks"
    return {"viewer_directory": str(directory), "pieces": len(placed), "steps": len(order),
            "glb_part_color_nodes": len(expected_nodes), "glb_meshes": len(scene.geometry)}


def audit_model(slug, engine, *, exports=False, quick_plan=False, viewer=False):
    project = Project(slug)
    model = project.build(engine.catalog)
    inventory = json.loads((project.dir / "reference" / "inventory.json").read_text())
    totals = audit_source(slug, model, engine.catalog, inventory)
    dependencies = audit_geometry(engine, model)
    assert set(project.checks_config.get("enabled", ORDER)) == set(ORDER), "not all checks enabled"
    results = run_checks(engine.context(model, project.checks_config), ORDER)
    failures = {r.name: r.items for r in results if r.status == "fail"}
    assert not failures, f"physical checks fail: {failures}"
    if exports:
        audit_exports(model, engine.catalog, project.out)
    if quick_plan:
        audit_quick(engine, model, project.config)
    if viewer:
        audit_viewer(engine, project, model)
    return {"model": slug, "pieces": sum(totals.values()), "source_steps": len(SOURCE[slug]),
            "expanded_steps": len(model.instruction_order()), "geometry_files": dependencies,
            "checks": {r.name: r.status for r in results}, "exports_verified": exports,
            "quick_verified": quick_plan, "viewer_verified": viewer}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", help="defaults to all four primary builds")
    parser.add_argument("--exports", action="store_true", help="also verify saved parts exports")
    parser.add_argument("--quick", action="store_true", help="also generate and verify every Quick flight")
    parser.add_argument("--viewer", action="store_true", help="also verify saved standalone viewer staging")
    args = parser.parse_args()
    engine = Engine()
    print(json.dumps(audit_set_inventory(engine)), flush=True)
    for slug in args.models or SOURCE:
        print(json.dumps(audit_model(slug, engine, exports=args.exports, quick_plan=args.quick, viewer=args.viewer)), flush=True)


if __name__ == "__main__":
    main()
