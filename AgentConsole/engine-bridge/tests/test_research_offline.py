"""研究前置抓取的離線夾具（`app/research/offline.py`；D-78、INT-06）。

純函式單元測試：何時離線（`offline_reason`）、劇本如何宣告夾具（`fixture_file`）、夾具如何變成
`FetchBatch`（`load_batch`）與壞夾具如何 fail-loud。整合面（orchestrator 走同一條入庫路徑、
零外呼）在 `test_research_orchestrator.py` 的 `test_D_78_*`。
"""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.research.offline import (
    LAYERS,
    OfflineFixtureError,
    fixture_file,
    load_batch,
    offline_reason,
)
from app.settings import RESEARCH_DEFAULT_FETCH_ALLOWLIST, Settings

SCRIPTS = Path(__file__).resolve().parent / "fixtures" / "research" / "scripts"
ENV = "MOCK_CLAUDE_RESEARCH_SCRIPT"


# ── offline_reason：兩個觸發條件 ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("script, claude_on_path, expected", [
    ("/x/script.json", True, "script"),          # 劇本模式優先：開發機有 claude 但跑的是替身劇本
    ("/x/script.json", False, "script"),
    ("", False, "mock-only"),           # compose 預設空字串＝沒設；PATH 上沒有 claude＝mock-only
    ("  ", False, "mock-only"),
    ("", True, None),                            # 本機模式：有 claude、沒劇本＝才是真抓取
])
def test_offline_reason_follows_the_script_variable_and_the_capabilities_mode(
        settings: Settings, monkeypatch: pytest.MonkeyPatch, script: str, claude_on_path: bool,
        expected: str | None) -> None:
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: (
        f"/fake/{name}" if name in ("claude", "git") and claude_on_path
        else None if name in ("claude", "git") else real_which(name, *a, **k)))
    assert offline_reason(settings, {ENV: script}) == expected
    if script.strip() == "":
        assert offline_reason(settings, {}) == expected, "變數不存在與空字串同義"


def test_offline_reason_reads_the_process_environment_by_default(
        settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "/x/script.json")
    assert offline_reason(settings) == "script"
    monkeypatch.delenv(ENV)
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    assert offline_reason(settings) == "mock-only"


# ── fixture_file：劇本宣告 ──────────────────────────────────────────────────────────────────
def write_script(tmp_path: Path, **top: Any) -> Path:
    path = tmp_path / "script.json"
    path.write_text(json.dumps({"schema": 1, "steps": [], **top}), encoding="utf-8")
    return path


def test_fixture_file_is_resolved_relative_to_the_script_directory(tmp_path: Path) -> None:
    script = write_script(tmp_path, prefetch="content/pf.json")
    assert fixture_file({ENV: str(script)}) == tmp_path / "content" / "pf.json"
    assert fixture_file({ENV: str(write_script(tmp_path))}) is None, "劇本沒宣告＝沒有夾具"
    assert fixture_file({}) is None and fixture_file({ENV: ""}) is None, "沒有劇本＝沒有夾具"


@pytest.mark.parametrize("declared", ["../outside.json", "/abs/path.json", "C:/abs.json",
                                      "", "   ", 5, ["x"]])
def test_an_unsafe_or_malformed_declaration_is_refused(tmp_path: Path, declared: Any) -> None:
    script = write_script(tmp_path, prefetch=declared)
    with pytest.raises(OfflineFixtureError):
        fixture_file({ENV: str(script)})


def test_an_unreadable_or_invalid_script_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OfflineFixtureError):
        fixture_file({ENV: str(tmp_path / "missing.json")})
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(OfflineFixtureError):
        fixture_file({ENV: str(broken)})
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"schema": 2, "steps": []}), encoding="utf-8")
    with pytest.raises(OfflineFixtureError):
        fixture_file({ENV: str(wrong)})


# ── load_batch ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_is_an_empty_batch_that_reads_as_no_evidence() -> None:
    batch = load_batch(None)
    assert (batch.planned, batch.records, batch.sources, batch.skipped) == (0, [], [], [])
    assert batch.no_sources is True and batch.exit_reason == "no_evidence"


@pytest.mark.parametrize("script", sorted(SCRIPTS.glob("mock_claude_script_*.json")),
                         ids=lambda p: p.stem)
