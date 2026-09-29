"""shrink_pdf: Ghostscript passes at 200 then 150 dpi, keeping the smallest file."""
from __future__ import annotations

import subprocess

import pytest

from brickkit.booklet import booklet as B


def _fake_gs(monkeypatch, sizes: dict[int, int], calls: list[int]):
    """Pretend gs is installed; a pass at `dpi` writes a file of sizes[dpi] bytes."""
    monkeypatch.setattr(B.shutil, "which", lambda name: "/usr/bin/gs")

    def run(cmd, **kw):
        dpi = int(next(a for a in cmd if a.startswith("-dColorImageResolution=")).split("=")[1])
        out = next(a for a in cmd if a.startswith("-sOutputFile=")).split("=", 1)[1]
        assert cmd[-1].endswith("booklet.pdf")          # every pass starts from the original
        calls.append(dpi)
        with open(out, "wb") as f:
            f.write(b"x" * sizes[dpi])
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(B.subprocess, "run", run)


def _pdf(tmp_path, n):
    p = tmp_path / "booklet.pdf"
    p.write_bytes(b"o" * n)
    return p


def test_small_booklet_untouched(tmp_path, monkeypatch):
    calls = []
    _fake_gs(monkeypatch, {200: 10, 150: 5}, calls)
    p = _pdf(tmp_path, 100)
    B.shrink_pdf(p, over=1000)
    assert calls == [] and p.stat().st_size == 100


def test_first_pass_enough(tmp_path, monkeypatch):
    calls = []
    _fake_gs(monkeypatch, {200: 800, 150: 500}, calls)
    p = _pdf(tmp_path, 3000)
    B.shrink_pdf(p, over=1000)
    assert calls == [200] and p.stat().st_size == 800
    assert sorted(f.name for f in tmp_path.iterdir()) == ["booklet.pdf"]


def test_second_pass_at_150_dpi(tmp_path, monkeypatch):
    calls = []
    _fake_gs(monkeypatch, {200: 2000, 150: 900}, calls)
    p = _pdf(tmp_path, 3000)
    B.shrink_pdf(p, over=1000)
    assert calls == [200, 150] and p.stat().st_size == 900
    assert sorted(f.name for f in tmp_path.iterdir()) == ["booklet.pdf"]


@pytest.mark.parametrize("sizes, kept", [({200: 2000, 150: 2500}, 2000),     # smaller wins
                                         ({200: 4000, 150: 5000}, 3000)])    # original kept
def test_keeps_smallest(tmp_path, monkeypatch, sizes, kept):
    calls = []
    _fake_gs(monkeypatch, sizes, calls)
    p = _pdf(tmp_path, 3000)
    B.shrink_pdf(p, over=1000)
    assert calls == [200, 150] and p.stat().st_size == kept
    assert sorted(f.name for f in tmp_path.iterdir()) == ["booklet.pdf"]


def test_no_ghostscript(tmp_path, monkeypatch):
    monkeypatch.setattr(B.shutil, "which", lambda name: None)
    p = _pdf(tmp_path, 3000)
    B.shrink_pdf(p, over=1000)
    assert p.stat().st_size == 3000
