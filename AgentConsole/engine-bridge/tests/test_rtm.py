"""BR-32：`GET /autoclaude/runs/{id}/rtm`（ADR-XPLAT-016 §8.5；契約 v1.5 §3.1.4 (f)）。

唯讀、不需權杖的諮詢視圖：讀 run 工作區 `engine/checkpoints/rtm/` 最新的 `RTM-COVERAGE-*.yaml`。
前半用手寫檔釘住讀取語意（舊報告相容、最新優先、壞檔 422）；後半用真引擎的 `RtmWritebackPlugin`
產物釘住「引擎寫的形狀＝Bridge 讀的形狀」——兩邊各自改格式時，這裡會先紅。
"""
from __future__ import annotations

import copy
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml

from app import rtm
from app.errors import ApiError
from app.runstate import RunPaths, RunRecord, save_record
from tests.conftest import TERMINAL
from tests.sdd_run_support import TCS_TEXT, digest_of, post, sdd_body, seed_frozen

DIGEST = "sha256:" + "a" * 64
BASE_REPORT: dict[str, Any] = {
    "kind": "rtm-coverage", "scenario": "greenfield", "spec_digest": DIGEST,
    "summary": {"total_at": 5, "passed_at": 3, "at_coverage_pct": 60.0, "total_ac": 3,
                "covered_ac": 1, "ac_coverage_pct": 33.3, "fully_covered": False,
                "unmapped_at": 1},
    "ac_coverage": [{"ac_id": "AC-001-1", "passed_at": 2, "total_at": 2}],
    "failed_at_ids": ["AT-002-1-1"], "weak_regex_at_ids": ["AT-001-1-2"],
    "unmapped_at_ids": ["AT-9-1"],
}
BASE_BODY = {
    "scenario": "greenfield", "spec_digest": DIGEST,
    "at": {"passed": 3, "total": 5, "pct": 60.0, "unmapped": 1},
    "ac": {"covered": 1, "total": 3, "pct": 33.3},
    "failed_at_ids": ["AT-002-1-1"], "weak_regex_at_ids": ["AT-001-1-2"],
    "unmapped_at_ids": ["AT-9-1"], "fully_covered": False, "advisory": True,
}
CORE_KEYS = ["passed_at", "total_at", "at_coverage_pct", "covered_ac", "total_ac",
             "ac_coverage_pct"]


def report(**summary_over: Any) -> dict[str, Any]:
    doc = copy.deepcopy(BASE_REPORT)
    for key, value in summary_over.items():
        if value is KeyError:
            del doc["summary"][key]
        else:
            doc["summary"][key] = value
    return doc


def place_run(settings, files: dict[str, bytes | str] | None = None) -> tuple[str, Path]:
    """在工作區放一個已完成 run 的目錄（Bridge 啟動時由 reconcile 載入、不起任何引擎）；
    `files`＝要放進 `engine/checkpoints/rtm/` 的檔案。回傳 (run_id, rtm 目錄)。"""
    run_id = str(uuid.uuid4())
    paths = RunPaths(settings.engine_workspace / run_id)
    paths.run_dir.mkdir(parents=True)
    paths.playbook.write_text("tasks: []\n", encoding="utf-8", newline="\n")
    save_record(paths, RunRecord(
        run_id=run_id, project="rtm", execution_path=str(settings.engine_workspace),
        status="COMPLETED", exit_code=0, completed_at="2026-10-17T00:00:00+00:00"))
    directory = paths.checkpoints / "rtm"
    for name, content in (files or {}).items():
        directory.mkdir(parents=True, exist_ok=True)
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        (directory / name).write_bytes(data)
    return run_id, directory


def dump(doc: Any) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def set_mtime(path: Path, ns: int) -> None:
    os.utime(path, ns=(ns, ns))


