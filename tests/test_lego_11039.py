"""Independent source-ledger audits for the four primary LEGO 11039 models."""
from copy import deepcopy
import json

import pytest

from brickkit.bom.bom import build_bom, write_bricklink_xml, write_parts_csv, write_pick_a_brick_csv
from brickkit.io.mpd import write_mpd
from brickkit.project import Project
from tools.audit_lego_11039 import SOURCE, audit_exports, audit_geometry, audit_model, audit_source


@pytest.mark.parametrize("slug", SOURCE)
def test_primary_food_models_preserve_source_steps_and_elements(engine, slug, tmp_path):
    project = Project(slug)
    model = project.build(engine.catalog)
    inventory = json.loads((project.dir / "reference" / "inventory.json").read_text())
    counts = audit_source(slug, model, engine.catalog, inventory)
    assert sum(counts.values()) == (20 if slug == "birthday_cake" else 23)
    audit_geometry(engine, model)
    bom = build_bom(model.flatten(), engine.catalog)
    write_parts_csv(bom, tmp_path / "parts.csv")
    assert not write_bricklink_xml(bom, tmp_path / "bricklink_wanted.xml")
    write_pick_a_brick_csv(bom, tmp_path / "pick_a_brick.csv")
    write_mpd(model, tmp_path / f"{model.slug}.mpd", engine.lib)
    audit_exports(model, engine.catalog, tmp_path)


@pytest.mark.parametrize("slug", SOURCE)
def test_primary_food_models_pass_checks_and_quick_contains_every_piece(engine, slug):
    audit_model(slug, engine, quick_plan=True)


@pytest.mark.parametrize("slug", SOURCE)
def test_source_audit_rejects_missing_part_or_step(engine, slug):
    project = Project(slug)
    model = project.build(engine.catalog)
    inventory = json.loads((project.dir / "reference" / "inventory.json").read_text())
    broken = deepcopy(inventory)
    broken["steps"].pop()
    with pytest.raises(AssertionError, match="missing numbered instruction step"):
        audit_source(slug, model, engine.catalog, broken)
    model.main.items.pop()
    with pytest.raises(AssertionError, match="model differs from ledger"):
        audit_source(slug, model, engine.catalog, inventory)


@pytest.mark.parametrize("slug", SOURCE)
def test_source_audit_rejects_same_omission_from_model_and_manifest(engine, slug):
    project = Project(slug)
    model = project.build(engine.catalog)
    inventory = json.loads((project.dir / "reference" / "inventory.json").read_text())
    model.main.items.pop(0)
    inventory["steps"][0]["parts"].pop(0)
    with pytest.raises(AssertionError, match="ledger differs from source"):
        audit_source(slug, model, engine.catalog, inventory)



def test_full_set_inventory_reconciles_all_primary_models(engine):
    from tools.audit_lego_11039 import audit_set_inventory
    result = audit_set_inventory(engine)
    assert result["total_pieces"] == result["primary_build_pieces"] + result["remaining_for_rebuilds"] == 150
    assert result["element_entries"] == 67


@pytest.mark.parametrize("field", ["used_in_primary_models", "remaining_for_rebuilds", "quantity"])
def test_full_set_inventory_rejects_incorrect_allocation(engine, field):
    from tools.audit_lego_11039 import ROOT, audit_set_inventory
    inventory = json.loads((ROOT / "docs/references/lego_11039/set_inventory.json").read_text())
    inventory["elements"][0][field] += 1
    with pytest.raises(AssertionError):
        audit_set_inventory(engine, inventory)


def test_full_set_inventory_rejects_altered_source_pdf(engine, tmp_path):
    from tools.audit_lego_11039 import ROOT, audit_set_inventory
    altered = tmp_path / "altered.pdf"
    altered.write_bytes((ROOT / "docs/references/lego_11039/6555451.pdf").read_bytes() + b"\n")
    with pytest.raises(AssertionError, match="source PDF SHA-256 differs"):
        audit_set_inventory(engine, source_pdf=altered)



@pytest.mark.parametrize("slug", SOURCE)
def test_standalone_viewer_preserves_every_piece_and_step(engine, slug, tmp_path):
    from brickkit.viewer_export import export_model
    from tools.audit_lego_11039 import audit_viewer
    project = Project(slug)
    model = project.build(engine.catalog)
    directory = export_model(engine, project, model, tmp_path)
    audit_viewer(engine, project, model, directory)
