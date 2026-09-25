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