# ── 200：形狀與數字 ─────────────────────────────────────────────────────────────────────────
def test_a_full_report_is_returned_in_the_contract_shape(settings, make_bridge) -> None:
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(BASE_REPORT)})
    resp = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm")
    assert resp.status_code == 200
    assert resp.json() == BASE_BODY


def test_the_endpoint_needs_no_token_even_when_the_write_surface_is_disabled(
        settings, make_bridge) -> None:
    """唯讀＝不需權杖；Bridge 沒設 BRIDGE_SDD_WRITE_TOKEN（寫入面停用）也照常讀，請求不帶任何標
    頭。"""
    assert settings.sdd_write_token is None
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(BASE_REPORT)})
    resp = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm")
    assert resp.status_code == 200 and resp.json()["advisory"] is True


def test_advisory_is_always_true_even_for_a_fully_covered_report(settings, make_bridge) -> None:
    full = report(passed_at=5, at_coverage_pct=100.0, covered_ac=3, ac_coverage_pct=100.0,
                  fully_covered=True, unmapped_at=0)
    full["failed_at_ids"], full["unmapped_at_ids"] = [], []
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(full)})
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["fully_covered"] is True and body["advisory"] is True
    assert (body["failed_at_ids"], body["unmapped_at_ids"]) == ([], [])


def test_a_report_written_before_the_unmapped_fields_existed_reads_as_zero_unmapped(
        settings, make_bridge) -> None:
    """舊報告（improving_115 之前）沒有 `summary.unmapped_at`／`unmapped_at_ids`（也沒有
    `weak_regex_at_ids`）：缺欄視為 0／[]，不是 422。"""
    old = report(unmapped_at=KeyError)
    del old["unmapped_at_ids"], old["weak_regex_at_ids"]
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(old)})
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["at"] == {"passed": 3, "total": 5, "pct": 60.0, "unmapped": 0}
    assert (body["unmapped_at_ids"], body["weak_regex_at_ids"]) == ([], [])
    assert body["failed_at_ids"] == ["AT-002-1-1"]


@pytest.mark.parametrize(("count", "ids", "expected"), [
    (2, [], 2),                        # 只有計數、沒有清單：以計數為準
    (None, ["AT-x"], 1),               # 缺計數：以清單長度為準
    (True, ["AT-x", "AT-y"], 2),       # 布林不是計數（isinstance(True, int) 是陷阱）
    ("3", ["a", "b"], 2),              # 字串不是計數
    (0, ["AT-x"], 0),                  # 兩者都在時以引擎寫的計數為準（不重算）
], ids=["count-only", "ids-only", "bool-is-not-a-count", "string-is-not-a-count", "count-wins"])
def test_unmapped_count_prefers_a_real_integer_and_falls_back_to_the_list_length(
        count: Any, ids: list[str], expected: int, settings, make_bridge) -> None:
    doc = report(unmapped_at=count)
    doc["unmapped_at_ids"] = ids
    if count is None:
        del doc["summary"]["unmapped_at"]
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(doc)})
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["at"]["unmapped"] == expected
    assert body["unmapped_at_ids"] == ids


def test_id_lists_are_coerced_to_strings_and_a_non_list_reads_as_empty(
        settings, make_bridge) -> None:
    doc = report()
    doc["failed_at_ids"] = [101, "AT-1-1-1"]
    doc["weak_regex_at_ids"] = "AT-1-1-1"            # 不是清單＝視為沒有，不拆字元
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": dump(doc)})
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["failed_at_ids"] == ["101", "AT-1-1-1"] and body["weak_regex_at_ids"] == []


