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
    assert "# Tiny Owl: posts" in (d / "SOCIAL.md").read_text()    # its Instagram and TikTok posts
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
    assert row["posts"] == "draft"                                 # (till no TODO is left in it)
    (d / "SOCIAL.md").write_text("# Tiny Owl: posts\n\nWho? Me.\n")
    assert status.model_status("tiny_owl", tmp_path, tmp_path / "site")["posts"] == "yes"
    assert cli.main(["status", "tiny_owl"]) == 0
    out = capsys.readouterr().out
    head = next(ln for ln in out.splitlines() if ln.startswith("model"))
    assert "scene" in head and head.rstrip().endswith("next")
    assert "tiny_owl" in out and "blue_mat/workbench/morning" in out


def test_cli_claims(tmp_path, monkeypatch, capsys):
    """A model is claimed before it is worked on: one holder at a time (the claim file is made
    with an exclusive create); the same name renews it; someone else is refused until it is
    released or has gone stale; `new --as` claims what it makes; `status` shows who has it."""
    from datetime import datetime, timedelta, timezone

    from brickkit import claims, cli, status
    monkeypatch.setattr(paths, "MODELS_DIR", tmp_path)
    monkeypatch.delenv("BRICKKIT_AGENT", raising=False)
    assert cli.main(["new", "tiny_owl", "--quick", "--as", "codex-1"]) == 0
    c = claims.read("tiny_owl")
    assert c["who"] == "codex-1" and c["stage"] == "1" and not c["stale"] and c["hours"] < 0.1
    assert cli.main(["claim", "tiny_owl"]) == 2                          # (who are you?)
    assert cli.main(["claim", "tiny_owl", "--as", "claude-2"]) == 1      # taken
    assert "claimed by codex-1" in capsys.readouterr().out
    assert cli.main(["claim", "tiny_owl", "--as", "codex-1", "--stage", "2-3"]) == 0     # renewed
    assert claims.read("tiny_owl")["stage"] == "2-3"
    assert status.model_status("tiny_owl", tmp_path, tmp_path / "site")["claim"].startswith("codex-1 ")
    assert cli.main(["release", "tiny_owl", "--as", "claude-2"]) == 1    # not theirs to release
    assert cli.main(["claim", "tiny_owl", "--as", "claude-2", "--take"]) == 1            # not stale
    old = (datetime.now(timezone.utc) - timedelta(hours=claims.STALE_HOURS + 2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    f = tmp_path / "tiny_owl" / claims.NAME
    f.write_text(f.read_text().replace(claims.read("tiny_owl")["when"], old))
    assert claims.read("tiny_owl")["stale"] and "STALE" in claims.label(claims.read("tiny_owl"))
    assert cli.main(["claim", "tiny_owl", "--as", "claude-2"]) == 1      # stale: only with --take
    assert cli.main(["claim", "tiny_owl", "--as", "claude-2", "--take"]) == 0
    assert claims.read("tiny_owl")["who"] == "claude-2"
    monkeypatch.setenv("BRICKKIT_AGENT", "claude-2")
    assert cli.main(["release", "tiny_owl"]) == 0 and claims.read("tiny_owl") is None
    assert cli.main(["release", "tiny_owl"]) == 0                        # nothing to release
    assert status.model_status("tiny_owl", tmp_path, tmp_path / "site")["claim"] == "-"
    assert cli.main(["claim", "no_such_model", "--as", "x"]) == 1
    assert cli.main(["new", "tiny_owl", "--quick", "--as", "x"]) == 1    # it exists: not theirs


def test_status_lists_the_inbox(tmp_path):
    """What is dropped in inbox/ waits there until its model folder exists: a folder per
    model (any files), or a lone file that still needs a folder; the README is not a model."""
    from brickkit import status
    inbox, models = tmp_path / "inbox", tmp_path / "models"
    (inbox / "Tiny Owl").mkdir(parents=True)
    (inbox / "Tiny Owl" / "plans.pdf").write_bytes(b"pdf")
    (inbox / "Tiny Owl" / "front.PNG").write_bytes(b"png")
    (inbox / "frog").mkdir()
    (inbox / "frog" / "frog.io").write_bytes(b"io")
    (inbox / "robot.jpg").write_bytes(b"jpg")
    (inbox / "README.md").write_text("how to use the inbox")
    (models / "frog").mkdir(parents=True)                               # the frog is taken in
    w = status.waiting(inbox, models)
    assert [(t["name"], t["slug"], t["files"], t["kinds"]) for t in w] == [
        ("Tiny Owl", "tiny_owl", 2, ["pdf", "png"]), ("robot.jpg", "robot", 1, ["jpg"])]
    assert w[0]["next"] == "brickkit new tiny_owl --quick --as NAME" and "folder" in w[1]["next"]
    assert status.waiting(tmp_path / "nowhere", models) == []
