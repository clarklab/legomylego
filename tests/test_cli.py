import subprocess
import sys

from brickkit import paths


def test_cli_all_sample(engine):
    r = subprocess.run([sys.executable, "-m", "brickkit", "all", "_sample"],
                       capture_output=True, text=True, cwd=paths.ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    out = paths.MODELS_DIR / "_sample" / "out"
    for f in ["_sample.mpd", "report.json", "report.html", "parts.csv", "bricklink_wanted.xml",
              "pick_a_brick.csv"]:
        assert (out / f).exists(), f
    assert "[PASS] buildability" in r.stdout


def test_cli_new_scaffolds_model(tmp_path, monkeypatch):
    from brickkit import cli
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path)
    assert cli.main(["new", "robot_dog", "--name", "Robot Dog"]) == 0
    toml = (tmp_path / "robot_dog" / "model.toml").read_text()
    assert 'name = "Robot Dog"' in toml and (tmp_path / "robot_dog" / "design.py").exists()


def test_cli_new_quick_and_status(tmp_path, monkeypatch, capsys):
    """`new --quick` scaffolds a Quick Bricks model to take in (docs/new-model.md): NOTES.md
    to fill in, reference/ for what was pasted, a [quick] block, not yet tagged for the site;
    `status` says where it is and what to do next."""
    from brickkit import cli, status
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path)
    assert cli.main(["new", "tiny_owl", "--quick", "--name", "Tiny Owl"]) == 0
    d = tmp_path / "tiny_owl"
    toml = (d / "model.toml").read_text()
    assert 'name = "Tiny Owl"' in toml and "[quick]" in toml and "brickkit quick tiny_owl" in toml
    assert '# collection = "quick_bricks"' in toml                 # not on the site yet
    assert (d / "reference").is_dir() and "# Tiny Owl" in (d / "NOTES.md").read_text()
    assert "def build(model)" in (d / "design.py").read_text()
    row = status.model_status("tiny_owl", tmp_path, tmp_path / "site")
    assert (row["source"], row["notes"], row["checks"], row["site"]) == ("-", "draft", "-", "off")
    assert row["next"] == "save what was pasted in reference/" and row["quick"]
    (d / "reference" / "page_01.png").write_bytes(b"png")
    row = status.model_status("tiny_owl", tmp_path, tmp_path / "site")
    assert row["source"] == "1 files" and row["next"].startswith("finish NOTES.md")
    (d / "NOTES.md").write_text("# Tiny Owl\n\nAll written up.\n")
    row = status.model_status("tiny_owl", tmp_path, tmp_path / "site")
    assert row["notes"] == "yes" and row["next"] == "write design.py, then: brickkit all tiny_owl"
    assert cli.main(["status", "tiny_owl"]) == 0
    out = capsys.readouterr().out
    head = next(ln for ln in out.splitlines() if ln.startswith("model"))
    assert "scene" in head and head.rstrip().endswith("next")
    assert "tiny_owl" in out and "blue_mat/workbench/morning" in out