# ── 多份報告：修改時間最新者；歷史與缺口檔不讀 ──────────────────────────────────────────────────
def test_the_newest_report_by_modification_time_wins_over_the_name_order(
        settings, make_bridge) -> None:
    older, newer = report(), report()
    older["scenario"], newer["scenario"] = "from-the-older-file", "from-the-newer-file"
    rid, directory = place_run(settings, {"RTM-COVERAGE-Z.yaml": dump(older),
                                          "RTM-COVERAGE-A.yaml": dump(newer)})
    set_mtime(directory / "RTM-COVERAGE-Z.yaml", 1_700_000_000_000_000_000)
    set_mtime(directory / "RTM-COVERAGE-A.yaml", 1_800_000_000_000_000_000)   # 名字排前、但較新
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["scenario"] == "from-the-newer-file"


def test_equal_modification_times_fall_back_to_the_larger_file_name(settings, make_bridge) -> None:
    first, second = report(), report()
    first["scenario"], second["scenario"] = "name-a", "name-z"
    rid, directory = place_run(settings, {"RTM-COVERAGE-A.yaml": dump(first),
                                          "RTM-COVERAGE-Z.yaml": dump(second)})
    for name in ("RTM-COVERAGE-A.yaml", "RTM-COVERAGE-Z.yaml"):
        set_mtime(directory / name, 1_800_000_000_000_000_000)
    assert make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()["scenario"] == "name-z"


def test_history_gap_and_lookalike_files_are_never_read(settings, make_bridge) -> None:
    decoys = {
        "RTM-COVERAGE-HISTORY-rtm.jsonl": '{"scenario": "history"}\n',
        "RTM-GAP-rtm.md": "# gap\n",
        "RTM-COVERAGE-rtm.yml": dump({**report(), "scenario": "wrong-extension"}),
        "notes.yaml": dump({**report(), "scenario": "wrong-prefix"}),
    }
    rid, directory = place_run(settings, {**decoys, "RTM-COVERAGE-rtm.yaml": dump(report())})
    (directory / "RTM-COVERAGE-folder.yaml").mkdir()                  # 同名的目錄不是報告
    for path in directory.iterdir():                                  # 讓誘餌全部「比真報告新」
        set_mtime(path, 1_800_000_000_000_000_000 if path.name != "RTM-COVERAGE-rtm.yaml"
                  else 1_700_000_000_000_000_000)
    body = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm").json()
    assert body["scenario"] == "greenfield"


# ── 404 ─────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("files", [
    None,                                                             # 連 rtm 目錄都沒有
    {"RTM-COVERAGE-HISTORY-rtm.jsonl": "{}\n", "RTM-GAP-rtm.md": "# gap\n"},   # 只有歷史與缺口檔
], ids=["no-rtm-directory", "only-history-and-gap"])
def test_a_run_without_a_coverage_report_is_404_rtm_not_found(
        files: dict[str, str] | None, settings, make_bridge) -> None:
    rid, _ = place_run(settings, files)
    resp = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm")
    assert (resp.status_code, resp.json()) == (404, {"code": 404, "reason": "rtm_not_found",
                                                     "run_id": rid})


def test_an_unknown_run_is_404_run_not_found_not_rtm_not_found(bridge) -> None:
    ghost = str(uuid.uuid4())
    resp = bridge.client.get(f"/autoclaude/runs/{ghost}/rtm")
    assert (resp.status_code, resp.json()["reason"], resp.json()["run_id"]) == (
        404, "run_not_found", ghost)


# ── 422 rtm_unreadable：壞檔一律結構化回報，不是 500 ────────────────────────────────────────────
BAD_FILES: list[tuple[str, bytes]] = [
    ("not-yaml", b":\n  - [unclosed"),
    ("scalar", b"just a string\n"),
    ("list", b"- 1\n- 2\n"),
    ("empty-file", b""),
    ("no-summary", b"scenario: x\n"),
    ("summary-is-a-number", b"summary: 3\n"),
    ("not-utf8", b"\xff\xfe\x00 bad bytes"),
    ("deep-nesting", b"[" * 3000 + b"]" * 3000),
    *[(f"missing-{key}", dump(report(**{key: KeyError})).encode("utf-8")) for key in CORE_KEYS],
    *[(f"passed_at-is-{label}", dump(report(passed_at=value)).encode("utf-8"))
      for label, value in (("string", "60"), ("bool", True), ("null", None), ("list", [1]))],
]


