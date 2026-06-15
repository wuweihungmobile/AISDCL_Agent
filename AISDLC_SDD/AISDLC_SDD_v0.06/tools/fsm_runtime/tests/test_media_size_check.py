"""Tests for media_size_check (QA Round-2 P1 #2 — Rule 9.13.5 enforcement)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.fsm_runtime import media_size_check as msc


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    root = tmp_path / "docs" / "99_media"
    (root / "ui").mkdir(parents=True)
    (root / "erd").mkdir(parents=True)
    (root / "arch").mkdir(parents=True)
    (root / "flow").mkdir(parents=True)
    return root


def _write_blob(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


class TestScanMedia:
    def test_empty_root_clean(self, media_root):
        report = msc.scan_media(media_root)
        assert report.scanned_files == 0
        assert report.warnings == []
        assert report.failures == []

    def test_skips_gitkeep_and_readme(self, media_root):
        (media_root / "ui" / ".gitkeep").write_text("", encoding="utf-8")
        (media_root / "README.md").write_text("# media", encoding="utf-8")
        report = msc.scan_media(media_root)
        assert report.scanned_files == 0

    def test_under_warn_threshold_clean(self, media_root):
        _write_blob(media_root / "ui" / "small.png", msc.WARN_BYTES - 1)
        report = msc.scan_media(media_root)
        assert report.scanned_files == 1
        assert report.warnings == []
        assert report.failures == []

    def test_warn_at_300kb(self, media_root):
        _write_blob(media_root / "ui" / "medium.png", msc.WARN_BYTES + 10)
        report = msc.scan_media(media_root)
        assert len(report.warnings) == 1
        assert report.warnings[0].severity == "warn"
        assert report.failures == []

    def test_fail_at_500kb(self, media_root):
        _write_blob(media_root / "arch" / "huge.png", msc.HARD_BYTES + 10)
        report = msc.scan_media(media_root)
        assert report.failures
        assert report.failures[0].severity == "fail"
        assert report.has_failures is True

    def test_warn_and_fail_classified_separately(self, media_root):
        _write_blob(media_root / "ui" / "warn.png", msc.WARN_BYTES + 1)
        _write_blob(media_root / "arch" / "fail.png", msc.HARD_BYTES + 1)
        report = msc.scan_media(media_root)
        assert {w.path for w in report.warnings} == {"ui/warn.png"}
        assert {f.path for f in report.failures} == {"arch/fail.png"}


class TestCLI:
    def test_main_returns_0_when_clean(self, media_root, monkeypatch):
        monkeypatch.setattr(msc, "DEFAULT_MEDIA_ROOT_REL", str(media_root))
        rc = msc.main(["--root", str(media_root)])
        assert rc == 0

    def test_main_returns_1_on_failure(self, media_root):
        _write_blob(media_root / "arch" / "huge.png", msc.HARD_BYTES + 1)
        rc = msc.main(["--root", str(media_root)])
        assert rc == 1

    def test_strict_mode_treats_warning_as_failure(self, media_root):
        _write_blob(media_root / "ui" / "warn.png", msc.WARN_BYTES + 1)
        rc_normal = msc.main(["--root", str(media_root)])
        assert rc_normal == 0
        rc_strict = msc.main(["--root", str(media_root), "--strict"])
        assert rc_strict == 1

    def test_returns_2_when_root_missing(self, tmp_path):
        rc = msc.main(["--root", str(tmp_path / "does-not-exist")])
        assert rc == 2

    def test_json_output_machine_readable(self, media_root, capsys):
        _write_blob(media_root / "arch" / "huge.png", msc.HARD_BYTES + 1)
        msc.main(["--root", str(media_root), "--json"])
        captured = capsys.readouterr()
        import json as _json
        payload = _json.loads(captured.out)
        assert payload["scanned_files"] == 1
        assert payload["failures"][0]["path"] == "arch/huge.png"