def test_every_shipped_script_declares_a_well_formed_fixture(script: Path) -> None:
    """夾具與劇本是成對交付的：每支劇本都宣告一份讀得進來的夾具；抓取紀錄是 OK／API／BRIDGE、網址是
    https、主機都在部署基底清單內（真實形狀但從不連線）、每個候選指向存在的抓取紀錄。"""
    path = fixture_file({ENV: str(script)})
    assert path is not None and path.is_file(), script.name
    batch = load_batch(path)
    assert batch.sources and batch.records and batch.planned == len(batch.records)
    for record in batch.records:
        assert (record.outcome, record.fetch_method, record.observed_by) == ("OK", "API", "BRIDGE")
        assert record.url.startswith("https://") and record.host in RESEARCH_DEFAULT_FETCH_ALLOWLIST
        assert record.layer in LAYERS and record.http_status == 200 and record.raw_text
        assert record.raw_bytes == len(record.raw_text.encode("utf-8"))
        assert record.raw_rel_path == f"00_research/raw/{record.raw_sha256[:12]}.txt"
    for bundle in batch.sources:
        assert bundle.source["url"].startswith("https://") and bundle.records[0] in batch.records
        assert "fetch" not in bundle.source, "夾具的 fetch 參照不進候選來源列"


GOOD: dict[str, Any] = json.loads((SCRIPTS / "content" / "prefetch_pass.json").read_text(
    encoding="utf-8"))


def mutated(edit: Any) -> dict[str, Any]:
    doc = copy.deepcopy(GOOD)
    edit(doc)
    return doc


BAD_FIXTURES = {
    "wrong schema": lambda d: d.update(schema=2),
    "not an object list": lambda d: d.update(fetches=["x"]),
    "fetches not a list": lambda d: d.update(fetches={}),
    "duplicate fetch id": lambda d: d["fetches"][1].update(id=d["fetches"][0]["id"]),
    "fetch without id": lambda d: d["fetches"][0].pop("id"),
    "fetch without text": lambda d: d["fetches"][0].pop("text"),
    "fetch with empty text": lambda d: d["fetches"][0].update(text="  "),
    "fetch with a non-https url": lambda d: d["fetches"][0].update(url="http://export.arxiv.org/x"),
    "fetch with a mock scheme": lambda d: d["fetches"][0].update(url="mock://fixture/1"),
    "unknown layer": lambda d: d["fetches"][0].update(layer="BLOG"),
    "status not an int": lambda d: d["fetches"][0].update(http_status="200"),
    "status is a bool": lambda d: d["fetches"][0].update(http_status=True),
    "query not a string": lambda d: d["fetches"][0].update(query=5),
    "source points nowhere": lambda d: d["sources"][0].update(fetch="nope"),
    "source without a title": lambda d: d["sources"][0].pop("title"),
    "source without a tier": lambda d: d["sources"][0].pop("tier"),
    "source with a non-https url": lambda d: d["sources"][0].update(url="http://arxiv.org/abs/1"),
}


@pytest.mark.parametrize("label", sorted(BAD_FIXTURES))
def test_a_malformed_fixture_is_refused_loudly(tmp_path: Path, label: str) -> None:
    path = tmp_path / "pf.json"
    path.write_text(json.dumps(mutated(BAD_FIXTURES[label])), encoding="utf-8")
    with pytest.raises(OfflineFixtureError):
        load_batch(path)


def test_an_unreadable_or_non_json_fixture_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OfflineFixtureError):
        load_batch(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(OfflineFixtureError):
        load_batch(broken)
    listy = tmp_path / "list.json"
    listy.write_text("[]", encoding="utf-8")
    with pytest.raises(OfflineFixtureError):
        load_batch(listy)


def test_zero_sources_with_recorded_fetches_still_reads_as_no_evidence(tmp_path: Path) -> None:
    doc = mutated(lambda d: d.update(sources=[]))
    path = tmp_path / "pf.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    batch = load_batch(path)
    assert len(batch.records) == 2 and batch.sources == []
    assert batch.exit_reason == "no_evidence", "有抓取紀錄但沒有候選來源＝沒有可用證據"