@pytest.mark.parametrize(("label", "content"), BAD_FILES, ids=[b[0] for b in BAD_FILES])
def test_a_corrupt_report_is_422_rtm_unreadable_with_a_bounded_detail(
        label: str, content: bytes, settings, make_bridge) -> None:
    rid, _ = place_run(settings, {"RTM-COVERAGE-rtm.yaml": content})
    resp = make_bridge().client.get(f"/autoclaude/runs/{rid}/rtm")
    assert resp.status_code == 422, f"{label}：{resp.text}"
    body = resp.json()
    assert (body["code"], body["reason"]) == (422, "rtm_unreadable")
    assert 0 < len(body["detail"]) <= 200, "detail 有上界（壞檔內容不會整份回灌進回應）"


def test_a_report_that_vanishes_between_listing_and_reading_is_422_not_500(tmp_path: Path) -> None:
    with pytest.raises(ApiError) as caught:
        rtm.load_report(tmp_path / "RTM-COVERAGE-gone.yaml")
    assert (caught.value.status_code, caught.value.body["reason"]) == (422, "rtm_unreadable")


def test_latest_report_on_a_missing_directory_is_none(tmp_path: Path) -> None:
    assert rtm.latest_report(tmp_path / "no-such-dir") is None


# ── 真引擎的 RtmWritebackPlugin 產物（引擎寫的形狀＝Bridge 讀的形狀）──────────────────────────────
def test_the_real_engine_report_of_a_completed_sdd_run_is_read_back(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    rid = post(sdd_live, sdd_body(run_body, sdd_proj, delay="0.2")).json()["run_id"]
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "COMPLETED"
    resp = sdd_live.client.get(f"/autoclaude/runs/{rid}/rtm")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "scenario": "greenfield", "spec_digest": digest_of(TCS_TEXT),
        "at": {"passed": 2, "total": 2, "pct": 100.0, "unmapped": 0},
        "ac": {"covered": 1, "total": 1, "pct": 100.0},
        "failed_at_ids": [], "weak_regex_at_ids": [], "unmapped_at_ids": [],
        "fully_covered": True, "advisory": True}
    # 對照引擎自己寫在磁碟上的檔：Bridge 的回應不是憑空的，兩邊的數字逐項相同
    written = sdd_live.settings.engine_workspace / rid / "engine" / "checkpoints" / "rtm"
    on_disk = yaml.safe_load((written / "RTM-COVERAGE-SddDemo.yaml").read_text(encoding="utf-8"))
    assert on_disk["summary"]["passed_at"] == resp.json()["at"]["passed"] == 2
    assert "unmapped_at_ids" in on_disk and "unmapped_at" in on_disk["summary"], \
        "引擎端（ADR §8.5）已寫出新欄位；缺了就表示 Bridge 讀的是舊引擎的格式"


def test_a_run_that_escalated_never_reaches_post_run_so_there_is_no_report(
        sdd_live, sdd_fake: Path, sdd_proj: Path, run_body) -> None:
    """引擎只在 run 正常走完時寫報告（POST_RUN 於 halt／escalate 不發）：升級失敗的 run＝404，
    不是「0% 覆蓋」——沒有報告與覆蓋為零是兩件事。"""
    seed_frozen(sdd_proj, "IMPLEMENTATION")
    body = sdd_body(run_body, sdd_proj, fail_step=2, delay="0.2")
    rid = post(sdd_live, body).json()["run_id"]
    assert sdd_live.wait_status(rid, TERMINAL)["status"] == "FAILED"
    resp = sdd_live.client.get(f"/autoclaude/runs/{rid}/rtm")
    assert (resp.status_code, resp.json()["reason"]) == (404, "rtm_not_found")
