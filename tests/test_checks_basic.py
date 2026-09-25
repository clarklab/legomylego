from brickkit.checks import run_checks
from brickkit.checks.report import write_report
from brickkit.model.builder import Model
from tests.test_builder import make


def run(engine, model, names):
    return {r.name: r for r in run_checks(engine.context(model), names)}


def test_good_model_passes(engine):
    res = run(engine, make(engine), ["connections", "collisions", "real_elements"])
    assert all(r.status == "pass" for r in res.values()), res


def test_floating_part_fails_connections(engine):
    m = Model("F", "f", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.place("3001", "White", (0, -100, 0))
    assert run(engine, m, ["connections"])["connections"].status == "fail"


def test_overlap_fails_collisions(engine):
    m = Model("C", "c", {}, engine.catalog)
    m.main.place("3001", "White")
    m.main.place("3001", "White", (0, -16, 0))
    r = run(engine, m, ["collisions"])["collisions"]
    assert r.status == "fail" and len(r.items) == 1


def test_unreal_colour_fails_real_elements(engine):
    cat = engine.catalog
    col = next(c for c in cat.colors.by_code.values()
               if c.rb_id is not None and cat.element("3001.dat", c) is None)
    m = Model("R", "r", {}, cat)
    m.main.place("3001", col)
    r = run(engine, m, ["real_elements"])["real_elements"]
    assert r.status == "fail" and r.items[0]["substitutes"]


def test_report_files(engine, tmp_path):
    results = run_checks(engine.context(make(engine)), ["connections"])
    write_report(results, tmp_path, "T")
    assert (tmp_path / "report.json").exists() and "connections" in (tmp_path / "report.html").read_text()
